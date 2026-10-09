import logging
import os
import uuid
from collections.abc import Callable

import streamlit as st
from streamlit.errors import StreamlitAPIException, StreamlitSecretNotFoundError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from database import get_db_engine

ORGANIZATION_COLUMNS = {
    "org_id",
    "subscription_status",
    "onboarding_completed",
    "subscription_plan",
    "updated_at",
}
AVAILABLE_SUBSCRIPTION_PLANS = ("Starter", "Professional", "Enterprise")
DEVELOPER_ACTIVATION_STATUSES = ("PENDING", "ACTIVE")


def is_paystack_configured() -> bool:
    """Check required Paystack credentials without exposing or persisting them."""
    return _are_gateway_credentials_configured(
        ("PAYSTACK_PUBLIC_KEY", "PAYSTACK_SECRET_KEY")
    )


def is_flutterwave_configured() -> bool:
    """Check Flutterwave credentials without exposing or persisting them."""
    return _are_gateway_credentials_configured(("FLW_PUBLIC_KEY", "FLW_SECRET_KEY"))


def _are_gateway_credentials_configured(setting_names: tuple[str, str]) -> bool:
    for setting_name in setting_names:
        value = os.getenv(setting_name, "").strip()
        if not value:
            try:
                secret_value = st.secrets.get(setting_name, "")
            except (AttributeError, KeyError, StreamlitSecretNotFoundError):
                secret_value = ""
            value = secret_value.strip() if isinstance(secret_value, str) else ""
        if not value:
            return False
    return True


def _organization_id_value(org_id: str, org_id_type: object) -> str | int:
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    if "integer" in str(org_id_type).lower():
        try:
            return int(normalized_org_id)
        except ValueError as exc:
            raise ValueError("Organization ID must be a valid integer.") from exc
    return normalized_org_id


def get_organization_status(org_id: str) -> tuple[str | None, str]:
    """Read an organization's activation status from the shared database."""
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    if not normalized_org_id:
        return None, "Organization ID is required."

    engine = get_db_engine()
    try:
        inspector = inspect(engine)
        if "organizations" not in inspector.get_table_names():
            return None, "The organizations table does not exist."
        columns = {
            column["name"]: column["type"]
            for column in inspector.get_columns("organizations")
        }
        if "org_id" not in columns or "subscription_status" not in columns:
            return None, "The organizations table is missing activation fields."
        org_id_value = _organization_id_value(
            normalized_org_id,
            columns["org_id"],
        )
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT subscription_status
                    FROM organizations
                    WHERE org_id = :org_id
                    """
                ),
                {"org_id": org_id_value},
            ).first()
        if result is None:
            return None, "Organization was not found."
        return str(result[0]).strip().upper(), ""
    except ValueError as exc:
        return None, str(exc)
    except SQLAlchemyError:
        logging.exception("Could not read organization activation status.")
        return None, "The database could not verify organization activation."


def complete_organization_onboarding(
    org_id: str | None,
    plan_name: str,
) -> tuple[bool, str, str | None]:
    """Create or reset an organization record pending developer activation."""
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    normalized_plan = str(plan_name).strip() if plan_name is not None else ""
    if normalized_plan not in AVAILABLE_SUBSCRIPTION_PLANS:
        return False, "Select Starter, Professional, or Enterprise.", None

    engine = get_db_engine()
    try:
        inspector = inspect(engine)
        if "organizations" not in inspector.get_table_names():
            return False, "The organizations table does not exist.", None
        columns = {
            column["name"]: column["type"]
            for column in inspector.get_columns("organizations")
        }
        missing_columns = ORGANIZATION_COLUMNS - columns.keys()
        if missing_columns:
            logging.error(
                "Cannot complete organization onboarding: organizations table lacks columns %s",
                ", ".join(sorted(missing_columns)),
            )
            return (
                False,
                "The organizations table is missing required subscription fields.",
                None,
            )

        with engine.begin() as connection:
            if "integer" in str(columns["org_id"]).lower() and not normalized_org_id:
                result = connection.execute(
                    text(
                        """
                        INSERT INTO organizations (
                            subscription_status, onboarding_completed,
                            subscription_plan, updated_at
                        ) VALUES (
                            'PENDING_DEVELOPER_ACTIVATION', TRUE,
                            :plan_name, CURRENT_TIMESTAMP
                        )
                        RETURNING org_id
                        """
                    ),
                    {"plan_name": normalized_plan},
                )
                generated_org_id = str(result.scalar_one())
                return (
                    True,
                    "Organization onboarding completed; developer activation is pending.",
                    generated_org_id,
                )

            if "integer" in str(columns["org_id"]).lower():
                try:
                    org_id_value: str | int = int(normalized_org_id)
                except ValueError:
                    return (
                        False,
                        "Organization ID must be a valid integer.",
                        None,
                    )
            else:
                org_id_value = normalized_org_id or f"org-{uuid.uuid4().hex}"

            result = connection.execute(
                text(
                    """
                    UPDATE organizations
                    SET subscription_status = 'PENDING_DEVELOPER_ACTIVATION',
                        onboarding_completed = TRUE,
                        subscription_plan = :plan_name,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE org_id = :org_id
                    """
                ),
                {"plan_name": normalized_plan, "org_id": org_id_value},
            )
            if result.rowcount == 0:
                connection.execute(
                    text(
                        """
                        INSERT INTO organizations (
                            org_id, subscription_status, onboarding_completed,
                            subscription_plan, updated_at
                        ) VALUES (
                            :org_id, 'PENDING_DEVELOPER_ACTIVATION', TRUE,
                            :plan_name, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {"plan_name": normalized_plan, "org_id": org_id_value},
                )
        return (
            True,
            "Organization onboarding completed; developer activation is pending.",
            str(org_id_value),
        )
    except ValueError as exc:
        return False, str(exc), None
    except SQLAlchemyError:
        logging.exception("Could not save organization onboarding status.")
        return False, "The database could not save organization onboarding.", None


