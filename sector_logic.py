import hashlib
import io
import logging
import os
import re
import secrets
import sqlite3
import tempfile
import zipfile
from collections.abc import Mapping
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import quote

import requests
import qrcode
import streamlit as st
from cryptography.fernet import Fernet
from streamlit.errors import StreamlitSecretNotFoundError

import database as db


MAX_DOSSIER_SIZE_BYTES = 25 * 1024 * 1024
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify"
_TENANT_SLUG_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}\Z")
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CLEARANCE_ACTIVE_STATUS = "PAYMENT_VERIFIED"
_CLEARANCE_SUBMITTED_STATUS = "DOSSIER_SUBMITTED"


def _widget_key(key_prefix: str | None, name: str) -> str:
    return f"{key_prefix}:{name}" if key_prefix else name


def _tenant_is_active(tenant_slug: str) -> bool:
    if not isinstance(tenant_slug, str) or not _TENANT_SLUG_PATTERN.fullmatch(
        tenant_slug
    ):
        return False
    tenant = db.get_tenant_by_slug(tenant_slug)
    return bool(
        tenant
        and str(tenant.get("status", "")).strip().upper() == "ACTIVE"
    )


def _get_paystack_secret_key() -> str | None:
    value = os.environ.get("PAYSTACK_SECRET_KEY", "").strip()
    if value:
        return value
    try:
        value = st.secrets.get("PAYSTACK_SECRET_KEY", "")
    except (KeyError, StreamlitSecretNotFoundError):
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


