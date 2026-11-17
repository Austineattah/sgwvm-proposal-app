import os
import pymupdf

pdf_dir = "uploads/proposals"
if os.path.exists(pdf_dir):
    files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    for file in files:
        full_path = os.path.join(pdf_dir, file)
        size_mb = os.path.getsize(full_path) / (1024 * 1024)
        print(f"📄 Found: {file} ({size_mb:.2f} MB)")
        doc = pymupdf.open(full_path)
        print(f"   📑 Pages: {len(doc)}")
        for i, page in enumerate(doc):
            imgs = page.get_images(full=True)
            if len(imgs) > 0:
                print(f"      - Page {i+1}: {len(imgs)} embedded image(s)")
else:
    print(f"Directory {pdf_dir} not found.")
