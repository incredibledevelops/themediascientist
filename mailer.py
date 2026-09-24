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