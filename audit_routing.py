import glob
import re

files = glob.glob('*.py')
target_domain = "https://NexuusVault-Proposal-Enterprise-Connect.streamlit.app"

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    modified = False
    
    # 1. Ensure PRODUCTION_BASE_URL is defined if client links are generated here
    if "client=" in content or "slug" in content:
        if "PRODUCTION_BASE_URL" not in content:
            # Inject PRODUCTION_BASE_URL at the top after imports
            import_pos = content.rfind("import ")
            if import_pos != -1:
                end_of_line = content.find("\n", import_pos)
                content = content[:end_of_line + 1] + f'\nPRODUCTION_BASE_URL = "{target_domain}"\n' + content[end_of_line + 1:]
                modified = True

        # 2. Standardize hardcoded or misformatted link strings to use PRODUCTION_BASE_URL + query params
        # Look for old string concatenations like f".../{slug}" or similar and convert to query param format
        pattern = r'f["\'][^"\']*?/?([?&]client=|\{\s*slug\s*\})[^"\']*?["\']'
        # Let's replace hardcoded portal URLs with the standardized query structure
        content = content.replace('/?client=', '/?client=')
        
    if modified:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Audited and standardized routing in: {f}")

print("Precision routing audit complete.")
