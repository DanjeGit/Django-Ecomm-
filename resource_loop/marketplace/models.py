from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    icon_class = models.CharField(max_length=50, default="fa-recycle", help_text="FontAwesome class (e.g., fa-laptop)")
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class WasteItem(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New / Surplus'),
        ('refurbished', 'Refurbished / Grade A'),
        ('used', 'Used / Good'),
        ('scrap', 'Scrap / Recyclable'),
    ]

    seller = models.ForeignKey('SellerProfile', on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(help_text="Detailed description of the item")
    specifications = models.TextField(blank=True, help_text="Technical specs (e.g., Weight: 5kg, Purity: 99%)")
    
    # Pricing & Stock
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Price in KES")
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_quantity = models.CharField(max_length=10, default="1", help_text="Available quantity (e.g., 10 units, 5 tons)")
    
    # Categorization
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='used')
    location = models.CharField(max_length=100, default="Kenya", help_text="Location of the item")

    
    # Visuals & Trust
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    is_verified_seller = models.BooleanField(default=False)
    is_flash_sale = models.BooleanField(default=False)
    
    # Impact
    co2_saved_kg = models.FloatField(default=0.0, verbose_name="CO2 Saved (kg)")
    
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    reviews_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.seller.username}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        return reverse('item_detail', args=[self.slug])

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        return sum(item.item.price * item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(WasteItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.title} in cart"

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyerprofile')
    phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sellerprofile')
    business_name = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.business_name


class Transaction(models.Model):
    STATE_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    mpesa_name = models.CharField(max_length=255, help_text="Payer's MPESA name")
    phone_number = models.CharField(max_length=20, help_text="MPESA phone number used to pay")
    item = models.ForeignKey(WasteItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.item.title if self.item else 'Item'} - {self.amount}"