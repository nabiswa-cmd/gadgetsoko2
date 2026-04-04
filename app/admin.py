from django.contrib import admin
from .models import (
    Category, Product, ProductImage, Order, 
    OrderItem, CartItem, ProductView, Brand
)

# --- BRAND ---
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')

# --- CATEGORY ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

# --- PRODUCT INLINE ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4

# --- PRODUCT ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'discount', 'get_discounted_price', 'stock')
    list_filter = ('category', 'brand')
    search_fields = ('name',)
    list_editable = ('price', 'discount', 'stock')
    inlines = [ProductImageInline]

    def get_discounted_price(self, obj):
        return obj.discounted_price
    get_discounted_price.short_description = 'Sale Price'

# --- ORDER ITEMS ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # To show total inside the inline
    readonly_fields = ('get_item_total',)
    
    def get_item_total(self, obj):
        return obj.total
    get_item_total.short_description = 'Line Total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_order_total', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [OrderItemInline]

    def get_order_total(self, obj):
        return obj.total
    get_order_total.short_description = 'Order Total'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    # This was the specific line causing your error
    list_display = ('order', 'product', 'quantity', 'price', 'get_total')
    list_filter = ('order', 'product')

    def get_total(self, obj):
        return obj.total
    get_total.short_description = 'Total'

# --- CART ---
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'added_at')

# --- ANALYTICS ---
@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'product', 'viewed_at')
    list_filter = ('viewed_at', 'product')
    search_fields = ('user__email', 'product__name')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Gmail'

# admin.py
from django.contrib import admin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    # Prevent the admin from creating multiple settings objects
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()