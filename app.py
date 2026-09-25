# =============================================================
#  The Media Scientist — Flask Application
#  Opoku Kwadwo Incredible
# =============================================================

import os
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, send_from_directory,
    abort, send_file, Response,
)
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user,
)
from werkzeug.utils import secure_filename

from config import Config
from models import (
    User, Inquiry, Service, PortfolioItem, SiteContent, seed_database,
    Project, Invoice, Deliverable, ClientMessage, Payment,
    gen_temp_password, deliverables_col, to_oid,
)
import mailer
import paystack
from pdf_generator import generate_invoice_pdf


# =============================================================
#  APP INITIALIZATION
# =============================================================
app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'lab_login'
login_manager.login_message = "Please log in to access the Lab Console."
login_manager.login_message_category = "error"


# =============================================================
#  HELPERS
# =============================================================

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def human_filesize(num_bytes):
    """Convert bytes to human-readable format (KB, MB, GB)."""
    try:
        num_bytes = float(num_bytes)
    except (ValueError, TypeError):
        return '—'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def icon_for_filename(filename):
    """Return a Font Awesome icon class based on file extension."""
    ext = filename.rsplit('.', 1)[-1].lower() if filename and '.' in filename else ''
    if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'):
        return 'fa-regular fa-image'
    if ext == 'pdf':
        return 'fa-solid fa-file-pdf'
    if ext in ('doc', 'docx'):
        return 'fa-solid fa-file-word'
    if ext in ('xls', 'xlsx', 'csv'):
        return 'fa-solid fa-file-excel'
    if ext in ('ppt', 'pptx'):
        return 'fa-solid fa-file-powerpoint'
    if ext in ('zip', 'rar', '7z'):
        return 'fa-solid fa-file-zipper'
    if ext in ('mp4', 'mov', 'avi', 'mkv', 'webm'):
        return 'fa-solid fa-file-video'
    if ext in ('mp3', 'wav'):
        return 'fa-solid fa-file-audio'
    if ext in ('psd', 'ai', 'fig', 'sketch', 'xd'):
        return 'fa-solid fa-palette'
    return 'fa-regular fa-file'


def safe_str(obj):
    """Safely convert any object to a string for template use."""
    if obj is None:
        return ''
    return str(obj)


def client_safe_filename(number):
    """Sanitize an invoice number for use as a download filename."""
    if not number:
        return 'invoice'
    return str(number).replace('/', '-').replace('\\', '-')


# =============================================================
#  USER MODEL (Flask-Login wrapper)
# =============================================================

