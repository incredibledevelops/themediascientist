# =============================================================
#  Mailer — The Media Scientist
#  Sends transactional emails via SMTP (Gmail by default).
# =============================================================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from config import Config


# =============================================================
#  CORE SEND
# =============================================================
def send_email(to_address, subject, html_body, text_body=None):
    """
    Send an email via SMTP.

    Args:
        to_address (str): Recipient email
        subject (str): Email subject
        html_body (str): HTML body
        text_body (str, optional): Plain-text fallback

    Returns:
        bool: True on success, False on failure
    """
    if not to_address:
        print("[MAILER] Missing recipient address")
        return False

    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        print("[MAILER] Missing SMTP credentials")
        return False

    sender = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr(("The Media Scientist", sender))
        msg['To'] = to_address

        # Plain-text fallback (auto-derived if not given)
        if text_body is None:
            import re
            text_body = re.sub(r'<[^>]+>', '', html_body)
            text_body = re.sub(r'\s+', ' ', text_body).strip()

        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.sendmail(sender, [to_address], msg.as_string())

        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[MAILER AUTH ERROR] {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"[MAILER SMTP ERROR] {e}")
        return False
    except Exception as e:
        print(f"[MAILER ERROR] {e}")
        return False


# =============================================================
#  SHARED: brand wrapper
# =============================================================
def _wrap(html_inner):
    """Wrap the email body in the branded container."""
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:auto;
                background:#0B0E17;color:#F9FAFB;padding:32px;border-radius:16px;
                line-height:1.6;">
        {html_inner}
        <p style="margin-top:32px;padding-top:16px;border-top:1px solid #1F2937;
                  font-size:12px;color:#64748b;">
            Opoku Kwadwo Incredible · The Media Scientist<br/>
            Kumasi, Ghana · Available Worldwide
        </p>
    </div>
    """


# =============================================================
#  EMAIL 1 — Notify admin of new inquiry
# =============================================================
def send_inquiry_notification(inquiry, admin_email):
    """Notify admin of a new inquiry."""
    if not admin_email:
        return False

    name = inquiry.get('name', 'Unknown')
    email = inquiry.get('email', '')
    services = inquiry.get('services', []) or []
    budget = inquiry.get('budget', 'Not specified')
    message = inquiry.get('message', '')

    services_str = ', '.join(services) if services else 'Not specified'

    inner = f"""
        <h2 style="color:#00F2FE;margin-top:0;">New Project Inquiry</h2>
        <p>You've received a new inquiry from <strong>{name}</strong>.</p>

        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    padding:20px;border-radius:12px;margin:20px 0;">
            <p style="margin:4px 0;"><strong>Name:</strong> {name}</p>
            <p style="margin:4px 0;"><strong>Email:</strong>
                <a href="mailto:{email}" style="color:#00F2FE;">{email}</a></p>
            <p style="margin:4px 0;"><strong>Services:</strong> {services_str}</p>
            <p style="margin:4px 0;"><strong>Budget:</strong> {budget}</p>
        </div>

        <p><strong>Message:</strong></p>
        <div style="background:#111827;border-left:3px solid #00F2FE;
                    padding:12px 16px;border-radius:6px;color:#cbd5e1;">
            {message}
        </p>

        <p style="margin-top:24px;">
            <a href="mailto:{email}?subject=Re: Your project inquiry with The Media Scientist"
               style="display:inline-block;background:linear-gradient(90deg,#00F2FE,#7928CA);
                      color:#fff;padding:12px 24px;border-radius:10px;text-decoration:none;
                      font-weight:600;">
                Reply to {name}
            </a>
        </p>
    """

    return send_email(
        admin_email,
        f"New Project Inquiry from {name}",
        _wrap(inner),
    )


# =============================================================
#  EMAIL 2 — Confirm receipt to the client
# =============================================================
def send_inquiry_confirmation(inquiry):
    """Confirm receipt to the client."""
    email = inquiry.get('email')
    if not email:
        return False

    name = inquiry.get('name', 'there')
    message = inquiry.get('message', '')

    inner = f"""
        <h2 style="color:#00F2FE;margin-top:0;">Thank you for reaching out</h2>
        <p>Hi <strong>{name}</strong>,</p>
        <p>I've received your project inquiry and will get back to you within 24 hours.</p>

        <p style="margin-top:20px;"><strong>Your message:</strong></p>
        <div style="background:#111827;border-left:3px solid #00F5A0;
                    padding:12px 16px;border-radius:6px;color:#cbd5e1;">
            {message}
        </div>

        <p style="margin-top:24px;">In the meantime, feel free to:</p>
        <ul style="padding-left:20px;color:#cbd5e1;">
            <li>Browse my <a href="https://themediascientist.com/portfolio"
                             style="color:#00F2FE;">portfolio</a></li>
            <li>Review my <a href="https://themediascientist.com/services"
                             style="color:#00F2FE;">services &amp; pricing</a></li>
            <li>Follow me on <a href="https://instagram.com/themediascientist_"
                                style="color:#00F2FE;">Instagram</a></li>
        </ul>

        <p style="margin-top:24px;">Warm regards,<br/>
        <strong>Opoku Kwadwo Incredible</strong><br/>
        The Media Scientist</p>
    """

    return send_email(
        email,
        "Thank you for contacting The Media Scientist",
        _wrap(inner),
    )


# =============================================================
#  EMAIL 3 — Client credentials
# =============================================================
def send_client_credentials(client_email, client_name, client_code, temp_password, login_url):
    """Send a newly created client their portal login details."""
    if not client_email:
        return False

    inner = f"""
        <h1 style="color:#00F2FE;margin-top:0;font-size:24px;">
            Welcome to Your Client Portal
        </h1>
        <p>Hi <strong>{client_name}</strong>,</p>
        <p>An account has been created for you on the
           <strong>The Media Scientist</strong> client portal. You can now log in to
           track your projects, view invoices, download deliverables, and message directly.</p>

        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    padding:20px;border-radius:12px;margin:24px 0;">
            <p style="margin:0 0 10px;font-size:13px;color:#94a3b8;
                      text-transform:uppercase;letter-spacing:1px;">
                Login Credentials
            </p>
            <p style="margin:6px 0;"><strong>Portal URL:</strong>
                <a href="{login_url}" style="color:#00F2FE;">{login_url}</a></p>
            <p style="margin:6px 0;"><strong>Email:</strong>
                <span style="color:#00F2FE;">{client_email}</span></p>
            <p style="margin:6px 0;"><strong>Temporary Password:</strong>
                <span style="color:#00F5A0;font-family:monospace;font-size:16px;">
                    {temp_password}
                </span></p>
            <p style="margin:6px 0;"><strong>Client ID:</strong>
                <span style="color:#7928CA;font-family:monospace;">{client_code}</span></p>
        </div>

        <p>Please change your password after your first login for security.</p>

        <p style="margin-top:24px;">
            <a href="{login_url}"
               style="display:inline-block;background:linear-gradient(90deg,#00F2FE,#7928CA);
                      color:#fff;padding:14px 28px;border-radius:10px;text-decoration:none;
                      font-weight:600;">
                Access Client Portal
            </a>
        </p>

        <p style="margin-top:32px;font-size:12px;color:#64748b;">
            If you didn't request this, please ignore this email.
        </p>
    """

    return send_email(
        client_email,
        "Your Media Scientist Client Portal Access",
        _wrap(inner),
    )


# =============================================================
#  EMAIL 4 — Password reset
# =============================================================
def send_client_password_reset(client_email, client_name, new_password, login_url):
    """Send a client their new password after admin reset."""
    if not client_email:
        return False

    inner = f"""
        <h1 style="color:#00F2FE;margin-top:0;font-size:24px;">Password Reset</h1>
        <p>Hi <strong>{client_name}</strong>,</p>
        <p>Your password has been reset by an administrator.
           Here is your new temporary password:</p>

        <div style="background:#111827;border:1px solid rgba(255,255,255,0.08);
                    padding:20px;border-radius:12px;margin:24px 0;text-align:center;">
            <p style="margin:0 0 8px;font-size:13px;color:#94a3b8;
                      text-transform:uppercase;">
                New Password
            </p>
            <p style="margin:0;color:#00F5A0;font-family:monospace;
                      font-size:22px;letter-spacing:2px;">
                {new_password}
            </p>
        </div>

        <p style="margin-top:24px;">
            <a href="{login_url}"
               style="display:inline-block;background:linear-gradient(90deg,#00F2FE,#7928CA);
                      color:#fff;padding:14px 28px;border-radius:10px;text-decoration:none;
                      font-weight:600;">
                Log In Now
            </a>
        </p>

        <p style="margin-top:24px;font-size:12px;color:#64748b;">
            If you didn't request this change, please contact support immediately.
        </p>
    """

    return send_email(
        client_email,
        "Your Media Scientist Password Has Been Reset",
        _wrap(inner),
    )