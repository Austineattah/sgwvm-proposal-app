import os
import fitz

def inspect_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File '{pdf_path}' not found.")
        return
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"📦 Total File Size: {file_size_mb:.2f} MB")
    doc = fitz.open(pdf_path)
    print(f"📑 Total Page Count: {len(doc)}")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        print(f"Page {page_num + 1}: {len(images)} embedded images")

if __name__ == '__main__':
    inspect_pdf('Hon_Ali_Isa_Beyond_Rhetorics.pdf')
