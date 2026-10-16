import io
from pypdf import PdfWriter, PdfReader
from PIL import Image, ImageDraw, ImageFont

def generate_evaluation_certificate(qr_ref, vendor_name, project_title, status, compliance_score, cost, summary):
    """
    Generates a high-contrast executive evaluation summary image 
    badge ready for MDA presentation and printing.
    """
    img_width, img_height = 800, 1000
    img = Image.new('RGB', (img_width, img_height), color='#070d19')
    draw = ImageDraw.Draw(img)

    # Outer Border
    draw.rectangle([20, 20, img_width-20, img_height-20], outline='#1d4ed8', width=3)
    draw.rectangle([28, 28, img_width-28, img_height-28], outline='#008751', width=2)

    # Header Panel
    draw.rectangle([40, 40, img_width-40, 140], fill='#0a192f', outline='#1d4ed8')
    draw.text((60, 55), "NEXUSVAULT TECHNOLOGIES - SOVEREIGN PLATFORM", fill='#ffffff')
    draw.text((60, 85), "OFFICIAL BPP & STATUTORY COMPLIANCE EVALUATION CERTIFICATE", fill='#38bdf8')

    # Main Details
    y_pos = 180
    details = [
        ("TRACKING REF ID:", qr_ref),
        ("VENDOR / BIDDER:", vendor_name),
        ("PROJECT / TENDER TITLE:", project_title),
        ("EVALUATION STATUS:", status),
        ("STATUTORY SCORE:", f"{compliance_score}% / 100%"),
        ("COST IMPLICATION:", cost),
    ]

    for label, val in details:
        draw.text((60, y_pos), label, fill='#94a3b8')
        draw.text((260, y_pos), str(val)[:50], fill='#ffffff')
        y_pos += 45
        draw.line([60, y_pos-10, img_width-60, y_pos-10], fill='#1e293b', width=1)

    # AI Summary Box
    draw.rectangle([60, y_pos+10, img_width-60, y_pos+180], fill='#0f172a', outline='#334155')
    draw.text((80, y_pos+25), "EXECUTIVE AI COMPLIANCE SUMMARY:", fill='#38bdf8')
    
    # Wrap Summary Text
    words = summary.split()
    line = ""
    text_y = y_pos + 55
    for word in words:
        if len(line + " " + word) < 60:
            line += " " + word
        else:
            draw.text((80, text_y), line, fill='#e2e8f0')
            line = word
            text_y += 25
            if text_y > y_pos + 160:
                break
    if line and text_y <= y_pos + 160:
        draw.text((80, text_y), line, fill='#e2e8f0')

    # Footer Seal
    draw.text((60, img_height-70), "STRICTLY CONFIDENTIAL - STATUTORY PROCUREMENT RECORD", fill='#ef4444')
    draw.text((60, img_height-45), "AUTHENTICATED BY NEXUSVAULT CRYPTOGRAPHIC LEDGER GATEWAY", fill='#34d399')

    # Convert to PNG Byte Stream
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()