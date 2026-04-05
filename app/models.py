import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import now
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver
from datetime import timedelta
from decimal import Decimal

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

# 3. PRODUCT (Updated with per-product shipping)
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    discount = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    # NEW FIELD: Individual shipping fee for this specific item
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    specifications = models.TextField(blank=True)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
   
    # ... your existing fields (name, price, etc.) ...
    short_description = models.TextField(
        max_length=300, 
        blank=True, 
        null=True, 
        help_text="A brief catchy description (max 300 characters)."
    )
    

    discount_duration_hours = models.PositiveIntegerField(default=0)
    discount_start_time = models.DateTimeField(null=True, blank=True)

    @property
    def is_on_sale(self):
        if self.discount > 0 and self.discount_start_time and self.discount_duration_hours > 0:
            expiry_time = self.discount_start_time + timedelta(hours=self.discount_duration_hours)
            return timezone.now() < expiry_time
        return False
        
    @property
    def discount_expiry(self):
        if self.discount_start_time and self.discount_duration_hours:
            return self.discount_start_time + timedelta(hours=self.discount_duration_hours)
        return None

    @property
    def discounted_price(self):
        if self.is_on_sale and self.discount > 0:
            return self.price * (1 - self.discount / 100)
        return self.price

    @property
    def final_price(self):
        return self.discounted_price

    def __str__(self):
        return self.name

# 4. PRODUCT IMAGES
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    views = models.IntegerField(default=0)
    class Meta:
        ordering = ['id']

# 5. CART SYSTEM
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=now)
    session_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product')

# 6. ORDERS & TRACKING (Updated with Max Shipping Logic)
class Order(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('STK_Sent', 'STK Push Sent'), ('Paid', 'Paid'), ('Failed', 'Failed')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    destination = models.CharField(max_length=255)
    
    region = models.CharField(max_length=20, default="nairobi") # 'nairobi' or 'upcountry'
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
        """Finds the highest shipping fee in the cart for Upcountry orders."""
        if self.region.lower() == "nairobi":
            return Decimal('0.00')
        
        items = self.items.all()
        if items.exists():
            # Get the max shipping_fee from all products in this order
            fees = [item.product.shipping_fee for item in items]
            return max(fees)
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        # We save once to ensure the ID exists if it's a new order
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order {self.id} - {self.name}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def get_total(self):
        return self.price * self.quantity

# 7. ANALYTICS (Activity tracking remains same)
class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra_info = models.TextField(blank=True, null=True)

# 8. SITE SETTINGS
class SiteSettings(models.Model):
    shipping_fee_nairobi = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discounts_active = models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = "Site Settings"
class ProductView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']
        # Ensure we don't have duplicate records for the same user-product combination
        unique_together = ('user', 'product')  # This enforces the uniqueness of user-product combination

    def __str__(self):
        return f"{self.user.username} viewed {self.product.name}"