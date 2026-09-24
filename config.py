import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-change-me')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://162.35.183.139:27017/media_scientist')
    SITE_URL = os.getenv('SITE_URL', 'http://localhost:5004')

    # Paystack
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_c45dabd81218e4fac598659fc1368c1dd76e3b26')
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_4caf27ba085782664d98466d38b07ec4d334426a')

    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'okwadwo642@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'bekgtunuejrsfmzt')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'okwadwo642@gmail.com')

    # Admin
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@gmail.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')