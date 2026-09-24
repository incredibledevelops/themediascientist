import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


def send_email(to_address, subject, html_body):
    """Send an email using SMTP. Returns True on success, False on failure."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME
        msg['To'] = to_address

        part = MIMEText(html_body, 'html')
        msg.attach(part)

        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.sendmail(msg['From'], [to_address], msg.as_string())
        return True
    except Exception as e:
        print(f"[MAILER ERROR] {e}")
        return False


def send_inquiry_notification(inquiry, admin_email):
    """Notify admin of a new inquiry."""
    subject = f"New Project Inquiry from {inquiry.get('name', 'Unknown')}"
    html = f"""
    <h2>New Project Inquiry</h2>
    <p><strong>Name:</strong> {inquiry.get('name')}</p>
    <p><strong>Email:</strong> {inquiry.get('email')}</p>
    <p><strong>Services:</strong> {', '.join(inquiry.get('services', [])) or 'Not specified'}</p>
    <p><strong>Budget:</strong> {inquiry.get('budget')}</p>
    <p><strong>Message:</strong></p>
    <p>{inquiry.get('message')}</p>
    """
    return send_email(admin_email, subject, html)


def send_inquiry_confirmation(inquiry):
    """Confirm receipt to the client."""
    subject = "Thank you for contacting The Media Scientist"
    html = f"""
    <h2>Hello {inquiry.get('name')},</h2>
    <p>Thank you for reaching out! I've received your project inquiry and will get back to you within 24 hours.</p>
    <p><strong>Your message:</strong></p>
    <p>{inquiry.get('message')}</p>
    <br>
    <p>Warm regards,<br>
    <strong>Opoku Kwadwo Incredible</strong><br>
    The Media Scientist</p>
    """
    return send_email(inquiry.get('email'), subject, html)


def send_client_credentials(client_email, client_name, client_code, temp_password, login_url):
    """Send newly created client their portal login details."""
    subject = "Your Media Scientist Client Portal Access"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#0B0E17;color:#F9FAFB;padding:32px;border-radius:16px;">
        <h1 style="color:#00F2FE;margin-top:0;">Welcome to Your Client Portal</h1>
        <p>Hi <strong>{client_name}</strong>,</p>
        <p>An account has been created for you on <strong>The Media Scientist</strong> client portal. You can now log in to track your projects, view invoices, download deliverables, and message directly.</p>

        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);padding:20px;border-radius:12px;margin:24px 0;">
            <p style="margin:0 0 10px;font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;">Login Credentials</p>
            <p style="margin:6px 0;"><strong>Portal URL:</strong> <a href="{login_url}" style="color:#00F2FE;">{login_url}</a></p>
            <p style="margin:6px 0;"><strong>Email:</strong> <span style="color:#00F2FE;">{client_email}</span></p>
            <p style="margin:6px 0;"><strong>Temporary Password:</strong> <span style="color:#00F5A0;font-family:monospace;font-size:16px;">{temp_password}</span></p>
            <p style="margin:6px 0;"><strong>Client ID:</strong> <span style="color:#7928CA;font-family:monospace;">{client_code}</span></p>
        </div>

        <p>Please change your password after your first login for security.</p>

        <a href="{login_url}" style="display:inline-block;background:linear-gradient(90deg,#00F2FE,#7928CA);color:#fff;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:600;margin-top:12px;">Access Client Portal</a>

        <p style="margin-top:32px;font-size:12px;color:#64748b;">If you didn't request this, please ignore this email.</p>
        <p style="font-size:12px;color:#64748b;">— Opoku Kwadwo Incredible, The Media Scientist</p>
    </div>
    """
    return send_email(client_email, subject, html)


def send_client_password_reset(client_email, client_name, new_password, login_url):
    """Send a client their new password after admin reset."""
    subject = "Your Media Scientist Password Has Been Reset"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#0B0E17;color:#F9FAFB;padding:32px;border-radius:16px;">
        <h1 style="color:#00F2FE;margin-top:0;">Password Reset</h1>
        <p>Hi <strong>{client_name}</strong>,</p>
        <p>Your password has been reset by an administrator. Here is your new temporary password:</p>

        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);padding:20px;border-radius:12px;margin:24px 0;text-align:center;">
            <p style="margin:0 0 8px;font-size:13px;color:#94a3b8;text-transform:uppercase;">New Password</p>
            <p style="margin:0;color:#00F5A0;font-family:monospace;font-size:22px;letter-spacing:2px;">{new_password}</p>
        </div>

        <a href="{login_url}" style="display:inline-block;background:linear-gradient(90deg,#00F2FE,#7928CA);color:#fff;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:600;">Log In Now</a>

        <p style="margin-top:32px;font-size:12px;color:#64748b;">— Opoku Kwadwo Incredible, The Media Scientist</p>
    </div>
    """
    return send_email(client_email, subject, html)