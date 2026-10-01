# =============================================================
#  PDF Invoice Generator — The Media Scientist
#  Uses ReportLab to produce branded invoices.
# =============================================================
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime, timezone
import io
import re


# ------------------------------------------------------------
#  Brand palette (matches the web UI)
# ------------------------------------------------------------
INK          = colors.HexColor("#0A0A0A")
PAPER        = colors.HexColor("#FFFFFF")
CANVAS       = colors.HexColor("#FAFAFA")
SURFACE      = colors.HexColor("#F5F5F5")
LINE         = colors.HexColor("#E5E5E5")
MUTED        = colors.HexColor("#6B7280")
ELECTRIC     = colors.HexColor("#0066FF")
TEAL         = colors.HexColor("#00C2A8")
ORANGE       = colors.HexColor("#F97316")
RED          = colors.HexColor("#EF4444")


# ------------------------------------------------------------
#  Safe accessor helpers — never crash on missing data
# ------------------------------------------------------------
def _get(obj, key, default=''):
    """Safely get a value from a dict-like object."""
    if obj is None:
        return default
    if hasattr(obj, 'get'):
        try:
            val = obj.get(key, default)
            return default if val is None else val
        except Exception:
            return default
    return getattr(obj, key, default)


def _format_date(dt, fallback='—'):
    """Format a datetime as 'Mon DD, YYYY'. Accepts datetime, str, or None."""
    if not dt:
        return fallback
    if isinstance(dt, str):
        return dt
    if hasattr(dt, 'strftime'):
        try:
            return dt.strftime('%b %d, %Y')
        except Exception:
            return fallback
    return fallback


def _format_amount(amount, fallback='0.00'):
    """Safely coerce amount to float and format with 2 decimals + thousands."""
    if amount is None:
        return fallback
    try:
        return f"{float(amount):,.2f}"
    except (ValueError, TypeError):
        return fallback


def _to_float(amount, default=0.0):
    """Coerce amount to float, safely."""
    try:
        return float(amount or 0)
    except (ValueError, TypeError):
        return default


def _escape(s):
    """Escape XML-special characters so ReportLab doesn't choke."""
    if s is None:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def _number_to_words(amount):
    """
    Convert a number to English words for invoices.
    Handles up to billions. Returns '' if it fails.
    """
    try:
        n = float(amount or 0)
    except (ValueError, TypeError):
        return ''

    if n < 0:
        return ''
    if n == 0:
        return 'Zero Ghana Cedis'

    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
            'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
            'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
            'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def chunk_to_words(num):
        if num == 0:
            return ''
        parts = []
        if num >= 100:
            parts.append(f"{ones[num // 100]} Hundred")
            num %= 100
        if num >= 20:
            parts.append(f"{tens[num // 10]}{(('- ' + ones[num % 10]) if num % 10 else '')}")
        elif num > 0:
            parts.append(ones[num])
        return ' '.join(parts).strip()

    major = int(n)
    minor = int(round((n - major) * 100))

    parts = []
    if major >= 1_000_000_000:
        parts.append(f"{chunk_to_words(major // 1_000_000_000)} Billion")
        major %= 1_000_000_000
    if major >= 1_000_000:
        parts.append(f"{chunk_to_words(major // 1_000_000)} Million")
        major %= 1_000_000
    if major >= 1_000:
        parts.append(f"{chunk_to_words(major // 1_000)} Thousand")
        major %= 1_000
    if major > 0:
        parts.append(chunk_to_words(major))

    words = ' '.join(parts).strip() or 'Zero'
    word_str = f"{words} Ghana Cedis"
    if minor > 0:
        word_str += f" and {minor:02d} Pesewas"
    else:
        word_str += " Only"
    return word_str


# ------------------------------------------------------------
#  Deterministic accent color per status
# ------------------------------------------------------------
def _status_meta(status):
    """Return (label, color, icon_glyph) for the status pill."""
    s = (status or 'pending').lower()
    if s == 'paid':
        return ('PAID', TEAL, '✓')
    if s == 'overdue':
        return ('OVERDUE', RED, '!')
    if s == 'draft':
        return ('DRAFT', MUTED, '·')
    if s == 'cancelled' or s == 'canceled':
        return ('CANCELLED', MUTED, '×')
    return ('PENDING', ORANGE, '•')


