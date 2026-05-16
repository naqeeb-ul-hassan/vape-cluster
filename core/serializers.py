# vape_cluster/serializers.py
# Django REST Framework serializers for all models
# Handles JSON serialization for API/AJAX responses

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

# Import all models
from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
    ProductColor,
    ELiquid,
    ELiquidFlavour,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ShippingAddress,
    BillingAddress,
    Payment,
    Blog,
    BlogCategory,
    BlogComment,
    ContactMessage,
    NewsletterSubscriber,
    AgeVerification,
    ProductReview,
    Coupon,
    WishList,
    WishListItem,
    CompareList,
    Banner,
    PageHero,
)

User = get_user_model()


# ─────────────────────────────────────────────
# USER SERIALIZERS
# ─────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """Serializer for basic user info returned in API responses"""

    class Meta:
        model = User
        # Never expose password in API responses
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with password confirmation"""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']
        read_only_fields = ['id']

    def validate(self, attrs):
        """Check that both passwords match"""
        if attrs.get('password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        """Remove confirm_password before creating user"""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        # Use set_password to properly hash the password
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login credentials"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing user password"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('confirm_new_password'):
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
        return attrs


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification (6-digit code)"""

    email = serializers.EmailField()
    # OTP is exactly 6 digits
    otp_code = serializers.CharField(min_length=6, max_length=6)

    def validate_otp_code(self, value):
        """Ensure OTP contains only digits"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain digits only.")
        return value


# ─────────────────────────────────────────────
# CATEGORY SERIALIZERS
# ─────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories"""

    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description',
            'image', 'is_active', 'product_count', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def get_product_count(self, obj):
        """Return count of active products in this category"""
        return obj.products.filter(is_active=True).count()


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for category lists/dropdowns"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'image']


# ─────────────────────────────────────────────
# BRAND SERIALIZERS
# ─────────────────────────────────────────────

class BrandSerializer(serializers.ModelSerializer):
    """Serializer for product brands (OXVA, VOOPOO, etc.)"""

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class BrandListSerializer(serializers.ModelSerializer):
    """Lightweight brand serializer for listings"""

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo']


# ─────────────────────────────────────────────
# PRODUCT COLOR SERIALIZER
# ─────────────────────────────────────────────

class ProductColorSerializer(serializers.ModelSerializer):
    """Serializer for product color options"""

    class Meta:
        model = ProductColor
        fields = ['id', 'name', 'hex_code', 'is_available']


# ─────────────────────────────────────────────
# PRODUCT IMAGE SERIALIZER
# ─────────────────────────────────────────────

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product gallery images"""

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']


# ─────────────────────────────────────────────
# PRODUCT VARIANT SERIALIZER
# ─────────────────────────────────────────────

class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for product variants (e.g., different sizes/configs)"""

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'sku', 'price',
            'sale_price', 'stock_quantity', 'is_available'
        ]


# ─────────────────────────────────────────────
# PRODUCT REVIEW SERIALIZER
# ─────────────────────────────────────────────

class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer for customer product reviews"""

    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            'id', 'user_name', 'rating', 'title',
            'body', 'is_verified_purchase', 'created_at'
        ]
        read_only_fields = ['id', 'user_name', 'is_verified_purchase', 'created_at']

    def get_user_name(self, obj):
        """Return display name for reviewer"""
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return "Anonymous"

    def validate_rating(self, value):
        """Rating must be between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new product review"""

    class Meta:
        model = ProductReview
        fields = ['product', 'rating', 'title', 'body']


# ─────────────────────────────────────────────
# PRODUCT SERIALIZERS
# ─────────────────────────────────────────────

class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product grid/listing pages.
    Used in shop page, category pages, search results.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku',
            'category_name', 'brand_name',
            'price', 'sale_price', 'is_on_sale',
            'primary_image', 'discount_percentage',
            'average_rating', 'review_count',
            'is_active', 'is_featured', 'is_new',
            'stock_quantity', 'is_in_stock',
        ]

    def get_primary_image(self, obj):
        """Return the URL of the primary product image"""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None

    def get_discount_percentage(self, obj):
        """Calculate discount percentage if product is on sale"""
        if obj.is_on_sale and obj.sale_price and obj.price > 0:
            discount = ((obj.price - obj.sale_price) / obj.price) * 100
            return round(discount, 0)
        return 0

    def get_average_rating(self, obj):
        """Return average rating from approved reviews"""
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            total = sum(r.rating for r in reviews)
            return round(total / reviews.count(), 1)
        return 0

    def get_review_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(is_approved=True).count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for product detail page.
    Includes images, variants, colors, and reviews.
    """

    category = CategoryListSerializer(read_only=True)
    brand = BrandListSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    colors = ProductColorSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku',
            'category', 'brand',
            'description', 'short_description', 'specifications',
            'price', 'sale_price', 'is_on_sale',
            'images', 'variants', 'colors',
            'stock_quantity', 'is_in_stock',
            'is_active', 'is_featured', 'is_new',
            'average_rating', 'review_count', 'reviews',
            'discount_percentage', 'related_products',
            'meta_title', 'meta_description',
            'created_at', 'updated_at',
        ]

    def get_reviews(self, obj):
        """Return approved reviews only"""
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:5]
        return ProductReviewSerializer(reviews, many=True).data

    def get_average_rating(self, obj):
        reviews = obj.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0

    def get_review_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()

    def get_discount_percentage(self, obj):
        if obj.is_on_sale and obj.sale_price and obj.price > 0:
            discount = ((obj.price - obj.sale_price) / obj.price) * 100
            return round(discount, 0)
        return 0

    def get_related_products(self, obj):
        """Return 4 related products from same category"""
        related = Product.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id)[:4]
        return ProductListSerializer(
            related, many=True, context=self.context
        ).data


class ProductQuickViewSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for the quick view modal.
    Returns only what's needed for the popup.
    """

    primary_image = serializers.SerializerMethodField()
    colors = ProductColorSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price',
            'sale_price', 'is_on_sale',
            'primary_image', 'colors',
            'is_in_stock', 'short_description',
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url
        return None


# ─────────────────────────────────────────────
# E-LIQUID SERIALIZERS
# ─────────────────────────────────────────────

class ELiquidFlavourSerializer(serializers.ModelSerializer):
    """Serializer for e-liquid flavour options"""

    class Meta:
        model = ELiquidFlavour
        fields = ['id', 'name', 'is_available']


class ELiquidListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for e-liquid product listings"""

    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ELiquid
        fields = [
            'id', 'name', 'slug', 'brand_name',
            'flavour_profile', 'nicotine_strength', 'bottle_size',
            'vg_pg_ratio', 'price', 'sale_price', 'is_on_sale',
            'primary_image', 'discount_percentage',
            'is_active', 'is_in_stock',
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image.url
        return None

    def get_discount_percentage(self, obj):
        if obj.is_on_sale and obj.sale_price and obj.price > 0:
            return round(((obj.price - obj.sale_price) / obj.price) * 100, 0)
        return 0


class ELiquidDetailSerializer(serial