class LoginUser(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.email = user_doc['email']
        self.name = user_doc.get('name', 'User')
        self.role = user_doc.get('role', 'admin')
        self.client_code = user_doc.get('client_code')
        self.is_active_flag = user_doc.get('is_active', True)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_client(self):
        return self.role == 'client'


@login_manager.user_loader
def load_user(user_id):
    doc = User.find_by_id(user_id)
    if doc:
        return LoginUser(doc)
    return None


# =============================================================
#  DECORATORS
# =============================================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "error")
            return redirect(url_for('lab_login'))
        return f(*args, **kwargs)
    return decorated


def client_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'client':
            flash("Client access required.", "error")
            return redirect(url_for('client_login'))
        return f(*args, **kwargs)
    return decorated


# =============================================================
#  CONTEXT PROCESSORS
# =============================================================

@app.context_processor
def inject_globals():
    ctx = {
        'site_settings': SiteContent.get_settings(),
        'current_year': datetime.now(timezone.utc).year,
        'pending_invoice_count': 0,
        'unreviewed_file_count': 0,
        'unread_message_count': 0,
    }
    if current_user.is_authenticated and getattr(current_user, 'role', None) == 'client':
        try:
            ctx['pending_invoice_count'] = len([
                i for i in Invoice.get_for_client(current_user.id)
                if i.get('status') == 'pending'
            ])
            ctx['unreviewed_file_count'] = Deliverable.count_for_client(current_user.id)
            ctx['unread_message_count'] = ClientMessage.count_unread_for_client(current_user.id)
        except Exception:
            pass
    return ctx


# =============================================================
#  SEO: robots.txt & sitemap.xml (dynamic host replacement)
# =============================================================

@app.route('/robots.txt')
def robots():
    """Serve robots.txt with the base URL replaced by the current SITE_URL."""
    path = os.path.join(app.root_path, 'robots.txt')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for placeholder in (
        'https://themediascientist.com',
        'http://162.35.183.139:5004',
        'http://localhost:5004',
    ):
        content = content.replace(placeholder, Config.SITE_URL)
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    """Serve sitemap.xml with the base URL replaced by the current SITE_URL."""
    path = os.path.join(app.root_path, 'sitemap.xml')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for placeholder in (
        'https://themediascientist.com',
        'http://162.35.183.139:5004',
        'http://localhost:5004',
    ):
        content = content.replace(placeholder, Config.SITE_URL)
    return Response(content, mimetype='application/xml')


# =============================================================
#  PUBLIC SITE ROUTES
# =============================================================

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
        try:
            mailer.send_inquiry_notification(data, Config.ADMIN_EMAIL)
            mailer.send_inquiry_confirmation(data)
        except Exception as e:
            print(f"[MAIL NOTIFY ERROR] {e}")

        flash("Thank you! Your inquiry has been sent. I'll get back to you within 24 hours.", "success")
        return redirect(url_for('contact'))

    contact_data = SiteContent.get_contact()
    return render_template('contact.html', contact=contact_data)


# =============================================================
#  FILE DOWNLOADS (protected — client must own the file)
# =============================================================

@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    """Serve an uploaded file. Only admin or the owning client can download."""
    target = deliverables_col.find_one({"stored_filename": filename})

    if not target:
        abort(404)

    if current_user.role == 'client':
        if str(target.get('client_id')) != current_user.id:
            abort(403)
        Deliverable.mark_reviewed(str(target['_id']))

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True,
        download_name=target.get('name', filename),
    )


# =============================================================
#  ADMIN / LAB CONSOLE ROUTES
# =============================================================

