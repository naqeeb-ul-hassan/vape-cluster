# vape_cluster/signals.py
# Django signals for order notifications and user registration events

from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver, Signal
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

# Get logger for vape_cluster
logger = logging.getLogger('vape_cluster')

# ---------------------------------------------------------------------------
# Custom signals for vape_cluster specific events
# ---------------------------------------------------------------------------

# Fired when an order status changes (e.g., pending -> processing -> shipped)
order_status_changed = Signal()

# Fired when a PayFast payment is confirmed (EasyPaisa, JazzCash, Card)
payment_confirmed = Signal()

# Fired when a payment fails
payment_failed = Signal()

# Fired when stock falls below threshold
low_stock_alert = Signal()

# Fired when a new review is submitted
review_submitted = Signal()

# Fired when a discount code is applied
discount_applied = Signal()

# Fired when age verification is completed
age_verified = Signal()


# ---------------------------------------------------------------------------
# Helper: Send HTML email safely with fallback to plain text
# ---------------------------------------------------------------------------

def send_notification_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Send an HTML email with plain text fallback.
    Returns True on success, False on failure.
    """
    if not from_email:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@vapecluster.com')

    try:
        # Render HTML content from template
        html_content = render_to_string(template_name, context)
        # Strip HTML tags for plain text version
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Email sent: '{subject}' to {recipient_list}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email '{subject}' to {recipient_list}: {str(e)}")
        return False


# ---------------------------------------------------------------------------
# Helper: Get admin email list for notifications
# ---------------------------------------------------------------------------

def get_admin_emails():
    """Return list of superuser emails for admin notifications."""
    admin_emails = list(
        User.objects.filter(
            is_superuser=True,
            is_active=True,
            email__isnull=False
        ).exclude(email='').values_list('email', flat=True)
    )

    # Fallback to ADMIN_EMAIL setting if no superusers found
    if not admin_emails:
        admin_email = getattr(settings, 'ADMIN_EMAIL', None)
        if admin_email:
            admin_emails = [admin_email]

    return admin_emails


# ---------------------------------------------------------------------------
# USER REGISTRATION SIGNALS
# ---------------------------------------------------------------------------

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_new_user_registration(sender, instance, created, **kwargs):
    """
    Fired when a new User is created.
    - Creates a UserProfile
    - Sends welcome email to new user
    - Notifies admin of new registration
    """
    if not created:
        return  # Only handle new user creation

    logger.info(f"New user registered: {instance.username} ({instance.email})")

    # ------------------------------------------------------------------
    # Create UserProfile for the new user
    # ------------------------------------------------------------------
    try:
        # Import here to avoid circular imports
        from shop.models import UserProfile

        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'age_verified': False,  # Age verification required for vape store
                'newsletter_subscribed': False,
                'created_at': timezone.now(),
            }
        )
        logger.info(f"UserProfile created for user: {instance.username}")

    except ImportError:
        logger.warning("UserProfile model not found. Skipping profile creation.")
    except Exception as e:
        logger.error(f"Failed to create UserProfile for {instance.username}: {str(e)}")

    # ------------------------------------------------------------------
    # Send welcome email to the new user (if email provided)
    # ------------------------------------------------------------------
    if instance.email:
        context = {
            'user': instance,
            'username': instance.username,
            'first_name': instance.first_name or instance.username,
            'site_name': 'Vape Cluster',
            'site_url': getattr(settings, 'SITE_URL', 'https://vapecluster.com'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vapecluster.com'),
            'year': timezone.now().year,
        }

        send_notification_email(
            subject='Welcome to Vape Cluster! 🎉',
            template_name='emails/welcome_email.html',
            context=context,
            recipient_list=[instance.email],
        )

    # ------------------------------------------------------------------
    # Notify admin of new user registration
    # ------------------------------------------------------------------
    admin_emails = get_admin_emails()
    if admin_emails:
        admin_context = {
            'new_user': instance,
            'username': instance.username,
            'email': instance.email,
            'date_joined': instance.date_joined,
            'site_name': 'Vape Cluster',
        }

        send_notification_email(
            subject=f'New User Registration: {instance.username}',
            template_name='emails/admin_new_user_notification.html',
            context=admin_context,
            recipient_list=admin_emails,
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_user_profile_update(sender, instance, created, **kwargs):
    """
    Fired when an existing User is updated.
    Syncs the UserProfile if it exists.
    """
    if created:
        return  # Skip, handled by handle_new_user_registration

    try:
        from shop.models import UserProfile
        # Save the related profile to trigger any profile-level signals
        if hasattr(instance, 'userprofile'):
            instance.userprofile.save()

    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to sync UserProfile for {instance.username}: {str(e)}")


# ---------------------------------------------------------------------------
# ORDER SIGNALS
# ---------------------------------------------------------------------------

@receiver(post_save, sender='core.Order')
def handle_new_order(sender, instance, created, **kwargs):
    """
    Fired when a new Order is created.
    - Sends order confirmation email to customer
    - Sends new order notification to admin
    """
    if not created:
        return  # Only handle new orders here

    logger.info(f"New order created: #{instance.order_number} for {instance.user}")

    # ------------------------------------------------------------------
    # Send order confirmation to customer
    # ------------------------------------------------------------------
    customer_email = None
    if instance.user and instance.user.email:
        customer_email = instance.user.email
    elif hasattr(instance, 'email') and instance.email:
        # Guest checkout email
        customer_email = instance.email

    if customer_email:
        context = {
            'order': instance,
            'order_number': instance.order_number,
            'order_items': instance.items.all() if hasattr(instance, 'items') else [],
            'subtotal': instance.subtotal,
            'discount': getattr(instance, 'discount_amount', 0),
            'shipping': getattr(instance, 'shipping_cost', 0),
            'total': instance.total_amount,
            'payment_method': getattr(instance, 'payment_method', 'N/A'),
            'shipping_address': getattr(instance, 'shipping_address', ''),
            'estimated_delivery': getattr(instance, 'estimated_delivery', '3-5 business days'),
            'site_name': 'Vape Cluster',
            'site_url': getattr(settings, 'SITE_URL', 'https://vapecluster.com'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vapecluster.com'),
            'year': timezone.now().year,
        }

        send_notification_email(
            subject=f'Order Confirmation - #{instance.order_number} | Vape Cluster',
            template_name='emails/order_confirmation.html',
            context=context,
            recipient_list=[customer_email],
        )

    # ------------------------------------------------------------------
    # Notify admin of new order
    # ------------------------------------------------------------------
    admin_emails = get_admin_emails()
    if admin_emails:
        admin_context = {
            'order': instance,
            'order_number': instance.order_number,
            'customer': instance.user,
            'total_amount': instance.total_amount,
            'payment_method': getattr(instance, 'payment_method', 'N/A'),
            'payment_status': getattr(instance, 'payment_status', 'pending'),
            'site_name': 'Vape Cluster',
        }

        send_notification_email(
            subject=f'🛒 New Order Received: #{instance.order_number}',
            template_name='emails/admin_new_order_notification.html',
            context=admin_context,
            recipient_list=admin_emails,
        )


@receiver(order_status_changed)
def handle_order_status_change(sender, order, old_status, new_status, **kwargs):
    """
    Fired when an order's status changes.
    Sends appropriate email based on new status.

    Status flow: pending -> processing -> shipped -> delivered -> cancelled/refunded
    """
    logger.info(
        f"Order #{order.order_number} status changed: {old_status} -> {new_status}"
    )

    # Determine customer email
    customer_email = None
    if order.user and order.user.email:
        customer_email = order.user.email
    elif hasattr(order, 'email') and order.email:
        customer_email = order.email

    if not customer_email:
        logger.warning(f"No customer email for order #{order.order_number}")
        return

    # ------------------------------------------------------------------
    # Map each status to an email template and subject
    # ------------------------------------------------------------------
    status_email_map = {
        'processing': {
            'subject': f'Your Order #{order.order_number} is Being Processed | Vape Cluster',
            'template': 'emails/order_processing.html',
        },
        'shipped': {
            'subject': f'Your Order #{order.order_number} Has Been Shipped! 🚚 | Vape Cluster',
            'template': 'emails/order_shipped.html',
        },
        'delivered': {
            'subject': f'Your Order #{order.order_number} Has Been Delivered! ✅ | Vape Cluster',
            'template': 'emails/order_delivered.html',
        },
        'cancelled': {
            'subject': f'Your Order #{order.order_number} Has Been Cancelled | Vape Cluster',
            'template': 'emails/order_cancelled.html',
        },
        'refunded': {
            'subject': f'Refund Processed for Order #{order.order_number} | Vape Cluster',
            'template': 'emails/order_refunded.html',
        },
        'failed': {
            'subject': f'Issue with Order #{order.order_number} | Vape Cluster',
            'template': 'emails/order_failed.html',
        },
    }

    email_config = status_email_map.get(new_status)

    if email_config:
        context = {
            'order': order,
            'order_number': order.order_number,
            'old_status': old_status,
            'new_status': new_status,
            'tracking_number': getattr(order, 'tracking_number', None),
            'tracking_url': getattr(order, 'tracking_url', None),
            'courier': getattr(order, 'courier', None),
            'refund_amount': getattr(order, 'refund_amount', None),
            'cancellation_reason': getattr(order, 'cancellation_reason', None),
            'site_name': 'Vape Cluster',
            'site_url': getattr(settings, 'SITE_URL', 'https://vapecluster.com'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vapecluster.com'),
            'year': timezone.now().year,
        }

        send_notification_email(
            subject=email_config['subject'],
            template_name=email_config['template'],
            context=context,
            recipient_list=[customer_email],
        )
    else:
        logger.info(f"No email template configured for status: {new_status}")


# ---------------------------------------------------------------------------
# PAYMENT SIGNALS (PayFast: EasyPaisa, JazzCash, Debit/Credit Card)
# ---------------------------------------------------------------------------

@receiver(payment_confirmed)
def handle_payment_confirmed(sender, order, payment, **kwargs):
    """
    Fired when a PayFast payment is confirmed.
    Handles EasyPaisa, JazzCash, and Debit/Credit Card payments.
    Sends payment receipt to customer and notifies admin.
    """
    logger.info(
        f"Payment confirmed for Order #{order.order_number} "
        f"via {payment.payment_method} - Amount: {payment.amount}"
    )

    # Determine customer email
    customer_email = None
    if order.user and order.user.email:
        customer_email = order.user.email
    elif hasattr(order, 'email') and order.email:
        customer_email = order.email

    # ------------------------------------------------------------------
    # Send payment receipt to customer
    # ------------------------------------------------------------------
    if customer_email:
        context = {
            'order': order,
            'payment': payment,
            'order_number': order.order_number,
            'payment_method': payment.payment_method,  # easypaysa/jazzcash/card
            'payment_method_display': _get_payment_method_display(payment.payment_method),
            'transaction_id': getattr(payment, 'transaction_id', 'N/A'),
            'payfast_reference': getattr(payment, 'payfast_reference', None),
            'amount_paid': payment.amount,
            'payment_date': payment.created_at if hasattr(payment, 'created_at') else timezone.now(),
            'site_name': 'Vape Cluster',
            'site_url': getattr(settings, 'SITE_URL', 'https://vapecluster.com'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@vapecluster.com'),
            'year': timezone.now().year,
        }

        send_notification_email(
            subject=f'Payment Receipt - #{order.order_number} | Vape Cluster',
            template_name='emails/payment_receipt.html',
            context=context,
            recipient_list=[customer_email],
        )

    # ------------------------------------------------------------------
    # Notify admin of confirmed payment
    # ------------------------------------------------------------------
    admin_emails = get_admin_emails()
    if admin_emails:
        admin_context = {
            'order': order,
            'payment': payment,
            'order_number': order.order_number,
            'customer': order.user,
            'amount': payment.amount,
        }
        send_notification_email(
            subject=f'New Payment Received - #{order.order_number}',
            template_name='emails/admin_payment_alert.html',
            context=admin_context,
            recipient_list=admin_emails,
        )