import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def _paragraph_value(value) -> str:
    return escape(str(value if value not in (None, "") else "N/A")).replace(
        "\n",
        "<br/>",
    )


def generate_pdf_audit_report(proposal_data: dict, kyb_data: dict) -> bytes:
    """Generates a professional 1-page PDF Executive Audit Report in memory."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("EXECUTIVE PROCUREMENT AUDIT REPORT", title_style))
    elements.append(Paragraph("SGWVM Technology Limited — Dynamic Proposal Evaluation System", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=15, spaceBefore=5))

    # Summary Table Data
    company_name = kyb_data.get("company_name", proposal_data.get("company_name", "N/A"))
    rc_number = kyb_data.get("rc_number", proposal_data.get("rc_number", "N/A"))
    cac_status = kyb_data.get("company_status", "UNKNOWN")
    tin_number = kyb_data.get("tin", "N/A")
    feasibility = proposal_data.get("feasibility_rating", "Conditional")
    risk_score = str(proposal_data.get("risk_score", "N/A"))
    budget_disp = proposal_data.get("budget_display", "N/A")

    table_data = [
        [Paragraph("<b>Vendor Entity</b>", body_style), Paragraph(_paragraph_value(company_name), body_style)],
        [Paragraph("<b>RC / BN Number</b>", body_style), Paragraph(_paragraph_value(rc_number), body_style)],
        [Paragraph("<b>CAC Status</b>", body_style), Paragraph(f"<b>{_paragraph_value(cac_status)}</b>", body_style)],
        [Paragraph("<b>Tax Identification (TIN)</b>", body_style), Paragraph(_paragraph_value(tin_number), body_style)],
        [Paragraph("<b>Financial Feasibility</b>", body_style), Paragraph(_paragraph_value(feasibility), body_style)],
        [Paragraph("<b>Detected Budget / Cost</b>", body_style), Paragraph(_paragraph_value(budget_disp), body_style)],
        [Paragraph("<b>Procurement Risk Score</b>", body_style), Paragraph(f"<b>{_paragraph_value(risk_score)} / 100</b>", body_style)]
    ]

    t = Table(table_data, colWidths=[180, 360])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 15))

    # Executive Brief & Risk Findings
    elements.append(Paragraph("<b>Executive Assessment & Risk Findings</b>", styles['Heading3']))
    brief_text = proposal_data.get("executive_summary", "No executive summary recorded for this proposal.")
    elements.append(Paragraph(_paragraph_value(brief_text), body_style))
    elements.append(Spacer(1, 10))

    # Directors List
    directors = kyb_data.get("directors", [])
    if directors:
        elements.append(Paragraph("<b>Verified Company Directors</b>", styles['Heading3']))
        dir_str = ", ".join(str(director) for director in directors)
        elements.append(Paragraph(_paragraph_value(dir_str), body_style))
        elements.append(Spacer(1, 10))

    # Compliance Flag
    if kyb_data.get("flagged") or proposal_data.get("risk_flagged"):
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#DC2626'), spaceAfter=10, spaceBefore=5))
        elements.append(Paragraph("<b>CRITICAL RISK FLAGGED:</b> Manual Procurement Committee Review Required before contract award.", ParagraphStyle('Warn', parent=body_style, textColor=colors.HexColor('#DC2626'), fontName='Helvetica-Bold')))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