@app.route('/lab/login', methods=['GET', 'POST'])
def lab_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('lab_dashboard'))
        return redirect(url_for('client_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user_doc = User.find_by_email(email)
        if user_doc and User.verify_password(user_doc, password):
            if user_doc.get("role", "admin") != "admin":
                flash("This account is a client account. Please use the client portal.", "error")
                return redirect(url_for('client_login'))
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
        'clients_count': User.count_clients(),
        'projects_count': Project.count(),
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
    try:
        order = int(request.form.get('order', 99))
    except (ValueError, TypeError):
        order = 99

    data = {
        'title': request.form.get('title', ''),
        'slug': request.form.get('slug', ''),
        'icon': request.form.get('icon', 'fa-cog'),
        'color': request.form.get('color', 'cyan'),
        'description': request.form.get('description', ''),
        'order': order,
        'plans': [],
    }
    Service.create(data)
    flash("Service created.", "success")
    return redirect(url_for('lab_services'))


@app.route('/lab/services/<service_id>/update', methods=['POST'])
@login_required
@admin_required
def lab_service_update(service_id):
    try:
        order = int(request.form.get('order', 99))
    except (ValueError, TypeError):
        order = 99

    data = {
        'title': request.form.get('title', ''),
        'description': request.form.get('description', ''),
        'icon': request.form.get('icon', 'fa-cog'),
        'color': request.form.get('color', 'cyan'),
        'order': order,
    }
    Service.update(service_id, data)
    flash("Service updated.", "success")
    return redirect(url_for('lab_services'))


@app.route('/lab/services/<service_id>/update-plans', methods=['POST'])
@login_required
@admin_required
def lab_service_update_plans(service_id):
    """Replace the entire plans array for a service."""
    names = request.form.getlist('plan_name[]')
    prices = request.form.getlist('plan_price[]')
    descs = request.form.getlist('plan_desc[]')

    plans = []
    for i in range(len(names)):
        name = (names[i] or '').strip()
        price = (prices[i] if i < len(prices) else '').strip()
        desc = (descs[i] if i < len(descs) else '').strip()
        if not name:
            continue
        plans.append({
            'name': name,
            'price': price or 'Contact for quote',
            'desc': desc,
        })

    Service.update_plans(service_id, plans)
    flash(f"Saved {len(plans)} plan{'s' if len(plans) != 1 else ''}.", "success")
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
        # Parse skills from parallel arrays
        skill_names = request.form.getlist('skill_name[]')
        skill_levels = request.form.getlist('skill_level[]')
        skills = []
        for name, level in zip(skill_names, skill_levels):
            name = (name or '').strip()
            if not name:
                continue
            try:
                lvl = max(0, min(100, int(level)))
            except (ValueError, TypeError):
                lvl = 50
            skills.append({'name': name, 'level': lvl})

        # Tools from comma-separated string
        tools_raw = request.form.get('tools', '') or ''
        tools = [t.strip() for t in tools_raw.split(',') if t.strip()]

        # Stats
        stats = [
            {'key': 'years',    'label': 'Years',    'value': (request.form.get('stat_years')    or '0').strip(), 'color': 'cyan'},
            {'key': 'projects', 'label': 'Projects', 'value': (request.form.get('stat_projects') or '0').strip(), 'color': 'purple'},
            {'key': 'happy',    'label': 'Happy',    'value': (request.form.get('stat_happy')    or '0').strip(), 'color': 'emerald'},
        ]

        data = {
            'heading': request.form.get('heading', '').strip(),
            'bio':     request.form.get('bio', '').strip(),
            'bio2':    request.form.get('bio2', '').strip(),
            'quote':   request.form.get('quote', '').strip(),
            'skills':  skills,
            'tools':   tools,
            'stats':   stats,
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
            'email':     request.form.get('email', ''),
            'phone':     request.form.get('phone', ''),
            'location':  request.form.get('location', ''),
            'instagram': request.form.get('instagram', ''),
            'tiktok':    request.form.get('tiktok', ''),
            'youtube':   request.form.get('youtube', ''),
            'github':    request.form.get('github', ''),
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
    role = request.form.get('role', 'admin')
    if not email or not password:
        flash("Email and password required.", "error")
        return redirect(url_for('lab_users'))
    User.create(email, password, name, role=role)
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
            'site_title':        request.form.get('site_title', ''),
            'owner_name':        request.form.get('owner_name', ''),
            'tagline':           request.form.get('tagline', ''),
            'status':            request.form.get('status', ''),
            'hero_description':  request.form.get('hero_description', ''),
        }
        SiteContent.update_settings(data)
        flash("Settings updated.", "success")
        return redirect(url_for('lab_settings'))

    settings = SiteContent.get_settings()
    return render_template('lab/settings.html', settings=settings)


# =============================================================
#  LAB: CLIENT MANAGEMENT
# =============================================================

@app.route('/lab/clients')
@login_required
@admin_required
def lab_clients():
    clients = User.get_all_clients()
    for c in clients:
        c['project_count'] = len(Project.get_for_client(c['_id']))
        c['pending_total'] = Invoice.pending_total_for_client(c['_id'])
    return render_template('lab/clients.html', clients=clients)


@app.route('/lab/clients/create', methods=['POST'])
@login_required
@admin_required
def lab_client_create():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    send_email_flag = request.form.get('send_email') == 'on'

    if not name or not email:
        flash("Client name and email are required.", "error")
        return redirect(url_for('lab_clients'))

    if User.find_by_email(email):
        flash(f"A user with email {email} already exists.", "error")
        return redirect(url_for('lab_clients'))

    temp_password = gen_temp_password(10)
    user_doc, _ = User.create(email, temp_password, name, role="client")

    login_url = url_for('client_login', _external=True)

    if send_email_flag:
        try:
            mailer.send_client_credentials(email, name, user_doc.get("client_code"), temp_password, login_url)
            flash(f"Client {name} created. Credentials emailed to {email}.", "success")
        except Exception as e:
            print(f"[MAIL CLIENT ERROR] {e}")
            flash(f"Client created but email failed. Temp password: {temp_password}", "error")
    else:
        flash(f"Client {name} created. Temp password: {temp_password}", "success")

    return redirect(url_for('lab_clients'))


@app.route('/lab/clients/<client_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def lab_client_reset_password(client_id):
    user_doc = User.find_by_id(client_id)
    if not user_doc:
        flash("Client not found.", "error")
        return redirect(url_for('lab_clients'))

    new_password = gen_temp_password(10)
    User.update_password(client_id, new_password)

    send_email_flag = request.form.get('send_email') == 'on'
    if send_email_flag:
        try:
            mailer.send_client_password_reset(
                user_doc['email'],
                user_doc['name'],
                new_password,
                url_for('client_login', _external=True),
            )
            flash(f"Password reset. New password emailed to {user_doc['email']}.", "success")
        except Exception as e:
            print(f"[MAIL RESET ERROR] {e}")
            flash(f"Password reset. New password: {new_password}", "error")
    else:
        flash(f"Password reset. New password: {new_password}", "success")

    return redirect(url_for('lab_clients'))


@app.route('/lab/clients/<client_id>/toggle', methods=['POST'])
@login_required
@admin_required
def lab_client_toggle(client_id):
    if str(current_user.id) == client_id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for('lab_clients'))
    new_state = User.toggle_active(client_id)
    if new_state is None:
        flash("Client not found.", "error")
    else:
        flash(f"Client {'activated' if new_state else 'deactivated'}.", "success")
    return redirect(url_for('lab_clients'))


@app.route('/lab/clients/<client_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_client_delete(client_id):
    if str(current_user.id) == client_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('lab_clients'))
    User.delete(client_id)
    flash("Client deleted.", "success")
    return redirect(url_for('lab_clients'))


@app.route('/lab/clients/<client_id>/projects')
@login_required
@admin_required
def lab_client_projects(client_id):
    user_doc = User.find_by_id(client_id)
    if not user_doc or user_doc.get('role') != 'client':
        flash("Client not found.", "error")
        return redirect(url_for('lab_clients'))

    projects = Project.get_for_client(client_id)
    invoices = Invoice.get_for_client(client_id)
    deliverables = Deliverable.get_for_client(client_id)

    return render_template(
        'lab/client_projects.html',
        client=user_doc,
        projects=projects,
        invoices=invoices,
        deliverables=deliverables,
    )


@app.route('/lab/clients/<client_id>/projects/create', methods=['POST'])
@login_required
@admin_required
def lab_client_project_create(client_id):
    oid = to_oid(client_id)
    if not oid:
        flash("Invalid client.", "error")
        return redirect(url_for('lab_clients'))

    try:
        progress = max(0, min(100, int(request.form.get('progress', 0))))
    except (ValueError, TypeError):
        progress = 0

    data = {
        "client_id": oid,
        "title": request.form.get('title', 'Untitled Project'),
        "service": request.form.get('service', ''),
        "timeline": request.form.get('timeline', ''),
        "progress": progress,
        "status": request.form.get('status', 'in_progress'),
        "stage_label": request.form.get('stage_label', 'Kickoff'),
    }
    Project.create(data)
    flash("Project created.", "success")
    return redirect(url_for('lab_client_projects', client_id=client_id))


@app.route('/lab/projects/<project_id>/update', methods=['POST'])
@login_required
@admin_required
def lab_project_update(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for('lab_clients'))

    try:
        progress = max(0, min(100, int(request.form.get('progress', project.get('progress', 0)))))
    except (ValueError, TypeError):
        progress = project.get('progress', 0)

    data = {
        "title":       request.form.get('title', project.get('title', '')),
        "service":     request.form.get('service', project.get('service', '')),
        "timeline":    request.form.get('timeline', project.get('timeline', '')),
        "progress":    progress,
        "status":      request.form.get('status', project.get('status', 'in_progress')),
        "stage_label": request.form.get('stage_label', project.get('stage_label', '')),
    }
    Project.update(project_id, data)
    flash("Project updated.", "success")
    return redirect(url_for('lab_client_projects', client_id=str(project['client_id'])))


@app.route('/lab/projects/<project_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_project_delete(project_id):
    project = Project.get_by_id(project_id)
    if not project:
        flash("Project not found.", "error")
        return redirect(url_for('lab_clients'))
    cid = str(project['client_id'])
    Project.delete(project_id)
    flash("Project deleted.", "success")
    return redirect(url_for('lab_client_projects', client_id=cid))


# ---------- Lab: Invoices ----------

@app.route('/lab/clients/<client_id>/invoices/create', methods=['POST'])
@login_required
@admin_required
def lab_invoice_create(client_id):
    oid = to_oid(client_id)
    if not oid:
        flash("Invalid client.", "error")
        return redirect(url_for('lab_clients'))

    try:
        amount = float(request.form.get('amount', 0) or 0)
    except (ValueError, TypeError):
        amount = 0.0

    data = {
        "client_id": oid,
        "number":    request.form.get('number') or ('INV-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')),
        "amount":    amount,
        "due_date":  request.form.get('due_date', ''),
        "description": request.form.get('description', 'Professional services rendered'),
        "status":    request.form.get('status', 'pending'),
    }
    Invoice.create(data)
    flash("Invoice created.", "success")
    return redirect(url_for('lab_client_projects', client_id=client_id))


@app.route('/lab/invoices/<invoice_id>/update', methods=['POST'])
@login_required
@admin_required
def lab_invoice_update(invoice_id):
    inv = Invoice.get_by_id(invoice_id)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for('lab_clients'))

    try:
        amount = float(request.form.get('amount', inv.get('amount', 0)) or 0)
    except (ValueError, TypeError):
        amount = inv.get('amount', 0)

    data = {
        "number":      request.form.get('number', inv.get('number')),
        "amount":      amount,
        "due_date":    request.form.get('due_date', inv.get('due_date', '')),
        "description": request.form.get('description', inv.get('description', '')),
        "status":      request.form.get('status', inv.get('status', 'pending')),
    }
    Invoice.update(invoice_id, data)
    flash("Invoice updated.", "success")
    return redirect(url_for('lab_client_projects', client_id=str(inv['client_id'])))


@app.route('/lab/invoices/<invoice_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_invoice_delete(invoice_id):
    inv = Invoice.get_by_id(invoice_id)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for('lab_clients'))
    cid = str(inv['client_id'])
    Invoice.delete(invoice_id)
    flash("Invoice deleted.", "success")
    return redirect(url_for('lab_client_projects', client_id=cid))


# ---------- Lab: Deliverables (FILE UPLOAD) ----------

@app.route('/lab/clients/<client_id>/deliverables/upload', methods=['POST'])
@login_required
@admin_required
def lab_deliverable_upload(client_id):
    if 'file' not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for('lab_client_projects', client_id=client_id))

    file = request.files['file']
    if not file or file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('lab_client_projects', client_id=client_id))

    if not allowed_file(file.filename):
        flash("File type not allowed.", "error")
        return redirect(url_for('lab_client_projects', client_id=client_id))

    oid = to_oid(client_id)
    if not oid:
        flash("Invalid client.", "error")
        return redirect(url_for('lab_clients'))

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else 'bin'
    stored_filename = f"{secrets.token_hex(12)}.{ext}"

    save_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
    file.save(save_path)

    size_bytes = os.path.getsize(save_path)

    data = {
        "client_id":       oid,
        "name":            original_name,
        "stored_filename": stored_filename,
        "size":            human_filesize(size_bytes),
        "size_bytes":      size_bytes,
        "file_type":       icon_for_filename(original_name),
    }
    Deliverable.create(data)
    flash(f"File '{original_name}' uploaded successfully.", "success")
    return redirect(url_for('lab_client_projects', client_id=client_id))