def set_developer_activation_status(
    org_id: str,
    status: str,
) -> tuple[bool, str]:
    """Set an existing organization to PENDING or ACTIVE for developer testing."""
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    normalized_status = str(status).strip().upper() if status is not None else ""
    if not normalized_org_id:
        return False, "Organization ID is required."
    if normalized_status not in DEVELOPER_ACTIVATION_STATUSES:
        return False, "Developer activation status must be PENDING or ACTIVE."

    engine = get_db_engine()
    try:
        inspector = inspect(engine)
        if "organizations" not in inspector.get_table_names():
            return False, "The organizations table does not exist."
        columns = {
            column["name"]: column["type"]
            for column in inspector.get_columns("organizations")
        }
        if "org_id" not in columns or "subscription_status" not in columns:
            return False, "The organizations table is missing activation fields."
        org_id_value = _organization_id_value(
            normalized_org_id,
            columns["org_id"],
        )
        with engine.begin() as connection:
            result = connection.execute(
                text(
                    """
                    UPDATE organizations
                    SET subscription_status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE org_id = :org_id
                    """
                ),
                {"status": normalized_status, "org_id": org_id_value},
            )
        if result.rowcount != 1:
            return False, "Organization was not found; no activation status changed."
        return True, f"Organization status changed to {normalized_status}."
    except ValueError as exc:
        return False, str(exc)
    except SQLAlchemyError:
        logging.exception("Could not change organization activation status.")
        return False, "The database could not update organization activation."


