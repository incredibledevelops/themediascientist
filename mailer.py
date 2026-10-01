# =============================================================
#  Mailer — The Media Scientist
#  Sends transactional emails via SMTP (Gmail by default).
# =============================================================
import smtplib
import re
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid
from html import escape as html_escape

from config import Config


# =============================================================
#  BRAND TOKENS (must match the web palette)
# =============================================================
BRAND = {
    'ink':            '#0A0A0A',
    'paper':          '#FFFFFF',
    'canvas':         '#FAFAFA',
    'surface':        '#F5F5F5',
    'line':           '#E5E5E5',
    'muted':          '#6B7280',
    'electric':       '#0066FF',
    'teal':           '#00C2A8',
    'text_dark':      '#0A0A0A',
    'text_muted':     '#6B7280',
    'bg_page':        '#F4F4F5',
    'bg_card':        '#FFFFFF',
    'bg_soft':        '#FAFAFA',
    'border':         '#E5E5E5',
}

# Default values — Config overrides these
DEFAULTS = {
    'site_title':    'The Media Scientist',
    'owner_name':    'Opoku Kwadwo Incredible',
    'tagline':       'Creative media, engineered with precision.',
    'site_url':      'https://themediascientist.com',
    'contact_email': 'contact@themediascientist.com',
    'instagram':     'https://instagram.com/themediascientist_',
    'tiktok':        'https://tiktok.com/@themediascientist',
}


def _cfg(key, fallback=None):
    """Safely read a config value with a fallback."""
    value = getattr(Config, key.upper(), None)
    if value:
        return value
    return fallback or DEFAULTS.get(key, '')


def _esc(s):
    """HTML-escape untrusted input."""
    return html_escape(str(s) if s is not None else '')