@app.route('/lab/deliverables/<deliverable_id>/delete', methods=['POST'])
@login_required
@admin_required
def lab_deliverable_delete(deliverable_id):
    d = Deliverable.get_by_id(deliverable_id)
    if not d:
        flash("Deliverable not found.", "error")
        return redirect(url_for('lab_clients'))
    cid = str(d['client_id'])

    # Remove file from disk
    stored = d.get('stored_filename')
    if stored:
        path = os.path.join(app.config['UPLOAD_FOLDER'], stored)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"[FILE DELETE ERROR] {e}")

    Deliverable.delete(deliverable_id)
    flash("Deliverable deleted.", "success")
    return redirect(url_for('lab_client_projects', client_id=cid))


# =============================================================
#  CLIENT PORTAL ROUTES
# =============================================================

@app.route('/client/login', methods=['GET', 'POST'])
def client_login():
    if current_user.is_authenticated:
        if current_user.role == 'client':
            return redirect(url_for('client_dashboard'))
        return redirect(url_for('lab_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user_doc = User.find_by_email(email)
        if user_doc and User.verify_password(user_doc, password):
            if user_doc.get("role", "client") != "client":
                flash("This is an admin account. Please use the Lab Console.", "error")
                return redirect(url_for('client_login'))
            if not user_doc.get("is_active", True):
                flash("Your account has been deactivated. Please contact support.", "error")
                return redirect(url_for('client_login'))
            remember = request.form.get('remember') == 'on'
            user = LoginUser(user_doc)
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for('client_dashboard'))
        flash("Invalid credentials. Please try again.", "error")

    return render_template('client/login.html')


@app.route('/client/logout')
@login_required
def client_logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for('client_login'))


