import os
from decimal import Decimal
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import now

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

# 1. BRAND
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name


# 2. CATEGORY
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


# 3. PRODUCT
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # percentage
    shipping_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    short_description = models.TextField(max_length=300, blank=True, null=True)
    specifications = models.TextField(blank=True, null=True)

    discount_duration_hours = models.PositiveIntegerField(default=0)
    discount_start_time = models.DateTimeField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)
    slug = models.SlugField(unique=True, blank=True, null=True)
    @property
    def is_out_of_stock(self):
        return self.stock <= 0

    # -------------------------------
    # Discount Calculations
    # -------------------------------
    @property
    def discount_expiry(self):
        if self.discount_start_time and self.discount_duration_hours:
            return self.discount_start_time + timedelta(hours=self.discount_duration_hours)
        return None
    def get_absolute_url(self):
        # We use 'pk' here because your path('products/<int:pk>/'...) 
        # specifically looks for an integer Primary Key.
        return reverse('product_detail', kwargs={'pk': self.pk})

    @property
    def is_discount_active(self):
        """Returns True if discount is currently active."""
        expiry = self.discount_expiry
        if expiry:
            return timezone.now() < expiry
        return False

    @property
    def discounted_price(self):
        """Calculates price after discount (Python-safe)."""
        if self.discount and self.discount > 0 and self.is_discount_active:
            return self.price * (Decimal('1.0') - (self.discount / Decimal('100')))
        return self.price

    @property
    def final_price(self):
        return self.discounted_price

    def savings(self):
        return self.price - self.discounted_price if self.discounted_price < self.price else Decimal('0.00')

    def update_discount_status(self):
        """Reset discount if expired."""
        if self.discount_expiry and timezone.now() > self.discount_expiry:
            self.discount = Decimal('0.00')
            self.save()

    def __str__(self):
        return self.name


# 4. PRODUCT IMAGES
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} Image"


# 5. CART SYSTEM
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=now)
    session_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"


# 6. ORDERS & TRACKING
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('STK_Sent', 'STK Push Sent'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    destination = models.CharField(max_length=255)
    region = models.CharField(max_length=20, default="nairobi")  # 'nairobi' or 'upcountry'
    location_area = models.CharField(max_length=255, default="N/A")
    address = models.TextField(default="")
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, default="mpesa")
    payment_status = models.CharField(max_length=50, default="Pending")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_shipping(self):
        """Max shipping fee for Upcountry orders."""
        if self.region.lower() == "nairobi":
            return Decimal('0.00')
        items = self.items.all()
        if items.exists():
            return max(item.product.shipping_fee for item in items)
        return Decimal('0.00')

    def __str__(self):
        return f"Order {self.id} - {self.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def get_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# 7. ANALYTICS
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.action}"


# 8. SITE SETTINGS
class SiteSettings(models.Model):
    shipping_fee_nairobi = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discounts_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"


# 9. PRODUCT VIEWS
class ProductView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"
    
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User


class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp}"

from django.db import models
from django.utils import timezone
from datetime import timedelta


class SignupOTP(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=255)  # temporarily store raw password
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return self.email