def _verify_paystack_payment(payment_reference: str, vendor_email: str) -> bool:
    secret_key = _get_paystack_secret_key()
    if not secret_key:
        st.error(
            "Payment verification is unavailable because the Paystack secret "
            "is not configured."
        )
        return False

    try:
        response = requests.get(
            f"{PAYSTACK_VERIFY_URL}/{quote(payment_reference, safe='')}",
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        logging.exception("Paystack payment verification request failed.")
        st.error("Payment could not be verified. Please retry or contact support.")
        return False

    if not isinstance(payload, Mapping) or payload.get("status") is not True:
        st.error("The payment provider did not confirm this payment.")
        return False

    transaction = payload.get("data")
    if not isinstance(transaction, Mapping):
        st.error("The payment provider returned an invalid verification response.")
        return False

    confirmed_reference = transaction.get("reference")
    transaction_status = transaction.get("status")
    amount = transaction.get("amount")
    customer = transaction.get("customer")
    if (
        transaction_status != "success"
        or not isinstance(confirmed_reference, str)
        or not secrets.compare_digest(confirmed_reference, payment_reference)
        or isinstance(amount, bool)
        or not isinstance(amount, int)
        or amount <= 0
    ):
        st.error("Payment is pending, invalid, or does not match the submitted reference.")
        return False

    if isinstance(customer, Mapping):
        paid_email = customer.get("email")
        if (
            isinstance(paid_email, str)
            and paid_email.strip()
            and paid_email.strip().casefold() != vendor_email.casefold()
        ):
            st.error("The confirmed payment email does not match the vendor email.")
            return False

    return True


def _create_payment_verified_pass(
    tenant_slug: str,
    rfq_code: str,
    vendor_name: str,
    vendor_email: str,
    payment_reference: str,
    proposal_title: str,
) -> str:
    pass_id = f"NV-QRPASS-{secrets.token_urlsafe(32)}"
    db.init_db()

    with db.get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        tenant = connection.execute(
            "SELECT status FROM tenants WHERE tenant_slug = ?",
            (tenant_slug,),
        ).fetchone()
        if tenant is None or str(tenant["status"] or "").strip().upper() != "ACTIVE":
            raise ValueError("This tenant is not active. No pass was issued.")

        existing_payment = connection.execute(
            "SELECT 1 FROM clearance_passes WHERE payment_reference = ? LIMIT 1",
            (payment_reference,),
        ).fetchone()
        if existing_payment is not None:
            raise ValueError("This payment reference has already been used.")

        connection.execute(
            """
            INSERT INTO clearance_passes (
                qr_pass_id, tenant_slug, rfq_code, vendor_name, email,
                payment_reference, proposal_title, clearance_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pass_id,
                tenant_slug,
                rfq_code,
                vendor_name,
                vendor_email,
                payment_reference,
                proposal_title,
                _CLEARANCE_ACTIVE_STATUS,
            ),
        )
    return pass_id


def _render_clearance_qr(tenant_slug: str, pass_id: str) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=4,
    )
    qr.add_data(f"nexusvault://clearance/{tenant_slug}/{pass_id}")
    qr.make(fit=True)
    st.image(
        qr.make_image(fill_color="#064e3b", back_color="white"),
        caption="Tenant-scoped QR clearance pass",
    )


def _get_encryption_key() -> bytes | None:
    value = os.environ.get("NEXUSVAULT_DOSSIER_ENCRYPTION_KEY", "").strip()
    if not value:
        try:
            value = st.secrets.get("NEXUSVAULT_DOSSIER_ENCRYPTION_KEY", "")
        except (KeyError, StreamlitSecretNotFoundError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        key = value.strip().encode("ascii")
        Fernet(key)
    except (UnicodeEncodeError, ValueError, TypeError):
        return None
    return key


def _validate_dossier(filename: str, file_bytes: bytes) -> None:
    if not file_bytes:
        raise ValueError("The dossier file is empty.")
    if len(file_bytes) > MAX_DOSSIER_SIZE_BYTES:
        raise ValueError("Dossiers must be 25 MB or smaller.")

    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("The uploaded file does not have a valid PDF signature.")
        return

    if extension != ".docx":
        raise ValueError("Upload a PDF or DOCX dossier.")

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as document:
            names = set(document.namelist())
            if (
                document.testzip() is not None
                or "[Content_Types].xml" not in names
                or "word/document.xml" not in names
            ):
                raise ValueError("The uploaded DOCX document is malformed.")
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded file is not a valid DOCX document.") from exc


def _dossier_path(tenant_slug: str, pass_id: str) -> Path:
    storage_root = Path(
        os.environ.get(
            "NEXUSVAULT_DOSSIER_DIR",
            Path(__file__).resolve().parent / "uploads" / "sealed_dossiers",
        )
    ).expanduser()
    pass_digest = hashlib.sha256(pass_id.encode("utf-8")).hexdigest()
    return storage_root / tenant_slug / f"{pass_digest}.fernet"


def _write_encrypted_dossier(
    tenant_slug: str,
    pass_id: str,
    file_bytes: bytes,
    key: bytes,
) -> Path:
    destination = _dossier_path(tenant_slug, pass_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("A dossier is already stored for this clearance pass.")

    encrypted_bytes = Fernet(key).encrypt(file_bytes)
    temporary_path: Path | None = None
    destination_created = False
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=".dossier-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            if os.name != "nt":
                os.chmod(temporary_path, 0o600)
            temporary_file.write(encrypted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.link(temporary_path, destination)
        destination_created = True
        temporary_path.unlink()
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if destination_created:
            destination.unlink(missing_ok=True)
        raise

    return destination


def _mark_dossier_submitted(
    tenant_slug: str,
    pass_id: str,
) -> bool:
    db.init_db()
    with db.get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE clearance_passes
            SET clearance_status = ?
            WHERE qr_pass_id = ?
              AND tenant_slug = ?
              AND clearance_status = ?
            """,
            (
                _CLEARANCE_SUBMITTED_STATUS,
                pass_id,
                tenant_slug,
                _CLEARANCE_ACTIVE_STATUS,
            ),
        )
    return cursor.rowcount == 1


def _render_solicited_vendor_portal(
    tenant_slug: str,
    key_prefix: str | None,
) -> None:
    st.markdown("### Solicited Vendor Submission")
    st.caption(
        "Complete payment verification, confirm clearance, then submit your "
        "sealed dossier. Dossiers are encrypted at rest."
    )

    pass_key = _widget_key(key_prefix, "clearance_pass_id")
    verification_key = _widget_key(key_prefix, "pass_verification_input")
    candidate_pass_id = st.session_state.get(pass_key, "")
    clearance_record = None

    step1_tab, step2_tab, step3_tab = st.tabs(
        [
            "Step 1: RFP, Vendor & Payment",
            "Step 2: Clearance Verification",
            "Step 3: Sealed Dossier",
        ]
    )

    with step1_tab:
        st.markdown("#### Verify payment and issue a clearance pass")
        with st.form(key=_widget_key(key_prefix, "solicited_step1_form")):
            rfq_code = st.text_input(
                "Official RFP / RFQ reference*",
                max_chars=100,
                key=_widget_key(key_prefix, "rfq_code"),
            )
            vendor_name = st.text_input(
                "Corporate vendor name*",
                max_chars=200,
                key=_widget_key(key_prefix, "vendor_name"),
            )
            vendor_email = st.text_input(
                "Official corporate email*",
                max_chars=254,
                key=_widget_key(key_prefix, "vendor_email"),
            )
            payment_reference = st.text_input(
                "Paystack transaction reference*",
                max_chars=150,
                key=_widget_key(key_prefix, "payment_reference"),
            )
            proposal_title = st.text_input(
                "Project / bid title*",
                max_chars=250,
                key=_widget_key(key_prefix, "proposal_title"),
            )
            submitted = st.form_submit_button(
                "Verify payment and generate QR clearance pass",
                key=_widget_key(key_prefix, "step1_submit"),
                type="primary",
            )

        if submitted:
            normalized_values = (
                rfq_code.strip(),
                vendor_name.strip(),
                vendor_email.strip(),
                payment_reference.strip(),
                proposal_title.strip(),
            )
            normalized_rfq, normalized_name, normalized_email, normalized_ref, normalized_title = (
                normalized_values
            )
            _, parsed_email = parseaddr(normalized_email)
            if (
                not all(normalized_values)
                or not _EMAIL_PATTERN.fullmatch(parsed_email)
            ):
                st.error("Complete all required fields with a valid corporate email.")
            elif not _tenant_is_active(tenant_slug):
                st.error("This tenant is no longer active. No pass was issued.")
            elif not _verify_paystack_payment(normalized_ref, parsed_email):
                pass
            else:
                try:
                    created_pass_id = _create_payment_verified_pass(
                        tenant_slug=tenant_slug,
                        rfq_code=normalized_rfq,
                        vendor_name=normalized_name,
                        vendor_email=parsed_email,
                        payment_reference=normalized_ref,
                        proposal_title=normalized_title,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                except sqlite3.Error:
                    logging.exception("Could not save verified clearance pass.")
                    st.error("The verified payment could not be recorded. Please contact support.")
                else:
                    st.session_state[pass_key] = created_pass_id
                    st.success("Payment verified and clearance pass recorded.")
                    st.code(created_pass_id, language="text")
                    st.info("Keep this pass ID. It is required for subsequent verification.")
                    st.rerun()

    with step2_tab:
        st.markdown("#### Verify clearance against the tenant database")
        pass_id_input = st.text_input(
            "QR clearance pass ID",
            value=str(candidate_pass_id),
            key=verification_key,
            max_chars=100,
        ).strip()
        if st.button(
            "Check clearance status",
            key=_widget_key(key_prefix, "verify_clearance"),
        ):
            st.session_state[pass_key] = pass_id_input
            candidate_pass_id = pass_id_input
        elif pass_id_input:
            candidate_pass_id = pass_id_input

        if candidate_pass_id:
            try:
                if _tenant_is_active(tenant_slug):
                    clearance_record = db.get_clearance_pass(
                        candidate_pass_id,
                        tenant_slug,
                    )
            except (sqlite3.Error, RuntimeError):
                logging.exception("Clearance pass lookup failed.")
                st.error("Clearance status could not be verified. Please retry.")
            else:
                if clearance_record is None:
                    st.error("No clearance pass was found for this tenant.")
                elif clearance_record["clearance_status"] == _CLEARANCE_ACTIVE_STATUS:
                    st.success("Clearance is active. The sealed dossier step is unlocked.")
                    _render_clearance_qr(tenant_slug, candidate_pass_id)
                    st.code(candidate_pass_id, language="text")
                    st.write("RFP reference:", clearance_record["rfq_code"])
                    st.write("Proposal:", clearance_record["proposal_title"])
                elif clearance_record["clearance_status"] == _CLEARANCE_SUBMITTED_STATUS:
                    st.info("A dossier has already been submitted for this pass.")
                else:
                    st.warning(
                        "This pass is not active for dossier submission. "
                        f"Current status: {clearance_record['clearance_status']}."
                    )
        else:
            st.info("Enter the pass ID from Step 1 to verify its current status.")

    with step3_tab:
        st.markdown("#### Submit the sealed bid dossier")
        if not candidate_pass_id:
            st.error("Locked: verify an active clearance pass in Step 2 first.")
        else:
            try:
                if _tenant_is_active(tenant_slug):
                    clearance_record = db.get_clearance_pass(
                        candidate_pass_id,
                        tenant_slug,
                    )
                else:
                    clearance_record = None
            except (sqlite3.Error, RuntimeError):
                logging.exception("Could not re-verify clearance before dossier upload.")
                clearance_record = None
                st.error("Clearance could not be re-verified. Dossier upload is locked.")

            if clearance_record is None:
                st.error("Locked: no valid pass exists for this tenant.")
            elif clearance_record["clearance_status"] == _CLEARANCE_SUBMITTED_STATUS:
                st.info("A dossier has already been submitted for this pass.")
            elif clearance_record["clearance_status"] != _CLEARANCE_ACTIVE_STATUS:
                st.error("Locked: the server-side clearance pass is not active.")
            else:
                encryption_key = _get_encryption_key()
                if encryption_key is None:
                    st.error(
                        "Dossier storage is unavailable. Configure a valid Fernet "
                        "NEXUSVAULT_DOSSIER_ENCRYPTION_KEY before accepting uploads."
                    )
                with st.form(key=_widget_key(key_prefix, "solicited_step3_form")):
                    st.caption(
                        "Files are encrypted at rest with the configured Fernet key. "
                        "Maximum size: 25 MB."
                    )
                    dossier = st.file_uploader(
                        "Sealed bid dossier (PDF or DOCX)*",
                        type=["pdf", "docx"],
                        key=_widget_key(key_prefix, "sealed_dossier"),
                        disabled=encryption_key is None,
                    )
                    submitted_dossier = st.form_submit_button(
                        "Encrypt and submit dossier",
                        key=_widget_key(key_prefix, "step3_submit"),
                        type="primary",
                        disabled=encryption_key is None,
                    )

                if submitted_dossier:
                    if dossier is None:
                        st.error("Select a dossier file before submitting.")
                    elif encryption_key is None:
                        st.error("Encrypted dossier storage is not configured.")
                    elif not _tenant_is_active(tenant_slug):
                        st.error("This tenant is no longer active. The dossier was not accepted.")
                    else:
                        encrypted_path: Path | None = None
                        try:
                            file_bytes = dossier.getvalue()
                            _validate_dossier(dossier.name, file_bytes)
                            latest_pass = db.get_clearance_pass(
                                candidate_pass_id,
                                tenant_slug,
                            )
                            if (
                                latest_pass is None
                                or latest_pass["clearance_status"]
                                != _CLEARANCE_ACTIVE_STATUS
                            ):
                                raise ValueError(
                                    "Clearance expired or was already consumed. "
                                    "The dossier was not accepted."
                                )
                            encrypted_path = _write_encrypted_dossier(
                                tenant_slug,
                                candidate_pass_id,
                                file_bytes,
                                encryption_key,
                            )
                            if not _mark_dossier_submitted(
                                tenant_slug,
                                candidate_pass_id,
                            ):
                                encrypted_path.unlink(missing_ok=True)
                                raise ValueError(
                                    "Clearance status changed during submission. "
                                    "The dossier was not accepted."
                                )
                        except ValueError as exc:
                            if encrypted_path is not None:
                                encrypted_path.unlink(missing_ok=True)
                            st.error(str(exc))
                        except (OSError, sqlite3.Error):
                            if encrypted_path is not None:
                                encrypted_path.unlink(missing_ok=True)
                            logging.exception("Sealed dossier submission failed.")
                            st.error(
                                "The dossier could not be stored securely. "
                                "Please retry or contact support."
                            )
                        else:
                            st.success(
                                "Dossier encrypted and recorded successfully. "
                                "Your clearance pass is now marked as submitted."
                            )


def render_solicited_vendor_qr_clearance_gate(
    tenant_slug: str | None = None,
    key_prefix: str | None = None,
) -> None:
    try:
        tenant_is_active = bool(tenant_slug and _tenant_is_active(tenant_slug))
    except (sqlite3.Error, RuntimeError):
        logging.exception("Could not verify tenant before rendering solicited portal.")
        st.error("Solicited submissions are temporarily unavailable.")
        return
    if not tenant_is_active:
        st.error("Solicited submissions are unavailable for this tenant.")
        return
    _render_solicited_vendor_portal(tenant_slug, key_prefix)


def render_unsolicited_vendor_portal(
    tenant_slug: str | None = None,
    key_prefix: str | None = None,
) -> None:
    st.markdown("### Unsolicited Proposal Submission")
    st.caption("Submit an independent proposal for preliminary review.")

    try:
        tenant_is_active = bool(tenant_slug and _tenant_is_active(tenant_slug))
    except (sqlite3.Error, RuntimeError):
        logging.exception("Could not verify tenant before rendering unsolicited portal.")
        st.error("Unsolicited submissions are temporarily unavailable.")
        return
    if not tenant_is_active:
        st.error("Unsolicited submissions are unavailable for this tenant.")
        return

    with st.form(
        key=_widget_key(
            key_prefix,
            f"unsolicited_form_{tenant_slug}",
        )
    ):
        st.text_input(
            "Organization / enterprise name*",
            max_chars=200,
            key=_widget_key(key_prefix, "unsolicited_organization"),
        )
        st.text_input(
            "CAC registration number*",
            max_chars=100,
            key=_widget_key(key_prefix, "unsolicited_cac"),
        )
        st.text_input(
            "Tax identification number",
            max_chars=100,
            key=_widget_key(key_prefix, "unsolicited_tin"),
        )
        st.text_input(
            "Proposal title*",
            max_chars=250,
            key=_widget_key(key_prefix, "unsolicited_title"),
        )
        st.text_area(
            "Executive summary / strategic objectives*",
            max_chars=10_000,
            key=_widget_key(key_prefix, "unsolicited_abstract"),
        )
        submitted = st.form_submit_button(
            "Submit proposal",
            key=_widget_key(key_prefix, "unsolicited_submit"),
        )

    if submitted:
        st.error(
            "Unsolicited submission storage is not configured. No proposal was recorded."
        )


def render_unified_vendor_portal(
    tenant_slug: str | None = None,
    default_tab: str = "solicited",
) -> None:
    st.markdown("## NEXUSVAULT Vendor Portal")
    if not tenant_slug or not _tenant_is_active(tenant_slug):
        st.error("Vendor access is unavailable for this tenant.")
        return

    st.caption(f"Tenant: {tenant_slug}")
    if default_tab == "unsolicited":
        render_unsolicited_vendor_portal(
            tenant_slug=tenant_slug,
            key_prefix=f"tenant:{tenant_slug}:vendor:unsolicited",
        )
    else:
        render_solicited_vendor_qr_clearance_gate(
            tenant_slug=tenant_slug,
            key_prefix=f"tenant:{tenant_slug}:vendor:solicited",
        )