@app.route('/client')
@app.route('/client/dashboard')
@login_required
@client_required
def client_dashboard():
    cid = current_user.id
    projects = Project.get_for_client(cid)
    invoices = Invoice.get_for_client(cid)
    deliverables = Deliverable.get_for_client(cid)

    active_projects = [p for p in projects if p.get('status') in ('in_progress', 'review')]
    pending_total = Invoice.pending_total_for_client(cid)
    unreviewed_files = [d for d in deliverables if not d.get('reviewed', False)]

    next_deadline = None
    for p in projects:
        tl = p.get('timeline', '')
        if tl and p.get('status') != 'completed':
            next_deadline = tl
            break

    stats = {
        'active_projects': len(active_projects),
        'pending_total': pending_total,
        'unreviewed_files': len(unreviewed_files),
        'next_deadline': next_deadline,
        'projects': projects,
        'invoices': invoices,
        'deliverables': deliverables,
    }
    return render_template('client/dashboard.html', stats=stats, client=current_user)


@app.route('/client/projects')
@login_required
@client_required
def client_projects():
    projects = Project.get_for_client(current_user.id)
    return render_template('client/projects.html', projects=projects, client=current_user)


@app.route('/client/invoices')
@login_required
@client_required
def client_invoices():
    invoices = Invoice.get_for_client(current_user.id)
    pending_total = Invoice.pending_total_for_client(current_user.id)
    return render_template(
        'client/invoices.html',
        invoices=invoices,
        pending_total=pending_total,
        client=current_user,
    )


