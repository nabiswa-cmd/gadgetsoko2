from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    

class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=4,decimal_places=2,default=0)
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    
    specifications = models.TextField(blank=True)
    views = models.IntegerField(default=0)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)

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
        return self.price - (self.price * self.discount / 100)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    views = models.IntegerField(default=0)
    class Meta :
        ordering = ['id'] 


# CART (SIMPLIFIED — WORKS WITH YOUR CURRENT SYSTEM)
class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=now)

    class Meta:
        unique_together = ('user', 'product')  # prevents duplicates

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    
    # --- UPDATED FIELDS ---
    region = models.CharField(max_length=20, default="nairobi") # 'nairobi' or 'outside'
    location_area = models.CharField(max_length=255, default="N/A") # Estate name or Town
    address = models.TextField(default="") # Specific house/office details
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, default="mpesa") # mpesa, equity, pochi, pod
    # ----------------------
    destination = models.CharField(max_length=255, default="N/A")
    payment_status = models.CharField(max_length=50, default="Pending")
    

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('STK_Sent', 'STK Push Sent'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]
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

    @property
    def total(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
    
# models.py
from django.contrib.auth.models import User

class ProductView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewed_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.email} viewed {self.product.name}"
    
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

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.timestamp}"