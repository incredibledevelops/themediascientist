# The Media Scientist

> Personal brand & portfolio website for **Opoku Kwadwo Incredible** — photographer, videographer, editor, retoucher, colorist, motion graphics animator, animator, graphic designer, software developer & digital marketer based in Kumasi, Ghana.

A full-stack Flask application with a public portfolio site, a private **client portal**, and an **admin console** (`/lab`). Powered by MongoDB, Paystack, PDF invoice generation, and file uploads.

---

## 📸 Screenshots

| Public Site | Client Portal | Admin Console |
|-------------|---------------|---------------|
| ![Home](docs/screenshots/home.png) | ![Client](docs/screenshots/client.png) | ![Admin](docs/screenshots/admin.png) |

> *Add your own screenshots to `docs/screenshots/` after first deploy.*

---

## ✨ Features

### 🌐 Public Website

- **Landing page** with animated hero, service previews, and portfolio highlights
- **About page** — bio, skills with animated bars, journey timeline, testimonials
- **Services page** — service packages with pricing plans, FAQ accordion
- **Portfolio** — filterable grid (Photo, Video, Web, Brand), lightbox-ready
- **Contact form** — inquiries saved to MongoDB + email notifications
- Full **SEO**: JSON-LD structured data, Open Graph, Twitter Cards, sitemap, robots.txt
- **Responsive** down to 320px — mobile-first layout with tablet & desktop polish
- **Dark theme** with tech-grid background and glassmorphism

### 👤 Client Portal (`/client`)

- **Secure login** with password visibility toggle + caps-lock warning
- **Dashboard** — KPI cards, active projects, recent files, recent invoices
- **My Projects** — filter by status, sort, search, per-project progress bar
- **Invoices & Billing** — view, download PDF, pay via **Paystack** checkout
- **Files & Deliverables** — thumbnail previews, search, category filters
- **Support Messages** — chat-style UI with date dividers, auto-scroll, copy buttons
- **Account Settings** — password change, notification preferences, session management, account deletion
- Auto-scroll behavior respects user position
- **Accessibility** — ARIA, semantic HTML, focus rings, reduced-motion support

### 🛠️ Admin Console (`/lab`)

- **Dashboard** — global KPIs, system status, quick actions
- **Inquiries** — read, filter, mark as new/read/replied/closed, reply by email
- **Clients** — create client accounts, auto-email credentials, reset passwords, toggle access
- **Client Projects** — manage projects, invoices, deliverables per client
- **Portfolio Manager** — CRUD with image preview + inline editing
- **Services & Pricing** — full CRUD with plan editor (add/remove/edit plans)
- **About Page Editor** — heading, bios, quote, stats, skills, tools
- **Contact Info Editor** — email, phone, location, social links (URL auto-normalization)
- **Users** — create admin/client accounts with password strength meter
- **Site Settings** — brand identity, hero copy, availability status

### 📤 File Uploads

- Drag-style upload zone
- **100 MB** max per file
- Extension whitelist (images, docs, videos, audio, PSDs, ZIPs)
- Hashed filenames (`secrets.token_hex(12)`)
- Access control — clients can only download their own files

### 💳 Paystack Payments

- Initialize transaction from invoice
- Redirect to Paystack checkout
- Verify on callback + webhook confirmation
- Audit log (`payments` collection)
- Mark invoice as paid on success

### 🧾 PDF Invoices

- Generated server-side with **ReportLab**
- Branded with your color palette
- Includes client name, invoice number, line items, total, due date
- Downloadable from client portal or admin console

### 📧 Email Notifications

- Contact form inquiry → notify admin
- Contact form inquiry → confirm to client
- New client credentials → sent to client
- Password reset → sent to client

### 🔍 SEO

- **Structured data**: `WebSite`, `Organization`, `Person`, `LocalBusiness`, `Service`, `OfferCatalog`, `BreadcrumbList`, `ContactPage`, `CollectionPage`, `ProfilePage`
- **Meta tags**: title, description, keywords, robots, canonical, hreflang
- **Open Graph** & **Twitter Card** with dynamic images
- **Sitemap.xml** with `hreflang` alternates and image entries
- **robots.txt** with AI-bot blocking, crawl-delay for SEO tools, social preview allow
- **Semantic HTML5** — `<main>`, `<article>`, `<section>`, `<nav>`, `<aside>`, `<time>`
- **Accessibility** — WCAG 2.1 AA (skip links, ARIA labels, focus visible, reduced motion)

---

## 🧱 Tech Stack

