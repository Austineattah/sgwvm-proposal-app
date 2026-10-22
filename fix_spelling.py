import glob

files = glob.glob('*.py')
old_domain = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"
new_domain = "https://NexusVault-Proposal-Enterprise-Connect.streamlit.app"

updated_count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if "NexusVault" in content:
        content = content.replace("NexusVault", "NexusVault")
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Corrected domain spelling in: {f}")
        updated_count += 1

print(f"Spelling update complete. Corrected {updated_count} files.")
