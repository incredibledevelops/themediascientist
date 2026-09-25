# =============================================================
#  Models — The Media Scientist
#  MongoDB access layer with static-method "models".
# =============================================================
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import secrets
import string

from config import Config


# ------------------------------------------------------------
#  Mongo client & collections
# ------------------------------------------------------------
client = MongoClient(Config.MONGO_URI)
db = client.get_database()

users_col = db.users
inquiries_col = db.inquiries
services_col = db.services
portfolio_col = db.portfolio
about_col = db.about
contact_col = db.contact
settings_col = db.settings
projects_col = db.projects
invoices_col = db.invoices
deliverables_col = db.deliverables
client_messages_col = db.client_messages
payments_col = db.payments


# ------------------------------------------------------------
#  Helpers
# ------------------------------------------------------------
def _now():
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


def gen_temp_password(length=10):
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def gen_client_code():
    """Generate a short client identifier like CLT-A1B2C3."""
    return "CLT-" + secrets.token_hex(3).upper()


def to_oid(value):
    """Safely convert to ObjectId; returns None on failure."""
    if not value:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(value)
    except Exception:
        return None


# =============================================================
#  USER
# =============================================================
class User:
    @staticmethod
    def create(email, password, name="Admin", role="admin"):
        """
        Create a user. Returns (user_doc, plain_password).
        If the email already exists, returns (existing_doc, None).
        """
        if not email or not password:
            return None, None

        email = email.strip().lower()
        existing = users_col.find_one({"email": email})
        if existing:
            return existing, None

        user = {
            "email": email,
            "password": generate_password_hash(password),
            "name": name or "User",
            "role": role,
            "is_admin": role == "admin",
            "client_code": gen_client_code() if role == "client" else None,
            "is_active": True,
            "preferences": {
                "email_on_files": True,
                "email_on_invoices": True,
                "email_on_messages": True,
            },
            "created_at": _now(),
        }
        result = users_col.insert_one(user)
        user["_id"] = result.inserted_id
        return user, password

    @staticmethod
    def find_by_email(email):
        if not email:
            return None
        return users_col.find_one({"email": email.strip().lower()})

    @staticmethod
    def find_by_id(user_id):
        oid = to_oid(user_id)
        if not oid:
            return None
        return users_col.find_one({"_id": oid})

    @staticmethod
    def verify_password(user, password):
        if not user or not user.get("password"):
            return False
        try:
            return check_password_hash(user["password"], password)
        except Exception:
            return False

    @staticmethod
    def get_all():
        return list(users_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_all_clients():
        return list(users_col.find({"role": "client"}).sort("created_at", DESCENDING))

    @staticmethod
    def count_clients():
        return users_col.count_documents({"role": "client"})

    @staticmethod
    def update_password(user_id, new_password):
        oid = to_oid(user_id)
        if not oid or not new_password:
            return None
        return users_col.update_one(
            {"_id": oid},
            {"$set": {"password": generate_password_hash(new_password)}},
        )

    @staticmethod
    def update_preferences(user_id, prefs):
        oid = to_oid(user_id)
        if not oid or not isinstance(prefs, dict):
            return None
        return users_col.update_one(
            {"_id": oid},
            {"$set": {"preferences": prefs}},
        )

    @staticmethod
    def toggle_active(user_id):
        oid = to_oid(user_id)
        if not oid:
            return None
        user = users_col.find_one({"_id": oid})
        if not user:
            return None
        new_state = not user.get("is_active", True)
        users_col.update_one({"_id": oid}, {"$set": {"is_active": new_state}})
        return new_state

    @staticmethod
    def delete(user_id):
        oid = to_oid(user_id)
        if not oid:
            return None
        return users_col.delete_one({"_id": oid})


# =============================================================
#  INQUIRY
# =============================================================
class Inquiry:
    @staticmethod
    def create(data):
        inquiry = {
            "name": data.get("name", "").strip(),
            "email": data.get("email", "").strip(),
            "services": data.get("services", []) or [],
            "budget": data.get("budget", ""),
            "message": data.get("message", "").strip(),
            "status": "new",
            "created_at": _now(),
        }
        return inquiries_col.insert_one(inquiry)

    @staticmethod
    def get_all():
        return list(inquiries_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_recent(limit=5):
        return list(inquiries_col.find().sort("created_at", DESCENDING).limit(limit))

    @staticmethod
    def count():
        return inquiries_col.count_documents({})

    @staticmethod
    def update_status(inquiry_id, status):
        oid = to_oid(inquiry_id)
        if not oid:
            return None
        return inquiries_col.update_one(
            {"_id": oid},
            {"$set": {"status": status}},
        )

    @staticmethod
    def delete(inquiry_id):
        oid = to_oid(inquiry_id)
        if not oid:
            return None
        return inquiries_col.delete_one({"_id": oid})


# =============================================================
#  SERVICE
# =============================================================
class Service:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        data.setdefault("plans", [])
        data.setdefault("order", 99)
        return services_col.insert_one(data)

    @staticmethod
    def get_all():
        return list(services_col.find().sort("order", 1))

    @staticmethod
    def get_by_id(service_id):
        oid = to_oid(service_id)
        if not oid:
            return None
        return services_col.find_one({"_id": oid})

    @staticmethod
    def update(service_id, data):
        oid = to_oid(service_id)
        if not oid:
            return None
        return services_col.update_one({"_id": oid}, {"$set": data})

    @staticmethod
    def update_plans(service_id, plans):
        """Replace the entire plans array for a service."""
        oid = to_oid(service_id)
        if not oid:
            return None
        return services_col.update_one({"_id": oid}, {"$set": {"plans": plans}})

    @staticmethod
    def delete(service_id):
        oid = to_oid(service_id)
        if not oid:
            return None
        return services_col.delete_one({"_id": oid})

    @staticmethod
    def seed_defaults():
        if services_col.count_documents({}) > 0:
            return
        defaults = [
            {
                "title": "Video & Photography",
                "slug": "video-photography",
                "icon": "fa-video",
                "color": "cyan",
                "description": "High-end photography, studio lighting setups, skin retouching, and cinematic video editing with color grading.",
                "order": 1,
                "plans": [
                    {"name": "Basic Portrait Plan", "price": "GH₵ 800 - GH₵ 1,500", "desc": "Includes studio/location shoot, 5-10 high-end retouched photos, color correction, and digital delivery."},
                    {"name": "Standard Event & Video Plan", "price": "GH₵ 2,500 - GH₵ 5,000", "desc": "Includes full event coverage, edited highlight video reel (4K), professional sound design, and color grading."},
                    {"name": "Commercial Production Plan", "price": "GH₵ 6,000+", "desc": "Full commercial shoot setup, multi-cam coverage, advanced color grading, motion edits, and full license rights."}
                ]
            },
            {
                "title": "Motion Graphics & Design",
                "slug": "motion-design",
                "icon": "fa-wand-magic-sparkles",
                "color": "purple",
                "description": "Eye-catching 2D/3D animated logos, graphic flyers, social media brand kits, and video intro graphics.",
                "order": 2,
                "plans": [
                    {"name": "Graphic Design Starter", "price": "GH₵ 600 - GH₵ 1,500", "desc": "Custom logo design, brand color palette, font selections, and 3 promotional artwork flyers."},
                    {"name": "2D/3D Motion Promo Plan", "price": "GH₵ 2,000 - GH₵ 4,000", "desc": "30-second animated product promo video, animated logo intro/outro, sound design, and custom typography."},
                    {"name": "Complete Brand Identity & Motion", "price": "GH₵ 5,000+", "desc": "Full visual identity system, vector source files, 3D animated motion assets, and complete video brand kit."}
                ]
            },
            {
                "title": "Web & Software Development",
                "slug": "web-development",
                "icon": "fa-laptop-code",
                "color": "emerald",
                "description": "Custom landing pages, web portals, e-commerce stores, desktop applications, and fast responsive layouts.",
                "order": 3,
                "plans": [
                    {"name": "Landing Page & Portfolio", "price": "GH₵ 1,500 - GH₵ 3,500", "desc": "Modern single-page or 3-page site, responsive mobile design, fast performance, contact forms, and SEO setup."},
                    {"name": "Business App / E-Commerce Plan", "price": "GH₵ 4,500 - GH₵ 9,000", "desc": "Custom web application, Paystack payment integration, user account systems, database setup, and admin dashboard."},
                    {"name": "Custom Enterprise Software", "price": "GH₵ 12,000+", "desc": "Full-scale software development, API backend architecture, multi-tenant portal, cloud setup, and ongoing maintenance."}
                ]
            },
            {
                "title": "Digital Marketing & Growth",
                "slug": "digital-marketing",
                "icon": "fa-chart-pie",
                "color": "cyan",
                "description": "Targeted social media ad campaigns, content creation plans, brand visibility, and qualified lead generation.",
                "order": 4,
                "plans": [
                    {"name": "Starter Ad Campaign", "price": "GH₵ 1,000 - GH₵ 2,000 / mo", "desc": "Targeted Meta/TikTok ad setup, target audience research, basic ad graphics, lead pixel tracking, and performance reporting."},
                    {"name": "Growth & Content Plan", "price": "GH₵ 3,000 - GH₵ 6,000 / mo", "desc": "Includes promotional video ads creation, weekly campaign management, A/B testing, and conversion rate optimization."},
                    {"name": "Full Brand Scale Strategy", "price": "GH₵ 8,000+ / mo", "desc": "End-to-end digital growth strategy, continuous video content production, web landing page integration, and dedicated campaign optimization."}
                ]
            },
        ]
        services_col.insert_many(defaults)


# =============================================================
#  PORTFOLIO
# =============================================================
class PortfolioItem:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        return portfolio_col.insert_one(data)

    @staticmethod
    def get_all(category=None):
        query = {}
        if category and category != 'all':
            query["category_key"] = category
        return list(portfolio_col.find(query).sort("created_at", DESCENDING))

    @staticmethod
    def get_by_id(item_id):
        oid = to_oid(item_id)
        if not oid:
            return None
        return portfolio_col.find_one({"_id": oid})

    @staticmethod
    def update(item_id, data):
        oid = to_oid(item_id)
        if not oid:
            return None
        return portfolio_col.update_one({"_id": oid}, {"$set": data})

    @staticmethod
    def delete(item_id):
        oid = to_oid(item_id)
        if not oid:
            return None
        return portfolio_col.delete_one({"_id": oid})

    @staticmethod
    def count():
        return portfolio_col.count_documents({})

    @staticmethod
    def seed_defaults():
        if portfolio_col.count_documents({}) > 0:
            return
        defaults = [
            {
                "title": "Commercial Beauty Photo Edit",
                "category": "Photo & Retouch",
                "category_key": "visual",
                "tools": "DaVinci Resolve, Photoshop, Lightroom",
                "description": "High-end beauty retouching paired with color grading for a commercial photo campaign.",
                "image": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80"
            },
            {
                "title": "Animated Product Promo Video",
                "category": "Video & Motion",
                "category_key": "video",
                "tools": "After Effects, Premiere Pro",
                "description": "3D motion graphics animation and sleek titles created for a high-energy product launch video.",
                "image": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"
            },
            {
                "title": "Modern Business Website Application",
                "category": "Websites & Software",
                "category_key": "code",
                "tools": "React, Tailwind CSS, JavaScript",
                "description": "A fast, responsive business website featuring custom design and mobile responsiveness.",
                "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80"
            },
            {
                "title": "Brand Identity & Logo Design",
                "category": "Graphic Design",
                "category_key": "brand",
                "tools": "Illustrator, Photoshop, Figma",
                "description": "Complete visual branding package including custom logos, typography, and social media flyers.",
                "image": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80"
            },
            {
                "title": "Studio Lighting Portrait Series",
                "category": "Photo & Retouching",
                "category_key": "visual",
                "tools": "Sony FX3, Studio Lights, Lightroom",
                "description": "Studio portrait photography project focusing on creative lighting setup and natural skin texture.",
                "image": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=800&q=80"
            },
            {
                "title": "Digital Marketing Landing Page",
                "category": "Websites & Software",
                "category_key": "code",
                "tools": "HTML, JavaScript, Meta Pixel",
                "description": "An interactive promotional web landing page integrated with social media ad tracking.",
                "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80"
            },
        ]
        portfolio_col.insert_many(defaults)


# =============================================================
#  SITE CONTENT (about / contact / settings)
# =============================================================
class SiteContent:
    @staticmethod
    def get_about():
        doc = about_col.find_one({"_id": "about"})
        if not doc:
            doc = {
                "_id": "about",
                "heading": "The Person Behind The Brand",
                "bio": "I am Opoku Kwadwo Incredible, known as The Media Scientist. I connect powerful visual storytelling with modern software technology.",
                "bio2": "Instead of separating photography, video production, photo retouching, animation, and web development, I combine them into a smooth, complete service to help individuals and businesses grow.",
                "quote": "Every project is a chance to make someone's vision a reality — with precision, care, and a bit of science.",
                "skills": [
                    {"name": "Photo Retouching & Color Grading", "level": 98},
                    {"name": "Photography & Videography", "level": 95},
                    {"name": "Motion Graphics & Animation", "level": 92},
                    {"name": "Web Development & Programming", "level": 94},
                    {"name": "Digital Marketing & Graphic Design", "level": 90}
                ],
                "tools": ["DaVinci Resolve", "Photoshop & Lightroom", "After Effects & Premiere Pro",
                          "HTML, CSS & JavaScript", "React, Python & Flask", "Meta Ads & Analytics"],
                "stats": [
                    {"key": "years", "label": "Years", "value": "7+", "color": "cyan"},
                    {"key": "projects", "label": "Projects", "value": "50+", "color": "purple"},
                    {"key": "happy", "label": "Happy", "value": "100%", "color": "emerald"},
                ],
            }
            about_col.insert_one(doc)
        return doc

    @staticmethod
    def update_about(data):
        data = dict(data)
        data.pop("_id", None)
        return about_col.update_one({"_id": "about"}, {"$set": data}, upsert=True)

    @staticmethod
    def get_contact():
        doc = contact_col.find_one({"_id": "contact"})
        if not doc:
            doc = {
                "_id": "contact",
                "email": "contact@themediascientist.com",
                "location": "Kumasi, Ghana // Available Worldwide Remote",
                "instagram": "https://instagram.com/themediascientist_",
                "tiktok": "https://tiktok.com/@themediascientist",
                "youtube": "#",
                "github": "#",
                "phone": "+233 (0) 55 123 4567",
            }
            contact_col.insert_one(doc)
        return doc

    @staticmethod
    def update_contact(data):
        data = dict(data)
        data.pop("_id", None)
        return contact_col.update_one({"_id": "contact"}, {"$set": data}, upsert=True)

    @staticmethod
    def get_settings():
        doc = settings_col.find_one({"_id": "settings"})
        if not doc:
            doc = {
                "_id": "settings",
                "site_title": "The Media Scientist",
                "owner_name": "Opoku Kwadwo Incredible",
                "tagline": "Combining Media Production, Visual Art & Software Development",
                "status": "AVAILABLE FOR HIRE",
                "hero_description": "Bringing together creativity and technical precision. I build high-impact websites, shoot high-quality videos, create professional graphic designs, retouch photos, and help brands grow online.",
            }
            settings_col.insert_one(doc)
        return doc

    @staticmethod
    def update_settings(data):
        data = dict(data)
        data.pop("_id", None)
        return settings_col.update_one({"_id": "settings"}, {"$set": data}, upsert=True)


# =============================================================
#  PROJECT
# =============================================================
class Project:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        data.setdefault("progress", 0)
        data.setdefault("status", "in_progress")
        data.setdefault("stage_label", "Kickoff")
        return projects_col.insert_one(data)

    @staticmethod
    def get_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return []
        return list(projects_col.find({"client_id": oid}).sort("created_at", DESCENDING))

    @staticmethod
    def get_all():
        return list(projects_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_by_id(project_id):
        oid = to_oid(project_id)
        if not oid:
            return None
        return projects_col.find_one({"_id": oid})

    @staticmethod
    def update(project_id, data):
        oid = to_oid(project_id)
        if not oid:
            return None
        return projects_col.update_one({"_id": oid}, {"$set": data})

    @staticmethod
    def delete(project_id):
        oid = to_oid(project_id)
        if not oid:
            return None
        return projects_col.delete_one({"_id": oid})

    @staticmethod
    def count():
        return projects_col.count_documents({})

    @staticmethod
    def count_active_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return 0
        return projects_col.count_documents({
            "client_id": oid,
            "status": {"$in": ["in_progress", "review"]},
        })


# =============================================================
#  INVOICE
# =============================================================
class Invoice:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        data.setdefault("status", "pending")
        return invoices_col.insert_one(data)

    @staticmethod
    def get_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return []
        return list(invoices_col.find({"client_id": oid}).sort("created_at", DESCENDING))

    @staticmethod
    def get_all():
        return list(invoices_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_by_id(invoice_id):
        oid = to_oid(invoice_id)
        if not oid:
            return None
        return invoices_col.find_one({"_id": oid})

    @staticmethod
    def get_by_reference(reference):
        if not reference:
            return None
        return invoices_col.find_one({"payment_reference": reference})

    @staticmethod
    def update(invoice_id, data):
        oid = to_oid(invoice_id)
        if not oid:
            return None
        return invoices_col.update_one({"_id": oid}, {"$set": data})

    @staticmethod
    def mark_paid(invoice_id, reference=None):
        oid = to_oid(invoice_id)
        if not oid:
            return None
        update_data = {"status": "paid", "paid_at": _now()}
        if reference:
            update_data["payment_reference"] = reference
        return invoices_col.update_one({"_id": oid}, {"$set": update_data})

    @staticmethod
    def delete(invoice_id):
        oid = to_oid(invoice_id)
        if not oid:
            return None
        return invoices_col.delete_one({"_id": oid})

    @staticmethod
    def pending_total_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return 0
        pipeline = [
            {"$match": {"client_id": oid, "status": "pending"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        res = list(invoices_col.aggregate(pipeline))
        return res[0]["total"] if res else 0


# =============================================================
#  DELIVERABLE
# =============================================================
class Deliverable:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        data.setdefault("reviewed", False)
        return deliverables_col.insert_one(data)

    @staticmethod
    def get_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return []
        return list(deliverables_col.find({"client_id": oid}).sort("created_at", DESCENDING))

    @staticmethod
    def get_all():
        return list(deliverables_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_by_id(deliverable_id):
        oid = to_oid(deliverable_id)
        if not oid:
            return None
        return deliverables_col.find_one({"_id": oid})

    @staticmethod
    def count_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return 0
        return deliverables_col.count_documents({"client_id": oid, "reviewed": False})

    @staticmethod
    def mark_reviewed(deliverable_id):
        oid = to_oid(deliverable_id)
        if not oid:
            return None
        return deliverables_col.update_one({"_id": oid}, {"$set": {"reviewed": True}})

    @staticmethod
    def delete(deliverable_id):
        oid = to_oid(deliverable_id)
        if not oid:
            return None
        return deliverables_col.delete_one({"_id": oid})


# =============================================================
#  CLIENT MESSAGE
# =============================================================
class ClientMessage:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        data.setdefault("read", False)
        data.setdefault("from_role", "client")
        return client_messages_col.insert_one(data)

    @staticmethod
    def get_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return []
        return list(client_messages_col.find({"client_id": oid}).sort("created_at", 1))

    @staticmethod
    def count_unread_for_admin():
        return client_messages_col.count_documents({"from_role": "client", "read": False})

    @staticmethod
    def count_unread_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return 0
        return client_messages_col.count_documents({
            "client_id": oid,
            "from_role": "admin",
            "read": False,
        })

    @staticmethod
    def mark_read_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return None
        return client_messages_col.update_many(
            {"client_id": oid, "from_role": "admin"},
            {"$set": {"read": True}},
        )

    @staticmethod
    def mark_read_for_admin(client_id):
        oid = to_oid(client_id)
        if not oid:
            return None
        return client_messages_col.update_many(
            {"client_id": oid, "from_role": "client"},
            {"$set": {"read": True}},
        )


# =============================================================
#  PAYMENT (audit log)
# =============================================================
class Payment:
    @staticmethod
    def create(data):
        data = dict(data)
        data["created_at"] = _now()
        return payments_col.insert_one(data)

    @staticmethod
    def get_all():
        return list(payments_col.find().sort("created_at", DESCENDING))

    @staticmethod
    def get_for_client(client_id):
        oid = to_oid(client_id)
        if not oid:
            return []
        return list(payments_col.find({"client_id": oid}).sort("created_at", DESCENDING))


# =============================================================
#  SEED — runs on first app boot
# =============================================================
def seed_database():
    """Ensure essential data exists on startup."""
    User.create(
        Config.ADMIN_EMAIL,
        Config.ADMIN_PASSWORD,
        "Opoku Kwadwo Incredible",
        role="admin",
    )
    Service.seed_defaults()
    PortfolioItem.seed_defaults()
    SiteContent.get_about()
    SiteContent.get_contact()
    SiteContent.get_settings()