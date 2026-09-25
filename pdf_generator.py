# =============================================================
#  PDF Invoice Generator — The Media Scientist
#  Uses ReportLab to produce branded invoices.
# =============================================================
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from datetime import datetime, timezone
import io


# ------------------------------------------------------------
#  Brand palette (matches the web UI)
# ------------------------------------------------------------
CYAN = colors.HexColor("#00F2FE")
PURPLE = colors.HexColor("#7928CA")
EMERALD = colors.HexColor("#00F5A0")
DARK = colors.HexColor("#0B0E17")
SLATE = colors.HexColor("#334155")
LIGHT_BG = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#E2E8F0")
AMBER = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")
WHITE = colors.white


# ------------------------------------------------------------
#  Safe accessor helpers — never crash on missing data
# ------------------------------------------------------------
def _get(obj, key, default=''):
    """Safely get a value from a dict-like object."""
    if obj is None:
        return default
    if hasattr(obj, 'get'):
        val = obj.get(key, default)
        return default if val is None else val
    return getattr(obj, key, default)


def _format_date(dt, fallback='—'):
    """Format a datetime as 'Mon DD, YYYY'. Accepts datetime, str, or None."""
    if not dt:
        return fallback
    if isinstance(dt, str):
        return dt  # already formatted
    if hasattr(dt, 'strftime'):
        try:
            return dt.strftime('%b %d, %Y')
        except Exception:
            return fallback
    return fallback


def _format_amount(amount, fallback='0.00'):
    """Safely coerce amount to float and format with 2 decimals."""
    if amount is None:
        return fallback
    try:
        return f"{float(amount):,.2f}"
    except (ValueError, TypeError):
        return fallback


