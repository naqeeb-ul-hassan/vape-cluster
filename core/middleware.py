# vape_cluster/middleware.py
# Middleware for authentication, security, and session handling

import re
import logging
import json
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.middleware.csrf import get_token

# Set up logging for security events
logger = logging.getLogger('vape_cluster.security')


# ─────────────────────────────────────────────
# 1. AGE VERIFICATION MIDDLEWARE
# ─────────────────────────────────────────────
class AgeVerificationMiddleware(MiddlewareMixin):
    """
    Enforce age verification gate (21+) before accessing the site.
    Checks session flag set when user confirms their age.
    Public URLs like /age-verify/, /static/, /media/ are excluded.
    """

    # URLs that bypass age verification
    EXEMPT_URLS = [
        r'^/age-verify/',
        r'^/static/',
        r'^/media/',
        r'^/admin/',
        r'^/api/age-verify/',
        r'^/robots\.txt$',
        r'^/favicon\.ico$',
    ]

    def process_request(self, request):
        # Compile exempt patterns
        exempt_patterns = [re.compile(url) for url in self.EXEMPT_URLS]

        # Check if current path is exempt
        path = request.path_info
        is_exempt = any(pattern.match(path) for pattern in exempt_patterns)

        if is_exempt:
            return None  # Allow through without verification

        # Check if age has been verified in session
        age_verified = request.session.get('age_verified', False)

        if not age_verified:
            # For AJAX requests, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(
                    {'error': 'Age verification required', 'redirect': '/age-verify/'},
                    status=403
                )
            # For normal requests, redirect to age verification page
            return HttpResponseRedirect('/age-verify/')

        return None


# ─────────────────────────────────────────────
# 2. SESSION TIMEOUT MIDDLEWARE
# ─────────────────────────────────────────────
class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Automatically log out users after a period of inactivity.
    Default timeout is 30 minutes (configurable via settings).
    Keeps guest sessions alive longer for cart persistence.
    """

    # Default session timeout in seconds (30 minutes for logged-in users)
    SESSION_TIMEOUT = getattr(settings, 'SESSION_IDLE_TIMEOUT', 1800)

    # Guest session timeout (2 hours for cart persistence)
    GUEST_SESSION_TIMEOUT = getattr(settings, 'GUEST_SESSION_TIMEOUT', 7200)

    # Paths that should not reset the session timer
    EXEMPT_PATHS = [
        r'^/static/',
        r'^/media/',
        r'^/favicon\.ico$',
    ]

    def process_request(self, request):
        exempt_patterns = [re.compile(p) for p in self.EXEMPT_PATHS]
        path = request.path_info

        # Skip static/media files
        if any(pattern.match(path) for pattern in exempt_patterns):
            return None

        # Only apply timeout to authenticated users
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')

            if last_activity:
                # Calculate time since last activity
                last_activity_time = datetime.fromisoformat(last_activity)
                elapsed = (datetime.now() - last_activity_time).total_seconds()

                if elapsed > self.SESSION_TIMEOUT:
                    # Log the timeout event
                    logger.info(
                        f"Session timeout for user: {request.user.username} "
                        f"after {elapsed:.0f} seconds of inactivity"
                    )
                    # Log out the user
                    logout(request)
                    request.session.flush()

                    # Redirect to login with timeout message
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse(
                            {'error': 'Session expired. Please log in again.', 'redirect': '/auth/login/'},
                            status=401
                        )
                    return HttpResponseRedirect('/auth/login/?next=' + request.path + '&timeout=1')

            # Update last activity timestamp
            request.session['last_activity'] = datetime.now().isoformat()

        return None


# ─────────────────────────────────────────────
# 3. SECURITY HEADERS MIDDLEWARE
# ─────────────────────────────────────────────
class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to all responses.
    Protects against XSS, clickjacking, MIME sniffing, and other attacks.
    """

    def process_response(self, request, response):
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection in older browsers
        response['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy for privacy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy (restrict camera, mic, geolocation)
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), '
            'payment=(self), usb=(), magnetometer=()'
        )

        # Content Security Policy
        # Allow PayFast payment gateway and social auth providers
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://www.google.com https://accounts.google.com "
            "https://connect.facebook.net https://checkout.payfast.io "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com",
            "img-src 'self' data: blob: https: http:",
            "connect-src 'self' https://accounts.google.com "
            "https://checkout.payfast.io",
            "frame-src 'self' https://checkout.payfast.io "
            "https://accounts.google.com",
            "form-action 'self' https://checkout.payfast.io "
            "https://sandbox.payfast.co.za",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # HSTS - only add in production (not development)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        return response


