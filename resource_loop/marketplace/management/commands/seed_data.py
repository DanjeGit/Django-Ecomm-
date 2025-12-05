import random
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify

from marketplace.models import Category, WasteItem, SellerProfile
from django.conf import settings


class Command(BaseCommand):
    help = "Seed the database with dummy categories, sellers, and items using three random images"

    def add_arguments(self, parser):
        parser.add_argument('--items', type=int, default=18, help='Number of items to create')
        parser.add_argument('--force', action='store_true', help='Create items even if some already exist')

    def handle(self, *args, **options):
        items_target = options['items']
        force = options['force']

        # Prepare three images from static folder
        base_dir = Path(settings.BASE_DIR)
        static_img_dir = base_dir / 'static' / 'img'
        candidate_images = [
            static_img_dir / 'metal.jpg',
            static_img_dir / 'textile.jpg',
            static_img_dir / 'wood.jpg',
        ]
        available_images = [p for p in candidate_images if p.exists()]
        if len(available_images) < 1:
            self.stdout.write(self.style.WARNING('No seed images found in static/img (expected metal.jpg, textile.jpg, wood.jpg). Proceeding without images.'))

        # Create categories
        categories = [
            ('Metals', 'fa-industry'),
            ('Electronics', 'fa-laptop'),
            ('Plastics', 'fa-bottle-water'),
            ('Textiles', 'fa-shirt'),
            ('Wood', 'fa-tree'),
        ]
        category_objs = []
        for name, icon in categories:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'icon_class': icon})
            category_objs.append(cat)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(category_objs)} categories'))

        # Create seller users and profiles
        sellers_seed = [
            dict(username='seller1', email='seller1@example.com', business_name='Green Metals Ltd'),
            dict(username='seller2', email='seller2@example.com', business_name='Urban E-Waste Co'),
            dict(username='seller3', email='seller3@example.com', business_name='Kenya Tech Refurbs'),
        ]
        seller_profiles = []
        for s in sellers_seed:
            user, created = User.objects.get_or_create(
                username=s['username'],
                defaults={'email': s['email']}
            )
            if created:
                user.set_password('password123')
                user.save()
            sp, _ = SellerProfile.objects.get_or_create(user=user, defaults={
                'business_name': s['business_name'],
                'is_verified': random.choice([True, False])
            })
            seller_profiles.append(sp)
        self.stdout.write(self.style.SUCCESS(f'Ensured {len(seller_profiles)} seller profiles'))

        # If not forcing and items already present, only top up to target
        existing = WasteItem.objects.count()
        if existing >= items_target and not force:
            self.stdout.write(self.style.WARNING(f'{existing} items already exist; use --force or lower --items to add more.'))
            return

        items_to_create = max(0, items_target - existing) if not force else items_target

        titles = [
            'Mixed Scrap Metal Batch', 'High-Grade Copper Wire', 'Aluminum Casing Offcuts',
            'E-Waste Motherboards', 'Used Laptop Batteries', 'LCD Screen Panels (Assorted)',
            'Plastic Pellets Regrind', 'PET Bottles Baled', 'HDPE Caps Bulk',
            'Textile Offcuts (Cotton)', 'Denim Scraps Bundle', 'Mixed Fabric Rolls',
            'Seasoned Hardwood Pallets', 'Pine Offcuts', 'Reclaimed Timber Boards',
            'Server Rack Parts', 'Network Switches (Used)', 'Computer Fans Lot'
        ]
        conditions = ['new', 'refurbished', 'used', 'scrap']
        locations = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika', 'Nyeri']

        created_count = 0
        for i in range(items_to_create):
            title = random.choice(titles)
            seller = random.choice(seller_profiles)
            category = random.choice(category_objs)
            price = round(random.uniform(500, 50000), 2)
            old_price = price + round(random.uniform(100, 10000), 2) if random.choice([True, False]) else None
            condition = random.choice(conditions)
            location = random.choice(locations)
            stock_quantity = f"{random.randint(1, 50)} units"
            co2_saved = round(random.uniform(1.0, 500.0), 2)
            rating = round(random.uniform(3.5, 5.0), 1)
            reviews = random.randint(0, 200)
            is_flash = random.choice([True, False, False])

            # Compose a unique slug to bypass model's seller.username reference
            base_slug = slugify(f"{title}-{seller.user.username}-{random.randint(1000,9999)}")

            item = WasteItem(
                seller=seller,
                category=category,
                title=title,
                slug=base_slug,
                description=f"Bulk lot: {title}. Suitable for recycling or refurbishment.",
                specifications="Weight: ~10-100kg; Purity varies; Packaging: Bags/Boxes",
                price=price,
                old_price=old_price,
                stock_quantity=stock_quantity,
                condition=condition,
                location=location,
                is_verified_seller=seller.is_verified,
                is_flash_sale=is_flash,
                co2_saved_kg=co2_saved,
                rating=rating,
                reviews_count=reviews,
            )

            # Attach image from one of the available three
            if available_images:
                img_path = random.choice(available_images)
                # Save a copy into MEDIA_ROOT/items/
                with img_path.open('rb') as f:
                    item.image.save(img_path.name, File(f), save=False)

            item.save()
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} new items (total now {WasteItem.objects.count()}).'))
