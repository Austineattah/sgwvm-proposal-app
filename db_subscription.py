import logging
from collections.abc import Callable

import streamlit as st
from streamlit.errors import StreamlitAPIException
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
    """Render persona and page navigation, enforcing subscription-based routes."""
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
            is_subscribed, subscription_message = checker(organization_id)
            st.sidebar.caption(subscription_message)
        else:
            st.sidebar.info("Enter your organization ID to check subscription status.")
    st.session_state["is_subscribed"] = is_subscribed

    if persona == "Developer Master Access":
        portal_options = [
            "Public Vendor Portal",
            "Internal Admin Portal",
            "Organization Onboarding Wizard",
        ]
        if admin_authenticated:
            portal_options.append("Subscription Management")
    elif persona == "Client":
        portal_options = (
            ["Client Dashboard", "Organization Onboarding Wizard"]
            if is_subscribed
            else ["Organization Onboarding Wizard"]
        )
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
    """Check whether an existing organization has an active subscription."""
    normalized_org_id = str(org_id).strip() if org_id is not None else ""
    if not normalized_org_id:
        return False, "Organization ID is required."

    engine = get_db_engine()
    if engine.dialect.name != "postgresql":
        return False, "Subscription checks require a PostgreSQL database."

    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            if "organizations" not in inspector.get_table_names():
                return False, "The PostgreSQL organizations table does not exist."

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
            return False, "Organization was not found."
        if str(result["subscription_status"]).strip().upper() != "ACTIVE":
            return False, "Organization does not have an active subscription."
        if not result["onboarding_completed"]:
            return False, "Organization onboarding is not complete."
        return True, "Organization subscription is active."
    except SQLAlchemyError:
        logging.exception("PostgreSQL subscription status check failed.")
        return False, "The database could not verify the subscription. Check server logs."


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
    if not normalized_plan or len(normalized_plan) > 100:
        return False, "Provide a subscription plan of 1 to 100 characters."

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
