from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
import uuid
import random

class ShippingConfiguration(models.Model):
    same_county_fee = models.DecimalField(max_digits=10, decimal_places=2, default=200.00, help_text="Fee when buyer and seller are in the same county")
    different_county_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, help_text="Fee when buyer and seller are in different counties")
    standard_fee = models.DecimalField(max_digits=10, decimal_places=2, default=300.00, help_text="Default fee when location is unknown")

    class Meta:
        verbose_name = "Shipping Configuration"
        verbose_name_plural = "Shipping Configuration"

    def __str__(self):
        return "Shipping Rates"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def is_valid(self):
        # Valid for 5 minutes
        return not self.is_used and (timezone.now() - self.created_at).total_seconds() < 300

    def __str__(self):
        return f"OTP for {self.user.username}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

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
    county = models.CharField(max_length=100, blank=True, null=True)
    sub_county = models.CharField(max_length=100, blank=True, null=True)

    
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
            self.slug = slugify(f"{self.title}-{self.seller.user.username}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        return reverse('item_detail', args=[self.slug])

    @property
    def stock_int(self):
        try:
            return int(float(self.stock_quantity))
        except (ValueError, TypeError):
            return 0

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

class PickupStation(models.Model):
    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100)
    address = models.TextField(help_text="Detailed address or landmarks")
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=200.00, help_text="Cost to ship to this station")
    
    def __str__(self):
        return f"{self.name} - {self.sub_county} (KSh {self.shipping_fee})"

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyerprofile')
    phone_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    sub_county = models.CharField(max_length=100, blank=True, null=True)
    pickup_station = models.ForeignKey(PickupStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='buyers')

    def __str__(self):
        return f"Profile of {self.user.username}"

class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sellerprofile')
    business_name = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    payment_number = models.CharField(max_length=20, blank=True, help_text="M-Pesa number for receiving payments")
    county = models.CharField(max_length=100, blank=True, null=True)
    sub_county = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to='seller_profiles/', blank=True, null=True)
    description = models.TextField(blank=True, help_text="About the seller")

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
    # STK identifiers to prevent duplication and link callbacks
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True, help_text="M-Pesa Receipt Number (e.g. QKH1234567)")
    # Link transaction to an order created at initiation
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['order', 'checkout_request_id'], name='uniq_order_checkout_tx')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.state}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('payment_pending', 'Payment Pending'),
        ('confirmed', 'Confirmed'),
        ('placed', 'Placed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel', 'Airtel Money'),
        ('card', 'Credit/Debit Card'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='placed')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    pickup_station = models.ForeignKey(PickupStation, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Public unique identifier for mapping/orders tracking
    order_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(WasteItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.item.title if self.item else 'Item'} x{self.quantity}"

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject} - {self.email}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