# =============================================================
#  CORE SEND
# =============================================================
def send_email(to_address, subject, html_body, text_body=None, reply_to=None):
    """
    Send an email via SMTP.

    Args:
        to_address (str): Recipient email
        subject (str): Email subject
        html_body (str): HTML body
        text_body (str, optional): Plain-text fallback (auto-derived if not given)
        reply_to (str, optional): Reply-To header

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
    sender_name = _cfg('site_title', 'The Media Scientist')

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((sender_name, sender))
        msg['To'] = to_address
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='themediascientist.com')
        if reply_to:
            msg['Reply-To'] = reply_to

        # Plain-text fallback
        if text_body is None:
            text_body = _html_to_text(html_body)

        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Try sending with one retry on transient failure
        for attempt in range(2):
            try:
                with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=20) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                    server.sendmail(sender, [to_address], msg.as_string())
                return True
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
                if attempt == 0:
                    print(f"[MAILER] Transient error, retrying: {e}")
                    time.sleep(1)
                    continue
                raise

    except smtplib.SMTPAuthenticationError as e:
        print(f"[MAILER AUTH ERROR] {e}")
        print(f"  → to={to_address}, subject={subject!r}")
        return False
    except smtplib.SMTPException as e:
        print(f"[MAILER SMTP ERROR] {e}")
        print(f"  → to={to_address}, subject={subject!r}")
        return False
    except Exception as e:
        print(f"[MAILER ERROR] {e}")
        print(f"  → to={to_address}, subject={subject!r}")
        return False


def send_email_async(to_address, subject, html_body, text_body=None, reply_to=None):
    """Fire-and-forget version of send_email. Runs in a background thread."""
    t = threading.Thread(
        target=send_email,
        args=(to_address, subject, html_body, text_body, reply_to),
        daemon=True,
    )
    t.start()
    return True


def _html_to_text(html):
    """
    Convert HTML to a readable plain-text fallback.
    Preserves line breaks, strips tags, collapses whitespace.
    """
    # Convert common block elements to newlines
    text = re.sub(r'<(br|BR)\s*/?>', '\n', html)
    text = re.sub(r'</(p|P|div|DIV|h[1-6]|H[1-6]|li|LI|tr|TR)>', '\n', text)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common entities
    text = (text
            .replace('&nbsp;', ' ')
            .replace('&amp;', '&')
            .replace('&lt;', '<')
            .replace('&gt;', '>')
            .replace('&quot;', '"')
            .replace('&#39;', "'"))
    # Collapse excessive whitespace but keep paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# =============================================================
#  SHARED: branded wrapper
# =============================================================
def _wrap(
    html_inner,
    preheader='',
    accent=BRAND['electric'],
    cta_url=None,
    cta_label=None,
    show_unsubscribe=False,
    recipient_email=None,
):
    """
    Wrap the email body in the branded container.

    Args:
        html_inner (str): The inner HTML of the email
        preheader (str): Hidden preview text (shown next to subject in inboxes)
        accent (str): Accent color for the header border
        cta_url (str, optional): Primary CTA URL
        cta_label (str, optional): Primary CTA label
        show_unsubscribe (bool): Show preferences/unsubscribe line
        recipient_email (str, optional): For the unsubscribe link

    Returns:
        str: Full HTML email
    """
    site_title = _cfg('site_title', 'The Media Scientist')
    owner_name = _cfg('owner_name', 'Opoku Kwadwo Incredible')
    contact_email = _cfg('contact_email', 'contact@themediascientist.com')
    site_url = _cfg('site_url', 'https://themediascientist.com')

    # Bulletproof CTA button
    cta_html = ''
    if cta_url and cta_label:
        cta_html = f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               style="margin:28px 0 0;">
            <tr>
                <td align="left" bgcolor="{BRAND['ink']}"
                    style="border-radius:999px;">
                    <a href="{_esc(cta_url)}"
                       target="_blank"
                       style="display:inline-block;padding:14px 28px;
                              font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
                                          Helvetica,Arial,sans-serif;
                              font-size:14px;font-weight:600;
                              color:#FFFFFF;text-decoration:none;
                              border-radius:999px;">
                        {_esc(cta_label)} &nbsp;→
                    </a>
                </td>
            </tr>
        </table>
        """

    # Unsubscribe line
    unsub_html = ''
    if show_unsubscribe:
        unsub_url = f"{site_url}/unsubscribe"
        if recipient_email:
            unsub_url += f"?email={_esc(recipient_email)}"
        unsub_html = f"""
        <p style="margin:8px 0 0;font-size:11px;color:{BRAND['muted']};">
            You're receiving this email because you have an account with {_esc(site_title)}.
            <a href="{_esc(unsub_url)}"
               style="color:{BRAND['muted']};text-decoration:underline;">
                Manage preferences
            </a>
        </p>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>{_esc(site_title)}</title>
    <style>
        /* Mobile tweaks */
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; border-radius: 0 !important; }}
            .card {{ padding: 24px 20px !important; }}
            .footer {{ padding: 20px !important; }}
        }}
        /* Dark mode */
        @media (prefers-color-scheme: dark) {{
            .page-bg {{ background: #0A0A0A !important; }}
            .card-bg {{ background: #141414 !important; border-color: #262626 !important; }}
            .text-dark {{ color: #F5F5F5 !important; }}
            .text-muted {{ color: #A1A1AA !important; }}
            .divider {{ border-color: #262626 !important; }}
            .soft-bg {{ background: #1A1A1A !important; border-color: #262626 !important; }}
        }}
    </style>
</head>
<body style="margin:0;padding:0;background:{BRAND['bg_page']};
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
             -webkit-font-smoothing:antialiased;">

    <!-- Preheader (hidden, but shown in inbox preview) -->
    <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;
                font-size:1px;line-height:1px;color:transparent;opacity:0;">
        {_esc(preheader)}
    </div>

    <table role="presentation" cellpadding="0" cellspacing="0" border="0"
           width="100%" class="page-bg"
           style="background:{BRAND['bg_page']};padding:40px 16px;">
        <tr>
            <td align="center">

                <!-- Card -->
                <table role="presentation" cellpadding="0" cellspacing="0" border="0"
                       width="600" class="container"
                       style="max-width:600px;width:100%;
                              background:{BRAND['bg_card']};
                              border:1px solid {BRAND['border']};
                              border-radius:20px;
                              overflow:hidden;">

                    <!-- Accent bar -->
                    <tr>
                        <td style="height:4px;background:{accent};"></td>
                    </tr>

                    <!-- Brand header -->
                    <tr>
                        <td class="card" style="padding:32px 40px 24px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td width="48" valign="middle">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td bgcolor="{BRAND['electric']}"
                                                    width="40" height="40"
                                                    align="center" valign="middle"
                                                    style="border-radius:10px;
                                                           font-family:-apple-system,BlinkMacSystemFont,
                                                                       Helvetica,Arial,sans-serif;
                                                           font-size:20px;font-weight:800;
                                                           color:#FFFFFF;line-height:40px;">
                                                    M
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td valign="middle" style="padding-left:14px;">
                                        <div class="text-dark"
                                             style="font-size:15px;font-weight:700;
                                                    color:{BRAND['text_dark']};
                                                    letter-spacing:-0.01em;">
                                            {_esc(site_title)}
                                        </div>
                                        <div class="text-muted"
                                             style="font-size:11px;
                                                    color:{BRAND['text_muted']};
                                                    font-family:'SF Mono',Menlo,Consolas,monospace;
                                                    letter-spacing:0.08em;
                                                    text-transform:uppercase;
                                                    margin-top:2px;">
                                            {_esc(owner_name)}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                        <td style="padding:0 40px;">
                            <hr class="divider" style="border:none;
                                                       border-top:1px solid {BRAND['border']};
                                                       margin:0;">
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td class="card text-dark"
                            style="padding:28px 40px 32px;
                                   color:{BRAND['text_dark']};
                                   font-size:15px;line-height:1.65;">
                            {html_inner}
                            {cta_html}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td class="footer soft-bg"
                            style="padding:24px 40px;
                                   background:{BRAND['bg_soft']};
                                   border-top:1px solid {BRAND['border']};
                                   text-align:center;">
                            <p class="text-muted"
                               style="margin:0 0 8px;
                                      font-size:11px;
                                      color:{BRAND['text_muted']};
                                      font-family:'SF Mono',Menlo,Consolas,monospace;
                                      letter-spacing:0.08em;
                                      text-transform:uppercase;">
                                {_esc(owner_name)} · Kumasi, Ghana
                            </p>
                            <p class="text-muted"
                               style="margin:0;font-size:12px;
                                      color:{BRAND['text_muted']};">
                                <a href="mailto:{_esc(contact_email)}"
                                   style="color:{accent};text-decoration:none;">
                                    {_esc(contact_email)}
                                </a>
                                &nbsp;·&nbsp;
                                <a href="{_esc(site_url)}"
                                   style="color:{accent};text-decoration:none;">
                                    themediascientist.com
                                </a>
                            </p>
                            {unsub_html}
                        </td>
                    </tr>
                </table>

            </td>
        </tr>
    </table>
</body>
</html>"""


