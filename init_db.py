from sqlalchemy import text

from database import get_db_engine, initialize_database as initialize_models


def initialize_database():
    """Initialize the application ORM schema and supporting PostgreSQL tables."""
    initialize_models()
    engine = get_db_engine()
    with engine.begin() as connection:
        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS tracking_logs (
                    id SERIAL PRIMARY KEY,
                    proposal_id INT REFERENCES proposals(id) ON DELETE CASCADE,
                    stage VARCHAR(100) NOT NULL,
                    status_message TEXT,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    action_performed VARCHAR(255) NOT NULL,
                    performed_by VARCHAR(100) DEFAULT 'system',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """)
        )


if __name__ == "__main__":
    initialize_database()
