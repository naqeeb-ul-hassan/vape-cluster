# core/views.py
# Consolidated views for Vape Cluster monolithic project
# All views are Function-Based Views (FBV) for simplicity

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import (
    CustomUser, Product, Category, Brand, Order, OrderItem, 
    Cart, CartItem, Blog, ContactMessage, Newsletter, 
    Review, Banner, Wishlist, WishlistItem, SiteSettings
)
from .forms import SignupForm, LoginForm # I will harmonize forms.py later

# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def home(request):
    """
    Homepage view - displays banners, categories, and latest products.
    """
    banners = Banner.objects.filter(is_active=True).order_by('order')
    categories = Category.objects.filter(is_active=True, parent=None)
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    
    context = {
        'banners': banners,
        'categories': categories,
        'latest_products': latest_products,
        'featured_products': featured_products,
    }
    # Rendering index.html which now extends base.html
    return render(request, 'index.html', context)

# ─────────────────────────────────────────────
# AUTHENTICATION (Login / Signup)
# ─────────────────────────────────────────────
def auth_view(request):
    """
    Combined login and signup page (sliding panel).
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    return render(request, 'login-signup.html')

def signup_view(request):
    """
    Handle user registration.
    """
    if request.method == 'POST':
        # Logic to handle signup data
        # For now, simple implementation
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('auth')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('auth')
            
        user = CustomUser.objects.create_user(
            username=email, 
            email=email, 
            password=password,
            first_name=full_name.split()[0] if full_name else "",
            last_name=" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else ""
        )
        login(request, user)
        messages.success(request, "Account created successfully!")
        return redirect('home')
        
    return redirect('auth')

def login_view(request):
    """
    Handle user login.
    """
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid email or password.")
            
    return redirect('auth')

def logout_view(request):
    """
    Handle user logout.
    """
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('home')

# ─────────────────────────────────────────────
# SHOP / PRODUCTS
# ─────────────────────────────────────────────
def shop_view(request):
    """
    Main shop page with all products.
    """
    products = Product.objects.filter(is_active=True)
    return render(request, 'shop.html', {'products': products})

def brand_view(request, brand_slug):
    """
    Listing page for products of a specific brand.
    """
    brand = get_object_or_404(Brand, slug=brand_slug)
    products = Product.objects.filter(brand=brand, is_active=True)
    return render(request, 'shop.html', {'products': products, 'brand': brand})

def product_detail(request, brand_slug, product_slug):
    """
    Product detail page.
    """
    # Mapping to existing HTML files for now as requested
    template_name = f'vape-products/{brand_slug}/{product_slug}-data.html'
    # Fallback if specific file doesn't exist (can happen during migration)
    try:
        return render(request, template_name)
    except:
        product = get_object_or_404(Product, slug=product_slug)
        return render(request, 'product_detail.html', {'product': product})

def eliquid_list(request):
    """
    E-Liquids listing page.
    """
    products = Product.objects.filter(category__slug='e-liquids', is_active=True)
    return render(request, 'E-Liquids.html', {'products': products})

def eliquid_detail(request, product_slug):
    """
    E-Liquid detail page.
    """
    template_name = f'E-liquids-products/{product_slug}-data.html'
    try:
        return render(request, template_name)
    except:
        return render(request, 'E-Liquids.html')

def coils_view(request):
    """
    Coils listing page.
    """
    return render(request, 'coils.html')

def deals_view(request):
    """
    Deals listing page.
    """
    return render(request, 'deals.html')

# ─────────────────────────────────────────────
# CART & CHECKOUT
# ─────────────────────────────────────────────
def cart_view(request):
    """
    Shopping cart page.
    """
    return render(request, 'cart.html')

def checkout_view(request):
    """
    Checkout page.
    """
    return render(request, 'checkout.html')

# ─────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────
def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    if request.method == 'POST':
        ContactMessage.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message')
        )
        messages.success(request, "Message sent successfully!")
        return redirect('contact')
    return render(request, 'contact.html')

def privacy_policy(request):
    return render(request, 'privacy-policy.html')

# ─────────────────────────────────────────────
# ADMIN DASHBOARD (CUSTOM)
# ─────────────────────────────────────────────
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')
    return render(request, 'admin/index.html')

@login_required
def admin_orders(request):
    return render(request, 'admin/orders.html')

# ─────────────────────────────────────────────
# NEWSLETTER
# ─────────────────────────────────────────────
def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not Newsletter.objects.filter(email=email).exists():
            Newsletter.objects.create(email=email)
            return JsonResponse({'status': 'success', 'message': 'Subscribed!'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})