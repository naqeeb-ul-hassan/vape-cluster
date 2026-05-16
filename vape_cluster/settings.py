# vape_cluster/settings.py
# Django settings for vape_cluster project
# Database: MySQL | Payments: PayFast (EasyPaisa, JazzCash, Debit/Credit Card)

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────────
# BASE DIRECTORY
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────
# SECURITY SETTINGS
# ─────────────────────────────────────────────
# IMPORTANT: Keep the secret key secret in production!
# Use environment variables for production deployment
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-vape-cluster-dev-key-change-in-production-xyz123!@#'
)

# Debug mode — set to False in production
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Allowed hosts — add your domain in production
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'localhost,127.0.0.1,0.0.0.0'
).split(',')

# ─────────────────────────────────────────────
# INSTALLED APPLICATIONS
# ─────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',   # for price formatting
    'django.contrib.sitemaps',   # for SEO sitemaps
]

THIRD_PARTY_APPS = [
    'rest_framework',                 # Django REST Framework for API
    'rest_framework.authtoken',       # Token-based auth
    'corsheaders',                    # CORS headers for frontend
    'django_filters',                 # Product filtering
    'storages',                       # For S3/cloud media storage (optional)
    'ckeditor',                       # Rich text editor for blog/products
    'ckeditor_uploader',              # CKEditor file uploads
    'django_otp',                     # OTP support
    'django_otp.plugins.otp_email',   # Email OTP
]

LOCAL_APPS = [
    'core',           # Consolidated app for models, views, etc.
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Serve static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',         # CORS — must be before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',           # OTP middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SessionTimeoutMiddleware',      # Added
    'core.middleware.SecurityHeadersMiddleware',     # Added
    'core.middleware.RateLimitMiddleware',           # Added
    'core.middleware.AgeVerificationMiddleware',     # Corrected path
    'core.middleware.CartSessionMiddleware',        # Corrected path
]

# ─────────────────────────────────────────────
# URL CONFIGURATION
# ─────────────────────────────────────────────
ROOT_URLCONF = 'vape_cluster.urls'

# ─────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Look for templates in project-level templates/ folder
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                # Custom context processors
                # 'core.context_processors.cart_context',         # Placeholder
                # 'core.context_processors.categories_context', # Placeholder
                # 'core.context_processors.site_settings',         # Placeholder
            ],
        },
    },
]

# ─────────────────────────────────────────────
# WSGI / ASGI
# ─────────────────────────────────────────────
WSGI_APPLICATION = 'vape_cluster.wsgi.application'
ASGI_APPLICATION = 'vape_cluster.asgi.application'

# ─────────────────────────────────────────────
# DATABASE — MySQL
# ─────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'vape_cluster_db'),
        'USER': os.environ.get('DB_USER', 'vape_cluster_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'your_mysql_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',           # Full Unicode support (emojis etc.)
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 10,
        },
        'TEST': {
            'NAME': 'test_vape_cluster_db',  # Separate DB for running tests
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        },
        'CONN_MAX_AGE': 60,  # Persistent connections — reuse for 60 seconds
    }
}

# ─────────────────────────────────────────────
# CACHE — Redis (recommended) or Database fallback
# ─────────────────────────────────────────────
CACHES = {
    'default': {
        # Use Redis if available, otherwise fallback to database cache
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'vape_cluster',
        'TIMEOUT': 300,  # 5 minutes default cache timeout
    }
}

# ─────────────────────────────────────────────
# SESSION CONFIGURATION
# ─────────────────────────────────────────────
# Sessions stored in database for persistence
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'vape_cluster_session'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30   # 30 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG          # HTTPS only in production
SESSION_SAVE_EVERY_REQUEST = False         # Only save when modified (performance)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # Keep session after browser closes

# ─────────────────────────────────────────────
# CUSTOM USER MODEL
# ─────────────────────────────────────────────
AUTH_USER_MODEL = 'core.CustomUser'

# ─────────────────────────────────────────────
# AUTHENTICATION BACKENDS
# ─────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',        # Default username/email + password
    'apps.users.backends.EmailAuthBackend',             # Custom: login with email
]

# ─────────────────────────────────────────────
# PASSWORD VALIDATION
# ─────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ─────────────────────────────────────────────
# LOGIN / LOGOUT URLS
# ─────────────────────────────────────────────
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ─────────────────────────────────────────────
# INTERNATIONALIZATION
# ─────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'    # Pakistan Standard Time (PST) — where vape_cluster operates
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────────────
# STATIC FILES (CSS, JavaScript, Images)
# ─────────────────────────────────────────────
STATIC_URL = '/static/'

# Where collectstatic gathers all static files for production
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional static file directories
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise compression for production static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Static file finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ─────────────────────────────────────────────
# MEDIA FILES (User uploads, product images, blog images)
# ─────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Media subdirectory structure
# media/
# ├── products/          — product images
# ├── products/variants/ — variant/color images
# ├── categories/        — category thumbnails
# ├── blog/              — blog post images
# ├── banners/           — homepage/deals banners
# ├── users/avatars/     — user profile pictures
# └── brands/            — brand logos

# ─────────────────────────────────────────────
# DEFAULT AUTO FIELD
# ─────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────────────
# EMAIL CONFIGURATION
# ─────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'  # Use console backend in dev
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'noreply@vapecluster.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your_email_app_password')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Vape Cluster <noreply@vapecluster.com>')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'server@vapecluster.com')

# Admin email for order notifications
ADMINS = [
    ('Vape Cluster Admin', os.environ.get('ADMIN_EMAIL', 'admin@vapecluster.com')),
]
MANAGERS = ADMINS

# ─────────────────────────────────────────────
# DJANGO REST FRAMEWORK
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    # Default authentication classes
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # Default permission — must be authenticated by default
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # Pagination for product listings
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Filtering/ordering/search
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Throttling to prevent abuse
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '10/hour',       # Login attempts throttle
        'otp': '5/hour',         # OTP request throttle
    },
    # Response format
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Date/time format
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# ─────────────────────────────────────────────
# SIMPLE JWT SETTINGS
# ─────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # 1 hour access tokens
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # 7 days
}

# ─────────────────────────────────────────────
# CKEDITOR SETTINGS
# ─────────────────────────────────────────────
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_JQUERY_URL = '//ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
    },
}
