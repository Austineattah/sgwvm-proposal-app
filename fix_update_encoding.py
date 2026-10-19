with open('update.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Clean non-ASCII bullet points or bad characters
cleaned_content = content.replace('\x95', '-').replace('•', '-')

# Ensure proper encoding header at top of file
if not cleaned_content.startswith('# -*- coding: utf-8 -*-'):
    cleaned_content = '# -*- coding: utf-8 -*-\n' + cleaned_content

with open('update.py', 'w', encoding='utf-8') as f:
    f.write(cleaned_content)

print("[+] Cleaned and re-encoded update.py to strict UTF-8!")