| Layer         | Technology                                        |
| ------------- | ------------------------------------------------- |
| **Backend**   | Python 3.10+ · Flask 3.0                          |
| **Database**  | MongoDB 7.0 (via PyMongo)                         |
| **Auth**      | Flask-Login · Werkzeug password hashing           |
| **Payments**  | Paystack (test & live)                            |
| **PDF**       | ReportLab                                         |
| **Email**     | smtplib (Gmail SMTP)                              |
| **Frontend**  | Tailwind CSS (CDN) · Font Awesome · Vanilla JS    |
| **Fonts**     | Inter · Space Grotesk (Google Fonts)              |
| **Hosting**   | InterServer VPS (recommended)                     |

---

## 📂 Project Structure

```txt
themediascientist/
├── app.py                          # Main Flask application
├── config.py                       # Config loader (reads .env)
├── models.py                       # MongoDB models & helpers
├── mailer.py                       # Email sending utilities
├── paystack.py                     # Paystack API wrapper
├── pdf_generator.py                # ReportLab invoice generator
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (DO NOT COMMIT)
├── .env.example                    # Template for .env
├── .gitignore
├── README.md
├── robots.txt                      # Dynamic, served by Flask
├── sitemap.xml                     # Dynamic, served by Flask
│
├── uploads/                        # User-uploaded files (gitignored)
│   └── .gitkeep
│
└── templates/
    ├── base.html                   # Public site base (SEO-rich)
    ├── index.html                  # Homepage
    ├── about.html
    ├── services.html
    ├── portfolio.html
    ├── contact.html
    │
    ├── client/                     # Client portal (login required)
    │   ├── base.html
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── projects.html
    │   ├── invoices.html
    │   ├── files.html
    │   ├── messages.html
    │   └── settings.html
    │
    └── lab/                        # Admin console (login required)
        ├── base.html
        ├── login.html
        ├── dashboard.html
        ├── inquiries.html
        ├── clients.html
        ├── client_projects.html
        ├── portfolio.html
        ├── services.html
        ├── about.html
        ├── contact.html
        ├── users.html
        └── settings.html
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **MongoDB 6.0+** running locally OR accessible via network
- **Git** (optional)

### 1. Clone & enter project

```bash
git clone https://github.com/yourusername/themediascientist.git
cd themediascientist
```

### 2. Create virtual environment

**Windows (PowerShell):**

```powershell
py -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:

- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `MONGO_URI` — your MongoDB connection string
- `PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` — from [Paystack dashboard](https://dashboard.paystack.com/#/settings/developer)
- `MAIL_USERNAME` / `MAIL_PASSWORD` — Gmail + App Password
- `SITE_URL` — `http://localhost:5004` for dev, `https://yourdomain.com` for prod

### 5. Create uploads folder

```bash
# Windows
mkdir uploads
type nul > uploads\.gitkeep

# macOS / Linux
mkdir -p uploads
touch uploads/.gitkeep
```

### 6. Run

```bash
python app.py
```

Visit **http://localhost:5004**

| URL             | Purpose          |
| --------------- | ---------------- |
| `/`             | Public website   |
| `/lab/login`    | Admin console    |
| `/client/login` | Client portal    |

**Default admin credentials** (from `.env`):

- Email: `admin@gmail.com`
- Password: `admin123`

⚠️ **Change the password immediately after first login.**

---

## ⚙️ Environment Variables

See `.env.example` for the full reference. Key variables:

| Variable                | Required | Description                                          |
| ----------------------- | -------- | ---------------------------------------------------- |
| `SECRET_KEY`            | ✅       | Flask session signing key (min 32 bytes hex)         |
| `SITE_URL`              | ✅       | Full base URL (no trailing slash)                    |
| `MONGO_URI`             | ✅       | MongoDB connection string                            |
| `PAYSTACK_SECRET_KEY`   | ✅       | Server-side Paystack key                             |
| `PAYSTACK_PUBLIC_KEY`   | ✅       | Client-side Paystack key                             |
| `MAIL_SERVER`           | ✅       | SMTP server (default: `smtp.gmail.com`)              |
| `MAIL_PORT`             | ✅       | SMTP port (default: `587`)                           |
| `MAIL_USERNAME`         | ✅       | SMTP username                                        |
| `MAIL_PASSWORD`         | ✅       | SMTP password / app password                         |
| `MAIL_DEFAULT_SENDER`   | ✅       | From address for outgoing mail                       |
| `ADMIN_EMAIL`           | ✅       | Seeds first admin user                               |
| `ADMIN_PASSWORD`        | ✅       | Seeds first admin password                           |
| `MAX_CONTENT_LENGTH`    | ⬜       | Upload size limit in bytes (default: 100 MB)         |
| `FLASK_DEBUG`           | ⬜       | `1` in dev, `0` in production                        |

---

## 🗄️ Database Schema

Collections created automatically on first run:

| Collection         | Purpose                                        |
| ------------------ | ---------------------------------------------- |
| `users`            | Admins + clients (role-based)                  |
| `inquiries`        | Contact form submissions                       |
| `services`         | Service packages with pricing plans            |
| `portfolio`        | Portfolio items                                |
| `projects`         | Client projects (status, progress, timeline)   |
| `invoices`         | Client invoices + Paystack references          |
| `deliverables`     | Uploaded files per client                      |
| `client_messages`  | Support thread between client & admin          |
| `payments`         | Paystack transaction audit log                 |
| `about`            | About page content (single doc)                |
| `contact`          | Contact info (single doc)                      |
| `settings`         | Global site settings (single doc)              |

---

## 🔐 Security

- **Password hashing** via Werkzeug (`pbkdf2:sha256`)
- **Session cookies** — HttpOnly, SameSite=Lax, Secure (in HTTPS)
- **Role-based access** — `@admin_required` and `@client_required` decorators
- **File upload validation** — extension whitelist + filename hashing
- **Paystack webhook** — HMAC SHA-512 signature verification
- **SQL/NoSQL injection** — PyMongo parameterized queries
- **XSS protection** — Jinja2 auto-escaping
- **CSRF** — Flask's built-in secret-based protection for forms
- **Rate limiting** — recommended via `flask-limiter` (not included by default)

### Production Checklist

- [ ] `FLASK_DEBUG=0` in `.env`
- [ ] `SECRET_KEY` is a strong 64-char hex string
- [ ] `SITE_URL` uses `https://`
- [ ] MongoDB has authentication enabled
- [ ] MongoDB is not exposed to the public internet (use SSH tunnel or firewall)
- [ ] Paystack keys are **live** keys
- [ ] Admin password is not `admin123`
- [ ] `.env` is in `.gitignore`
- [ ] HTTPS via Let's Encrypt (Certbot)
- [ ] Reverse proxy (Nginx) with rate limiting
- [ ] Regular MongoDB backups
- [ ] Uptime monitoring configured

---

## 💳 Paystack Setup

### Local Development

1. Sign up at [paystack.com](https://paystack.com)
2. Use **test mode** keys from Settings → API Keys
3. Test card: `4084 0840 8408 4081` · CVV `408` · Expiry any future date
4. OTP: `123456` · PIN: `0000`

### Production

1. Complete KYC verification
2. Switch to **live mode** and copy live keys
3. Set webhook URL: `https://yourdomain.com/api/paystack/webhook`
4. Test with a small live transaction

---

## 📧 Gmail App Password

1. Enable **2-Factor Authentication** on the Google account
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password named "The Media Scientist"
4. Copy the 16-character password to `MAIL_PASSWORD` in `.env`

**Note**: Regular Gmail passwords do NOT work with SMTP. You must use an App Password.

---

## 🌍 Deployment (Ubuntu VPS)

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx mongodb-org
```

### 2. Clone and set up the app

```bash
cd /var/www
sudo git clone https://github.com/yourusername/themediascientist.git
cd themediascientist
sudo python3 -m venv venv
sudo ./venv/bin/pip install -r requirements.txt
```

### 3. Configure `.env` for production

```bash
sudo cp .env.example .env
sudo nano .env
```

Set:

```env
FLASK_ENV=production
FLASK_DEBUG=0
SITE_URL=https://yourdomain.com
SECRET_KEY=<new 64-char hex>
```

### 4. Create systemd service

`/etc/systemd/system/themediascientist.service`:

```ini
[Unit]
Description=The Media Scientist Flask App
After=network.target mongod.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/themediascientist
Environment="PATH=/var/www/themediascientist/venv/bin"
ExecStart=/var/www/themediascientist/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:5004 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable themediascientist
sudo systemctl start themediascientist
sudo systemctl status themediascientist
```

### 5. Configure Nginx

`/etc/nginx/sites-available/themediascientist`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/themediascientist/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/themediascientist /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
sudo certbot renew --dry-run
```

### 7. MongoDB backup (daily cron)

```bash
sudo crontab -e
```

Add:

```cron
0 3 * * * mongodump --uri="mongodb://localhost:27017/media_scientist" --out=/var/backups/mongo/$(date +\%Y\%m\%d) && find /var/backups/mongo -mtime +30 -delete
```

---

## 🧪 Testing

### Manual test flow

1. **Public site** — visit `/`, `/about`, `/services`, `/portfolio`, `/contact`
2. **Submit contact form** — check `/lab/inquiries` for the new entry
3. **Admin login** — `/lab/login` → dashboard
4. **Create a client** — `/lab/clients` → check your email for credentials
5. **Client login** — `/client/login` with those credentials
6. **Add a project + invoice + file** — `/lab/clients/<id>/projects`
7. **Client sees them** — refresh client dashboard
8. **Pay an invoice** — use Paystack test card
9. **Verify paid status** — invoice flips to "Paid"
10. **Download PDF** — check formatting
11. **Test file upload** — anything from `/uploads/<hashed>`

### SEO checks

```bash
# Structured data
curl -s https://yourdomain.com/ | grep -o 'application/ld+json' | wc -l

# Sitemap URLs
curl -s https://yourdomain.com/sitemap.xml | grep '<loc>'

# Robots.txt
curl -s https://yourdomain.com/robots.txt
```

Validate with:

- https://search.google.com/test/rich-results
- https://validator.schema.org/
- https://developers.facebook.com/tools/debug/
- https://cards-dev.twitter.com/validator

---

## 📦 Dependencies

```txt
Flask==3.0.3
Flask-Login==0.6.3
Flask-WTF==1.2.1
WTForms==3.1.2
pymongo==4.7.3
python-dotenv==1.0.1
Werkzeug==3.0.3
requests==2.32.3
email-validator==2.1.1
gunicorn==22.0.0
reportlab==4.2.2
```

---

## 🛠️ Common Issues

### `ModuleNotFoundError: No module named 'flask'`

You forgot to activate the virtual environment.

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### `pymongo.errors.ServerSelectionTimeoutError`

MongoDB isn't running or isn't reachable.

```bash
# Local
sudo systemctl status mongod

# Remote
telnet <host> 27017
```

### `[MAILER ERROR] 535 Authentication failed`

Your Gmail password isn't an App Password.

→ Regenerate at https://myaccount.google.com/apppasswords

### Pillow build error

You shouldn't need Pillow — it's not in `requirements.txt`. If you see this, you accidentally added it.

### `TemplateNotFound: client/dashboard.html`

Missing template folder. Verify:

```bash
ls templates/client/
```

### Port 5004 already in use

```bash
# Windows
netstat -ano | findstr :5004
taskkill /PID <PID> /F

# macOS / Linux
lsof -ti:5004 | xargs kill -9
```

---

## 🎯 Roadmap

- [ ] Blog / case studies section
- [ ] Real-time chat (WebSockets instead of form submits)
- [ ] Multi-language support (English + Twi)
- [ ] Quote builder (client selects services → auto-generates estimate)
- [ ] Recurring invoices
- [ ] Two-factor authentication for admin
- [ ] Google Analytics 4 integration
- [ ] Cloud storage (S3 / Cloudflare R2) for uploads
- [ ] Advanced analytics dashboard (revenue, clients, projects)

---

## 🤝 Contributing

This is a personal project, but suggestions are welcome.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-idea`
3. Commit changes: `git commit -am 'Add feature'`
4. Push: `git push origin feature/your-idea`
5. Open a Pull Request

---

## 📄 License

This project is proprietary. All rights reserved.

© 2026 Opoku Kwadwo Incredible — The Media Scientist

You may **not** redistribute, resell, or use this code as a template for commercial projects without explicit written permission.

For licensing inquiries: **contact@themediascientist.com**

---

## 👤 Author

**Opoku Kwadwo Incredible**  
*The Media Scientist*

- 🌐 [themediascientist.com](https://themediascientist.com)
- 📧 [contact@themediascientist.com](mailto:contact@themediascientist.com)
- 📸 [Instagram @themediascientist\_](https://instagram.com/themediascientist_)
- 🎵 [TikTok @themediascientist](https://tiktok.com/@themediascientist)
- 💻 [GitHub](https://github.com/yourusername)

---

## 🙏 Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [MongoDB](https://www.mongodb.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Font Awesome](https://fontawesome.com/)
- [Paystack](https://paystack.com/)
- [ReportLab](https://www.reportlab.com/)
- [Inter](https://fonts.google.com/specimen/Inter) & [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) fonts

---

## ⭐ Show Your Support

If this project helped you, please ⭐ star the repository.

Built with 💙 in Kumasi, Ghana.