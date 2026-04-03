import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import now
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import pre_save
from django.dispatch import receiver

# 1. DEFINE BRAND FIRST (Consolidated with Logo field)
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

# 2. DEFINE CATEGORY
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# 3. DEFINE PRODUCT
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    specifications = models.TextField(blank=True)
    views = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount_expiry = models.DateTimeField(null=True, blank=True)

    @property
    def is_on_sale(self):
        if self.discount_expiry and self.discount_expiry > timezone.now():
            return True
        return False

    @property
    def discounted_price(self):
        if self.discount > 0:
            return self.price - (self.price * self.discount / 100)
        return self.price

    def __str__(self):
        return self.name

# 4. PRODUCT IMAGES (GALLERY)
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

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

# 6. ORDERS & TRACKING
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('STK_Sent', 'STK Push Sent'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    destination = models.CharField(max_length=255)
    
    region = models.CharField(max_length=20, default="nairobi")
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

    def __str__(self):
        return f'Order {self.id} - {self.name}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

# 7. ANALYTICS & ACTIVITY
class ProductView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

class UserActivity(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('VIEW', 'Viewed Product'),
        ('CART', 'Added to Cart'),
        ('CHECKOUT', 'Checkout Attempt'),
        ('PAYMENT', 'Payment Attempt'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    extra_info = models.TextField(blank=True)


# --- AUTOMATION: LOGO GENERATOR SIGNAL ---
@receiver(pre_save, sender=Brand)
def auto_assign_brand_logo(sender, instance, **kwargs):
    """
    Looks into media/brand_master_assets/ for a file named after the brand.
    Example: 'Samsung' -> 'media/brand_master_assets/samsung.png'
    """
    if not instance.logo:
        brand_slug = slugify(instance.name)
        # Check if a matching PNG exists in your master folder
        relative_path = f'brand_master_assets/{brand_slug}.png'
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        if os.path.exists(absolute_path):
            instance.logo = relative_path