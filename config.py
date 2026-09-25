# =============================================================
#  Configuration Loader — The Media Scientist
#  Reads environment variables from .env
#
#  Production behavior:
#    - Critical vars (SECRET_KEY, SITE_URL, MONGO_URI) MUST be set.
#    - Missing critical vars raise EnvironmentError at startup.
#    - No development fallbacks — configuration lives in .env only.
# =============================================================
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ============================================================
#  Environment helpers
#  IMPORTANT: These MUST be defined before the Config class.
# ============================================================
def _require(key):
    """
    Read a REQUIRED env var. Raises EnvironmentError if missing or empty.
    Strips whitespace.
    """
    value = os.getenv(key)
    if value is None or not value.strip():
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Add it to your .env file."
        )
    return value.strip()


def _env(key, default=None):
    """Read an optional env var, strip whitespace, return default if empty."""
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _env_url(key, required=False, default=None):
    """
    Read an env var as a URL.
    - Strips whitespace and trailing slash.
    - When required=True, raises if missing.
    """
    if required:
        value = _require(key)
    else:
        value = _env(key, default)
        if value is None:
            return None
    return value.rstrip('/')


def _bool_env(key, default=False):
    """Parse a boolean environment variable safely."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def _int_env(key, default):
    """Read an env var as an integer, with a safe fallback."""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


# ============================================================
#  Config
# ============================================================
class Config:
    # ------------------------------------------------------------
    # Core — CRITICAL, must be set in .env
    # ------------------------------------------------------------
    SECRET_KEY = _require('SECRET_KEY')
    SITE_URL = _env_url('SITE_URL', required=True)
    PREFERRED_URL_SCHEME = 'https' if SITE_URL.startswith('https') else 'http'

    # ------------------------------------------------------------
    # Session cookie hardening
    # ------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = SITE_URL.startswith('https')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SITE_URL.startswith('https')
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 days

    # ------------------------------------------------------------
    # MongoDB — CRITICAL
    # ------------------------------------------------------------
    MONGO_URI = _require('MONGO_URI')

    # ------------------------------------------------------------
    # Paystack — optional (falls back to empty; app degrades gracefully)
    # ------------------------------------------------------------
    PAYSTACK_SECRET_KEY = _env('PAYSTACK_SECRET_KEY', '')
    PAYSTACK_PUBLIC_KEY = _env('PAYSTACK_PUBLIC_KEY', '')

    # ------------------------------------------------------------
    # Mail — optional (falls back to empty; mailer skips if unset)
    # ------------------------------------------------------------
    MAIL_SERVER = _env('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = _int_env('MAIL_PORT', 587)
    MAIL_USERNAME = _env('MAIL_USERNAME', '')
    MAIL_PASSWORD = _env('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = _env('MAIL_DEFAULT_SENDER', '')

    # ------------------------------------------------------------
    # Admin seeding — optional (only used on first run if DB is empty)
    # ------------------------------------------------------------
    ADMIN_EMAIL = _env('ADMIN_EMAIL', 'admin@gmail.com')
    ADMIN_PASSWORD = _env('ADMIN_PASSWORD', 'admin123')

    # ------------------------------------------------------------
    # File uploads
    # ------------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = _int_env('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg',
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'zip', 'rar', '7z',
        'mp4', 'mov', 'avi', 'mkv', 'webm',
        'mp3', 'wav',
        'psd', 'ai', 'fig', 'sketch', 'xd',
        'txt', 'csv',
    }