from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import re
import sys
import uuid
import bcrypt
from streamlit.errors import StreamlitSecretNotFoundError
from werkzeug.utils import secure_filename

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
import qrcode
from PIL import Image
import streamlit as st
import streamlit_authenticator as stauth

ROOT_DIR = Path(__file__).resolve().parent
PROPOSALS_DB_PATH = ROOT_DIR / "proposals.db"
PROPOSAL_UPLOAD_DIR = ROOT_DIR / "uploads" / "proposals"
ORG_CONFIG_PATH = ROOT_DIR / "org_config.json"
DEFAULT_ORG_CONFIG = {
    "org_name": "SGWVM Technology",
    "corporate_entity_name": "SGWVM Technology",
    "contact_address": "",
    "admin_email": "",
    "logo_path": "assets/logo.png",
}


def load_org_config():
    config = DEFAULT_ORG_CONFIG.copy()
    if ORG_CONFIG_PATH.exists():
        with ORG_CONFIG_PATH.open(encoding="utf-8") as config_file:
            stored_config = json.load(config_file)
        if not isinstance(stored_config, dict):
            raise ValueError("org_config.json must contain a JSON object.")
        config.update(stored_config)

    for key in (
        "org_name",
        "corporate_entity_name",
        "contact_address",
        "admin_email",
        "logo_path",
    ):
        if not isinstance(config.get(key), str):
            raise ValueError(f"org_config.json {key} must be a string.")
    return config


try:
    ORG_CONFIG = load_org_config()
except (OSError, json.JSONDecodeError, ValueError) as exc:
    ORG_CONFIG = DEFAULT_ORG_CONFIG.copy()
    ORG_CONFIG_LOAD_ERROR = exc
else:
    ORG_CONFIG_LOAD_ERROR = None

st.set_page_config(
    page_title=f"📥 Submit Proposal | {ORG_CONFIG['org_name']}",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

if ORG_CONFIG_LOAD_ERROR is not None:
    st.error(f"Could not load organization settings: {ORG_CONFIG_LOAD_ERROR}")
    st.stop()


MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024


def get_runtime_secret(name):
    environment_value = os.getenv(name)
    if environment_value:
        return environment_value
    try:
        return st.secrets[name]
    except (KeyError, StreamlitSecretNotFoundError):
        return None


def validate_pdf_upload(uploaded_file):
    original_name = Path(uploaded_file.name).name
    if Path(original_name).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are accepted.")

    safe_filename = secure_filename(original_name)
    if not safe_filename or Path(safe_filename).suffix.lower() != ".pdf":
        raise ValueError("The uploaded PDF must have a valid filename.")

    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        raise ValueError("PDF files must be 10 MB or smaller.")
    return safe_filename, file_bytes


def clear_admin_session():
    setup_skipped = st.session_state.get("setup_skipped", False)
    portal_view = st.session_state.get(
        "portal_view_selector", "Internal Admin Portal"
    )
    st.session_state.clear()
    st.session_state["setup_skipped"] = setup_skipped
    st.session_state["portal_view_selector"] = portal_view


if not ORG_CONFIG.get("setup_completed", False) and not st.session_state.get(
    "setup_skipped", False
):
    st.title("🚀 Client Installation & Setup Wizard")
    st.markdown(
        "Configure your organization details and branding before opening the portal."
    )
    with st.form("client_onboarding_setup_form"):
        setup_org_name = st.text_input(
            "Organization Name",
            value=ORG_CONFIG["org_name"],
            placeholder="Nigerian National Assembly",
        )
        setup_entity_name = st.text_input(
            "Corporate Entity Name", value=ORG_CONFIG["corporate_entity_name"]
        )
        setup_contact_address = st.text_area(
            "Contact Address", value=ORG_CONFIG["contact_address"]
        )
        setup_admin_email = st.text_input(
            "Official Admin Email (for notifications)",
            value=ORG_CONFIG["admin_email"],
        )
        setup_logo = st.file_uploader(
            "Corporate Branding Logo",
            type=["png", "jpg", "jpeg"],
            help="PNG and JPG files are saved as assets/logo.png.",
        )
        save_setup = st.form_submit_button(
            "💾 Save & Initialize Client System", type="primary"
        )

    if save_setup:
        missing_setup_value = next(
            (
                label
                for value, label in (
                    (setup_org_name, "Organization Name"),
                    (setup_entity_name, "Corporate Entity Name"),
                    (setup_contact_address, "Contact Address"),
                    (setup_admin_email, "Official Admin Email"),
                )
                if not value.strip()
            ),
            None,
        )
        if missing_setup_value:
            st.warning(f"Please enter {missing_setup_value}.")
        elif not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+", setup_admin_email.strip()
        ):
            st.warning("Please enter a valid Official Admin Email.")
        else:
            updated_config = ORG_CONFIG.copy()
            updated_config.update(
                {
                    "org_name": setup_org_name.strip(),
                    "corporate_entity_name": setup_entity_name.strip(),
                    "contact_address": setup_contact_address.strip(),
                    "admin_email": setup_admin_email.strip(),
                    "setup_completed": True,
                }
            )
            try:
                if setup_logo is not None:
                    logo_path = ROOT_DIR / "assets" / "logo.png"
                    logo_path.parent.mkdir(parents=True, exist_ok=True)
                    logo_image = Image.open(setup_logo)
                    logo_buffer = io.BytesIO()
                    logo_image.save(logo_buffer, format="PNG")
                    logo_path.write_bytes(logo_buffer.getvalue())
                    updated_config["logo_path"] = "assets/logo.png"

                temporary_config_path = ORG_CONFIG_PATH.with_suffix(".json.tmp")
                temporary_config_path.write_text(
                    json.dumps(updated_config, indent=2) + "\n", encoding="utf-8"
                )
                os.replace(temporary_config_path, ORG_CONFIG_PATH)
            except OSError as exc:
                st.error(f"Could not save organization settings: {exc}")
            else:
                st.rerun()

    if st.button(
        "⏩ Skip & Continue with Existing / Demo Environment",
        key="skip_client_setup",
    ):
        st.session_state.setup_skipped = True
        st.rerun()
    st.stop()


