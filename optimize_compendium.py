import os
import pymupdf

target_folder = r"C:\Users\USER\Desktop\Media Stuff for Ali"
if not os.path.exists(target_folder):
    target_folder = r"C:\Users\USER\Desktop"

pdf_files = [f for f in os.listdir(target_folder) if f.lower().endswith(".pdf")]

if not pdf_files:
    print(f"❌ No PDF files found in {target_folder}")
else:
    for filename in pdf_files:
        src_path = os.path.join(target_folder, filename)
        size_mb = os.path.getsize(src_path) / (1024 * 1024)
        print(f"==================================================")
        print(f"📄 Compendium: {filename}")
        print(f"📦 Original Size: {size_mb:.2f} MB")
        
        doc = pymupdf.open(src_path)
        print(f"📑 Total Pages: {len(doc)}")
        
        out_filename = filename.replace(".pdf", "_web_optimized.pdf")
        out_path = os.path.join(target_folder, out_filename)
        
        # Save compressed web version (removed linear=True)
        doc.save(
            out_path, 
            garbage=4, 
            deflate=True
        )
        doc.close()
        
        new_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        reduction = ((size_mb - new_size_mb) / size_mb) * 100
        print(f"✅ Optimized Version Created: {out_filename}")
        print(f"📦 New Web Size: {new_size_mb:.2f} MB ({reduction:.1f}% size reduction)")
        print(f"==================================================")
