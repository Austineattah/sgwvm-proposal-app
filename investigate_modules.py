import glob
import re

PRODUCTION_BASE_URL = "https://NexuusVault-Proposal-Enterprise-Connect.streamlit.app"

print("="*70)
print("🔍 INVESTIGATING TENANT ACTIVATION, URLS, AND VENDOR MODULES")
print("="*70)

keywords = ["solicited", "unsolicited", "vendor", "client", "slug", "admin", "token", "credentials"]

for file in glob.glob("*.py"):
    if file.startswith("test_") or file.startswith("fix_") or file.startswith("wrap_"):
        continue
    with open(file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    matches = []
    for idx, line in enumerate(lines, 1):
        for kw in keywords:
            if kw in line.lower():
                matches.append((idx, line.strip()))
                break
    
    if matches:
        print(f"\n📄 {file} ({len(matches)} keyword matches):")
        # Print first few relevant lines
        for idx, line in matches[:5]:
            print(f"    Line {idx}: {line}")
        if len(matches) > 5:
            print(f"    ... and {len(matches) - 5} more matches")

print("\n" + "="*70)
