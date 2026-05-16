# vape_cluster/models.py
# Complete models for vape shop with all required entities

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


# ============================================================
# CUSTOM USER MANAGER
# ============================================================

class CustomUserManager(BaseUserManager):
    """Manager for custom user model with email as username"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


# ============================================================
# USER MODEL
# ============================================================

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for vape shop.
    Uses email instead of username for authentication.
    Includes age verification flag for regulatory compliance.
    """

    # Basic info
    username = models.EmailField(unique=True, db_index=True, blank=True, null=True) # For compatibility
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # Profile
    profile_picture = models.ImageField(
        upload_to='users/profile_pictures/',
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)

    # Address fields (default shipping address)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Pakistan')

    # Age verification - required for vape products
    age_verified = models.BooleanField(
        default=False,
        help_text='User confirmed they are 21+ years old'
    )
    is_age_verified = models.BooleanField(default=False) # For admin compatibility
    age_verified_at = models.DateTimeField(blank=True, null=True)

    # Auth status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(
        default=False,
        help_text='Email verified via OTP'
    )

    # Social auth flags
    is_google_user = models.BooleanField(default=False)
    is_facebook_user = models.BooleanField(default=False)

    # Newsletter subscription
    newsletter_subscribed = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    objects = CustomUserManager()

    # Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]


# ============================================================
# OTP MODEL (for email verification)
# ============================================================

class OTPVerification(models.Model):
    """
    Stores OTP codes for email verification and password reset.
    OTP has 6 digits as seen in the frontend otp-input fields.
    """

    OTP_PURPOSE_CHOICES = [
        ('email_verify', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('login', 'Login Verification'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='otp_codes'
    )
    otp_code = models.CharField(max_length=6)  # 6-digit OTP
    purpose = models.CharField(
        max_length=20,
        choices=OTP_PURPOSE_CHOICES,
        default='email_verify'
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Usually 10 minutes from creation

    class Meta:
        db_table = 'otp_verifications'
        verbose_name = 'OTP Verification'
        verbose_name_plural = 'OTP Verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.user.email} - {self.purpose}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()


# ============================================================
# CATEGORY MODEL
# ============================================================

class Category(models.Model):
    """
    Product categories for the vape shop.
    Supports hierarchy (parent/child) for sub-categories.
    Examples: Vapes, E-Liquids, Accessories
    """

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True)

    # Category image (used in category boxes on homepage)
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True
    )

    # Parent category for nested categories
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    # Display order on the site
    display_order = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0) # For admin compatibility
    is_active = models.BooleanField(default=True)
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children') # For admin compatibility
    is_featured = models.BooleanField(
        default=False,
        help_text='Show in featured categories section'
    )

    # SEO fields
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_all_children(self):
        """Return all subcategories recursively"""
        children = list(self.subcategories.filter(is_active=True))
        for child in self.subcategories.filter(is_active=True):
            children.extend(child.get_all_children())
        return children


# ============================================================
# BRAND MODEL
# ============================================================

class Brand(models.Model):
    """
    Vape product brands like OXVA, Argus, Drip Down etc.
    """
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brands'
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


# ============================================================
# PRODUCT MODEL
# ============================================================

class Product(models.Model):
    """
    Main product model for vape devices and e-liquids.
    Supports color variants, nicotine strengths, and comparison features.
    """

    PRODUCT_TYPE_CHOICES = [
        ('vape_device', 'Vape Device'),
        ('e_liquid', 'E-Liquid'),
        ('accessory', 'Accessory'),
        ('coil', 'Coil'),
        ('pod', 'Pod'),
        ('battery', 'Battery'),
        ('other', 'Other'),
    ]

    NICOTINE_STRENGTH_CHOICES = [
        ('0mg', '0mg - Nicotine Free'),
        ('3mg', '3mg'),
        ('6mg', '6mg'),
        ('12mg', '12mg'),
        ('18mg', '18mg'),
        ('25mg', '25mg - Salt Nic'),
        ('50mg', '50mg - Salt Nic'),
    ]

    # Basic info
    name = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=300, unique=True, db_index=True)
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        help_text='Stock Keeping Unit'
    )
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        default='vape_device'
    )

    # Relationships
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    # Description
    short_description = models.TextField(
        blank=True,
        help_text='Brief description shown in product cards'
    )
    description = models.TextField(
        blank=True,
        help_text='Full product description'
    )
    specifications = models.JSONField(
        default=dict,
        blank=True,
        help_text='Technical specs stored as JSON (e.g., battery, wattage, etc.)'
    )

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original price before discount (shown as strikethrough)'
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Internal cost price for profit calculation'
    )

    # Inventory
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text='Alert when stock falls below this number'
    )
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)

    # E-Liquid specific fields
    nicotine_strength = models.CharField(
        max_length=10,
        choices=NICOTINE_STRENGTH_CHOICES,
        blank=True,
        null=True,
        help_text='Only for e-liquid products'
    )
    bottle_size_ml = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Bottle size in ml for e-liquids'
    )
    flavor_profile = models.CharField(
        max_length=300,
        blank=True,
        help_text='Flavor description e.g. Apple, Ice, Menthol'
    )
    vg_pg_ratio = models.CharField(
        max_length=20,
        blank=True,
        help_text='VG/PG ratio e.g. 70/30'
    )

    # Main product image
    main_image = models.ImageField(
        upload_to='products/images/',
        blank=True,
        null=True
    )

    # Flags
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(
        default=False,
        help_text='Show in featured products section'
    )
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False) # For admin compatibility
    is_on_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) # For admin compatibility
    stock = models.PositiveIntegerField(default=0) # For admin compatibility

    # For product comparison feature (seen in chunk 4)
    is_comparable = models.BooleanField(
        default=True,
        help_text='Allow this product to be added to compare'
    )

    # Tabs data (inferred from tab-link, tab-content classes)
    tab_description = models.TextField(blank=True)
    tab_specifications = models.TextField(blank=True)
    tab_reviews_enabled = models.BooleanField(default=True)

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        # Check if it's an e-liquid based on category slug
        if self.category.slug == 'e-liquids':
            return reverse('core:eliquid_detail', kwargs={'product_slug': self.slug})
        return reverse('core:vape_product_detail', kwargs={'brand_slug': self.brand.slug, 'product_slug': self.slug})

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=100) # e.g., Color, Nicotine Strength
    value = models.CharField(max_length=100) # e.g., Black, 3mg
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)

class ELiquid(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    nicotine_strength = models.CharField(max_length=50)
    vg_pg_ratio = models.CharField(max_length=50)
    flavor_profile = models.CharField(max_length=255)

class VapeDevice(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    battery_capacity = models.CharField(max_length=100)
    wattage_range = models.CharField(max_length=100)
    charging_port = models.CharField(max_length=50)

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

class Blog(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog/')
    categories = models.ManyToManyField('BlogCategory', related_name='blogs', blank=True)
    tags = models.ManyToManyField('BlogTag', related_name='blogs', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Banner(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='banners/')
    link = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

class Wishlist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=False)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default='Vape Cluster')
    contact_email = models.EmailField(default='vapecluster872@gmail.com')
    contact_phone = models.CharField(max_length=20, default='+92 3200489485')
    address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)

class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

class BlogTag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

class BlogComment(models.Model):
    blog = models.ForeignKey(Blog, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ShippingAddress(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

class AgeVerification(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    verified_at = models.DateTimeField(auto_now_add=True)
    document_image = models.ImageField(upload_to='age_verification/', blank=True, null=True)
