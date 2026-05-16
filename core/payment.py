# vape_cluster/payments/payfast.py
# Complete PayFast payment integration for vape_cluster
# Supports EasyPaisa, JazzCash, and Debit/Credit Card payments

import hashlib
import hmac
import urllib.parse
import requests
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PAYFAST CONFIGURATION
# ─────────────────────────────────────────────

PAYFAST_CONFIG = {
    # Toggle between sandbox and live mode
    "SANDBOX_MODE": getattr(settings, "PAYFAST_SANDBOX", True),

    # Merchant credentials — replace with real values in settings.py
    "MERCHANT_ID": getattr(settings, "PAYFAST_MERCHANT_ID", "YOUR_MERCHANT_ID"),
    "MERCHANT_KEY": getattr(settings, "PAYFAST_MERCHANT_KEY", "YOUR_MERCHANT_KEY"),

    # Passphrase set in PayFast dashboard (used for signature hashing)
    "PASSPHRASE": getattr(settings, "PAYFAST_PASSPHRASE", "YOUR_PASSPHRASE"),

    # URLs PayFast will POST notifications to
    "NOTIFY_URL": getattr(settings, "PAYFAST_NOTIFY_URL", "https://yourdomain.com/payments/notify/"),
    "RETURN_URL": getattr(settings, "PAYFAST_RETURN_URL", "https://yourdomain.com/payments/success/"),
    "CANCEL_URL": getattr(settings, "PAYFAST_CANCEL_URL", "https://yourdomain.com/payments/cancel/"),

    # PayFast API endpoints
    "SANDBOX_URL": "https://sandbox.payfast.co.za/eng/process",
    "LIVE_URL": "https://www.payfast.co.za/eng/process",

    # Sandbox and live query endpoints for payment verification
    "SANDBOX_QUERY_URL": "https://api.payfast.co.za/transactions/lookup/{pf_payment_id}?testing=true",
    "LIVE_QUERY_URL": "https://api.payfast.co.za/transactions/lookup/{pf_payment_id}",

    # PayFast valid IPs for ITN (Instant Transfer Notification) verification
    "VALID_IPS": [
        "197.97.145.144",
        "197.97.145.145",
        "197.97.145.146",
        "197.97.145.147",
        "41.74.179.194",
    ],

    # EasyPaisa & JazzCash are handled via PayFast gateway in Pakistan
    # These are the payment method codes PayFast uses
    "PAYMENT_METHODS": {
        "CARD": "cc",          # Credit/Debit Card
        "EASYPAISA": "ep",     # EasyPaisa wallet
        "JAZZCASH": "jc",      # JazzCash wallet
    },

    # Currency for transactions
    "CURRENCY": "PKR",

    # Maximum seconds allowed between payment generation and verification
    "PAYMENT_TIMEOUT_SECONDS": 600,
}


def get_payfast_url():
    """Return the correct PayFast processing URL based on mode."""
    if PAYFAST_CONFIG["SANDBOX_MODE"]:
        return PAYFAST_CONFIG["SANDBOX_URL"]
    return PAYFAST_CONFIG["LIVE_URL"]


def get_query_url(pf_payment_id):
    """Return the correct PayFast query URL for verifying a payment."""
    if PAYFAST_CONFIG["SANDBOX_MODE"]:
        return PAYFAST_CONFIG["SANDBOX_QUERY_URL"].format(pf_payment_id=pf_payment_id)
    return PAYFAST_CONFIG["LIVE_QUERY_URL"].format(pf_payment_id=pf_payment_id)


# ─────────────────────────────────────────────
# SIGNATURE GENERATION & VERIFICATION
# ─────────────────────────────────────────────

def generate_signature(data: dict, passphrase: str = None) -> str:
    """
    Generate an MD5 signature for PayFast payment data.
    PayFast requires parameters sorted alphabetically, URL-encoded,
    joined as query string, then MD5-hashed.
    """
    # Remove any existing signature from the data before hashing
    payload = {k: v for k, v in data.items() if k != "signature" and v != ""}

    # Sort keys alphabetically as PayFast requires
    sorted_payload = sorted(payload.items())

    # Build query string — PayFast uses standard URL encoding
    query_string = urllib.parse.urlencode(sorted_payload)

    # Append passphrase if provided
    if passphrase:
        query_string += f"&passphrase={urllib.parse.quote_plus(passphrase)}"

    # Generate MD5 hash
    signature = hashlib.md5(query_string.encode("utf-8")).hexdigest()
    return signature