# ------------------------------------------------------------
#  Page footer callback — page numbers + brand
# ------------------------------------------------------------
def _make_page_footer(site_title, site_url):
    def _draw(canvas, doc):
        canvas.saveState()
        width, height = A4

        # Footer divider
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(20 * mm, 15 * mm, width - 20 * mm, 15 * mm)

        # Left: site title
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 11 * mm, site_title)

        # Center: page number
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(width / 2, 11 * mm, f"Page {doc.page}")

        # Right: site url
        if site_url:
            canvas.drawRightString(width - 20 * mm, 11 * mm, site_url)

        canvas.restoreState()
    return _draw


# ------------------------------------------------------------
#  Main entry point
# ------------------------------------------------------------
def generate_invoice_pdf(invoice, client, settings=None):
    """
    Generate a professional PDF invoice.

    Args:
        invoice: dict-like invoice document (supports `items[]` for multiple line items)
        client:  dict-like user document (the client being billed)
        settings: optional dict-like global site settings

    Returns:
        io.BytesIO buffer positioned at start, ready for send_file().
    """
    settings = settings or {}

    buffer = io.BytesIO()
    invoice_number = _get(invoice, 'number', 'INV-000000') or 'INV-000000'

    site_title = _get(settings, 'site_title', 'The Media Scientist') or 'The Media Scientist'
    owner_name = _get(settings, 'owner_name', 'Opoku Kwadwo Incredible') or 'Opoku Kwadwo Incredible'
    site_url = _get(settings, 'site_url', 'themediascientist.com') or 'themediascientist.com'
    contact_email = _get(settings, 'contact_email', 'contact@themediascientist.com') or 'contact@themediascientist.com'

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=f"Invoice {invoice_number}",
        author=site_title,
        subject=f"Invoice {invoice_number} from {site_title}",
        creator=site_title,
        keywords="invoice, media, scientist, creative, agency",
    )

    styles = getSampleStyleSheet()

    # ---------- Paragraph styles ----------
    brand_title = ParagraphStyle(
        'BrandTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, textColor=INK,
        leading=18, spaceAfter=0
    )
    brand_sub = ParagraphStyle(
        'BrandSub', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, textColor=MUTED,
        leading=10, spaceAfter=0
    )
    invoice_label = ParagraphStyle(
        'InvoiceLabel', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, textColor=MUTED,
        leading=10, alignment=TA_RIGHT
    )
    invoice_number_style = ParagraphStyle(
        'InvoiceNumber', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, textColor=INK,
        leading=18, alignment=TA_RIGHT
    )
    section_label = ParagraphStyle(
        'SectionLabel', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, textColor=MUTED,
        leading=10
    )
    body_style = ParagraphStyle(
        'BodyText', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=INK, leading=12
    )
    small_muted = ParagraphStyle(
        'SmallMuted', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8, textColor=MUTED, leading=11
    )
    total_style = ParagraphStyle(
        'TotalStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=20, textColor=INK,
        alignment=TA_RIGHT, leading=22
    )
    words_style = ParagraphStyle(
        'WordsStyle', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8, textColor=MUTED,
        leading=11
    )
    th_style = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8, textColor=PAPER, leading=10
    )
    th_right = ParagraphStyle(
        'TableHeaderRight', parent=th_style, alignment=TA_RIGHT
    )
    th_center = ParagraphStyle(
        'TableHeaderCenter', parent=th_style, alignment=TA_CENTER
    )

    story = []

    # ============================================================
    #  STATUS + INVOICE BADGE ROW
    # ============================================================
    status_raw = (_get(invoice, 'status', 'pending') or 'pending')
    status_label, status_color, _ = _status_meta(status_raw)

    # ============================================================
    #  HEADER — brand mark + invoice number
    # ============================================================
    mark_size = 10 * mm
    mark_style = ParagraphStyle(
        'Mark', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=20, textColor=PAPER,
        leading=24, alignment=TA_CENTER
    )

    brand_block = [
        [
            Table(
                [[Paragraph("M", mark_style)]],
                colWidths=[mark_size], rowHeights=[mark_size],
                style=TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), ELECTRIC),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('ROUNDEDCORNERS', [6, 6, 6, 6]),
                ])
            ),
            Paragraph(
                f"<b>{_escape(site_title)}</b><br/>"
                f"<font color='#6B7280' size='8'>{_escape(owner_name)}</font>",
                ParagraphStyle('BrandCol', parent=body_style, leading=12)
            ),
        ]
    ]
    brand_table = Table(brand_block, colWidths=[mark_size + 4 * mm, 106 * mm])
    brand_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    invoice_block = Paragraph(
        f"<font color='#6B7280' size='8'>INVOICE</font><br/>"
        f"<b>{_escape(invoice_number)}</b>",
        invoice_number_style
    )

    header_table = Table(
        [[brand_table, invoice_block]],
        colWidths=[120 * mm, 50 * mm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    story.append(Spacer(1, 5))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=0))
    story.append(Spacer(1, 2))

    # Status bar
    status_bar = Table(
        [[
            Paragraph(
                f"<font color='{status_color.hexval()}'><b>{status_label}</b></font>",
                ParagraphStyle('Status', parent=body_style, fontSize=9, leading=11)
            ),
            Paragraph(
                f"<font color='#6B7280' size='8'>Issued {_escape(_format_date(_get(invoice, 'created_at', None)))}</font>",
                ParagraphStyle('Issued', parent=body_style, fontSize=8, leading=10, alignment=TA_RIGHT)
            ),
        ]],
        colWidths=[85 * mm, 85 * mm],
    )
    status_bar.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(status_bar)
    story.append(Spacer(1, 16))

    # ============================================================
    #  FROM / BILL TO
    # ============================================================
    from_block = (
        f"<font color='#6B7280' size='8'>FROM</font><br/>"
        f"<b>{_escape(owner_name)}</b><br/>"
        f"{_escape(site_title)}<br/>"
        f"Kumasi, Ghana<br/>"
        f"<font color='#0066FF'>{_escape(contact_email)}</font>"
    )

    client_name = _get(client, 'name', 'Client') or 'Client'
    client_email = _get(client, 'email', '') or ''
    client_code = _get(client, 'client_code', '—') or '—'
    client_location = _get(client, 'location', '') or ''

    to_block = (
        f"<font color='#6B7280' size='8'>BILL TO</font><br/>"
        f"<b>{_escape(client_name)}</b><br/>"
        + (f"{_escape(client_email)}<br/>" if client_email else '')
        + (f"{_escape(client_location)}<br/>" if client_location else '')
        + f"<font color='#6B7280' size='8'>Client ID: {_escape(client_code)}</font>"
    )

    info_table = Table(
        [[Paragraph(from_block, body_style), Paragraph(to_block, body_style)]],
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
    #  LINE ITEMS
    # ============================================================
    items_header = [
        Paragraph("DESCRIPTION", th_style),
        Paragraph("QTY", th_center),
        Paragraph("UNIT (GH₵)", th_right),
        Paragraph("AMOUNT (GH₵)", th_right),
    ]

    # Accept either a single `amount` or an `items[]` list
    items = _get(invoice, 'items', None) or []
    if not isinstance(items, (list, tuple)):
        items = []

    if not items:
        description = _get(invoice, 'description', 'Professional services rendered') or 'Professional services rendered'
        amount = _to_float(_get(invoice, 'amount', 0))
        items = [{'description': description, 'quantity': 1, 'unit_price': amount, 'amount': amount}]

    items_rows = [items_header]
    subtotal = 0.0
    for it in items:
        desc = _get(it, 'description', '') or ''
        qty = _get(it, 'quantity', 1) or 1
        unit = _get(it, 'unit_price', _get(it, 'amount', 0)) or 0
        amt = _to_float(_get(it, 'amount', _to_float(unit) * _to_float(qty, 1)))
        subtotal += amt

        items_rows.append([
            Paragraph(_escape(desc), body_style),
            Paragraph(str(qty), ParagraphStyle('q', parent=body_style, alignment=TA_CENTER)),
            Paragraph(f"{_format_amount(unit)}", ParagraphStyle('u', parent=body_style, alignment=TA_RIGHT)),
            Paragraph(f"{_format_amount(amt)}", ParagraphStyle('a', parent=body_style, alignment=TA_RIGHT)),
        ])

    items_table = Table(
        items_rows,
        colWidths=[90 * mm, 15 * mm, 30 * mm, 35 * mm],
        repeatRows=1,
    )
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INK),
        ('BOX', (0, 0), (-1, -1), 0.5, LINE),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [PAPER, CANVAS]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8))

    # ============================================================
    #  TOTALS (subtotal / VAT / total)
    # ============================================================
    vat_rate = _to_float(_get(invoice, 'vat_rate', _get(settings, 'vat_rate', 0)))
    vat_amount = _to_float(_get(invoice, 'vat_amount', subtotal * vat_rate / 100 if vat_rate else 0))

    total_due = subtotal + vat_amount

    # If invoice has explicit amount (backward compat), trust it as the total
    explicit_amount = _to_float(_get(invoice, 'amount', None))
    if explicit_amount and not _get(invoice, 'items', None):
        total_due = explicit_amount

    totals_rows = [
        [
            Paragraph("<font color='#6B7280'>Subtotal</font>",
                      ParagraphStyle('sub', parent=body_style, alignment=TA_RIGHT)),
            Paragraph(f"<b>GH₵ {_format_amount(subtotal)}</b>",
                      ParagraphStyle('subv', parent=body_style, alignment=TA_RIGHT)),
        ],
    ]

    if vat_amount > 0:
        totals_rows.append([
            Paragraph(f"<font color='#6B7280'>VAT ({vat_rate:.0f}%)</font>",
                      ParagraphStyle('vat', parent=body_style, alignment=TA_RIGHT)),
            Paragraph(f"<b>GH₵ {_format_amount(vat_amount)}</b>",
                      ParagraphStyle('vatv', parent=body_style, alignment=TA_RIGHT)),
        ])

    totals_table = Table(totals_rows, colWidths=[40 * mm, 40 * mm], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)

    # Divider before total
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="80mm", thickness=1, color=INK,
                            hAlign='RIGHT', spaceAfter=8))

    # Grand total
    total_data = [[
        Paragraph("TOTAL DUE", ParagraphStyle(
            'TotalLabel', parent=body_style, alignment=TA_RIGHT,
            fontName='Helvetica-Bold', fontSize=9, textColor=MUTED, leading=11)),
        Paragraph(f"GH₵ {_format_amount(total_due)}", total_style),
    ]]
    total_table = Table(total_data, colWidths=[40 * mm, 40 * mm], hAlign='RIGHT')
    total_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(total_table)

    # Amount in words
    words = _number_to_words(total_due)
    if words:
        story.append(Spacer(1, 6))
        words_table = Table(
            [[Paragraph(f"<b>Amount in words:</b> {_escape(words)}", words_style)]],
            colWidths=[180 * mm], hAlign='RIGHT'
        )
        words_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(words_table)

    story.append(Spacer(1, 24))

    # ============================================================
    #  PAYMENT INSTRUCTIONS
    # ============================================================
    pay_url = _get(invoice, 'pay_url', None) or _get(settings, 'pay_url', None)
    if status_label.lower() != 'paid':
        instruction_lines = [
            "Payments can be made securely via Paystack through your client portal.",
        ]
        if pay_url:
            instruction_lines.append(
                f"<font color='#0066FF'>{_escape(pay_url)}</font>"
            )

        payment_table = Table(
            [[
                Paragraph(
                    "<b>Payment Instructions</b><br/>"
                    + "<br/>".join(instruction_lines),
                    ParagraphStyle('pay', parent=body_style, leading=13)
                )
            ]],
            colWidths=[180 * mm],
        )
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F7FF")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#D0E0FF")),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 18))

    # ============================================================
    #  FOOTER NOTE
    # ============================================================
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=10))
    footer_text = (
        f"Thank you for your business. If you have any questions about this invoice, "
        f"please contact <b>{_escape(contact_email)}</b>.<br/>"
        f"<font color='#6B7280' size='7'>"
        f"This is a computer-generated invoice. No signature required."
        f"</font>"
    )
    story.append(Paragraph(
        footer_text,
        ParagraphStyle('f', parent=small_muted, alignment=TA_CENTER, fontSize=8, leading=11)
    ))

    # ============================================================
    #  BUILD
    # ============================================================
    footer_callback = _make_page_footer(site_title, site_url)

    # Draw "PAID" watermark for settled invoices
    def on_first_page(canvas, doc):
        if status_label == 'PAID':
            canvas.saveState()
            canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
            canvas.setFont('Helvetica-Bold', 130)
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(30)
            canvas.drawCentredString(0, 0, 'PAID')
            canvas.restoreState()
        footer_callback(canvas, doc)

    doc.build(story, onFirstPage=on_first_page, onLaterPages=footer_callback)
    buffer.seek(0)
    return buffer