import glob
import re

files = glob.glob('*.py')
new_domain = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"
old_domains = [
    "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app",
    "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app",
    "NexusVault-Proposal-Enterprise-Connect.streamlit.app",
    "NexusVault-Proposal-Enterprise-Connect.streamlit.app"
]

updated_count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    changed = False
    for old in old_domains:
        if old in content:
            replacement = new_domain if old.startswith("https://") else new_domain.replace("https://", "")
            content = content.replace(old, replacement)
            changed = True
    
    # Update PRODUCTION_BASE_URL constant if present
    if "PRODUCTION_BASE_URL" in content:
        content = re.sub(r'PRODUCTION_BASE_URL\s*=\s*["\'][^"\']+["\']', f'PRODUCTION_BASE_URL = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"', content)
        changed = True

    if changed:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Updated domain references in {f}")
        updated_count += 1

print(f"Domain update complete. Updated {updated_count} files.")
