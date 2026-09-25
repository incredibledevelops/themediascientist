# =============================================================
#  Paystack API Wrapper — The Media Scientist
#  Docs: https://paystack.com/docs/api/
# =============================================================
import hmac
import hashlib
import secrets
import requests

from config import Config


PAYSTACK_BASE = "https://api.paystack.co"
TIMEOUT = 15  # seconds


# ------------------------------------------------------------
#  Helper: build auth headers
# ------------------------------------------------------------
def _headers():
    return {
        "Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _error(message):
    """Standardized error response matching Paystack's shape."""
    return {"status": False, "message": str(message)}


# ------------------------------------------------------------
#  Initialize a transaction
# ------------------------------------------------------------
def initialize_transaction(email, amount_kobo, reference=None, callback_url=None, metadata=None):
    """
    Initialize a Paystack transaction.

    Args:
        email (str): Customer email
        amount_kobo (int): Amount in kobo (1 GHS = 100 kobo)
        reference (str, optional): Unique transaction reference
        callback_url (str, optional): Where Paystack redirects after checkout
        metadata (dict, optional): Arbitrary data returned on webhook

    Returns:
        dict: Paystack API response (contains `data.authorization_url` on success)
    """
    if not reference:
        reference = secrets.token_hex(8)

    payload = {
        "email": email,
        "amount": int(amount_kobo),
        "reference": reference,
    }
    if callback_url:
        payload["callback_url"] = callback_url
    if metadata:
        payload["metadata"] = metadata

    try:
        r = requests.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            json=payload,
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return r.json()
    except requests.exceptions.Timeout:
        return _error("Paystack request timed out")
    except requests.exceptions.RequestException as e:
        return _error(f"Paystack request failed: {e}")
    except Exception as e:
        return _error(e)


# ------------------------------------------------------------
#  Verify a transaction
# ------------------------------------------------------------
def verify_transaction(reference):
    """
    Verify a Paystack transaction by reference.

    Args:
        reference (str): Transaction reference

    Returns:
        dict: Paystack API response (contains `data.status` on success)
    """
    if not reference:
        return _error("Reference is required")

    try:
        r = requests.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        return r.json()
    except requests.exceptions.Timeout:
        return _error("Paystack verify request timed out")
    except requests.exceptions.RequestException as e:
        return _error(f"Paystack verify failed: {e}")
    except Exception as e:
        return _error(e)


# ------------------------------------------------------------
#  Webhook signature verification
# ------------------------------------------------------------
def verify_webhook_signature(payload_bytes, signature_header):
    """
    Verify a Paystack webhook signature.

    Args:
        payload_bytes (bytes): Raw request body
        signature_header (str): Value of `x-paystack-signature` header

    Returns:
        bool: True if signature matches
    """
    if not payload_bytes or not signature_header:
        return False

    secret = (Config.PAYSTACK_SECRET_KEY or '').encode('utf-8')
    if not secret:
        return False

    computed = hmac.new(secret, payload_bytes, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature_header)