# =============================================================
#  Reusable inner blocks
# =============================================================
def _info_card(rows, border_color=None):
    """
    Render a soft-bordered info card.

    rows: list of (label, value_html) tuples
    """
    border = border_color or BRAND['electric']
    rows_html = ''
    for label, value in rows:
        rows_html += f"""
        <tr>
            <td class="text-muted"
                style="padding:6px 0;font-size:12px;
                       color:{BRAND['text_muted']};
                       font-family:'SF Mono',Menlo,Consolas,monospace;
                       letter-spacing:0.06em;
                       text-transform:uppercase;
                       white-space:nowrap;
                       vertical-align:top;">
                {_esc(label)}
            </td>
            <td class="text-dark"
                style="padding:6px 0 6px 16px;font-size:14px;
                       color:{BRAND['text_dark']};
                       vertical-align:top;">
                {value}
            </td>
        </tr>
        """
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"
           width="100%" class="soft-bg"
           style="background:{BRAND['bg_soft']};
                  border-left:3px solid {border};
                  border-radius:10px;
                  padding:0;margin:20px 0;">
        <tr>
            <td style="padding:16px 20px;">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                    {rows_html}
                </table>
            </td>
        </tr>
    </table>
    """


def _message_quote(text):
    """Render a quoted message block."""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"
           width="100%"
           style="margin:16px 0;">
        <tr>
            <td class="soft-bg"
                style="background:{BRAND['bg_soft']};
                       border-left:3px solid {BRAND['muted']};
                       border-radius:10px;
                       padding:16px 20px;
                       font-size:14px;
                       line-height:1.6;
                       color:{BRAND['text_dark']};
                       white-space:pre-wrap;
                       font-style:italic;">
                {_esc(text)}
            </td>
        </tr>
    </table>
    """


def _divider():
    return f"""
    <hr class="divider"
        style="border:none;border-top:1px solid {BRAND['border']};
               margin:24px 0;">
    """


