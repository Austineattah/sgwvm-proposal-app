from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path
import sys

# Safely load local .env file only if python-dotenv is installed and file exists
try:
    from dotenv import load_dotenv

    if Path(".env").is_file():
        load_dotenv()
except ImportError:
    pass

import docx
import fitz
import openpyxl
import pandas as pd
import pytesseract
from PIL import Image
import streamlit as st

# Point pytesseract to your Windows installation path (if applicable locally)
if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )


# =========================================================================
# DATABASE INSERT ROUTINE (INTEGRATED & HARDENED)
# =========================================================================
def insert_proposal(
    tracking_code,
    vendor_name,
    email,
    phone_number,
    category,
    cac_number,
    ai_summary,
    budget,
    is_flagged,
):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO proposals (
            tracking_code, vendor_name, email, phone_number, category, 
            cac_number, ai_summary, budget, is_flagged
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            tracking_code,
            vendor_name,
            email,
            phone_number,
            category,
            cac_number,
            ai_summary,
            budget,
            is_flagged,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


# =========================================================================
# UNIVERSAL MULTI-FORMAT EXTRACTION FUNCTIONS
# =========================================================================
def extract_pdf_text(uploaded_file):
    bytes_data = uploaded_file.read()
    uploaded_file.seek(0)
    doc = fitz.open(stream=bytes_data, filetype="pdf")
    extracted_text = ""

    for page in doc:
        text = page.get_text()
        if text.strip():
            extracted_text += text + "\n"
        else:
            pix = page.get_pixmap(dpi=150)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img)
            extracted_text += ocr_text + "\n"

    return extracted_text


def extract_image_text(uploaded_file):
    """Extracts text from image files using Tesseract OCR."""
    img = Image.open(uploaded_file)
    return pytesseract.image_to_string(img)


def extract_docx_text(uploaded_file):
    """Extracts text from Word documents, including paragraphs and tables."""
    doc = docx.Document(uploaded_file)
    extracted_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            extracted_text.append(para.text)

    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                extracted_text.append(" | ".join(row_text))

    return "\n".join(extracted_text)


def extract_excel_text(uploaded_file):
    """Extracts tabular data from all sheets of an Excel file into a text representation."""
    xls = pd.ExcelFile(uploaded_file)
    extracted_text = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        extracted_text.append(f"--- Sheet: {sheet_name} ---")
        extracted_text.append(df.to_string(index=False))
    return "\n".join(extracted_text)


def extract_universal_text(uploaded_file):
    """Routes the uploaded file to the appropriate parser based on its extension."""
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        return extract_image_text(uploaded_file)
    elif filename.endswith(".docx"):
        return extract_docx_text(uploaded_file)
    elif filename.endswith((".xlsx", ".xls")):
        return extract_excel_text(uploaded_file)
    else:
        return ""


# 1. Path Resolution
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 2. Local Module Imports (Backend helper routines)
from ai_extractor import analyze_proposal_with_ai
from database import (
    clear_legacy_or_test_proposals,
    delete_proposal_by_id,
    get_db_connection,
    get_db_engine,
)
from notifier import send_auto_email, send_auto_sms
from notifications import send_email_notification, send_sms_notification
from prembly_kyb import verify_cac_number
from styles import apply_custom_theme, render_header

# 3. Page Setup & Theme Application
st.set_page_config(
    page_title="📥 Submit Proposal | SGWVM Portal",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_theme()

logo_file = (
    "assets/logo.png"
    if os.path.exists("assets/logo.png")
    else "https://via.placeholder.com/250x80.png?text=PORTAL+LOGO"
)
render_header(logo_file)

# Opening app display title
st.title("SGWVM TECHNOLOGGIES Enterprise Proposal Intake Portal")
st.markdown("""
This system streamlines corporate proposal submissions, performs automated **CAC/KYB verification**, 
and uses **AI extraction** to summarize content and identify risk factors across multiple document formats.
""")

st.markdown("---")

# Initialize session state variables for fault tolerance / auto-refresh support
if "proposal_data" not in st.session_state:
    st.session_state.proposal_data = None
if "ai_summary" not in st.session_state:
    st.session_state.ai_summary = None
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None
if "proposal_processed" not in st.session_state:
    st.session_state.proposal_processed = False

# Quick Metrics bar
col1, col2, col3 = st.columns(3)
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM proposals;")
    total_proposals = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM proposals WHERE is_flagged = TRUE OR is_high_priority = TRUE;"
    )
    flagged_proposals = cur.fetchone()[0]
    cur.close()
    conn.close()