@app.route('/client/files')
@login_required
@client_required
def client_files():
    deliverables = Deliverable.get_for_client(current_user.id)
    return render_template('client/files.html', deliverables=deliverables, client=current_user)


@app.route('/client/messages', methods=['GET', 'POST'])
@login_required
@client_required
def client_messages():
    if request.method == 'POST':
        body = request.form.get('message', '').strip()
        if body:
            ClientMessage.create({
                "client_id": to_oid(current_user.id),
                "from_role": "client",
                "from_name": current_user.name,
                "body": body,
            })
            flash("Message sent.", "success")
        return redirect(url_for('client_messages'))

    ClientMessage.mark_read_for_client(current_user.id)
    messages = ClientMessage.get_for_client(current_user.id)
    return render_template('client/messages.html', messages=messages, client=current_user)


# ---------- Client: Settings ----------

@app.route('/client/settings', methods=['GET', 'POST'])
@login_required
@client_required
def client_settings():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user_doc = User.find_by_id(current_user.id)
        if not user_doc:
            flash("Account not found.", "error")
            return redirect(url_for('client_login'))

        if not User.verify_password(user_doc, current_password):
            flash("Current password is incorrect.", "error")
            return redirect(url_for('client_settings'))
        if not new_password or len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
            return redirect(url_for('client_settings'))
        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('client_settings'))

        User.update_password(current_user.id, new_password)
        flash("Password updated successfully.", "success")
        return redirect(url_for('client_settings'))

    return render_template('client/settings.html', client=current_user)


