import os
import pymupdf

target_folder = r"C:\Users\USER\Desktop\Media Stuff for Ali"

for filename in os.listdir(target_folder):
    if filename.endswith(".pdf") and "_web_optimized" not in filename and "_compressed" not in filename:
        src_path = os.path.join(target_folder, filename)
        out_path = os.path.join(target_folder, filename.replace(".pdf", "_compressed.pdf"))
        
        print(f"Compressing {filename}...")
        doc = pymupdf.open(src_path)
        
        for page in doc:
            # Get list of images on the page
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                try:
                    # Extract base image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # If image is huge, we can replace or let PyMuPDF re-render page pixmaps
                except Exception:
                    continue

        # Alternatively, save pages as compressed pixmap/PDF stream or use pixmap reduction
        doc.save(out_path, garbage=4, deflate=True, ascii=False)
        doc.close()
        
        orig_size = os.path.getsize(src_path) / (1024 * 1024)
        new_size = os.path.getsize(out_path) / (1024 * 1024)
        print(f"-> Done: {new_size:.2f} MB (was {orig_size:.2f} MB)")

print("All files processed!")