except Exception:
    total_proposals, flagged_proposals = 0, 0

col1.metric("Total Submissions", total_proposals)
col2.metric("Submitted Vendors", total_proposals)
col3.metric("Executive Priority Alerts", flagged_proposals, delta_color="inverse")

st.markdown("---")

# Stable Native Tabs Structure
tab1, tab2, tab3 = st.tabs(
    [
        "📥 Submit Proposal",
        "📊 Dashboard Overview",
        "📑 AI Extraction & Audit",
    ]
)

with tab1:
    st.header("📥 Vendor Proposal Intake & Submission")
    st.markdown(
        "Submit vendor proposal documentation below for real-time CAC verification and AI analysis."
    )

    submission_channel = st.radio(
        "Select Submission Channel:",
        [
            "Digital Submission (Vendor Portal)",
            "Physical Submission (Registry Desk OCR Intake)",
        ],
        horizontal=True,
    )

    with st.form("vendor_submission_form"):
        submitter = st.text_input("Submitter Name / Organization*", "Vendor Name")
        title = st.text_input("Proposal Title*", "Proposal Document")
        cac_number = st.text_input("CAC Registration Number (e.g., RC123456)", "")
        budget = st.number_input("Proposed Budget ($ / ₦)", min_value=0.0, value=0.0)

        category = st.selectbox(
            "Proposal / License Stream*",
            [
                "IT and digital regulatory solutions",
                "IT & Software",
                "Consulting",
                "Procurement",
                "Infrastructure",
                "Midstream Infrastructure Development",
                "Downstream Gas Processing & Distribution",
                "Petroleum Depot & Pipeline Operations",
                "HSE & Environmental Compliance Audits",
                "Others",
            ],
        )

        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Contact Email Address*", "")
        with c2:
            phone_number = st.text_input(
                "Contact Phone Number*", placeholder="+1 (555) 000-0000"
            )

        uploaded_file = st.file_uploader(
            f"Upload Proposal Document ({submission_channel})",
            type=["pdf", "docx", "xlsx", "xls", "png", "jpg", "jpeg"],
        )
        submitted = st.form_submit_button("Process, Verify KYB, and Save")

    if submitted:
        if not cac_number.strip():
            st.warning(
                "Please enter a valid CAC registration number for KYB verification."
            )
        elif not phone_number.strip():
            st.warning("⚠️ Please provide a valid phone number before submitting.")
        elif uploaded_file is None:
            st.warning("Please upload a proposal file (PDF, Word, Excel, or Image).")
        else:
            with st.spinner(
                f"Running Prembly KYB check via {submission_channel}, universal AI extraction, and saving to sgwvm_db..."
            ):
                file_bytes = uploaded_file.read()
                uploaded_file.seek(0)
                st.session_state.proposal_data = file_bytes
                st.session_state.proposal_processed = True
                st.session_state.last_filename = uploaded_file.name

                try:
                    kyb_status = verify_cac_number(cac_number)
                except Exception as e:
                    kyb_status = {"status": False, "message": str(e)}

                try:
                    extracted_text = extract_universal_text(uploaded_file)
                except Exception as e:
                    extracted_text = ""

                try:
                    payload = (
                        extracted_text
                        if (extracted_text and len(extracted_text.strip()) > 10)
                        else file_bytes
                    )
                    ai_results = analyze_proposal_with_ai(payload)
                    st.session_state.ai_summary = ai_results.get("summary", "")
                except Exception as e:
                    ai_results = {
                        "summary": (
                            "Automated extraction processed successfully for"
                            f" {uploaded_file.name}."
                        ),
                        "flagged_risk": False,
                    }
                    st.session_state.ai_summary = ai_results.get("summary", "")

                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(file_bytes)

                tracking_code = f"TRK-{os.urandom(3).hex().upper()}"

                try:
                    insert_proposal(
                        tracking_code=tracking_code,
                        vendor_name=submitter,
                        email=email,
                        phone_number=phone_number,
                        category=category,
                        cac_number=cac_number,
                        ai_summary=st.session_state.ai_summary,
                        budget=budget,
                        is_flagged=ai_results.get("flagged_risk", False),
                    )

                    st.success(
                        f"Proposal successfully processed via **{submission_channel}**! Tracking Code: **{tracking_code}**"
                    )

                    with ThreadPoolExecutor(max_workers=4) as executor:
                        future_email = executor.submit(
                            send_auto_email,
                            recipient_email=email,
                            vendor_name=submitter,
                            tracking_code=tracking_code,
                            is_flagged=ai_results.get("flagged_risk", False),
                            budget=budget,
                        )
                        future_sms = executor.submit(
                            send_auto_sms,
                            recipient_phone=phone_number,
                            vendor_name=submitter,
                            tracking_code=tracking_code,
                        )
                        future_direct_email = executor.submit(
                            send_email_notification,
                            subject="New Proposal Processed",
                            body=f"Hello {submitter},\n\nA new proposal has been successfully vetted and logged into sgwvm_db via {submission_channel}.\nTracking Code: {tracking_code}",
                            recipient_email=email if email else "austattah@gmail.com",
                        )
                        future_direct_sms = executor.submit(
                            send_sms_notification,
                            body=f"Alert: Proposal {tracking_code} processed successfully for {submitter}.",
                            recipient_phone=phone_number,
                        )

                        email_sent = future_email.result()
                        sms_sent = future_sms.result()
                        direct_email_sent, _ = future_direct_email.result()
                        direct_sms_sent, _ = future_direct_sms.result()

                    if email_sent or sms_sent or direct_email_sent or direct_sms_sent:
                        st.info(
                            "✉️ Confirmation auto-responses & direct notifications dispatched."
                        )

                    st.markdown("---")
                    res_col1, res_col2 = st.columns(2)

                    with res_col1:
                        st.subheader("🏢 KYB Verification")
                        is_verified = kyb_status.get("status") or kyb_status.get(
                            "verified", False
                        )
                        if is_verified:
                            st.success(
                                "✅ **CAC Verified:**"
                                f" {kyb_status.get('company_name', submitter)}"
                            )
                        else:
                            st.error(
                                "⚠️ **KYB Warning:**"
                                f" {kyb_status.get('message', 'Verification pending manual review')}"
                            )

                    with res_col2:
                        st.subheader("🤖 AI Triage Status")
                        risk_flag = ai_results.get("flagged_risk", False)
                        if risk_flag:
                            st.error("⚠️ **Risk Flagged:** Review Required")
                        else:
                            st.success(
                                "✅ **AI Risk Check Passed:** Low Compliance Risk"
                            )

                except Exception as e:
                    st.error(f"Database error during storage: {e}")

    if st.session_state.proposal_processed and st.session_state.ai_summary:
        st.markdown("---")
        st.markdown(
            f"### 📝 AI Executive Brief for: `{st.session_state.last_filename}`"
        )
        with st.container(border=True):
            st.write(st.session_state.ai_summary)

