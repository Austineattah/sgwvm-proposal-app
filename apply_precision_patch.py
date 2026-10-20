with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Phase 1 query param extraction
target_phase1 = 'client_slug = query_params.get("client", None)'
replacement_phase1 = 'client_slug = query_params.get("client", None)\nview_override = query_params.get("view", None)'

if target_phase1 in code and 'view_override =' not in code:
    code = code.replace(target_phase1, replacement_phase1, 1)

# 2. Update Phase 2 routing logic
target_phase2 = '''        st.session_state["custom_portal_heading"] = client_data["custom_title"]
        st.session_state["portal_mode"] = "vendor_portal"'''

replacement_phase2 = '''        st.session_state["custom_portal_heading"] = client_data["custom_title"]
        if view_override == "admin":
            st.session_state["portal_mode"] = "client_admin_portal"
        else:
            st.session_state["portal_mode"] = "vendor_portal"'''

if target_phase2 in code:
    code = code.replace(target_phase2, replacement_phase2, 1)

# 3. Insert ROUTE C (Client Internal Admin Portal) before Route C/D Vendor Portal
target_route_insert = '# ROUTE C: PUBLIC VENDOR PROPOSAL PORTAL'

admin_route_block = '''# ROUTE C: CLIENT INTERNAL ADMIN PORTAL (?client=<slug>&view=admin)
if st.session_state["portal_mode"] == "client_admin_portal":
    try:
        import admin_portal
        admin_portal.render_admin_portal()
    except Exception as e:
        st.error(f"❌ Critical Error loading Client Admin Portal: {e}")
    st.stop()

# ROUTE D: PUBLIC VENDOR PROPOSAL PORTAL'''

if target_route_insert in code:
    code = code.replace(target_route_insert, admin_route_block, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("[SUCCESS] Precision patch cleanly integrated into app.py!")