# =============================================================
#  EMAIL 1 — Notify admin of new inquiry
# =============================================================
def send_inquiry_notification(inquiry, admin_email):
    """Notify admin of a new inquiry."""
    if not admin_email:
        return False

    name = _esc(inquiry.get('name', 'Unknown'))
    email = _esc(inquiry.get('email', ''))
    services = inquiry.get('services', []) or []
    budget = _esc(inquiry.get('budget', 'Not specified') or 'Not specified')
    message = _esc(inquiry.get('message', '') or '')

    services_str = ', '.join(_esc(s) for s in services) if services else 'Not specified'

    info = _info_card([
        ('From', f'<strong>{name}</strong>'),
        ('Email', f'<a href="mailto:{email}" style="color:{BRAND["electric"]};text-decoration:none;">{email}</a>'),
        ('Services', services_str),
        ('Budget', budget),
    ])

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            New project inquiry
        </h2>
        <p class="text-muted"
           style="margin:0 0 4px;font-size:13px;color:{BRAND['text_muted']};">
            Someone just reached out through your contact form.
        </p>

        {info}

        <p class="text-muted"
           style="margin:20px 0 8px;font-size:11px;
                  color:{BRAND['text_muted']};
                  font-family:'SF Mono',Menlo,Consolas,monospace;
                  letter-spacing:0.06em;
                  text-transform:uppercase;">
            Message
        </p>
        {_message_quote(message)}
    """

    return send_email(
        admin_email,
        f"New inquiry from {inquiry.get('name', 'someone')}",
        _wrap(
            inner,
            preheader=f"{inquiry.get('name', 'Someone')} wants to work with you · {budget}",
            accent=BRAND['electric'],
            cta_url=f"mailto:{email}?subject=Re: Your project inquiry with The Media Scientist",
            cta_label=f"Reply to {inquiry.get('name', 'them')}",
        ),
    )


# =============================================================
#  EMAIL 2 — Confirm receipt to the client
# =============================================================
def send_inquiry_confirmation(inquiry):
    """Confirm receipt to the client."""
    email = inquiry.get('email')
    if not email:
        return False

    name = _esc(inquiry.get('name', 'there'))
    first_name = _esc((inquiry.get('name') or 'there').split(' ')[0])
    message = _esc(inquiry.get('message', '') or '')

    site_url = _cfg('site_url', 'https://themediascientist.com')
    instagram = _cfg('instagram', 'https://instagram.com/themediascientist_')

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            Thank you for reaching out
        </h2>
        <p class="text-dark"
           style="margin:0 0 16px;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong> — I've received your inquiry and
            will get back to you within <strong>24 hours</strong>.
        </p>

        <p class="text-muted"
           style="margin:20px 0 8px;font-size:11px;
                  color:{BRAND['text_muted']};
                  font-family:'SF Mono',Menlo,Consolas,monospace;
                  letter-spacing:0.06em;
                  text-transform:uppercase;">
            Your message
        </p>
        {_message_quote(message)}

        {_divider()}

        <p class="text-muted"
           style="margin:0 0 12px;font-size:13px;color:{BRAND['text_muted']};">
            In the meantime, feel free to:
        </p>

        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               style="margin:0;">
            <tr>
                <td style="padding:6px 0;">
                    <a href="{site_url}/portfolio"
                       style="color:{BRAND['electric']};
                              text-decoration:none;
                              font-size:14px;font-weight:500;">
                        → &nbsp;Browse the portfolio
                    </a>
                </td>
            </tr>
            <tr>
                <td style="padding:6px 0;">
                    <a href="{site_url}/services"
                       style="color:{BRAND['electric']};
                              text-decoration:none;
                              font-size:14px;font-weight:500;">
                        → &nbsp;See services &amp; pricing
                    </a>
                </td>
            </tr>
            <tr>
                <td style="padding:6px 0;">
                    <a href="{instagram}"
                       style="color:{BRAND['electric']};
                              text-decoration:none;
                              font-size:14px;font-weight:500;">
                        → &nbsp;Follow on Instagram
                    </a>
                </td>
            </tr>
        </table>

        {_divider()}

        <p class="text-dark"
           style="margin:0;font-size:14px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Warm regards,<br/>
            <strong>{_esc(_cfg('owner_name', 'Opoku Kwadwo Incredible'))}</strong><br/>
            <span class="text-muted" style="color:{BRAND['text_muted']};font-size:13px;">
                {_esc(_cfg('site_title', 'The Media Scientist'))}
            </span>
        </p>
    """

    return send_email(
        email,
        "Thanks for reaching out — I'll reply within 24 hours",
        _wrap(
            inner,
            preheader="Your inquiry is in — expect a reply within 24 hours.",
            accent=BRAND['teal'],
        ),
    )


