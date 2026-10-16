import cv2
import numpy as np
from PIL import Image
import re

def decode_qr_from_image(image_bytes):
    """
    Decodes QR code data from image bytes uploaded or captured via webcam.
    Returns the extracted QR reference ID if found.
    """
    try:
        # Convert bytes to PIL Image and then to OpenCV format
        pil_img = Image.open(image_bytes).convert('RGB')
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        # Initialize OpenCV QR Code Detector
        qr_detector = cv2.QRCodeDetector()
        data, bbox, _ = qr_detector.detectAndDecode(cv_img)

        if data:
            # Extract tracking ID pattern (NV-QREF-... or NV-SOLICIT-...)
            match = re.search(r'(NV-[A-Z]+-\d+-\d+)', data)
            if match:
                return match.group(1)
            return data.strip()
        return None
    except Exception as e:
        print(f"QR Scan Error: {e}")
        return None