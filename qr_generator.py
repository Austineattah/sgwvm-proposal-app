import qrcode
import io
from PIL import Image, ImageDraw, ImageFont

def generate_qr_badge(qr_ref_id, vendor_name, project_title):
    qr_payload = f"NEXUSVAULT-VERIFIED\nRef: {qr_ref_id}\nVendor: {vendor_name}\nTitle: {project_title}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#059669", back_color="#0f172a").convert('RGB')
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()