import requests
import secrets
from config import Config


PAYSTACK_BASE = "https://api.paystack.co"


def initialize_transaction(email, amount_kobo, reference=None, callback_url=None):
    """Initialize a Paystack transaction. Amount is in kobo (1 GHS = 100 kobo)."""
    if not reference:
        reference = secrets.token_hex(8)

    headers = {
        "Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    try:
        r = requests.post(f"{PAYSTACK_BASE}/transaction/initialize",
                          json=payload, headers=headers, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[PAYSTACK ERROR] {e}")
        return {"status": False, "message": str(e)}


def verify_transaction(reference):
    """Verify a Paystack transaction by reference."""
    headers = {"Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}"}
    try:
        r = requests.get(f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                         headers=headers, timeout=15)
        return r.json()
    except Exception as e:
        print(f"[PAYSTACK VERIFY ERROR] {e}")
        return {"status": False, "message": str(e)}