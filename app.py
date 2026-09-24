from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, send_from_directory, abort
)
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from datetime import datetime
from functools import wraps
import os

from config import Config
from models import (
    User, Inquiry, Service, PortfolioItem, SiteContent, seed_database
)
import mailer
import paystack


app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager(app)
login_manager.login_view = 'lab_login'
login_manager.login_message = "Please log in to access the Lab Console."


# ---------- User Loader ----------
class LoginUser(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.email = user_doc['email']
        self.name = user_doc.get('name', 'Admin')
        self.is_admin = user_doc.get('is_admin', True)


@login_manager.user_loader
def load_user(user_id):
    doc = User.find_by_id(user_id)
    if doc:
        return LoginUser(doc)
    return None


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            flash("Admin access required.", "error")
            return redirect(url_for('lab_login'))
        return f(*args, **kwargs)
    return decorated


# ---------- Context Processors ----------
@app.context_processor
def inject_globals():
    return {
        'site_settings': SiteContent.get_settings(),
        'current_year': datetime.utcnow().year,
    }


# ==========================================================
#  PUBLIC SITE ROUTES
# ==========================================================

@app.route('/')
def index():
    services = Service.get_all()
    portfolio = PortfolioItem.get_all()[:6]
    about = SiteContent.get_about()
    return render_template('index.html', services=services, portfolio=portfolio, about=about)


@app.route('/about')
def about():
    about_data = SiteContent.get_about()
    return render_template('about.html', about=about_data)


@app.route('/services')
def services():
    services_list = Service.get_all()
    return render_template('services.html', services=services_list)


@app.route('/portfolio')
def portfolio():
    category = request.args.get('category', 'all')
    items = PortfolioItem.get_all(category if category != 'all' else None)
    return render_template('portfolio.html', portfolio=items, active_category=category)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'services': request.form.getlist('services'),
            'budget': request.form.get('budget', ''),
            'message': request.form.get('message', '').strip(),
        }
        if not data['name'] or not data['email'] or not data['message']:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('contact'))

        Inquiry.create(data)
        # Optional email notifications
        try:
            mailer.send_inquiry_notification(data, Config.ADMIN_EMAIL)
            mailer.send_inquiry_confirmation(data)
        except Exception as e:
            print(f"[MAIL NOTIFY ERROR] {e}")

        flash("Thank you! Your inquiry has been sent. I'll get back to you within 24 hours.", "success")
        return redirect(url_for('contact'))

    contact_data = SiteContent.get_contact()
    return render_template('contact.html', contact=contact_data)


@app.route('/robots.txt')
def robots():
    return send_from_directory(app.root_path, 'robots.txt')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(app.root_path, 'sitemap.xml')


# ==========================================================
#  ADMIN / LAB CONSOLE ROUTES
# ==========================================================

