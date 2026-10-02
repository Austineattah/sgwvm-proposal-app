import os
import re
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load environment variables for local development
load_dotenv()


# --- SECURE DATABASE CONFIGURATION ---
def get_secret(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


# Pull explicit connection URL or construct it using the hardened least-privileged user
DATABASE_URL = get_secret("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST = get_secret("DB_HOST", "localhost")
    DB_NAME = get_secret("DB_NAME", "sgwvm_db")
    DB_USER = get_secret("DB_USER", "sgwvm_app_user")
    DB_PASSWORD = get_secret("DB_PASSWORD", "YourStrongSecurePasswordHere123!")
    DB_PORT = get_secret("DB_PORT", "5432")

    DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Create the SQLAlchemy Engine for Pandas and ORM/Bulk Operations
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_db_engine():
    """Returns the SQLAlchemy engine instance for Pandas and DB operations."""
    return engine


def get_db_connection():
    """Returns a raw psycopg2 PostgreSQL database connection using the connection URL."""
    return psycopg2.connect(
        DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    )


VALID_PROPOSAL_STATUSES = ("Draft", "Pending", "Approved")


def normalize_proposal_status(status):
    """Validates a proposal status and falls back to Draft when an invalid value is passed."""
    if status is None:
        return "Draft"

    normalized = str(status).strip()
    return normalized if normalized in VALID_PROPOSAL_STATUSES else "Draft"


def ensure_proposal_status_column():
    """Ensures older proposal tables gain the status field and normalizes legacy values."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'proposals' AND column_name = 'status';
            """)
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE proposals ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Draft';"
            )

        cur.execute("""
            UPDATE proposals
            SET status = 'Draft'
            WHERE status IS NULL OR status = '' OR status NOT IN ('Draft', 'Pending', 'Approved');
            """)
        cur.execute("ALTER TABLE proposals ALTER COLUMN status SET DEFAULT 'Draft';")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


try:
    ensure_proposal_status_column()
except Exception:
    pass


def sanitize_budget(budget_val):
    """Converts string budget values to float, or None (SQL NULL) if invalid or non-numeric."""
    if isinstance(budget_val, (int, float)):
        return float(budget_val)
    if isinstance(budget_val, str):
        # Clean out non-digit and non-decimal characters (e.g., "$15,000.00" -> "15000.00")
        cleaned = re.sub(r"[^\d.]", "", budget_val)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


def insert_proposal(
    tracking_code,
    vendor_name,
    email,
    category,
    cac_number,
    ai_summary,
    budget,
    is_flagged=False,
    status="Draft",
):
    """Inserts a new proposal record into PostgreSQL with sanitized budget and automated high-priority tagging."""
    safe_budget = sanitize_budget(budget)
    normalized_status = normalize_proposal_status(status)

    # Calculate high-priority status based on the threshold (e.g., >= 50,000,000)
    is_high_priority = bool(safe_budget is not None and safe_budget >= 50000000.0)

    query = """
        INSERT INTO proposals (
            tracking_code, 
            vendor_name, 
            email, 
            category, 
            cac_number, 
            ai_summary, 
            budget, 
            is_flagged,
            is_high_priority,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            query,
            (
                tracking_code,
                vendor_name,
                email,
                category,
                cac_number,
                ai_summary,
                safe_budget,
                is_flagged,
                is_high_priority,
                normalized_status,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def update_proposal_status(proposal_id, status):
    """Updates a proposal's lifecycle status, allowing Draft, Pending, or Approved."""
    normalized_status = normalize_proposal_status(status)
    query = "UPDATE proposals SET status = %s WHERE id = %s;"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(query, (normalized_status, proposal_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def delete_proposal_by_id(proposal_id):
    """Deletes a single proposal record by its primary key ID."""
    query = "DELETE FROM proposals WHERE id = %s;"
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, (proposal_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def clear_legacy_or_test_proposals():
    """Deletes test proposals or those containing AI skip notices and nan placeholders."""
    query = """
        DELETE FROM proposals 
        WHERE ai_summary LIKE '%AI processing skipped%' 
            OR tracking_code LIKE 'TRK-TEST%' 
            OR vendor_name = 'nan';
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query)
        deleted_count = cur.rowcount
        conn.commit()
        return deleted_count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()
