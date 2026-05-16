# vape_cluster/admin.py
# Django admin configuration for the Vape Cluster e-commerce platform
# Registers all models with proper admin classes for MySQL database

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils import timezone
from .models import (
    CustomUser,
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
    ELiquid,
    VapeDevice,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Payment,
    Blog,
    BlogCategory,
    BlogTag,
    BlogComment,
    ContactMessage,
    Newsletter,
    Review,
    Coupon,
    CouponUsage,
    AgeVerification,
    Banner,
    Wishlist,
    WishlistItem,
    ShippingAddress,
    Notification,
    SiteSettings,
)


# ─────────────────────────────────────────────
# Inline Admin Classes
# ─────────────────────────────────────────────

class ProductImageInline(admin.TabularInline):
    """Inline for managing multiple product images on the Product admin page"""
    model = ProductImage
    extra = 3  # Show 3 empty image upload slots by default
    fields = ('image', 'alt_text', 'is_primary', 'order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """Show a small thumbnail preview of uploaded image"""
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px; width:auto; border-radius:4px;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = "Preview"


class ProductVariantInline(admin.TabularInline):
    """Inline for managing product variants (color, size, nicotine strength etc.)"""
    model = ProductVariant
    extra = 2
    fields = ('name', 'value', 'sku', 'price_modifier', 'stock', 'is_available')


class OrderItemInline(admin.TabularInline):
    """Inline to show order line items within the Order admin page"""
    model = OrderItem
    extra = 0  # Don't show empty rows for order items
    readonly_fields = ('product', 'variant', 'quantity', 'unit_price', 'subtotal')
    can_delete = False  # Prevent accidental deletion of order items

    def subtotal(self, obj):
        """Calculate and display item subtotal"""
        return f"Rs. {obj.quantity * obj.unit_price:,.2f}"
    subtotal.short_description = "Subtotal"


class CartItemInline(admin.TabularInline):
    """Inline to show cart items within Cart admin"""
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'added_at')
    can_delete = True


class ProductImageGalleryInline(admin.StackedInline):
    """Stacked inline for product gallery with larger previews"""
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:120px; width:auto; border-radius:6px; '
                'box-shadow: 0 2px 6px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return "No Image Uploaded"
    image_preview.short_description = "Image Preview"


class BlogTagInline(admin.TabularInline):
    """Inline for managing tags on a blog post"""
    model = Blog.tags.through  # Many-to-many through table
    extra = 2
    verbose_name = "Tag"
    verbose_name_plural = "Tags"


class WishlistItemInline(admin.TabularInline):
    """Inline to show wishlist items"""
    model = WishlistItem
    extra = 0
    readonly_fields = ('product', 'added_at')
    can_delete = True


# ─────────────────────────────────────────────
# Custom User Admin
# ─────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin for the custom user model.
    Extends Django's built-in UserAdmin with extra vape-store fields.
    """
    list_display = (
        'email', 'username', 'full_name', 'phone_number',
        'is_age_verified', 'is_active', 'date_joined', 'last_login'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser',
        'is_age_verified', 'date_joined'
    )
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'profile_picture_preview')

    # Fieldsets define how fields are grouped in the admin detail view
    fieldsets = (
        ('Login Credentials', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'last_name', 'phone_number',
                'date_of_birth', 'profile_picture', 'profile_picture_preview'
            )
        }),
        ('Age Verification', {
            'fields': ('is_age_verified', 'age_verified_at'),
            'description': 'Regulatory compliance for vape product purchases'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)  # Collapsed by default to save space
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )

    # Fields shown when creating a new user
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name', 'last_name',
                'phone_number', 'password1', 'password2', 'is_age_verified'
            )
        }),
    )

    def full_name(self, obj):
        """Display combined first and last name"""
        return f"{obj.first_name} {obj.last_name}".strip() or "—"
    full_name.short_description = "Full Name"

    def profile_picture_preview(self, obj):
        """Show profile picture thumbnail in admin"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="height:80px; width:80px; border-radius:50%; '
                'object-fit:cover;" />',
                obj.profile_picture.url
            )
        return "No Picture"
    profile_picture_preview.short_description = "Profile Picture"


# ─────────────────────────────────────────────
# Category Admin
# ─────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for product categories (Vape Devices, E-Liquids, Accessories, etc.)"""
    list_display = (
        'name', 'slug', 'parent_category', 'product_count',
        'is_active', 'order', 'category_image_preview'
    )
    list_filter = ('is_active', 'parent_category')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # Auto-generate slug from name
    ordering = ('order', 'name')
    list_editable = ('is_active', 'order')  # Edit these columns directly in list view

    fieldsets = (
        ('Category Details', {
            'fields': ('name', 'slug', 'parent_category', 'description')
        }),
        ('Media', {
            'fields': ('image', 'category_image_preview', 'icon_class')
        }),
        ('Settings', {
            'fields': ('is_active', 'order', 'meta_title', 'meta_description')
        }),
    )
    readonly_fields = ('category_image_preview',)

    def product_count(self, obj):
        """Count products in this category"""
        count = obj.products.count()
        return format_html('<strong>{}</strong>', count)
    product_count.short_description = "Products"

    def category_image_preview(self, obj):
        """Thumbnail preview of category image"""
        if obj.image:
            return format_html(
                '<img src="{}" style="height:50px; width:auto;" />',
                obj.image.url
            )
        return "No Image"
    category_image_preview.short_description = "Image Preview"

    def parent_category(self, obj):
        """Show parent category name"""
        return obj.parent.name if obj.parent else "—"
    parent_category.short_description = "Parent Category"


