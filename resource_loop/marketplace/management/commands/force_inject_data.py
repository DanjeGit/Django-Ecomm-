from django.core.management.base import BaseCommand
from marketplace.models import Category, PickupStation, ShippingConfiguration
from marketplace.locations import KENYA_LOCATIONS
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Force injects static data (Categories, PickupStations, ShippingConfig) into the database'

    def handle(self, *args, **options):
        self.stdout.write('Starting data injection...')

        # 1. Shipping Configuration
        config, created = ShippingConfiguration.objects.get_or_create(pk=1)
        config.same_county_fee = 200.00
        config.different_county_fee = 500.00
        config.standard_fee = 300.00
        config.save()
        self.stdout.write(self.style.SUCCESS(f'Shipping Configuration updated.'))

        # 2. Categories
        categories = [
            {"name": "Electronics", "icon_class": "fa-laptop"},
            {"name": "Plastics", "icon_class": "fa-bottle-water"},
            {"name": "Metals", "icon_class": "fa-gears"},
            {"name": "Paper", "icon_class": "fa-newspaper"},
            {"name": "Glass", "icon_class": "fa-wine-bottle"},
            {"name": "Organic", "icon_class": "fa-leaf"},
            {"name": "Textiles", "icon_class": "fa-shirt"},
        ]

        for cat_data in categories:
            cat, created = Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "slug": slugify(cat_data["name"]),
                    "icon_class": cat_data["icon_class"]
                }
            )
            if created:
                self.stdout.write(f'Created Category: {cat.name}')
            else:
                self.stdout.write(f'Category already exists: {cat.name}')

        # 3. Pickup Stations from KENYA_LOCATIONS
        self.stdout.write('Generating Pickup Stations from KENYA_LOCATIONS...')
        
        count_created = 0
        for county, sub_counties in KENYA_LOCATIONS.items():
            for sub_county in sub_counties:
                # Create a station name like "Nairobi - Westlands Station"
                station_name = f"{county} - {sub_county} Station"
                
                station, created = PickupStation.objects.get_or_create(
                    name=station_name,
                    defaults={
                        "county": county,
                        "sub_county": sub_county,
                        "address": f"{sub_county} Center, {county}", # Generic address
                        "shipping_fee": 250.00 # Default fee
                    }
                )
                if created:
                    count_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Finished processing stations. Created {count_created} new stations.'))
        self.stdout.write(self.style.SUCCESS('Data injection complete!'))