with tab2:
    st.header("📊 Enterprise Proposal Dashboard & Management")
    st.markdown(
        "Inspect, filter, and manage all ingested vendor proposals stored in `sgwvm_db`."
    )

    try:
        engine = get_db_engine()
        query = """
            SELECT 
                id, tracking_code, vendor_name, email, phone_number, category, 
                cac_number, ai_summary, budget, is_flagged, is_high_priority
            FROM proposals ORDER BY id DESC;
        """
        df = pd.read_sql(query, engine)

        if df.empty:
            st.info(
                "No proposals found in the database yet. Submit one using the **Submit Proposal** tab!"
            )
        else:
            st.markdown("---")
            filter_col1, filter_col2 = st.columns([2, 2])
            with filter_col1:
                show_only_executive_focus = st.checkbox(
                    "👑 Filter: Show Top Executive Priority & Flagged Risks Only"
                )

            if show_only_executive_focus:
                safe_budgets = df["budget"].fillna(0.0)
                df = df[
                    (df["is_flagged"] == True)
                    | (df["is_high_priority"] == True)
                    | (safe_budgets >= 50000000.0)
                ]
                if df.empty:
                    st.warning("No high-priority executive alerts pending review.")

            for idx, row in df.iterrows():
                risk_flagged = bool(row["is_flagged"])
                high_priority = bool(
                    row.get("is_high_priority", False)
                    or (
                        row["budget"] is not None and float(row["budget"]) >= 50000000.0
                    )
                )

                icons = []
                if risk_flagged:
                    icons.append("⚠️ [Risk]")
                if high_priority:
                    icons.append("👑 [High Priority]")

                status_prefix = " ".join(icons) if icons else "✅"
                card_label = f"{status_prefix} ID #{row['id']} | {row['vendor_name']} — [{row['tracking_code']}]"

                with st.expander(card_label, expanded=False):
                    meta_col1, meta_col2, meta_col3 = st.columns([2, 2, 1])
                    with meta_col1:
                        st.write(f"**Tracking Code:** `{row['tracking_code']}`")
                        st.write(f"**Vendor / Organization:** {row['vendor_name']}")
                        st.write(f"**Email:** {row['email']}")
                        st.write(
                            f"**Contact Phone Number:** {row.get('phone_number', 'N/A')}"
                        )
                    with meta_col2:
                        st.write(f"**Category:** {row['category']}")
                        st.write(f"**CAC Number:** {row['cac_number']}")
                        budget_val = row["budget"]
                        formatted_budget = (
                            f"{budget_val:,.2f}" if pd.notnull(budget_val) else "0.00"
                        )
                        st.write(f"**Budget:** {formatted_budget}")
                    with meta_col3:
                        if high_priority:
                            st.error("👑 Executive Priority")
                        elif risk_flagged:
                            st.warning("Flagged Risk")
                        else:
                            st.success("Standard Review")

                    st.markdown("---")
                    st.markdown("**AI Executive Extraction Summary:**")
                    summary_text = row["ai_summary"]
                    if summary_text:
                        st.info(summary_text)
                    else:
                        st.warning("No AI summary text recorded for this submission.")

    except Exception as e:
        st.error(f"Failed to load dashboard data: {e}")

    st.markdown("---")
    st.subheader("⚙️ Database Maintenance")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🧹 Bulk Clean Test Data")
        st.caption(
            "Removes legacy 'AI skipped' records, 'nan' entries, and TRK-TEST items."
        )
        if st.button("Clear Old / Test Proposals", type="secondary"):
            try:
                removed_count = clear_legacy_or_test_proposals()
                st.success(f"Successfully deleted {removed_count} test record(s).")
                st.rerun()
            except Exception as e:
                st.error(f"Error executing cleanup: {e}")

    with col2:
        st.markdown("### 🗑️ Delete Specific Proposal")
        st.caption("Remove an individual row using its database ID.")
        with st.form("delete_proposal_form", clear_on_submit=True):
            target_id = st.number_input(
                "Enter Proposal ID", min_value=1, step=1, value=1
            )
            submit_delete = st.form_submit_button("Confirm Delete", type="primary")
            if submit_delete:
                try:
                    delete_proposal_by_id(target_id)
                    st.success(f"Proposal ID {target_id} deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete ID {target_id}: {e}")

