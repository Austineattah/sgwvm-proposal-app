import os
import pymupdf

target_folder = r"C:\Users\USER\Desktop\Media Stuff for Ali"

for filename in os.listdir(target_folder):
    if filename.endswith(".pdf") and "_web_compressed" not in filename and "_ultra" not in filename:
        src_path = os.path.join(target_folder, filename)
        out_path = os.path.join(target_folder, filename.replace(".pdf", "_ultra_compressed.pdf"))
        
        print(f"Ultra-compressing {filename}...")
        doc = pymupdf.open(src_path)
        new_doc = pymupdf.open()
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render at 110 DPI for ultra-lightweight web delivery
            pix = page.get_pixmap(dpi=110)
            img_bytes = pix.tobytes("jpeg")
            
            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)
            
        new_doc.save(out_path, garbage=4, deflate=True)
        new_doc.close()
        doc.close()
        
        orig_size = os.path.getsize(src_path) / (1024 * 1024)
        new_size = os.path.getsize(out_path) / (1024 * 1024)
        print(f"-> Done: {new_size:.2f} MB (was {orig_size:.2f} MB)")

print("All files compressed under 10MB for Streamlit Cloud!")
