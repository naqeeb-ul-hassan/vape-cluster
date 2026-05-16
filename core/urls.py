# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main Pages
    path('', views.home, name='home'),
    path('auth/', views.auth_view, name='auth'),
    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # Products
    path('shop/', views.shop_view, name='shop'),
    path('vape-products/<slug:brand_slug>/', views.brand_view, name='vape_brand'),
    path('vape-products/<slug:brand_slug>/<slug:product_slug>/', views.product_detail, name='vape_product_detail'),
    path('e-liquids/', views.eliquid_list, name='eliquid_list'),
    path('e-liquids/<slug:product_slug>/', views.eliquid_detail, name='eliquid_detail'),
    path('coils/', views.coils_view, name='coils'),
    path('deals/', views.deals_view, name='deals'),
    
    # Cart & Checkout
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    
    # Static Pages
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    
    # Custom Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('admin-dashboard/eliquids/', views.admin_dashboard, name='admin_manage_eliquids'), # Placeholder
    path('admin-dashboard/deals/', views.admin_dashboard, name='admin_manage_deals'), # Placeholder
    path('admin-dashboard/brand/<slug:brand>/', views.admin_dashboard, name='admin_manage_brand'), # Placeholder
    path('admin-dashboard/coils/', views.admin_dashboard, name='admin_manage_coils'), # Placeholder
    path('admin-dashboard/home-page/', views.admin_dashboard, name='admin_manage_home'), # Placeholder
    path('admin-dashboard/about-us/', views.admin_dashboard, name='admin_about_us'), # Placeholder
    path('admin-dashboard/contact-us/', views.admin_dashboard, name='admin_contact_us'), # Placeholder
    path('admin-dashboard/add-product/', views.admin_dashboard, name='admin_add_product'), # Placeholder
    
    # API / AJAX
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]