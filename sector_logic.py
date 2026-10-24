import datetime

def classify_and_route_proposal(org_name, proposal_text):
    text_lower = proposal_text.lower()
    if any(k in text_lower for k in ['legal', 'compliance', 'regulatory', 'policy', 'audit', 'contract', 'act']):
        directorate = "Directorate of Legal & Compliance"
        feasibility = 87.0
        alignment = 79.0
        risk = "LOW"
        optimization = 92.0
    elif any(k in text_lower for k in ['procurement', 'infrastructure', 'hardware', 'supply', 'facility', 'equipment', 'build']):
        directorate = "Directorate of Procurement & Infrastructure"
        feasibility = 88.0
        alignment = 77.5
        risk = "LOW"
        optimization = 89.0
    else:
        directorate = "Directorate of ICT & Innovation"
        feasibility = 84.0
        alignment = 79.0
        risk = "MEDIUM"
        optimization = 85.0
        
    return directorate, {
        "feasibility_score": feasibility,
        "alignment_score": alignment,
        "risk_index": risk,
        "optimization_score": optimization
    }

def generate_tenant_activation_artifacts(client_name, client_slug, client_email, client_phone):
    base_url = "https://nexusvault-proposal-enterprise-connect.streamlit.app"
    
    tenant_url = f"{base_url}/?tenant={client_slug}"
    vendor_url = f"{base_url}/?tenant={client_slug}&portal=vendor"
    solicitor_url = f"{base_url}/?tenant={client_slug}&portal=directorate"
    
    dispatch_payload = {
        "client_name": client_name,
        "client_slug": client_slug,
        "email": client_email,
        "phone": client_phone,
        "tenant_url": tenant_url,
        "vendor_url": vendor_url,
        "solicitor_url": solicitor_url,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return dispatch_payload

def render_master_developer_console():
    return "Master Developer Console Active"

def render_sector_onboarding_wizard():
    return "Onboarding Wizard Active"

def render_vendor_proposal_submission_portal():
    return "Vendor Portal Active"

def render_tenant_admin_console():
    return "Tenant Admin Active"

def render_sector_analytics():
    return "Analytics Active"

def render_audit_trail():
    return "Audit Trail Active"

def render_executive_dashboard():
    return "Executive Dashboard Active"
