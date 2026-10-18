import streamlit as st
import datetime
from theme_manager import ThemeManager
from schedule_enforcer import ScheduleEnforcer
from payment_gatekeeper import PaymentGatekeeper
from session_resume import SessionResumeManager
from complaint_desk import ComplaintDesk
from postgres_adapter import PostgresStorage

# --- STORAGE ADAPTER INITIALIZATION (PostgreSQL with Fallback) ---
class InMemoryStorage:
    def __init__(self):
        self.store = {}
    def upsert(self, key: str, value: dict) -> bool:
        self.store[key] = value
        return True
    def get(self, key: str) -> dict:
        return self.store.get(key)
    def save(self, key: str, value: dict):
        self.store[key] = value

if "db" not in st.session_state:
    try:
        # Attempt connection to persistent PostgreSQL database
        st.session_state.db = PostgresStorage()
        st.sidebar.success("🔗 Connected to PostgreSQL Database")
    except Exception:
        # Fallback to in-memory storage if PostgreSQL service is offline
        st.session_state.db = InMemoryStorage()
        st.sidebar.warning("⚠️ Using Temporary Memory Store (PostgreSQL offline)")

# --- 1. PRIORITY 1: THEME MANAGEMENT ---
st.set_page_config(page_title="NexusVault Proposal Intake Portal", layout="wide")
theme_mode = st.sidebar.selectbox("Select Portal Theme", ["DEEP_BLUE", "SHARP_MAGENTA", "DYNAMIC_10MIN"])
st.markdown(ThemeManager.get_theme_css(theme_mode), unsafe_allow_html=True)

st.title("🏛️ Super Intelligence - Agentic AI Proposal Intake Portal")
st.markdown("### NexusVault Technologies Ltd & Federal Public Sector Procurement Gateway")

# --- MOCK CLIENT MDA CONFIGURATION ---
client_config = {
    "slug": "nitda",
    "mda_name": "National Information Technology Development Agency (NITDA)",
    "pre_bidding_cutoff": "2026-12-31T23:59:59+00:00",
    "final_bidding_cutoff": "2026-12-31T23:59:59+00:00",
    "payment_gateway": "remita",
    "gateway_api_key": "live_key_sample",
    "gateway_merchant_id": "MERCH-001"
}

# --- 2. PRIORITY 2: SCHEDULE ENFORCER ---
status_text, is_open, metrics = ScheduleEnforcer.check_bidding_status(client_config)
st.sidebar.markdown(f"**Portal Status:** `{status_text}`")
st.sidebar.markdown(f"⏱️ Time Remaining: **{metrics['days']}d {metrics['hours']}h {metrics['minutes']}m**")

if not is_open:
    st.error("⚠️ The bidding window for this solicitation is currently CLOSED or under evaluation. Submissions are disabled.")
    st.stop()

# --- NAVIGATION TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 New Submission / Payment Gate", "📂 Resume Draft Session", "🛠️ Complaint & Support Desk"])

# --- TAB 1: PAYMENT GATE & INTAKE ---
with tab1:
    st.subheader("Step 1: Pre-Bidding Payment & Access Gate")
    vendor_email = st.text_input("Official Vendor Corporate Email", key="pay_email")
    tx_ref = st.text_input("Bank Transaction Reference / Remita Retrieval Reference (RRR)", key="pay_ref")

    if st.button("Verify Payment & Unlock Portal"):
        if not vendor_email or not tx_ref:
            st.warning("Please provide both email and transaction reference.")
        else:
            result = PaymentGatekeeper.verify_payment_and_unlock(client_config, vendor_email, tx_ref)
            if result["success"]:
                st.success(result["message"])
                st.info(f"🔑 Your QR Tracking Code: `{result['tracking_code']}` (Save this code to resume later!)")
                st.session_state["unlocked_tracking"] = result["tracking_code"]
                st.session_state["unlocked_email"] = vendor_email
            else:
                st.error(result["message"])

    if st.session_state.get("unlocked_tracking"):
        st.markdown("---")
        st.subheader("Step 2: Solicited Vendor Document Intake Portal")
        st.success(f"Session Active | Tracking Key: {st.session_state['unlocked_tracking']}")
        
        company_name = st.text_input("Registered Corporate Name")
        cac_number = st.text_input("CAC Registration Number (RC/BN)")
        firs_tcc = st.file_uploader("Upload 3-Year FIRS Tax Clearance Certificate (PDF)", type=["pdf"])
        technical_proposal = st.file_uploader("Upload Technical Proposal (PDF)", type=["pdf"])

        resume_mgr = SessionResumeManager(st.session_state.db)
        if st.button("💾 Auto-Save Draft Progress"):
            draft_data = {"company_name": company_name, "cac_number": cac_number}
            resume_mgr.save_draft_state(st.session_state["unlocked_tracking"], st.session_state["unlocked_email"], draft_data)
            st.success("Draft state saved successfully to persistent database! You can safely close your browser and resume later.")

# --- TAB 2: RESUME DRAFT ---
with tab2:
    st.subheader("Resume Saved Submission Session")
    res_code = st.text_input("Enter Your QR Tracking Code")
    res_email = st.text_input("Enter Vendor Corporate Email")

    if st.button("Restore Session"):
        resume_mgr = SessionResumeManager(st.session_state.db)
        data = resume_mgr.resume_session(res_code, res_email)
        if data:
            st.success("Session restored successfully from database!")
            st.json(data)
        else:
            st.error("Invalid tracking code or email combination.")

# --- TAB 3: COMPLAINT & SUPPORT DESK ---
with tab3:
    st.subheader("Vendor Support & Issue Resolution Desk")
    st.markdown("Experiencing payment timeouts, network drops, or gateway debits without confirmation? Log a ticket below.")

    c_email = st.text_input("Vendor Email", key="cmp_email")
    c_phone = st.text_input("Phone Number", key="cmp_phone")
    c_ref = st.text_input("Transaction / RRR Reference", key="cmp_ref")
    c_issue = st.selectbox("Issue Category", ["Payment Timeout / Debit without QR", "Portal Access Failure", "Document Upload Error"])
    c_narrative = st.text_area("Describe the issue in detail")

    complaint_desk = ComplaintDesk(st.session_state.db)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Self-Service Re-Query Payment"):
            res = complaint_desk.re_query_payment_gateway(client_config, c_ref, c_email)
            if res["success"]:
                st.success(res["message"])
            else:
                st.error(res["message"])
    with col2:
        if st.button("📨 Submit Formal Complaint Ticket"):
            if not c_email or not c_ref:
                st.warning("Please fill in your email and transaction reference.")
            else:
                ticket_res = complaint_desk.log_complaint_ticket(
                    client_slug=client_config["slug"],
                    vendor_email=c_email,
                    phone_number=c_phone,
                    bank_ref=c_ref,
                    issue_category=c_issue,
                    narrative=c_narrative
                )
                st.success(ticket_res["message"])