@app.route('/client/settings/preferences', methods=['POST'])
@login_required
@client_required
def client_settings_preferences():
    prefs = {
        'email_on_files':    request.form.get('email_on_files')    == 'on',
        'email_on_invoices': request.form.get('email_on_invoices') == 'on',
        'email_on_messages': request.form.get('email_on_messages') == 'on',
    }
    User.update_preferences(current_user.id, prefs)
    flash("Notification preferences updated.", "success")
    return redirect(url_for('client_settings'))


@app.route('/client/logout-all', methods=['POST'])
@login_required
@client_required
def client_logout_all():
    """Sign out from all devices (best-effort)."""
    logout_user()
    flash("You've been signed out of all devices.", "success")
    return redirect(url_for('client_login'))


@app.route('/client/delete-account', methods=['POST'])
@login_required
@client_required
def client_delete_account():
    """Delete the client's own account after they type DELETE to confirm."""
    confirm = request.form.get('confirm', '').strip().upper()
    if confirm != 'DELETE':
        flash("Please type DELETE to confirm account deletion.", "error")
        return redirect(url_for('client_settings'))

    user_doc = User.find_by_id(current_user.id)
    if not user_doc:
        flash("Account not found.", "error")
        return redirect(url_for('client_login'))

    if user_doc.get('role') != 'client':
        flash("This action is only available for client accounts.", "error")
        return redirect(url_for('client_settings'))

    User.delete(current_user.id)
    logout_user()
    flash("Your account has been deleted. We're sorry to see you go.", "success")
    return redirect(url_for('index'))


# =============================================================
#  PDF INVOICE DOWNLOAD
# =============================================================

@app.route('/client/invoices/<invoice_id>/pdf')
@login_required
def client_invoice_pdf(invoice_id):
    """Generate & serve a PDF invoice. Accessible by admin or owning client."""
    invoice = Invoice.get_by_id(invoice_id)
    if not invoice:
        abort(404)

    if current_user.role == 'client':
        if str(invoice.get('client_id')) != current_user.id:
            abort(403)

    client_doc = User.find_by_id(str(invoice.get('client_id')))
    if not client_doc:
        abort(404)

    settings = SiteContent.get_settings()
    buffer = generate_invoice_pdf(invoice, client_doc, settings)

    filename = f"{client_safe_filename(invoice.get('number', 'invoice'))}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


# =============================================================
#  PAYSTACK PAYMENT FLOW
# =============================================================

@app.route('/client/invoices/<invoice_id>/pay')
@login_required
@client_required
def client_invoice_pay(invoice_id):
    """Initialize a Paystack transaction for an invoice and redirect to checkout."""
    invoice = Invoice.get_by_id(invoice_id)
    if not invoice:
        flash("Invoice not found.", "error")
        return redirect(url_for('client_invoices'))

    if str(invoice.get('client_id')) != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for('client_invoices'))

    if invoice.get('status') == 'paid':
        flash("This invoice is already paid.", "success")
        return redirect(url_for('client_invoices'))

    try:
        amount_ghs = float(invoice.get('amount', 0) or 0)
    except (ValueError, TypeError):
        amount_ghs = 0.0

    amount_kobo = int(amount_ghs * 100)

    reference = f"INV-{str(invoice['_id'])[:8]}-{secrets.token_hex(4)}"
    callback_url = url_for('client_invoice_verify', invoice_id=invoice_id, _external=True)

    result = paystack.initialize_transaction(
        email=current_user.email,
        amount_kobo=amount_kobo,
        reference=reference,
        callback_url=callback_url,
        metadata={
            "invoice_id":     str(invoice['_id']),
            "invoice_number": invoice.get('number'),
            "client_id":      current_user.id,
            "custom_fields": [
                {"display_name": "Invoice", "variable_name": "invoice_number", "value": invoice.get('number', '')},
                {"display_name": "Client",  "variable_name": "client_name",    "value": current_user.name},
            ],
        },
    )

    if not result.get('status'):
        flash(f"Payment initialization failed: {result.get('message', 'Unknown error')}", "error")
        return redirect(url_for('client_invoices'))

    Invoice.update(invoice_id, {"payment_reference": reference})
    return redirect(result['data']['authorization_url'])


