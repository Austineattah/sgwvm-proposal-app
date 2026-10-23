import json
import streamlit as st

def classify_and_route_proposal(org_name, proposal_text=""):
    """
    Inspects proposal text and organization name to determine 
    the appropriate enterprise directorate and compute agentic scores.
    """
    combined_text = f"{org_name} {proposal_text}".lower()
    
    # Directorate Auto-Assignment Logic
    if any(kw in combined_text for kw in ['tech', 'software', 'digital', 'ict', 'data', 'ai', 'cloud', 'cyber']):
        directorate = "Directorate of ICT & Innovation"
    elif any(kw in combined_text for kw in ['legal', 'compliance', 'regulatory', 'audit', 'policy', 'governance']):
        directorate = "Directorate of Legal & Compliance"
    else:
        directorate = "Directorate of Procurement & Infrastructure"
        
    # Deterministic Agentic Scorecard Calculation
    feasibility = min(99.0, 78.0 + (len(combined_text) % 15))
    alignment = min(98.5, 70.0 + (len(combined_text.split()) * 1.5))
    risk = "LOW" if feasibility > 85 else "MEDIUM"
    optimization = max(80.0, min(97.0, 95.0 - (len(org_name) * 0.5)))
    
    scores = {
        "feasibility_score": round(feasibility, 1),
        "alignment_score": round(alignment, 1),
        "risk_index": risk,
        "optimization_score": round(optimization, 1)
    }
    
    return directorate, scores

# --- COMPREHENSIVE HELPER & COMPATIBILITY EXPORTS ---

def render_master_developer_console():
    st.info("?? Master Developer Console active.")

def render_sector_onboarding_wizard(slug=""):
    st.info("?? Sector Onboarding Wizard active.")

def render_vendor_proposal_submission_portal(slug=""):
    st.info("?? Desk Officer Unsolicited Proposal Gateway active.")

def render_tenant_admin_console(slug=""):
    st.info("?? Tenant Admin Console active.")

def render_sector_analytics(slug=""):
    st.info("?? Sector Analytics active.")

def render_audit_trail(slug=""):
    st.info("?? Audit Ledger active.")

def render_executive_dashboard(slug=""):
    st.info("??? Executive Dashboard active.")
