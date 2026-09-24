from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from datetime import datetime
import io


# Brand colors
CYAN = colors.HexColor("#00F2FE")
PURPLE = colors.HexColor("#7928CA")
EMERALD = colors.HexColor("#00F5A0")
DARK = colors.HexColor("#0B0E17")
SLATE = colors.HexColor("#334155")
LIGHT_BG = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#E2E8F0")


def generate_invoice_pdf(invoice, client, settings=None):
    """Generate a professional PDF invoice. Returns a BytesIO buffer."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {invoice.get('number', '')}",
        author="The Media Scientist"
    )

    styles = getSampleStyleSheet()

    # Custom styles
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
    small_right = ParagraphStyle(
        'SmallRight', parent=small_style, alignment=TA_RIGHT
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
    status_style = ParagraphStyle(
        'StatusStyle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=colors.white, alignment=TA_CENTER
    )

    story = []

    # ---- Header row: Logo left, invoice title right
    owner_name = (settings or {}).get('owner_name', 'Opoku Kwadwo Incredible')
    site_title = (settings or {}).get('site_title', 'The Media Scientist')

    header_data = [
        [
            Paragraph(f"<b>{site_title.upper()}</b>", title_style),
            Paragraph(f"<b>INVOICE</b><br/>{invoice.get('number', '')}", brand_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=2, color=CYAN, spaceAfter=12))

    # ---- From / To info
    from_block = (
        f"<b>{owner_name}</b><br/>"
        f"Creative Media Professional<br/>"
        f"Kumasi, Ghana<br/>"
        f"contact@themediascientist.com"
    )

    to_block = (
        f"<b>BILL TO</b><br/>"
        f"{client.get('name', '')}<br/>"
        f"{client.get('email', '')}<br/>"
        f"Client ID: {client.get('client_code', '—')}"
    )

    info_data = [
        [Paragraph(from_block, small_style), Paragraph(to_block, small_style)]
    ]
    info_table = Table(info_data, colWidths=[85 * mm, 85 * mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # ---- Invoice details table
    issued = invoice.get('created_at')
    due = invoice.get('due_date', '—')
    status = invoice.get('status', 'pending').upper()
    status_color = EMERALD if status == 'PAID' else (colors.HexColor("#F59E0B") if status == 'PENDING' else colors.HexColor("#EF4444"))

    details_data = [
        [
            Paragraph("DATE ISSUED", label_style),
            Paragraph("DUE DATE", label_style),
            Paragraph("STATUS", label_style),
        ],
        [
            Paragraph(issued.strftime('%b %d, %Y') if issued else '—', small_style),
            Paragraph(due, small_style),
            Paragraph(f"<font color='{status_color.hexval()}'><b>{status}</b></font>", small_style),
        ]
    ]
    details_table = Table(details_data, colWidths=[56 * mm, 56 * mm, 58 * mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
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

    # ---- Line items
    items_header = [
        Paragraph("<b>DESCRIPTION</b>", ParagraphStyle('h', parent=small_style, textColor=colors.white, fontName='Helvetica-Bold')),
        Paragraph("<b>QTY</b>", ParagraphStyle('h', parent=small_style, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph("<b>AMOUNT (GH₵)</b>", ParagraphStyle('h', parent=small_style, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
    ]

    description = invoice.get('description', 'Professional services rendered')
    amount = float(invoice.get('amount', 0))

    items_data = [
        items_header,
        [
            Paragraph(description, small_style),
            Paragraph("1", ParagraphStyle('c', parent=small_style, alignment=TA_CENTER)),
            Paragraph(f"{amount:,.2f}", ParagraphStyle('r', parent=small_style, alignment=TA_RIGHT)),
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

    # ---- Total row
    total_data = [
        [
            Paragraph("", small_style),
            Paragraph("<b>Total Due:</b>", ParagraphStyle('t', parent=small_style, alignment=TA_RIGHT, fontName='Helvetica-Bold', fontSize=11)),
            Paragraph(f"GH₵ {amount:,.2f}", total_style),
        ]
    ]
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

    # ---- Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=10))
    footer_text = (
        "Thank you for your business. If you have any questions about this invoice, "
        "please contact <b>contact@themediascientist.com</b>.<br/>"
        "<i>Payments can be made securely via Paystack using the client portal.</i>"
    )
    story.append(Paragraph(footer_text, ParagraphStyle('f', parent=small_style, alignment=TA_CENTER, fontSize=8)))

    doc.build(story)
    buffer.seek(0)
    return buffer