@app.route('/client/invoices/<invoice_id>/verify')
@login_required
@client_required
def client_invoice_verify(invoice_id):
    """Verify the Paystack transaction after the user returns from checkout."""
    invoice = Invoice.get_by_id(invoice_id)
    if not invoice:
        flash("Invoice not found.", "error")
        return redirect(url_for('client_invoices'))

    if str(invoice.get('client_id')) != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for('client_invoices'))

    reference = request.args.get('reference') or invoice.get('payment_reference')
    if not reference:
        flash("No payment reference found.", "error")
        return redirect(url_for('client_invoices'))

    result = paystack.verify_transaction(reference)
    if not result.get('status'):
        flash(f"Payment verification failed: {result.get('message', 'Unknown error')}", "error")
        return redirect(url_for('client_invoices'))

    data = result.get('data', {})
    pay_status = data.get('status')
    amount_paid = data.get('amount', 0) / 100.0

    if pay_status == 'success':
        Invoice.mark_paid(invoice_id, reference=reference)
        Payment.create({
            "client_id":  to_oid(current_user.id),
            "invoice_id": to_oid(invoice_id),
            "amount":     amount_paid,
            "reference":  reference,
            "status":     "success",
            "channel":    data.get('channel', 'card'),
            "currency":   data.get('currency', 'GHS'),
        })
        flash(f"Payment successful! GH₵ {amount_paid:,.2f} received for {invoice.get('number')}.", "success")
    else:
        flash(f"Payment was not successful. Status: {pay_status}", "error")

    return redirect(url_for('client_invoices'))


# ---------- API: Paystack webhook ----------

@app.route('/api/paystack/webhook', methods=['POST'])
def paystack_webhook():
    import json as _json

    signature = request.headers.get('x-paystack-signature', '')
    if not paystack.verify_webhook_signature(request.data, signature):
        return jsonify({'status': False, 'message': 'Invalid signature'}), 400

    try:
        event = _json.loads(request.data)
    except Exception:
        return jsonify({'status': False, 'message': 'Bad JSON'}), 400

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        reference = data.get('reference')
        inv = Invoice.get_by_reference(reference)
        if inv and inv.get('status') != 'paid':
            Invoice.mark_paid(str(inv['_id']), reference=reference)

    return jsonify({'status': True}), 200


# ---------- API: generic Paystack init ----------

@app.route('/api/paystack/initialize', methods=['POST'])
def api_paystack_init():
    data = request.get_json() or {}
    email = data.get('email')
    amount = data.get('amount', 10000)
    if not email:
        return jsonify({'status': False, 'message': 'Email required'}), 400
    result = paystack.initialize_transaction(
        email, amount,
        callback_url=url_for('index', _external=True),
    )
    return jsonify(result)


# =============================================================
#  ERROR HANDLERS
# =============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error_code=404, error_msg="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_msg="Server error"), 500


# =============================================================
#  APP BOOTSTRAP
# =============================================================

with app.app_context():
    seed_database()


if __name__ == '__main__':
    # In production, use: gunicorn --workers 3 --bind 0.0.0.0:5004 app:app
    app.run(debug=True, host='0.0.0.0', port=5004)