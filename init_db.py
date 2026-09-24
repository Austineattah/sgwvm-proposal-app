import psycopg2


def initialize_database():
    # Connection parameters
    db_params = {
        "dbname": "sgwvm_db",
        "user": "postgres",
        "password": "admin",
        "host": "localhost",
        "port": 5432,
    }

    try:
        # Connect to the PostgreSQL database
        print("Connecting to the database...")
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Connected successfully!")

        # DDL statements for tables
        commands = [
            """
            CREATE TABLE IF NOT EXISTS proposals (
                id SERIAL PRIMARY KEY,
                proposal_reference VARCHAR(100) UNIQUE NOT NULL,
                submitter_name VARCHAR(255) NOT NULL,
                submitter_email VARCHAR(255) NOT NULL,
                submission_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'Received',
                raw_payload TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS tracking_logs (
                id SERIAL PRIMARY KEY,
                proposal_id INT REFERENCES proposals(id) ON DELETE CASCADE,
                stage VARCHAR(100) NOT NULL,
                status_message TEXT,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                action_performed VARCHAR(255) NOT NULL,
                performed_by VARCHAR(100) DEFAULT 'system',
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            );
            """,
        ]

        # Execute table creation commands
        for command in commands:
            cursor.execute(command)

        print(
            "All tables (`proposals`, `tracking_logs`, `audit_logs`) created successfully!"
        )

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error connecting or creating tables: {e}")


if __name__ == "__main__":
    initialize_database()