# ─────────────────────────────────────────────
# 4. RATE LIMITING MIDDLEWARE
# ─────────────────────────────────────────────
class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limit sensitive endpoints to prevent brute force attacks.
    Uses Django cache (Redis recommended) to track request counts.
    Protects login, signup, OTP, checkout, and PayFast endpoints.
    """

    # Define rate limits: {url_pattern: (max_requests, window_seconds)}
    RATE_LIMITS = {
        r'^/auth/login/': (10, 300),          # 10 attempts per 5 minutes
        r'^/auth/signup/': (5, 300),           # 5 signups per 5 minutes
        r'^/auth/otp/': (5, 300),              # 5 OTP attempts per 5 minutes
        r'^/auth/password-reset/': (5, 600),   # 5 resets per 10 minutes
        r'^/api/cart/': (60, 60),              # 60 cart requests per minute
        r'^/checkout/': (20, 60),              # 20 checkout requests per minute
        r'^/api/payfast/': (10, 60),           # 10 payment requests per minute
        r'^/api/newsletter/': (3, 3600),       # 3 newsletter signups per hour
        r'^/api/contact/': (5, 3600),          # 5 contact form submissions per hour
    }

    def get_client_ip(self, request):
        """Extract the real client IP address, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP from the forwarded list
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip

    def process_request(self, request):
        path = request.path_info
        client_ip = self.get_client_ip(request)

        # Check each rate limit rule
        for pattern, (max_requests, window_seconds) in self.RATE_LIMITS.items():
            if re.match(pattern, path):
                # Create a unique cache key for this IP + endpoint
                cache_key = f'rate_limit:{client_ip}:{pattern}'

                # Get current request count
                request_count = cache.get(cache_key, 0)

                if request_count >= max_requests:
                    # Log rate limit violation
                    logger.warning(
                        f"Rate limit exceeded: IP={client_ip}, "
                        f"path={path}, count={request_count}"
                    )

                    # Return 429 Too Many Requests
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse(
                            {
                                'error': 'Too many requests. Please try again later.',
                                'retry_after': window_seconds
                            },
                            status=429
                        )
                    return HttpResponseForbidden(
                        'Too many requests. Please try again later.'
                    )

                # Increment counter
                if request_count == 0:
                    # First request - set with expiry
                    cache.set(cache_key, 1, window_seconds)
                else:
                    # Increment existing counter
                    cache.incr(cache_key)

                break  # Only apply the first matching rule

        return None


# ─────────────────────────────────────────────
# 5. CART SESSION MIDDLEWARE
# ─────────────────────────────────────────────
class CartSessionMiddleware(MiddlewareMixin):
    """
    Manage shopping cart in session for both authenticated and guest users.
    Merges guest cart with user cart upon login.
    Ensures cart data persists across sessions.
    """

    def process_request(self, request):
        # Initialize cart in session if not present
        if 'cart' not in request.session:
            request.session['cart'] = {}

        # Attach cart count to request for use in templates/views
        cart = request.session.get('cart', {})
        request.cart_count = sum(
            item.get('quantity', 0) for item in cart.values()
        )

        return None

    def process_response(self, request, response):
        # Ensure session is saved when cart is modified
        if hasattr(request, 'session') and request.session.modified:
            request.session.save()
        return response


# ─────────────────────────────────────────────
# 6. PAYFAST SECURITY MIDDLEWARE
# ─────────────────────────────────────────────
class PayFastSecurityMiddleware(MiddlewareMixin):
    """
    Validate PayFast payment notifications (ITN - Instant Transaction Notification).
    Ensures payment callbacks come from legitimate PayFast servers.
    Handles EasyPaisa, JazzCash, and card payment verification.
    """

    # PayFast server IP ranges for ITN validation
    PAYFAST_IP_RANGES = getattr(
        settings,
        'PAYFAST_VALID_IPS',
        [
            '197.97.145.144/28',   # PayFast production IPs
            '197.97.145.160/28',
            '41.74.179.192/27',
            '127.0.0.1',           # Localhost for testing
        ]
    )

    # PayFast ITN endpoint
    PAYFAST_ITN_URL = r'^/api/payfast/itn/'

    def _is_payfast_ip(self, ip):
        """
        Check if the request IP is from PayFast.
        Simple string matching - use ipaddress module for production CIDR matching.
        """
        import ipaddress

        try:
            client_ip = ipaddress.ip_address(ip)
            for ip_range in self.PAYFAST_IP_RANGES:
                if '/' in ip_range:
                    # Check CIDR range
                    network = ipaddress.ip_network(ip_range, strict=False)
                    if client_ip in network:
                        return True
                else:
                    # Direct IP comparison
                    if str(client_ip) == ip_range:
                        return True
        except ValueError:
            logger.error(f"Invalid IP address format: {ip}")
            return False

        return False

    def process_request(self, request):
        # Only validate PayFast ITN endpoint
        if not re.match(self.PAYFAST_ITN_URL, request.path_info):
            return None

        # Only POST requests are valid ITN callbacks
        if request.method != 'POST':
            logger.warning(
                f"Non-POST request to PayFast ITN endpoint: {request.method}"
            )
            return HttpResponseForbidden('Method not allowed')

        # Validate source IP in production
        if not settings.DEBUG:
            client_ip = request.META.get('REMOTE_ADDR', '')
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')

            # Use forwarded IP if available
            if x_forwarded:
                client_ip = x_forwarded.split(',')[0].strip()

            if not self._is_payfast_ip(client_ip):
                logger.warning(
                    f"PayFast ITN from unauthorized IP: {client_ip}"
                )
                return HttpResponseForbidden('Unauthorized payment callback')

        # Log ITN request for audit trail
        logger.info(
            f"PayFast ITN received: path={request.path_info}, "
            f"ip={request.META.get('REMOTE_ADDR')}"
        )

        return None


# ─────────────────────────────────────────────
# 7. REQUEST LOGGING MIDDLEWARE
# ─────────────────────────────────────────────
class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Log all requests for security auditing and debugging.
    Tracks response times, user actions, and errors.
    Does not log static file requests to reduce noise.
    """

    # Paths to skip logging (static/