# ------------------------------------------------------------
#  Main entry point
# ------------------------------------------------------------
def generate_invoice_pdf(invoice, client, settings=None):
    """
    Generate a professional PDF invoice.

    Args:
        invoice: dict-like invoice document
        client:  dict-like user document (the client being billed)
        settings: optional dict-like global site settings

    Returns:
        io.BytesIO buffer positioned at start, ready for send_file().
    """
    settings = settings or {}

    buffer = io.BytesIO()
    invoice_number = _get(invoice, 'number', 'INV-000000') or 'INV-000000'

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {invoice_number}",
        author=_get(settings, 'site_title', 'The Media Scientist') or 'The Media Scientist',
        subject=f"Invoice {invoice_number}",
    )

    styles = getSampleStyleSheet()

    # ---------- Paragraph styles ----------
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=26, textColor=DARK,
        spaceAfter=0, alignment=TA_LEFT, leading=30
    )
    brand_style = ParagraphStyle(
        'BrandStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, textColor=CYAN,
        alignment=TA_RIGHT, leading=14
    )
    small_style = ParagraphStyle(
        'SmallStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=SLATE, leading=13
    )
    label_style = ParagraphStyle(
        'LabelStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, textColor=SLATE, leading=13
    )
    total_style = ParagraphStyle(
        'TotalStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=20, textColor=DARK,
        alignment=TA_RIGHT, leading=24
    )

    story = []

    # ============================================================
    #  HEADER — brand + invoice number
    # ============================================================
    owner_name = _get(settings, 'owner_name', 'Opoku Kwadwo Incredible') or 'Opoku Kwadwo Incredible'
    site_title = _get(settings, 'site_title', 'The Media Scientist') or 'The Media Scientist'

    header_data = [[
        Paragraph(f"<b>{site_title.upper()}</b>", title_style),
        Paragraph(f"<b>INVOICE</b><br/>{invoice_number}", brand_style),
    ]]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=CYAN, spaceAfter=12))

    # ============================================================
    #  FROM / BILL TO
    # ============================================================
    from_block = (
        f"<b>{owner_name}</b><br/>"
        f"Creative Media Professional<br/>"
        f"Kumasi, Ghana<br/>"
        f"contact@themediascientist.com"
    )

    client_name = _get(client, 'name', 'Client') or 'Client'
    client_email = _get(client, 'email', '') or ''
    client_code = _get(client, 'client_code', '—') or '—'

    to_block = (
        f"<b>BILL TO</b><br/>"
        f"{client_name}<br/>"
        f"{client_email}<br/>"
        f"Client ID: {client_code}"
    )

    info_table = Table(
        [[Paragraph(from_block, small_style), Paragraph(to_block, small_style)]],
        colWidths=[85 * mm, 85 * mm]
    )
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # ============================================================
    #  INVOICE DETAILS (issued / due / status)
    # ============================================================
    issued_display = _format_date(_get(invoice, 'created_at', None))
    due_display = _get(invoice, 'due_date', '—') or '—'
    status_raw = (_get(invoice, 'status', 'pending') or 'pending').upper()

    if status_raw == 'PAID':
        status_color = EMERALD
    elif status_raw == 'OVERDUE':
        status_color = RED
    elif status_raw == 'PENDING':
        status_color = AMBER
    else:
        status_color = AMBER

    details_data = [
        [
            Paragraph("DATE ISSUED", label_style),
            Paragraph("DUE DATE", label_style),
            Paragraph("STATUS", label_style),
        ],
        [
            Paragraph(issued_display, small_style),
            Paragraph(str(due_display), small_style),
            Paragraph(f"<font color='{status_color.hexval()}'><b>{status_raw}</b></font>", small_style),
        ],
    ]
    details_table = Table(details_data, colWidths=[56 * mm, 56 * mm, 58 * mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('BACKGROUND', (0, 1), (-1, 1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 24))

    # ============================================================
    #  LINE ITEMS
    # ============================================================
    items_header = [
        Paragraph("<b>DESCRIPTION</b>", ParagraphStyle(
            'h1', parent=small_style, textColor=WHITE, fontName='Helvetica-Bold')),
        Paragraph("<b>QTY</b>", ParagraphStyle(
            'h2', parent=small_style, textColor=WHITE, fontName='Helvetica-Bold',
            alignment=TA_CENTER)),
        Paragraph("<b>AMOUNT (GH₵)</b>", ParagraphStyle(
            'h3', parent=small_style, textColor=WHITE, fontName='Helvetica-Bold',
            alignment=TA_RIGHT)),
    ]

    description = _get(invoice, 'description', 'Professional services rendered') or 'Professional services rendered'
    amount_str = _format_amount(_get(invoice, 'amount', 0))

    items_data = [
        items_header,
        [
            Paragraph(str(description), small_style),
            Paragraph("1", ParagraphStyle('c', parent=small_style, alignment=TA_CENTER)),
            Paragraph(amount_str, ParagraphStyle('r', parent=small_style, alignment=TA_RIGHT)),
        ],
    ]
    items_table = Table(items_data, colWidths=[110 * mm, 20 * mm, 40 * mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # ============================================================
    #  TOTAL ROW
    # ============================================================
    total_data = [[
        Paragraph("", small_style),
        Paragraph("<b>Total Due:</b>", ParagraphStyle(
            't', parent=small_style, alignment=TA_RIGHT,
            fontName='Helvetica-Bold', fontSize=11)),
        Paragraph(f"GH₵ {amount_str}", total_style),
    ]]
    total_table = Table(total_data, colWidths=[100 * mm, 30 * mm, 40 * mm])
    total_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 30))

    # ============================================================
    #  FOOTER
    # ============================================================
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=10))
    footer_text = (
        "Thank you for your business. If you have any questions about this invoice, "
        "please contact <b>contact@themediascientist.com</b>.<br/>"
        "<i>Payments can be made securely via Paystack using the client portal.</i>"
    )
    story.append(Paragraph(
        footer_text,
        ParagraphStyle('f', parent=small_style, alignment=TA_CENTER, fontSize=8)
    ))

    # ============================================================
    #  BUILD
    # ============================================================
    doc.build(story)
    buffer.seek(0)
    return buffer