def verify_payment_signature(data: dict, received_signature: str) -> bool:
    """
    Verify that the signature received from PayFast matches
    what we generate locally. Prevents tampered notifications.
    """
    try:
        # Generate our own signature from the received data
        expected_signature = generate_signature(
            data, PAYFAST_CONFIG["PASSPHRASE"]
        )

        # Use hmac.compare_digest for timing-safe comparison
        return hmac.compare_digest(expected_signature, received_signature)

    except Exception as e:
        logger.error(f"[PayFast] Signature verification failed: {e}")
        return False


# ─────────────────────────────────────────────
# PAYMENT DATA GENERATION
# ─────────────────────────────────────────────

def generate_payment_data(order, payment_method: str = "CARD") -> dict:
    """
    Build the complete payment data dictionary for PayFast.

    Args:
        order: Django Order model instance with fields:
               - id, total_price, customer (User), billing info
        payment_method: One of 'CARD', 'EASYPAISA', 'JAZZCASH'

    Returns:
        dict with all PayFast fields + generated signature
    """
    # Validate payment method
    method_code = PAYFAST_CONFIG["PAYMENT_METHODS"].get(payment_method.upper())
    if not method_code:
        raise ValueError(
            f"Invalid payment method: {payment_method}. "
            f"Choose from: {list(PAYFAST_CONFIG['PAYMENT_METHODS'].keys())}"
        )

    # Build a unique merchant reference using order ID + timestamp
    merchant_reference = f"ORDER-{order.id}-{int(datetime.now().timestamp())}"

    # Format amount to 2 decimal places as PayFast requires
    amount = f"{Decimal(str(order.total_price)):.2f}"

    # Collect buyer details from the order
    customer = order.customer
    first_name = getattr(customer, "first_name", "") or "Customer"
    last_name = getattr(customer, "last_name", "") or ""
    email = getattr(customer, "email", "") or "noreply@vapecluster.com"
    phone = getattr(order, "phone_number", "") or ""

    # Core payment data required by PayFast
    payment_data = {
        # Merchant credentials
        "merchant_id": PAYFAST_CONFIG["MERCHANT_ID"],
        "merchant_key": PAYFAST_CONFIG["MERCHANT_KEY"],

        # Redirect URLs
        "return_url": PAYFAST_CONFIG["RETURN_URL"],
        "cancel_url": PAYFAST_CONFIG["CANCEL_URL"],
        "notify_url": PAYFAST_CONFIG["NOTIFY_URL"],

        # Buyer info
        "name_first": first_name[:100],
        "name_last": last_name[:100],
        "email_address": email[:200],
        "cell_number": phone[:20],

        # Payment details
        "m_payment_id": merchant_reference,
        "amount": amount,
        "item_name": f"Vape Cluster Order #{order.id}"[:100],
        "item_description": f"Payment for Order #{order.id} from Vape Cluster"[:255],

        # Custom field to store our internal order ID for retrieval in notify
        "custom_int1": str(order.id),
        "custom_str1": payment_method.upper(),

        # Force specific payment method on PayFast checkout
        "payment_method": method_code,
    }

    # Add EasyPaisa-specific fields if applicable
    if payment_method.upper() == "EASYPAISA":
        payment_data.update(_build_easypaisa_data(order, phone))

    # Add JazzCash-specific fields if applicable
    elif payment_method.upper() == "JAZZCASH":
        payment_data.update(_build_jazzcash_data(order, phone))

    # Add Card-specific fields if applicable
    elif payment_method.upper() == "CARD":
        payment_data.update(_build_card_data(order))

    # Generate and append signature last (must not be included in hash)
    payment_data["signature"] = generate_signature(
        payment_data, PAYFAST_CONFIG["PASSPHRASE"]
    )

    return payment_data


def _build_easypaisa_data(order, phone: str) -> dict:
    """
    Extra fields specific to EasyPaisa mobile wallet payments.
    EasyPaisa requires the customer's mobile number for OTP verification.
    """
    return {
        # EasyPaisa registered mobile number (03XXXXXXXXX format)
        "ep_mobile": phone.strip() if phone else "",
        # Additional metadata for reconciliation
        "custom_str2": "EASYPAISA",
        "custom_str3": f"EP-ORDER-{order.id}",
    }


def _build_jazzcash_data(order, phone: str) -> dict:
    """
    Extra fields specific to JazzCash mobile wallet payments.
    JazzCash also needs mobile number for wallet deduction.
    """
    return {
        # JazzCash registered mobile number
        "jc_mobile": phone.strip() if phone else "",
        # Additional metadata for reconciliation
        "custom_str2": "JAZZCASH",
        "custom_str3": f"JC-ORDER-{order.id}",
    }


