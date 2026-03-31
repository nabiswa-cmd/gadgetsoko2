from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem, CartItem,ProductView
from .models import Brand

admin.site.register(Brand)

# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

# Product Image Inline
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4

# Product Admin (ONLY ONE)
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name','brand', 'category', 'price', 'discount', 'discounted_price', 'stock')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('price', 'discount', 'stock')
    ordering = ('name',)
    inlines = [ProductImageInline]

# Order Admin
from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    inlines = [OrderItemInline]


admin.site.register(Order, OrderAdmin)

# OrderItem Admin
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total')
    list_filter = ('order', 'product')

# CartItem Admin
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'added_at')
    list_filter = ('user', 'product')

@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    # This lets you see the Gmail, Product Name, and Time at a glance
    list_display = ('user_email', 'product', 'viewed_at')
    list_filter = ('viewed_at', 'product')
    search_fields = ('user__email', 'product__name')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Gmail'