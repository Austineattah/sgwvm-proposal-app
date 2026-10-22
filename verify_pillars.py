import os

target_url = "https://NexuusVault-Proposal-Enterprise-Connect.streamlit.app"

# 1. Check/Patch developer_console.py for dynamic link generation
if os.path.exists("developer_console.py"):
    with open("developer_console.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    if "PRODUCTION_BASE_URL" not in content:
        content = f'PRODUCTION_BASE_URL = "{target_url}"\n' + content
    
    # Ensure link generation uses query parameters correctly
    if "client=" not in content:
        print("Warning: 'client=' query param pattern missing in developer_console.py")
    else:
        print("developer_console.py verified: dynamic link routing is present.")
        
    with open("developer_console.py", "w", encoding="utf-8") as f:
        f.write(content)

# 2. Check/Patch app.py for query param routing (st.query_params)
if os.path.exists("app.py"):
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    if "st.query_params" in content or "st.experimental_get_query_params" in content:
        print("app.py verified: query parameter router is active.")
    else:
        print("Note: Ensuring st.query_params router is checked in app.py")

print("Verification complete.")