# =============================================================
#  EMAIL 3 — Client credentials
# =============================================================
def send_client_credentials(client_email, client_name, client_code, temp_password, login_url):
    """Send a newly created client their portal login details."""
    if not client_email:
        return False

    first_name = _esc((client_name or 'there').split(' ')[0])

    credentials = _info_card([
        ('Portal', f'<a href="{_esc(login_url)}" style="color:{BRAND["electric"]};text-decoration:none;">{_esc(login_url)}</a>'),
        ('Email', f'<span style="color:{BRAND["electric"]};">{_esc(client_email)}</span>'),
        ('Password',
         f'<code style="background:{BRAND["bg_soft"]};'
         f'border:1px solid {BRAND["border"]};'
         f'padding:4px 10px;border-radius:6px;'
         f'font-family:\'SF Mono\',Menlo,Consolas,monospace;'
         f'font-size:14px;letter-spacing:0.5px;'
         f'color:{BRAND["teal"]};'
         f'word-break:break-all;">{_esc(temp_password)}</code>'),
        ('Client ID',
         f'<code style="font-family:\'SF Mono\',Menlo,Consolas,monospace;'
         f'color:{BRAND["muted"]};font-size:13px;">{_esc(client_code)}</code>'),
    ], border_color=BRAND['electric'])

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            Welcome to your client portal
        </h2>
        <p class="text-dark"
           style="margin:0 0 4px;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong>,
        </p>
        <p class="text-dark"
           style="margin:0;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            An account has been created for you on the
            <strong>{_esc(_cfg('site_title'))}</strong> client portal. Use the
            credentials below to sign in and track your projects.
        </p>

        {credentials}

        <p class="text-dark"
           style="margin:0;font-size:14px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            <strong>Security tip:</strong>
            <span class="text-muted" style="color:{BRAND['text_muted']};">
                please change your password after your first login.
            </span>
        </p>
    """

    return send_email(
        client_email,
        "Your client portal is ready — sign in",
        _wrap(
            inner,
            preheader=f"Your login details for {_cfg('site_title')} are inside.",
            accent=BRAND['electric'],
            cta_url=login_url,
            cta_label="Access client portal",
        ),
    )


# =============================================================
#  EMAIL 4 — Password reset
# =============================================================
def send_client_password_reset(client_email, client_name, new_password, login_url):
    """Send a client their new password after admin reset."""
    if not client_email:
        return False

    first_name = _esc((client_name or 'there').split(' ')[0])

    password_block = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"
           width="100%"
           style="margin:20px 0;">
        <tr>
            <td class="soft-bg"
                align="center"
                style="background:{BRAND['bg_soft']};
                       border:1px solid {BRAND['border']};
                       border-radius:12px;
                       padding:24px 20px;">
                <p class="text-muted"
                   style="margin:0 0 8px;font-size:11px;
                          color:{BRAND['text_muted']};
                          font-family:'SF Mono',Menlo,Consolas,monospace;
                          letter-spacing:0.08em;
                          text-transform:uppercase;">
                    New Password
                </p>
                <p class="text-dark"
                   style="margin:0;
                          font-family:'SF Mono',Menlo,Consolas,monospace;
                          font-size:24px;
                          letter-spacing:2px;
                          color:{BRAND['text_dark']};
                          word-break:break-all;">
                    {_esc(new_password)}
                </p>
            </td>
        </tr>
    </table>
    """

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            Your password was reset
        </h2>
        <p class="text-dark"
           style="margin:0;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong> — an administrator has reset your
            password. Here's the new one:
        </p>

        {password_block}

        <p class="text-dark"
           style="margin:0;font-size:14px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            You'll be asked to change it after logging in.
        </p>

        {_divider()}

        <p class="text-muted"
           style="margin:0;font-size:12px;
                  color:{BRAND['text_muted']};line-height:1.6;">
            <strong>Didn't request this?</strong>
            Contact support immediately — someone may have access to your account.
        </p>
    """

    return send_email(
        client_email,
        "Your password has been reset",
        _wrap(
            inner,
            preheader="Your new password is inside — sign in and change it.",
            accent=BRAND['electric'],
            cta_url=login_url,
            cta_label="Log in now",
        ),
    )


# =============================================================
#  EMAIL 5 — Invoice issued
# =============================================================
def send_invoice_notification(client_email, client_name, invoice, pay_url=None):
    """Notify a client that a new invoice has been issued."""
    if not client_email:
        return False

    first_name = _esc((client_name or 'there').split(' ')[0])
    number = _esc(invoice.get('number', '—'))
    description = _esc(invoice.get('description', '') or '')
    amount = invoice.get('amount', 0)
    due_date = _esc(invoice.get('due_date', '—') or '—')
    status = (invoice.get('status', 'pending') or 'pending').lower()

    try:
        amount_str = f"{float(amount):,.2f}"
    except (ValueError, TypeError):
        amount_str = '0.00'

    accent = BRAND['teal'] if status == 'paid' else BRAND['electric']

    info = _info_card([
        ('Invoice', f'<strong>{number}</strong>'),
        ('Amount', f'<strong>GH₵ {amount_str}</strong>'),
        ('Due date', due_date),
        ('Status', status.upper()),
    ], border_color=accent)

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            New invoice from {_esc(_cfg('site_title'))}
        </h2>
        <p class="text-dark"
           style="margin:0;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong> — a new invoice is available in your portal.
        </p>

        {info}

        {f'<p class="text-muted" style="margin:0;font-size:13px;color:{BRAND["text_muted"]};">{description}</p>' if description else ''}
    """

    return send_email(
        client_email,
        f"New invoice {number} — GH₵ {amount_str}",
        _wrap(
            inner,
            preheader=f"Invoice {number} for GH₵ {amount_str} · due {due_date}",
            accent=accent,
            cta_url=pay_url or f"{_cfg('site_url')}/client/invoices",
            cta_label="View invoice",
        ),
    )


