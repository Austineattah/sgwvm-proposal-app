import os
import re
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine

# Load environment variables for local development
load_dotenv()


# Database Connection Details (Checking Streamlit Secrets first, then fallback to environment variables/defaults)
def get_secret(key, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


DB_HOST = get_secret("DB_HOST", "localhost")
DB_NAME = get_secret("DB_NAME", "sgwvm_db")
DB_USER = get_secret("DB_USER", "postgres")
DB_PASSWORD = get_secret("DB_PASSWORD", get_secret("DB_PASS", "admin"))
DB_PORT = get_secret("DB_PORT", "5432")

# Construct PostgreSQL Connection String with explicit psycopg2 driver mapping
DATABASE_URL = get_secret("DATABASE_URL")
if not DATABASE_URL:
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
    """Returns a raw psycopg2 PostgreSQL database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
    )


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
):
    """Inserts a new proposal record into PostgreSQL with sanitized budget and automated high-priority tagging."""
    safe_budget = sanitize_budget(budget)

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
            is_high_priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
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
            ),
        )
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