@app.route('/lab/login', methods=['GET', 'POST'])
def lab_login():
    if current_user.is_authenticated:
        return redirect(url_for('lab_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user_doc = User.find_by_email(email)
        if user_doc and User.verify_password(user_doc, password):
            user = LoginUser(user_doc)
            login_user(user, remember=True)
            flash("Welcome back to the Lab Console.", "success")
            return redirect(url_for('lab_dashboard'))
        flash("Invalid credentials. Please try again.", "error")

    return render_template('lab/login.html')


@app.route('/lab/logout')
@login_required
def lab_logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('lab_login'))


@app.route('/lab')
@app.route('/lab/dashboard')
@login_required
@admin_required
def lab_dashboard():
    stats = {
        'total_inquiries': Inquiry.count(),
        'portfolio_count': PortfolioItem.count(),
        'services_count': len(Service.get_all()),
        'recent_inquiries': Inquiry.get_recent(5),
        'services': Service.get_all(),
    }
    return render_template('lab/dashboard.html', stats=stats)


# ---------- Lab: Inquiries ----------
@app.route('/lab/inquiries')
@login_required
@admin_required
def lab_inquiries():
    inquiries = Inquiry.get_all()
    return render_template('lab/inquiries.html', inquiries=inquiries)


@app.route('/lab/inquiries/<inquiry_id>/status', methods=['POST'])
@login_required
@admin_required
def lab_inquiry_status(inquiry_id):
    status = request.form.get('status', 'new')
    Inquiry.update_status(inquiry_id, status)
    flash("Inquiry status updated.", "success")
    return redirect(url_for('lab_inquiries'))


@app.route('/lab/inquiries/<inquiry_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_inquiry_delete(inquiry_id):
    Inquiry.delete(inquiry_id)
    flash("Inquiry deleted.", "success")
    return redirect(url_for('lab_inquiries'))


# ---------- Lab: Services ----------
@app.route('/lab/services')
@login_required
@admin_required
def lab_services():
    services_list = Service.get_all()
    return render_template('lab/services.html', services=services_list)


@app.route('/lab/services/create', methods=['POST'])
@login_required
@admin_required
def lab_service_create():
    data = {
        'title': request.form.get('title', ''),
        'slug': request.form.get('slug', ''),
        'icon': request.form.get('icon', 'fa-cog'),
        'color': request.form.get('color', 'cyan'),
        'description': request.form.get('description', ''),
        'order': int(request.form.get('order', 99)),
        'plans': []
    }
    Service.create(data)
    flash("Service created.", "success")
    return redirect(url_for('lab_services'))


@app.route('/lab/services/<service_id>/update', methods=['POST'])
@login_required
@admin_required
def lab_service_update(service_id):
    data = {
        'title': request.form.get('title', ''),
        'description': request.form.get('description', ''),
        'icon': request.form.get('icon', 'fa-cog'),
        'color': request.form.get('color', 'cyan'),
        'order': int(request.form.get('order', 99)),
    }
    Service.update(service_id, data)
    flash("Service updated.", "success")
    return redirect(url_for('lab_services'))


@app.route('/lab/services/<service_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_service_delete(service_id):
    Service.delete(service_id)
    flash("Service deleted.", "success")
    return redirect(url_for('lab_services'))


# ---------- Lab: Portfolio ----------
@app.route('/lab/portfolio')
@login_required
@admin_required
def lab_portfolio():
    items = PortfolioItem.get_all()
    return render_template('lab/portfolio.html', portfolio=items)


@app.route('/lab/portfolio/create', methods=['POST'])
@login_required
@admin_required
def lab_portfolio_create():
    data = {
        'title': request.form.get('title', ''),
        'category': request.form.get('category', ''),
        'category_key': request.form.get('category_key', 'visual'),
        'tools': request.form.get('tools', ''),
        'description': request.form.get('description', ''),
        'image': request.form.get('image', ''),
    }
    PortfolioItem.create(data)
    flash("Portfolio item created.", "success")
    return redirect(url_for('lab_portfolio'))


@app.route('/lab/portfolio/<item_id>/update', methods=['POST'])
@login_required
@admin_required
def lab_portfolio_update(item_id):
    data = {
        'title': request.form.get('title', ''),
        'category': request.form.get('category', ''),
        'category_key': request.form.get('category_key', 'visual'),
        'tools': request.form.get('tools', ''),
        'description': request.form.get('description', ''),
        'image': request.form.get('image', ''),
    }
    PortfolioItem.update(item_id, data)
    flash("Portfolio item updated.", "success")
    return redirect(url_for('lab_portfolio'))


@app.route('/lab/portfolio/<item_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_portfolio_delete(item_id):
    PortfolioItem.delete(item_id)
    flash("Portfolio item deleted.", "success")
    return redirect(url_for('lab_portfolio'))


# ---------- Lab: About ----------
@app.route('/lab/about', methods=['GET', 'POST'])
@login_required
@admin_required
def lab_about():
    if request.method == 'POST':
        data = {
            'heading': request.form.get('heading', ''),
            'bio': request.form.get('bio', ''),
            'bio2': request.form.get('bio2', ''),
        }
        SiteContent.update_about(data)
        flash("About page updated.", "success")
        return redirect(url_for('lab_about'))

    about_data = SiteContent.get_about()
    return render_template('lab/about.html', about=about_data)


# ---------- Lab: Contact ----------
@app.route('/lab/contact', methods=['GET', 'POST'])
@login_required
@admin_required
def lab_contact():
    if request.method == 'POST':
        data = {
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'location': request.form.get('location', ''),
            'instagram': request.form.get('instagram', ''),
            'tiktok': request.form.get('tiktok', ''),
            'youtube': request.form.get('youtube', ''),
            'github': request.form.get('github', ''),
        }
        SiteContent.update_contact(data)
        flash("Contact information updated.", "success")
        return redirect(url_for('lab_contact'))

    contact_data = SiteContent.get_contact()
    return render_template('lab/contact.html', contact=contact_data)


# ---------- Lab: Users ----------
@app.route('/lab/users')
@login_required
@admin_required
def lab_users():
    users = User.get_all()
    return render_template('lab/users.html', users=users)


@app.route('/lab/users/create', methods=['POST'])
@login_required
@admin_required
def lab_user_create():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    name = request.form.get('name', 'Admin')
    if not email or not password:
        flash("Email and password required.", "error")
        return redirect(url_for('lab_users'))
    User.create(email, password, name, True)
    flash(f"User {email} created.", "success")
    return redirect(url_for('lab_users'))


@app.route('/lab/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_user_delete(user_id):
    if str(current_user.id) == user_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('lab_users'))
    User.delete(user_id)
    flash("User deleted.", "success")
    return redirect(url_for('lab_users'))


# ---------- Lab: Settings ----------
@app.route('/lab/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def lab_settings():
    if request.method == 'POST':
        data = {
            'site_title': request.form.get('site_title', ''),
            'owner_name': request.form.get('owner_name', ''),
            'tagline': request.form.get('tagline', ''),
            'status': request.form.get('status', ''),
            'hero_description': request.form.get('hero_description', ''),
        }
        SiteContent.update_settings(data)
        flash("Settings updated.", "success")
        return redirect(url_for('lab_settings'))

    settings = SiteContent.get_settings()
    return render_template('lab/settings.html', settings=settings)


# ---------- API: Paystack test route (optional) ----------
@app.route('/api/paystack/initialize', methods=['POST'])
def api_paystack_init():
    data = request.get_json() or {}
    email = data.get('email')
    amount = data.get('amount', 10000)  # kobo
    if not email:
        return jsonify({'status': False, 'message': 'Email required'}), 400
    result = paystack.initialize_transaction(
        email, amount,
        callback_url=url_for('index', _external=True)
    )
    return jsonify(result)


# ---------- Error Handlers ----------
@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_msg="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_msg="Server error"), 500


# ---------- App Bootstrap ----------
with app.app_context():
    seed_database()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)