# =============================================================
#  EMAIL 6 — File uploaded
# =============================================================
def send_file_notification(client_email, client_name, filename, portal_url, size=None):
    """Notify a client when a new deliverable is ready."""
    if not client_email:
        return False

    first_name = _esc((client_name or 'there').split(' ')[0])
    filename_esc = _esc(filename)
    size_line = f'<p class="text-muted" style="margin:6px 0 0;font-size:12px;color:{BRAND["text_muted"]};">{_esc(size)}</p>' if size else ''

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            New deliverable ready
        </h2>
        <p class="text-dark"
           style="margin:0 0 16px;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong> — a new file has been uploaded to your portal.
        </p>

        {_info_card([
            ('File', f'<strong>{filename_esc}</strong>'),
        ], border_color=BRAND['teal'])}

        {size_line}

        <p class="text-dark"
           style="margin:16px 0 0;font-size:14px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Sign in to download it and mark it as reviewed.
        </p>
    """

    return send_email(
        client_email,
        f"New file: {filename}",
        _wrap(
            inner,
            preheader=f"{filename} is now available in your portal.",
            accent=BRAND['teal'],
            cta_url=portal_url,
            cta_label="Open in portal",
        ),
    )


# =============================================================
#  EMAIL 7 — Support reply
# =============================================================
def send_support_reply(client_email, client_name, reply_body, portal_url):
    """Notify a client when support replies to their message."""
    if not client_email:
        return False

    first_name = _esc((client_name or 'there').split(' ')[0])
    reply_esc = _esc(reply_body or '')

    inner = f"""
        <h2 class="text-dark"
            style="margin:0 0 8px;
                   font-size:22px;font-weight:700;
                   letter-spacing:-0.01em;
                   color:{BRAND['text_dark']};">
            New reply from support
        </h2>
        <p class="text-dark"
           style="margin:0 0 16px;font-size:15px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Hi <strong>{first_name}</strong> — the support team just replied to your message.
        </p>

        {_message_quote(reply_esc)}

        <p class="text-dark"
           style="margin:16px 0 0;font-size:14px;line-height:1.65;
                  color:{BRAND['text_dark']};">
            Reply directly from your portal to keep the conversation in one place.
        </p>
    """

    return send_email(
        client_email,
        "New reply from The Media Scientist support",
        _wrap(
            inner,
            preheader="You have a new reply in your portal.",
            accent=BRAND['electric'],
            cta_url=portal_url,
            cta_label="View reply",
            show_unsubscribe=True,
            recipient_email=client_email,
        ),
    )