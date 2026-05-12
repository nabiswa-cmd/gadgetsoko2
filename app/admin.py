from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Product, ProductImage, Order,
    OrderItem, CartItem, ProductView, Brand,
    SiteSettings, UserProfile, UserActivity,
    EmailOTP, SignupOTP
)


# ─────────────────────────────────────────────────────────────────
# BRAND
# ─────────────────────────────────────────────────────────────────
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand_logo_preview')

    def brand_logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit:contain;border-radius:4px;">',
                obj.logo.url
            )
        return "—"
    brand_logo_preview.short_description = 'Logo'


# ─────────────────────────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


# ─────────────────────────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────────────────────────
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" '
                'style="object-fit:cover;border-radius:6px;">',
                obj.image.url
            )
        return "—"
    image_preview.short_description = 'Preview'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'product_image_preview', 'name', 'brand', 'category',
        'price', 'discount', 'discounted_price_display',
        'stock', 'discount_start_time'
    )
    list_filter = ('category', 'brand')
    search_fields = ('name',)
    list_editable = ('price', 'discount', 'stock', 'discount_start_time')
    inlines = [ProductImageInline]
    readonly_fields = ('main_image_preview',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'brand', 'category', 'slug', 'short_description', 'specifications')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'discount', 'shipping_fees', 'stock')
        }),
        ('Discount Schedule', {
            'fields': ('discount_start_time', 'discount_duration_hours')
        }),
        ('Main Image', {
            'fields': ('image', 'main_image_preview')
        }),
    )

    def product_image_preview(self, obj):
        # Show first available image — main image or first gallery image
        img_url = None
        if obj.image:
            img_url = obj.image.url
        else:
            first = obj.images.first()
            if first:
                img_url = first.image.url
        if img_url:
            return format_html(
                '<img src="{}" width="55" height="55" '
                'style="object-fit:cover;border-radius:6px;'
                'border:1px solid #e2e8f0;">',
                img_url
            )
        return "—"
    product_image_preview.short_description = '📷'

    def main_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="120" height="120" '
                'style="object-fit:cover;border-radius:8px;">',
                obj.image.url
            )
        return "No image uploaded"
    main_image_preview.short_description = 'Current Image'

    def discounted_price_display(self, obj):
        dp = obj.discounted_price
        if dp < obj.price:
            return format_html(
                '<span style="color:#16a34a;font-weight:bold;">KSh {}</span>',
                f"{dp:,.2f}"
            )
        return f"KSh {dp:,.2f}"
    discounted_price_display.short_description = 'Sale Price'


# ─────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total',)

    def line_total(self, obj):
        return f"KSh {obj.price * obj.quantity:,.2f}"
    line_total.short_description = 'Line Total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'region', 'status', 'payment_status', 'total_display', 'created_at')
    list_filter = ('status', 'payment_status', 'region', 'created_at')
    search_fields = ('name', 'phone', 'email', 'mpesa_receipt')
    readonly_fields = ('created_at', 'checkout_request_id', 'mpesa_receipt')
    inlines = [OrderItemInline]

    def total_display(self, obj):
        return f"KSh {obj.total:,.2f}"
    total_display.short_description = 'Total'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'line_total')
    list_filter = ('order__status',)
    search_fields = ('product__name',)

    def line_total(self, obj):
        return f"KSh {obj.price * obj.quantity:,.2f}"
    line_total.short_description = 'Total'


# ─────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'added_at')
    search_fields = ('user__username', 'product__name')


# ─────────────────────────────────────────────────────────────────
# USER PROFILE
# ─────────────────────────────────────────────────────────────────
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('avatar_preview', 'user', 'user_email', 'phone', 'region', 'nairobi_area')
    search_fields = ('user__username', 'user__email', 'phone')
    list_filter = ('region',)
    readonly_fields = ('avatar_preview_large',)

    fieldsets = (
        ('Account', {
            'fields': ('user', 'avatar', 'avatar_preview_large', 'phone')
        }),
        ('Delivery Address', {
            'fields': ('region', 'nairobi_area', 'upcountry_county', 'upcountry_town', 'address_notes')
        }),
    )

    def avatar_preview(self, obj):
        url = obj.get_avatar_url()
        if url:
            return format_html(
                '<img src="{}" width="40" height="40" '
                'style="border-radius:50%;object-fit:cover;'
                'border:2px solid #f4330c;">',
                url
            )
        # Fallback: initial circle
        initial = (obj.user.username[0] if obj.user.username else "?").upper()
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;'
            'background:linear-gradient(135deg,#f4330c,#ff8c00);'
            'display:flex;align-items:center;justify-content:center;'
            'color:#fff;font-weight:900;font-size:16px;">{}</div>',
            initial
        )
    avatar_preview.short_description = '👤'

    def avatar_preview_large(self, obj):
        url = obj.get_avatar_url()
        if url:
            return format_html(
                '<img src="{}" width="100" height="100" '
                'style="border-radius:50%;object-fit:cover;'
                'border:3px solid #f4330c;">',
                url
            )
        return "No avatar uploaded"
    avatar_preview_large.short_description = 'Current Avatar'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


# ─────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────
@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'product', 'viewed_at')
    list_filter = ('viewed_at', 'product')
    search_fields = ('user__email', 'product__name')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Email'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'product', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username',)


# ─────────────────────────────────────────────────────────────────
# OTP MODELS
# ─────────────────────────────────────────────────────────────────
@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'created_at')
    search_fields = ('email',)


@admin.register(SignupOTP)
class SignupOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'otp', 'created_at')
    search_fields = ('email', 'username')


# ─────────────────────────────────────────────────────────────────
# SITE SETTINGS (singleton — no add permission if one exists)
# ─────────────────────────────────────────────────────────────────
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()