# ─────────────────────────────────────────────
# Brand Admin
# ─────────────────────────────────────────────

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    Admin for vape brands (OXVA, Voopoo, Argus, Drip Down etc.)
    Brands found from product HTML file names in frontend analysis
    """
    list_display = (
        'name', 'slug', 'country_of_origin', 'product_count',
        'is_active', 'is_featured', 'logo_preview'
    )
    list_filter = ('is_active', 'is_featured', 'country_of_origin')
    search_fields = ('name', 'description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)
    list_editable = ('is_active', 'is_featured')

    fieldsets = (
        ('Brand Information', {
            'fields': ('name', 'slug', 'description', 'country_of_origin', 'website_url')
        }),
        ('Media', {
            'fields': ('logo', 'logo_preview', 'banner_image')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_featured', 'order')
        }),
    )
    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px; width:auto;" />',
                obj.logo.url
            )
        return "No Logo"
    logo_preview.short_description = "Logo"

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


# ─────────────────────────────────────────────
# Product Admin
# ─────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Main product admin — covers all products:
    Vape devices (ARGUS, XLIM, OXVA etc.) and E-Liquids (Drip Down etc.)
    """
    list_display = (
        'name', 'category', 'brand', 'product_type', 'sku',
        'price', 'sale_price', 'stock', 'is_active', 'is_featured',
        'is_new_arrival', 'created_at', 'thumbnail_preview'
    )
    list_filter = (
        'is_active', 'is_featured', 'is_new_arrival', 'is_bestseller',
        'category', 'brand', 'product_type'
    )
    search_fields = ('name', 'sku', 'description', 'short_description', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    list_editable = ('price', 'sale_price', 'stock', 'is_active', 'is_featured')
    date_hierarchy = 'created_at'
    inlines = [ProductVariantInline, ProductImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'sku', 'product_type',
                'category', 'brand', 'short_description', 'description'
            )
        }),
        ('Pricing', {
            'fields': ('price', 'sale_price', 'cost_price'),
            'description': 'Prices in Pakistani Rupees (PKR)'
        }),
        ('Inventory', {
            'fields': ('stock', 'low_stock_threshold', 'track_inventory', 'allow_backorder')
        }),
        ('Media', {
            'fields': ('thumbnail', 'thumbnail_preview', 'video_url')
        }),
        ('Product Status', {
            'fields': (
                'is_active', 'is_featured', 'is_new_arrival',
                'is_bestseller', 'is_on_sale'
            )
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('thumbnail_preview', 'created_at', 'updated_at')

    def thumbnail_preview(self, obj):
        """Show product thumbnail in admin"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:60px; width:60px; object-fit:cover; '
                'border-radius:4px;" />',
                obj.thumbnail.url
            )
        return "No Image"
    thumbnail_preview.short_description = "Thumbnail"

    def get_queryset(self, request):
        """Optimize query by selecting related category and brand"""
        return super().get_queryset(request).select_related('category', 'brand')

    def price_display(self, obj):
        """Show price with sale indicator"""
        if obj.sale_price:
            return format_html(
                '<span style="text-decoration:line-through; color:#999;">Rs.{}</span> '
                '<span style="color:#cc0000; font-weight:bold;">Rs.{}</span>',
                obj.price, obj.sale_price
            )
        return f"Rs. {obj.price:,.2f}"
    price_display.short_description = "Price"


# ─────────────────────────────────────────────
# E-Liquid Admin (specialized product type)
# ─────────────────────────────────────────────

@admin.register(ELiquid)
class ELiquidAdmin(admin.ModelAdmin):
    """
    Specialized admin for E-Liquid products.
    Drip Down and similar brands with flavor/nicotine/VG-PG ratio details.
    """
    list_display = ('product', 'nicotine_strength', 'vg_pg_ratio', 'flavor_profile')
    search_fields = ('product__name', 'flavor_profile')

admin.site.register(VapeDevice)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Blog)
admin.site.register(BlogCategory)
admin.site.register(BlogTag)
admin.site.register(BlogComment)
admin.site.register(ContactMessage)
admin.site.register(Newsletter)
admin.site.register(Review)
admin.site.register(Banner)
admin.site.register(Wishlist)
admin.site.register(WishlistItem)
admin.site.register(Coupon)
admin.site.register(CouponUsage)
admin.site.register(AgeVerification)
admin.site.register(SiteSettings)
admin.site.register(ShippingAddress)
admin.site.register(Notification)