def get_requested_mode() -> str:
    """Read the `mode` query parameter across supported Streamlit versions."""
    try:
        query_params = getattr(st, "query_params", None)
    except StreamlitAPIException:
        query_params = None
    if query_params is not None:
        try:
            value = query_params.get("mode", "")
        except (AttributeError, StreamlitAPIException):
            value = None
    else:
        value = None
    if value is None:
        try:
            legacy_params = st.experimental_get_query_params()
        except (AttributeError, StreamlitAPIException):
            return ""
        value = legacy_params.get("mode", "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value).strip()


def render_master_router(
    admin_authenticated: bool = False,
    subscription_checker: Callable[[str], tuple[bool, str]] | None = None,
) -> tuple[str, str, bool]:
    """Render persona and page navigation, exposing activation-gated workspaces."""
    if get_requested_mode() == "submit_proposal":
        st.sidebar.caption("Opened via proposal submission link.")
        return "Public Vendor", "Public Vendor Portal", True

    persona = st.sidebar.selectbox(
        "Developer persona",
        [
            "Developer Master Access",
            "Client",
            "Public Vendor",
            "Internal Admin",
        ],
        key="portal_persona",
    )

    is_subscribed = False
    if persona == "Client":
        organization_id = st.sidebar.text_input(
            "Organization ID",
            key="organization_id",
        ).strip()
        if organization_id:
            checker = subscription_checker or check_organization_subscription
            st.session_state["active_org_status"] = "PENDING_DEVELOPER_ACTIVATION"
            is_subscribed, subscription_message = checker(organization_id)
            if is_subscribed:
                st.session_state["active_org_status"] = "ACTIVE"
            st.sidebar.caption(subscription_message)
        else:
            st.session_state["active_org_status"] = "PENDING_DEVELOPER_ACTIVATION"
            st.sidebar.info("Enter your organization ID to check subscription status.")
    st.session_state["is_subscribed"] = is_subscribed

    if persona == "Developer Master Access":
        portal_options = [
            "Public Vendor Portal",
            "Internal Admin Portal",
            "Organization Admin Settings",
            "Organization Onboarding Wizard",
        ]
        if admin_authenticated:
            portal_options.append("Subscription Management")
    elif persona == "Client":
        portal_options = [
            "Client Dashboard",
            "Organization Admin Settings",
            "Organization Onboarding Wizard",
        ]
    elif persona == "Public Vendor":
        portal_options = ["Public Vendor Portal"]
    else:
        portal_options = ["Internal Admin Portal"]

    portal_view = st.sidebar.radio(
        "Choose a portal",
        portal_options,
        key=f"portal_view_selector_{persona}",
    )
    return persona, portal_view, False


def check_organization_subscription(org_id: str) -> tuple[bool, str]:
    """Check whether an existing organization has developer-granted access."""
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    if not normalized_org_id:
        return False, "Organization ID is required."

    engine = get_db_engine()
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            if "organizations" not in inspector.get_table_names():
                return False, "The organizations table does not exist."

            columns = {
                column["name"]: column["type"]
                for column in inspector.get_columns("organizations")
            }
            missing_columns = ORGANIZATION_COLUMNS - columns.keys()
            if missing_columns:
                logging.error(
                    "Cannot check organization subscription: organizations table lacks columns %s",
                    ", ".join(sorted(missing_columns)),
                )
                return False, "The organizations table is missing required subscription fields."

            org_id_value = normalized_org_id
            if "integer" in str(columns["org_id"]).lower():
                try:
                    org_id_value = int(normalized_org_id)
                except ValueError:
                    return False, "Organization ID must be a valid integer."

            result = connection.execute(
                text(
                    """
                    SELECT subscription_status, onboarding_completed,
                           subscription_plan, updated_at
                    FROM organizations
                    WHERE org_id = :org_id
                    """
                ),
                {"org_id": org_id_value},
            ).mappings().first()

        if result is None:
            st.session_state["active_org_status"] = "PENDING_DEVELOPER_ACTIVATION"
            return False, "Organization was not found."
        status = str(result["subscription_status"]).strip().upper()
        st.session_state["active_org_status"] = status
        if status != "ACTIVE":
            if status == "PENDING_DEVELOPER_ACTIVATION":
                return False, "Organization is pending developer activation."
            return False, "Organization does not have active developer access."
        if not result["onboarding_completed"]:
            return False, "Organization onboarding is not complete."
        return True, "Organization developer access is active."
    except SQLAlchemyError:
        logging.exception("Organization activation status check failed.")
        return (
            False,
            "The database could not verify organization activation. Check server logs.",
        )


def complete_organization_subscription(
    org_id: str,
    plan_name: str = "Enterprise",
) -> tuple[bool, str]:
    """Activate an existing organization after its payment is verified.

    The database URL and connection pool come from the shared database module,
    which resolves the cloud secret/environment URL or local dotenv URL.
    """
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    normalized_plan = str(plan_name).strip() if plan_name is not None else ""
    if not normalized_org_id:
        return False, "Organization ID is required."
    if normalized_plan not in AVAILABLE_SUBSCRIPTION_PLANS:
        return False, "Select Starter, Professional, or Enterprise."
    if not is_paystack_configured():
        return False, "Configure Paystack before activating a subscription."

    engine = get_db_engine()
    if engine.dialect.name != "postgresql":
        return False, "Subscription activation requires a PostgreSQL database."

    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if "organizations" not in inspector.get_table_names():
                return False, "The PostgreSQL organizations table does not exist."

            organization_columns = inspector.get_columns("organizations")
            available_columns = {column["name"] for column in organization_columns}
            missing_columns = ORGANIZATION_COLUMNS - available_columns
            if missing_columns:
                logging.error(
                    "Cannot activate organization: organizations table lacks columns %s",
                    ", ".join(sorted(missing_columns)),
                )
                return False, "The organizations table is missing required subscription fields."

            org_id_column = next(
                column for column in organization_columns if column["name"] == "org_id"
            )
            org_id_value = normalized_org_id
            if "integer" in str(org_id_column["type"]).lower():
                try:
                    org_id_value = int(normalized_org_id)
                except ValueError:
                    return False, "Organization ID must be a valid integer."

            result = connection.execute(
                text(
                    """
                    UPDATE organizations
                    SET subscription_status = 'ACTIVE',
                        onboarding_completed = TRUE,
                        subscription_plan = :plan_name,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE org_id = :org_id
                    """
                ),
                {"plan_name": normalized_plan, "org_id": org_id_value},
            )
            if result.rowcount != 1:
                return False, "Organization was not found; no subscription was activated."
        return True, "Subscription successfully activated."
    except SQLAlchemyError:
        logging.exception("PostgreSQL subscription activation failed.")
        return False, "The database could not activate the subscription. Check server logs."