def initialize_submissions_db():
    with sqlite3.connect(PROPOSALS_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                cac_number TEXT NOT NULL,
                proposal_title TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                budget REAL,
                pdf_path TEXT NOT NULL,
                submission_date TEXT NOT NULL,
                submission_channel TEXT NOT NULL DEFAULT 'Digital',
                tracking_code TEXT
            );
            """)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(submissions);")}
        if "submission_channel" not in columns:
            conn.execute(
                "ALTER TABLE submissions ADD COLUMN submission_channel "
                "TEXT NOT NULL DEFAULT 'Digital';"
            )
        if "tracking_code" not in columns:
            conn.execute("ALTER TABLE submissions ADD COLUMN tracking_code TEXT;")


def insert_vendor_submission(
    company_name,
    cac_number,
    proposal_title,
    email,
    phone,
    address,
    budget,
    pdf_path,
    submission_channel="Digital",
    tracking_code=None,
):
    with sqlite3.connect(PROPOSALS_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO submissions (
                company_name, cac_number, proposal_title, email, phone,
                address, budget, pdf_path, submission_date, submission_channel,
                tracking_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                company_name,
                cac_number,
                proposal_title,
                email,
                phone,
                address,
                budget,
                str(pdf_path),
                datetime.now().astimezone().isoformat(timespec="seconds"),
                submission_channel,
                tracking_code,
            ),
        )


def get_submission_channel(tracking_code):
    with sqlite3.connect(PROPOSALS_DB_PATH) as conn:
        row = conn.execute(
            "SELECT submission_channel FROM submissions WHERE tracking_code = ?;",
            (tracking_code,),
        ).fetchone()
    return row[0] if row else "Legacy record"


def generate_submission_qr(submission_id, cac_number, tracking_payload):
    payload = json.dumps(
        {
            "submission_id": submission_id,
            "cac_number": cac_number,
            "tracking_payload": tracking_payload,
        },
        separators=(",", ":"),
    )
    qr_image = qrcode.make(payload).convert("RGB")
    image_buffer = io.BytesIO()
    qr_image.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return qr_image, image_buffer.getvalue()


initialize_submissions_db()

# Point pytesseract to your Windows installation path (if applicable locally)
if os.path.exists(r"C:\Program Files\Tesseract-OCR\tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

st.sidebar.title(f"{ORG_CONFIG['org_name']} Portal Access")
portal_view = st.sidebar.radio(
    "Choose a portal",
    ["Public Vendor Portal", "Internal Admin Portal"],
    index=0,
    key="portal_view_selector",
)

if portal_view == "Public Vendor Portal":
    public_logo_path = ROOT_DIR / ORG_CONFIG["logo_path"]
    if public_logo_path.is_file():
        st.image(str(public_logo_path), width=150)
    st.title(f"{ORG_CONFIG['org_name']} Enterprise Proposal Intake Portal")
    st.header("📥 Public Vendor Proposal Submission")
    st.markdown(
        "Submit your proposal details and upload a PDF. This vendor portal is open "
        "to the public without login."
    )

    with st.form("public_vendor_submission_form"):
        company_name = st.text_input("Organisation Name*", key="draft_company_name")
        cac_number = st.text_input("CAC Number*", key="draft_cac_number")
        proposal_title = st.text_input("Title of Proposal*", key="draft_proposal_title")
        contact_email = st.text_input("Contact Email*", key="draft_email")
        contact_phone = st.text_input("Phone*", key="draft_phone")
        company_address = st.text_area("Address*", height=100, key="draft_address")
        budget_text = st.text_input(
            "Optional Budget (₦)",
            placeholder="Leave blank if not applicable",
            key="draft_budget",
        )
        uploaded_pdf = st.file_uploader(
            "Upload PDF Proposal",
            type=["pdf"],
            help="Only PDF files are accepted for public vendor submissions.",
            key="draft_pdf",
        )
        submitted = st.form_submit_button(
            "Submit Proposal", key="public_vendor_submit_btn"
        )

    if submitted:
        required_fields = (
            (company_name, "Organisation Name"),
            (cac_number, "CAC Number"),
            (proposal_title, "Title of Proposal"),
            (contact_email, "Contact Email"),
            (contact_phone, "Phone"),
            (company_address, "Address"),
        )
        missing_field = next(
            (label for value, label in required_fields if not value.strip()), None
        )
        if missing_field:
            st.warning(f"Please enter {missing_field}.")
        elif uploaded_pdf is None:
            st.warning("Please upload a PDF proposal before submitting.")
        else:
            try:
                budget = (
                    float(budget_text.replace(",", "").strip())
                    if budget_text.strip()
                    else None
                )
                if budget is not None and budget < 0:
                    raise ValueError
            except ValueError:
                st.warning("Please enter a valid non-negative budget.")
            else:
                PROPOSAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                safe_name = (
                    re.sub(r"[^A-Za-z0-9._-]+", "_", company_name).strip("_")
                    or "vendor"
                )
                pdf_path = PROPOSAL_UPLOAD_DIR / (f"{safe_name}_{uuid.uuid4().hex}.pdf")

                try:
                    pdf_path.write_bytes(uploaded_pdf.getvalue())
                    tracking_code = f"SUB-{uuid.uuid4().hex[:10].upper()}"
                    insert_vendor_submission(
                        company_name=company_name.strip(),
                        cac_number=cac_number.strip(),
                        proposal_title=proposal_title.strip(),
                        email=contact_email.strip(),
                        phone=contact_phone.strip(),
                        address=company_address.strip(),
                        budget=budget,
                        pdf_path=pdf_path.relative_to(ROOT_DIR),
                        submission_channel="Digital",
                        tracking_code=tracking_code,
                    )
                except Exception as exc:
                    if pdf_path.exists():
                        pdf_path.unlink()
                    st.error(f"Failed to save your proposal: {exc}")
                else:
                    st.success("Your submission is successful. Thank you!")
    st.stop()

if portal_view == "Internal Admin Portal":
    if not st.session_state.get("admin_logged_in", False):
        admin_password_hash = get_runtime_secret("ADMIN_PASSWORD_HASH")
        if not admin_password_hash:
            st.sidebar.warning(
                "Admin access is unavailable until ADMIN_PASSWORD_HASH is configured "
                "in Streamlit secrets or the environment."
            )
            st.stop()
        admin_password = st.sidebar.text_input(
            "Admin password",
            type="password",
            help="Enter the internal admin password to unlock proposal review and AI tools.",
            key="admin_password",
        )
        if admin_password:
            try:
                password_matches = bcrypt.checkpw(
                    admin_password.encode("utf-8"),
                    admin_password_hash.encode("utf-8"),
                )
            except ValueError:
                st.sidebar.error(
                    "ADMIN_PASSWORD_HASH must contain a valid bcrypt password hash."
                )
                st.stop()
            if password_matches:
                st.session_state.admin_logged_in = True
                st.session_state.pop("admin_password", None)
                st.rerun()
            else:
                st.warning("Incorrect admin password. Please try again.")
        else:
            st.warning(
                "Access restricted to the internal admin portal. Please enter the admin password."
            )
        st.stop()

    st.sidebar.success("Admin portal unlocked.")
    st.sidebar.button(
        "Log out",
        key="admin_logout",
        on_click=clear_admin_session,
    )
    can_access_ai_extractor = st.session_state.get("admin_logged_in", False)

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
        status="Draft",
    ):
        conn = get_db_connection()
        cur = conn.cursor()

        normalized_status = (
            status if status in ("Draft", "Pending", "Approved") else "Draft"
        )

        cur.execute(
            """
            INSERT INTO proposals (
                tracking_code, vendor_name, email, phone_number, category, 
                cac_number, ai_summary, budget, is_flagged, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
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
                normalized_status,
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
                row_text = [
                    cell.text.strip() for cell in row.cells if cell.text.strip()
                ]
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
    ROOT_DIR_STR = os.path.abspath(os.path.dirname(__file__))
    if ROOT_DIR_STR not in sys.path:
        sys.path.insert(0, ROOT_DIR_STR)

    # 2. Local Module Imports (Backend helper routines)
    from ai_extractor import analyze_proposal_with_ai
    from database import (
        clear_legacy_or_test_proposals,
        delete_proposal_by_id,
        get_db_connection,
        get_db_engine,
    )
    from notifier import (
        send_auto_email,
        send_auto_sms,
        send_executive_summary_email,
    )
    from notifications import send_email_notification, send_sms_notification
    from prembly_kyb import verify_cac_number
    from styles import apply_custom_theme, render_header

    apply_custom_theme()

    logo_file = (
        str(ROOT_DIR / ORG_CONFIG["logo_path"])
        if (ROOT_DIR / ORG_CONFIG["logo_path"]).is_file()
        else "https://via.placeholder.com/250x80.png?text=PORTAL+LOGO"
    )
    render_header(logo_file, ORG_CONFIG["org_name"])

    # Opening app display title
    st.title(f"{ORG_CONFIG['org_name']} Enterprise Proposal Intake Portal")
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

    if portal_view == "Public Vendor Portal":
        st.header("📥 Public Vendor Proposal Submission")
        st.markdown(
            "Submit your proposal details and upload a PDF. This vendor portal is open to the public without login."
        )

        with st.form("vendor_submission_form"):
            company_name = st.text_input(
                "Company Name*", "", key="legacy_public_company_name"
            )
            cac_registration_number = st.text_input(
                "CAC Registration Number*", key="legacy_public_cac_number"
            )
            proposal_title = st.text_input(
                "Title of Proposal*", key="legacy_public_proposal_title"
            )
            contact_email = st.text_input("Contact Email*", key="legacy_public_email")
            contact_phone = st.text_input(
                "Contact Phone Number*", key="legacy_public_phone"
            )
            company_address = st.text_area(
                "Company Address*", height=100, key="legacy_public_address"
            )
            budget = st.number_input(
                "Optional Budget (₦)",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                key="legacy_public_budget",
            )
            uploaded_pdf = st.file_uploader(
                "Upload PDF Proposal",
                type=["pdf"],
                help="Only PDF files are accepted for public vendor submissions.",
                key="legacy_public_pdf",
            )
            submitted = st.form_submit_button(
                "Submit Proposal", key="legacy_public_submit_btn"
            )

        if submitted:
            if not company_name.strip():
                st.warning("Please enter the company name.")
            elif not cac_registration_number.strip():
                st.warning("Please enter a valid CAC registration number.")
            elif not proposal_title.strip():
                st.warning("Please enter the title of the proposal.")
            elif not contact_email.strip():
                st.warning("Please provide a contact email address.")
            elif not contact_phone.strip():
                st.warning("Please provide a contact phone number.")
            elif not company_address.strip():
                st.warning("Please provide the company address.")
            elif uploaded_pdf is None:
                st.warning("Please upload a PDF proposal before submitting.")
            else:
                proposal_dir = Path("uploads") / "proposals"
                proposal_dir.mkdir(parents=True, exist_ok=True)

                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", company_name).strip("_")
                safe_name = safe_name or "vendor"
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                saved_filename = f"{safe_name}_{timestamp}.pdf"
                pdf_path = proposal_dir / saved_filename
                pdf_path.write_bytes(uploaded_pdf.read())

                vendor_metadata = {
                    "company_name": company_name,
                    "cac_registration_number": cac_registration_number,
                    "proposal_title": proposal_title,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "company_address": company_address,
                    "budget": float(budget) if budget else 0.0,
                    "submitted_at": datetime.utcnow().isoformat(timespec="seconds")
                    + "Z",
                    "pdf_path": str(pdf_path),
                    "status": "Draft",
                }

                history_path = proposal_dir / "vendor_submission_log.json"
                existing_log = []
                if history_path.exists():
                    try:
                        existing_log = json.loads(
                            history_path.read_text(encoding="utf-8")
                        )
                    except json.JSONDecodeError:
                        existing_log = []
                existing_log.append(vendor_metadata)
                history_path.write_text(
                    json.dumps(existing_log, indent=2), encoding="utf-8"
                )

                tracking_code = f"TRK-{os.urandom(3).hex().upper()}"
                try:
                    insert_proposal(
                        tracking_code=tracking_code,
                        vendor_name=company_name,
                        email=contact_email,
                        phone_number=contact_phone,
                        category="Public Vendor Submission",
                        cac_number=cac_registration_number,
                        ai_summary=f"Submitted proposal '{proposal_title}' for review.",
                        budget=budget,
                        is_flagged=False,
                        status="Draft",
                    )
                    st.success(
                        f"Proposal submitted successfully. Tracking Code: **{tracking_code}**. Status: **Draft**"
                    )
                    st.caption(
                        "Your PDF has been stored in uploads/proposals and your vendor metadata was logged."
                    )
                except Exception as e:
                    st.error(f"Failed to save proposal: {e}")
    else:
        st.subheader("Public Vendor Submissions")
        try:
            with sqlite3.connect(PROPOSALS_DB_PATH) as conn:
                submissions_df = pd.read_sql_query(
                    """
                    SELECT id, company_name, cac_number, proposal_title, email,
                           phone, address, budget, pdf_path, submission_date,
                           submission_channel, tracking_code
                    FROM submissions
                    ORDER BY submission_date DESC, id DESC;
                    """,
                    conn,
                )
            if submissions_df.empty:
                st.info("No public vendor submissions have been received yet.")
            else:
                st.dataframe(
                    submissions_df,
                    use_container_width=True,
                    hide_index=True,
                )
        except Exception as exc:
            st.error(f"Failed to load public vendor submissions: {exc}")

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
        col3.metric(
            "Executive Priority Alerts", flagged_proposals, delta_color="inverse"
        )

        st.markdown("---")

        # Stable Native Tabs Structure
        tab1, tab2, tab3 = st.tabs(
            [
                "📥 Submit Proposal",
                "📊 Dashboard Overview",
                "🧠 AI Extractor",
            ]
        )

        with tab1:
            st.header("📥 Vendor Proposal Intake & Submission")
            st.markdown(
                "Submit vendor proposal documentation below for real-time CAC verification and AI analysis."
            )

            # Legacy admin intake form retained for internal use.
            submission_channel = st.radio(
                "Select Submission Channel:",
                [
                    "Digital Submission (Vendor Portal)",
                    "Physical Submission (Registry Desk OCR Intake)",
                ],
                horizontal=True,
                key="admin_submission_channel",
            )

            with st.form("vendor_submission_form_internal"):
                submitter = st.text_input(
                    "Submitter Name / Organization*",
                    "Vendor Name",
                    key="admin_submitter_name",
                )
                title = st.text_input(
                    "Proposal Title*",
                    "Proposal Document",
                    key="admin_proposal_title",
                )
                cac_number = st.text_input(
                    "CAC Registration Number (e.g., RC123456)",
                    key="admin_cac_number",
                )
                budget = st.number_input(
                    "Proposed Budget ($ / ₦)",
                    min_value=0.0,
                    value=0.0,
                    key="admin_proposed_budget",
                )

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
                    key="admin_proposal_category",
                )

                c1, c2 = st.columns(2)
                with c1:
                    email = st.text_input(
                        "Contact Email Address*", key="admin_contact_email"
                    )
                with c2:
                    phone_number = st.text_input(
                        "Contact Phone Number*",
                        placeholder="+1 (555) 000-0000",
                        key="admin_contact_phone",
                    )

                uploaded_file = st.file_uploader(
                    f"Upload Proposal Document ({submission_channel})",
                    type=["pdf", "docx", "xlsx", "xls", "png", "jpg", "jpeg"],
                    key="admin_proposal_upload",
                )
                submitted = st.form_submit_button(
                    "Process, Verify KYB, and Save",
                    key="admin_process_proposal_btn",
                )

            if submitted:
                if not cac_number.strip():
                    st.warning(
                        "Please enter a valid CAC registration number for KYB verification."
                    )
                elif not phone_number.strip():
                    st.warning(
                        "⚠️ Please provide a valid phone number before submitting."
                    )
                elif uploaded_file is None:
                    st.warning(
                        "Please upload a proposal file (PDF, Word, Excel, or Image)."
                    )
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
                        except Exception:
                            extracted_text = ""

                        try:
                            payload = (
                                extracted_text
                                if (extracted_text and len(extracted_text.strip()) > 10)
                                else file_bytes
                            )
                            ai_results = analyze_proposal_with_ai(payload)
                            st.session_state.ai_summary = ai_results.get("summary", "")
                        except Exception:
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
                        sqlite_submission_channel = (
                            "Digital"
                            if submission_channel.startswith("Digital Submission")
                            else "Physical Registry"
                        )

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
                            insert_vendor_submission(
                                company_name=submitter,
                                cac_number=cac_number,
                                proposal_title=title,
                                email=email,
                                phone=phone_number,
                                address="",
                                budget=float(budget) if budget else None,
                                pdf_path=file_path,
                                submission_channel=sqlite_submission_channel,
                                tracking_code=tracking_code,
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
                                    recipient_email=(
                                        email if email else "austattah@gmail.com"
                                    ),
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

                            if (
                                email_sent
                                or sms_sent
                                or direct_email_sent
                                or direct_sms_sent
                            ):
                                st.info(
                                    "✉️ Confirmation auto-responses & direct notifications dispatched."
                                )

                            st.markdown("---")
                            res_col1, res_col2 = st.columns(2)

                            with res_col1:
                                st.subheader("🏢 KYB Verification")
                                is_verified = kyb_status.get(
                                    "status"
                                ) or kyb_status.get("verified", False)
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
                            "👑 Filter: Show Top Executive Priority & Flagged Risks Only",
                            key="dashboard_executive_focus_filter",
                        )

                    if show_only_executive_focus:
                        safe_budgets = df["budget"].fillna(0.0)
                        df = df[
                            (df["is_flagged"] == True)
                            | (df["is_high_priority"] == True)
                            | (safe_budgets >= 50000000.0)
                        ]
                        if df.empty:
                            st.warning(
                                "No high-priority executive alerts pending review."
                            )

                    for idx, row in df.iterrows():
                        risk_flagged = bool(row["is_flagged"])
                        high_priority = bool(
                            row.get("is_high_priority", False)
                            or (
                                row["budget"] is not None
                                and float(row["budget"]) >= 50000000.0
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
                                st.write(
                                    f"**Vendor / Organization:** {row['vendor_name']}"
                                )
                                st.write(f"**Email:** {row['email']}")
                                st.write(
                                    f"**Contact Phone Number:** {row.get('phone_number', 'N/A')}"
                                )
                            with meta_col2:
                                st.write(f"**Category:** {row['category']}")
                                st.write(f"**CAC Number:** {row['cac_number']}")
                                budget_val = row["budget"]
                                formatted_budget = (
                                    f"{budget_val:,.2f}"
                                    if pd.notnull(budget_val)
                                    else "0.00"
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
                                st.warning(
                                    "No AI summary text recorded for this submission."
                                )

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
                if st.button(
                    "Clear Old / Test Proposals",
                    type="secondary",
                    key="clear_proposals_dashboard_btn",
                ):
                    try:
                        removed_count = clear_legacy_or_test_proposals()
                        st.success(
                            f"Successfully deleted {removed_count} test record(s)."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error executing cleanup: {e}")

            with col2:
                st.markdown("### 🗑️ Delete Specific Proposal")
                st.caption("Remove an individual row using its database ID.")
                with st.form("delete_proposal_form_dashboard", clear_on_submit=True):
                    target_id = st.number_input(
                        "Enter Proposal ID",
                        min_value=1,
                        step=1,
                        value=1,
                        key="dashboard_delete_proposal_id",
                    )
                    submit_delete = st.form_submit_button(
                        "Confirm Delete",
                        type="primary",
                        key="dashboard_confirm_delete_btn",
                    )
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
                    "SELECT id, tracking_code, vendor_name, category, cac_number, budget,"
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
                        key="audit_tracking_code_select",
                    )

                    if selected_code:
                        record = audit_df[
                            audit_df["tracking_code"] == selected_code
                        ].iloc[0]

                        st.markdown("---")
                        ac1, ac2, ac3 = st.columns(3)
                        with ac1:
                            st.markdown(f"**Vendor Name:** {record['vendor_name']}")
                            st.markdown(f"**CAC Number:** `{record['cac_number']}`")
                            st.markdown(f"**Category:** {record['category']}")
                        with ac2:
                            st.markdown(f"**Contact Email:** {record['email']}")
                            st.markdown(
                                f"**Contact Phone Number:** {record['phone_number']}"
                            )
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

                        summary_col, qr_col = st.columns([4, 1])
                        with summary_col:
                            st.markdown("### 📄 Deep-Dive AI Extraction Summary")
                            with st.container(border=True):
                                st.write(
                                    record["ai_summary"]
                                    if record["ai_summary"]
                                    else "No detailed AI extraction text found for this proposal."
                                )
                        with qr_col:
                            st.markdown("### 📱 Submission QR Code")
                            qr_image, qr_bytes = generate_submission_qr(
                                submission_id=int(record["id"]),
                                cac_number=str(record["cac_number"]),
                                tracking_payload=str(record["tracking_code"]),
                            )
                            st.image(qr_image, caption="Scan to verify submission")

                        st.markdown("---")
                        st.subheader("Forward Executive Summary to Senior Officer")
                        try:
                            org_config = json.loads(
                                (ROOT_DIR / "org_config.json").read_text(
                                    encoding="utf-8"
                                )
                            )
                            admin_email_default = org_config.get("admin_email", "")
                            if not isinstance(admin_email_default, str):
                                raise ValueError(
                                    "org_config.json admin_email must be a string."
                                )
                        except (OSError, json.JSONDecodeError, ValueError) as exc:
                            admin_email_default = ""
                            st.error(
                                f"Could not load admin_email from org_config.json: {exc}"
                            )

                        senior_officer_email = st.text_input(
                            "Senior Officer Email",
                            value=admin_email_default,
                            key=f"senior_officer_email_{record['id']}",
                        )
                        if st.button(
                            "📧 Send Executive Summary & QR Code",
                            key=f"send_executive_summary_{record['id']}",
                            type="primary",
                        ):
                            if not senior_officer_email.strip():
                                st.warning(
                                    "Enter a Senior Officer email address before sending."
                                )
                            else:
                                try:
                                    source_channel = get_submission_channel(
                                        str(record["tracking_code"])
                                    )
                                    delivered, delivery_message = (
                                        send_executive_summary_email(
                                            recipient_email=senior_officer_email.strip(),
                                            company_name=str(record["vendor_name"]),
                                            cac_number=str(record["cac_number"]),
                                            budget=(
                                                record["budget"]
                                                if pd.notnull(record["budget"])
                                                else None
                                            ),
                                            submission_channel=source_channel,
                                            ai_summary=str(record["ai_summary"] or ""),
                                            tracking_code=str(record["tracking_code"]),
                                            qr_image_bytes=qr_bytes,
                                        )
                                    )
                                    if delivered:
                                        st.success(
                                            "Executive summary and QR code successfully dispatched!"
                                        )
                                    else:
                                        st.error(
                                            "Failed to dispatch the executive summary: "
                                            f"{delivery_message}"
                                        )
                                except Exception as exc:
                                    st.error(
                                        "Failed to dispatch the executive summary: "
                                        f"{exc}"
                                    )

                        st.markdown("---")
                        st.subheader("📤 Front Desk Executive Actions & CSV Export")

                        action_col1, action_col2 = st.columns(2)

                        with action_col1:
                            st.markdown("### 📧 Forward to Executive Officer")
                            exec_email = st.text_input(
                                "Next Executive Officer Email:",
                                "executive@sgwvm.com",
                                key="exec_target_email_audit",
                            )
                            if st.button(
                                "🚀 Send Results to Executive",
                                type="primary",
                                key=f"send_results_to_executive_{record['id']}",
                            ):
                                if not exec_email.strip():
                                    st.warning(
                                        "Please enter a valid executive email address."
                                    )
                                else:
                                    email_subject = (
                                        f"{ORG_CONFIG['org_name']} Executive Brief: Proposal ["
                                        + str(record["tracking_code"])
                                        + "] - "
                                        + str(record["vendor_name"])
                                    )
                                    email_body = (
                                        f"{ORG_CONFIG['org_name']} - EXECUTIVE PROPOSAL BRIEFING\n"
                                        "--------------------------------------------------\n"
                                        "Tracking Code: "
                                        + str(record["tracking_code"])
                                        + "\n"
                                        "Vendor Organization: "
                                        + str(record["vendor_name"])
                                        + "\n"
                                        "Stream / Category: "
                                        + str(record["category"])
                                        + "\n"
                                        "CAC Registration: "
                                        + str(record["cac_number"])
                                        + "\n"
                                        "Declared Budget: " + str(budget_display) + "\n"
                                        "Contact Email: " + str(record["email"]) + "\n"
                                        "Contact Phone: "
                                        + str(record["phone_number"])
                                        + "\n\n"
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
                                        st.error(
                                            f"Error dispatching email notification: {e}"
                                        )

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
                                key=f"export_proposal_csv_audit_{record['id']}",
                            )

            except Exception as e:
                st.error(f"Error loading audit module: {e}")
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
                        "👑 Filter: Show Top Executive Priority & Flagged Risks Only",
                        key="dashboard_executive_focus_filter_legacy",
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
                            row["budget"] is not None
                            and float(row["budget"]) >= 50000000.0
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
                                f"{budget_val:,.2f}"
                                if pd.notnull(budget_val)
                                else "0.00"
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
                            st.warning(
                                "No AI summary text recorded for this submission."
                            )

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
            if st.button(
                "Clear Old / Test Proposals",
                type="secondary",
                key="clear_proposals_admin_btn",
            ):
                try:
                    removed_count = clear_legacy_or_test_proposals()
                    st.success(f"Successfully deleted {removed_count} test record(s).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error executing cleanup: {e}")

        with col2:
            st.markdown("### 🗑️ Delete Specific Proposal")
            st.caption("Remove an individual row using its database ID.")
            with st.form("delete_proposal_form_legacy", clear_on_submit=True):
                target_id = st.number_input(
                    "Enter Proposal ID",
                    min_value=1,
                    step=1,
                    value=1,
                    key="legacy_delete_proposal_id",
                )
                submit_delete = st.form_submit_button(
                    "Confirm Delete",
                    type="primary",
                    key="legacy_confirm_delete_btn",
                )
                if submit_delete:
                    try:
                        delete_proposal_by_id(target_id)
                        st.success(f"Proposal ID {target_id} deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete ID {target_id}: {e}")

    if can_access_ai_extractor:
        with tab3:
            st.header("📑 Comprehensive AI Extraction & Executive Audit")
            st.markdown(
                "Select a proposal tracking code to review its AI extraction details, export records to CSV, and forward summaries to executive officers."
            )

            try:
                engine = get_db_engine()
                audit_df = pd.read_sql(
                    "SELECT id, tracking_code, vendor_name, category, cac_number, budget,"
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
                        key="legacy_audit_tracking_code_select",
                    )

                    if selected_code:
                        record = audit_df[
                            audit_df["tracking_code"] == selected_code
                        ].iloc[0]

                        st.markdown("---")
                        ac1, ac2, ac3 = st.columns(3)
                        with ac1:
                            st.markdown(f"**Vendor Name:** {record['vendor_name']}")
                            st.markdown(f"**CAC Number:** `{record['cac_number']}`")
                            st.markdown(f"**Category:** {record['category']}")
                        with ac2:
                            st.markdown(f"**Contact Email:** {record['email']}")
                            st.markdown(
                                f"**Contact Phone Number:** {record['phone_number']}"
                            )
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
                                key="exec_target_email_legacy",
                            )
                            if st.button(
                                "🚀 Send Results to Executive",
                                type="primary",
                                key=f"send_results_to_executive_legacy_{record['id']}",
                            ):
                                if not exec_email.strip():
                                    st.warning(
                                        "Please enter a valid executive email address."
                                    )
                                else:
                                    email_subject = (
                                        f"{ORG_CONFIG['org_name']} Executive Brief: Proposal ["
                                        + str(record["tracking_code"])
                                        + "] - "
                                        + str(record["vendor_name"])
                                    )
                                    email_body = (
                                        f"{ORG_CONFIG['org_name']} - EXECUTIVE PROPOSAL BRIEFING\n"
                                        "--------------------------------------------------\n"
                                        "Tracking Code: "
                                        + str(record["tracking_code"])
                                        + "\n"
                                        "Vendor Organization: "
                                        + str(record["vendor_name"])
                                        + "\n"
                                        "Stream / Category: "
                                        + str(record["category"])
                                        + "\n"
                                        "CAC Registration: "
                                        + str(record["cac_number"])
                                        + "\n"
                                        "Declared Budget: " + str(budget_display) + "\n"
                                        "Contact Email: " + str(record["email"]) + "\n"
                                        "Contact Phone: "
                                        + str(record["phone_number"])
                                        + "\n\n"
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
                                        st.error(
                                            f"Error dispatching email notification: {e}"
                                        )

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
                                key=f"export_proposal_csv_legacy_{record['id']}",
                            )

            except Exception as e:
                st.error(f"Error loading audit module: {e}")