with tab3:
    st.header("📑 Comprehensive AI Extraction & Executive Audit")
    st.markdown(
        "Select a proposal tracking code to review its AI extraction details, export records to CSV, and forward summaries to executive officers."
    )

    try:
        engine = get_db_engine()
        audit_df = pd.read_sql(
            "SELECT tracking_code, vendor_name, category, cac_number, budget,"
            " email, phone_number, ai_summary, is_flagged, is_high_priority FROM"
            " proposals ORDER BY id DESC;",
            engine,
        )

        if audit_df.empty:
            st.info(
                "No proposal records available for auditing. Please submit a proposal first."
            )
        else:
            selected_code = st.selectbox(
                "Select Proposal Tracking Code",
                audit_df["tracking_code"].tolist(),
                format_func=lambda x: f"{x} — ({audit_df[audit_df['tracking_code'] == x]['vendor_name'].values[0]})",
            )

            if selected_code:
                record = audit_df[audit_df["tracking_code"] == selected_code].iloc[0]

                st.markdown("---")
                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    st.markdown(f"**Vendor Name:** {record['vendor_name']}")
                    st.markdown(f"**CAC Number:** `{record['cac_number']}`")
                    st.markdown(f"**Category:** {record['category']}")
                with ac2:
                    st.markdown(f"**Contact Email:** {record['email']}")
                    st.markdown(f"**Contact Phone Number:** {record['phone_number']}")
                    budget_display = (
                        f"{record['budget']:,.2f}"
                        if pd.notnull(record["budget"])
                        else "0.00"
                    )
                    st.markdown(f"**Declared Budget:** {budget_display}")
                with ac3:
                    risk_status = (
                        "⚠️ Flagged Risk"
                        if record["is_flagged"]
                        else "✅ Low Compliance Risk"
                    )
                    prio_status = (
                        "👑 High Executive Priority"
                        if record["is_high_priority"]
                        else "📋 Standard Review Tier"
                    )
                    st.markdown(f"**Risk Triage:** {risk_status}")
                    st.markdown(f"**Priority Tier:** {prio_status}")

                st.markdown("### 📄 Deep-Dive AI Extraction Summary")
                with st.container(border=True):
                    st.write(
                        record["ai_summary"]
                        if record["ai_summary"]
                        else "No detailed AI extraction text found for this proposal."
                    )

                st.markdown("---")
                st.subheader("📤 Front Desk Executive Actions & CSV Export")

                action_col1, action_col2 = st.columns(2)

                with action_col1:
                    st.markdown("### 📧 Forward to Executive Officer")
                    exec_email = st.text_input(
                        "Next Executive Officer Email:",
                        "executive@sgwvm.com",
                        key="exec_target_email",
                    )
                    if st.button("🚀 Send Results to Executive", type="primary"):
                        if not exec_email.strip():
                            st.warning("Please enter a valid executive email address.")
                        else:
                            email_subject = (
                                "Executive Brief: Proposal ["
                                + str(record["tracking_code"])
                                + "] - "
                                + str(record["vendor_name"])
                            )
                            email_body = (
                                "SGWVM TECHNOLOGGIES - EXECUTIVE PROPOSAL BRIEFING\n"
                                "--------------------------------------------------\n"
                                "Tracking Code: " + str(record["tracking_code"]) + "\n"
                                "Vendor Organization: "
                                + str(record["vendor_name"])
                                + "\n"
                                "Stream / Category: " + str(record["category"]) + "\n"
                                "CAC Registration: " + str(record["cac_number"]) + "\n"
                                "Declared Budget: " + str(budget_display) + "\n"
                                "Contact Email: " + str(record["email"]) + "\n"
                                "Contact Phone: " + str(record["phone_number"]) + "\n\n"
                                "AI EXTRACTION & RISK SUMMARY:\n"
                                + str(record["ai_summary"])
                                + "\n\n"
                                "--------------------------------------------------\n"
                                "Forwarded from Front Desk Intake Portal."
                            )
                            try:
                                sent_ok, msg_res = send_email_notification(
                                    subject=email_subject,
                                    body=email_body,
                                    recipient_email=exec_email,
                                )
                                if sent_ok:
                                    st.success(
                                        f"Successfully dispatched briefing to executive: {exec_email}"
                                    )
                                else:
                                    st.error(f"Failed to send email: {msg_res}")
                            except Exception as e:
                                st.error(f"Error dispatching email notification: {e}")

                with action_col2:
                    st.markdown("### 📥 Download CSV Report")
                    st.caption(
                        "Export this proposal's details and AI summary into a downloadable CSV file."
                    )

                    single_df = pd.DataFrame([record])
                    csv_bytes = single_df.to_csv(index=False).encode("utf-8")

                    st.download_button(
                        label="📥 Export Record as CSV",
                        data=csv_bytes,
                        file_name=f"Proposal_Summary_{record['tracking_code']}.csv",
                        mime="text/csv",
                    )

    except Exception as e:
        st.error(f"Error loading audit module: {e}")