def _build_card_data(order) -> dict:
    """
    Extra fields for Debit/Credit Card payments.
    Enables card-specific features like 3D Secure.
    """
    return {
        # Allow saving card for future payments (optional feature)
        "subscription_type": "",
        # Additional metadata
        "custom_str2": "CARD",
        "custom_str3": f"CARD-ORDER-{order.id}",
    }


# ─────────────────────────────────────────────
# PAYMENT PROCESSING
# ─────────────────────────────────────────────

def process_payment(order, payment_method: str = "CARD") -> dict:
    """
    Main function to initiate a PayFast payment.
    Generates payment data and returns the form URL + fields
    needed to redirect the customer to PayFast.

    Args:
        order: Order model instance
        payment_method: 'CARD', 'EASYPAISA', or 'JAZZCASH'

    Returns:
        {
            'success': bool,
            'payment_url': str (PayFast URL to POST to),
            'payment_data': dict (form fields),
            'transaction_id': str,
            'error': str (only on failure)
        }
    """
    try:
        # Check for duplicate pending payments for this order
        if _is_duplicate_payment(order):
            logger.warning(f"[PayFast] Duplicate payment attempt for Order #{order.id}")
            return {
                "success": False,
                "error": "A payment for this order is already being processed.",
                "payment_url": None,
                "payment_data": None,
                "transaction_id": None,
            }

        # Validate the order before sending to PayFast
        validation_result = _validate_order(order)
        if not validation_result["valid"]:
            logger.error(
                f"[PayFast] Order validation failed for Order #{order.id}: "
                f"{validation_result['reason']}"
            )
            return {
                "success": False,
                "error": validation_result["reason"],
                "payment_url": None,
                "payment_data": None,
                "transaction_id": None,
            }

        # Generate unique transaction ID for tracking
        transaction_id = str(uuid.uuid4()).replace("-", "")[:32]

        # Generate the full payment data package
        payment_data = generate_payment_data(order, payment_method)

        # Store transaction ID in custom field for later retrieval
        payment_data["custom_str4"] = transaction_id

        # Re-sign after adding transaction ID
        payment_data["signature"] = generate_signature(
            payment_data, PAYFAST_CONFIG["PASSPHRASE"]
        )

        # Mark order as payment-initiated in the database
        _mark_payment_initiated(order, transaction_id, payment_method)

        logger.info(
            f"[PayFast] Payment initiated for Order #{order.id} "
            f"via {payment_method}, Transaction: {transaction_id}"
        )

        return {
            "success": True,
            "payment_url": get_payfast_url(),
            "payment_data": payment_data,
            "transaction_id": transaction_id,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[PayFast] process_payment error for Order #{order.id}: {e}")
        return {
            "success": False,
            "error": "Payment processing failed. Please try again.",
            "payment_url": None,
            "payment_data": None,
            "transaction_id": None,
        }


def _validate_order(order) -> dict:
    """
    Validate an order before sending it to PayFast.
    Checks amount, status, and required fields.
    """
    # Order must exist
    if not order:
        return {"valid": False, "reason": "Order not found."}

    # Amount must be positive
    if not order.total_price or Decimal(str(order.total_price)) <= 0:
        return {"valid": False, "reason": "Order total must be greater than zero."}

    # Minimum transaction amount (PayFast requirement)
    if Decimal(str(order.total_price)) < Decimal("10.00"):
        return {"valid": False, "reason": "Minimum payment amount is PKR 10."}

    # Order must not already be paid
    if hasattr(order, "payment_status") and order.payment_status == "PAID":
        return {"valid": False, "reason": "This order has already been paid."}

    # Order must not be cancelled
    if hasattr(order, "status") and order.status == "CANCELLED":
        return {"valid": False, "reason": "Cannot process payment for a cancelled order."}

    return {"valid": True, "reason": None}


def _is_duplicate_payment(order) -> bool:
    """
    Check if a payment is already in progress for this order.
    Prevents double-charging customers on page refresh.
    """
    try:
        # Import here to avoid circular imports
        from vape_cluster.orders.models import PaymentTransaction

        # Look for any pending transaction created in the last 10 minutes
        cutoff = timezone.now() - timedelta(
            seconds=PAYFAST_CONFIG["PAYMENT_TIMEOUT_SECONDS"]
        )

        return PaymentTransaction.objects.filter(
            order