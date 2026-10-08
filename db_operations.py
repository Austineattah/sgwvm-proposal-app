from database import VALID_PROPOSAL_STATUSES, get_proposal_db_connection


def insert_proposal(
    title,
    submitter,
    file_path="",
    extracted_text="",
    category="Others",
    email="",
    phone="",
    is_flagged=False,
    status="Draft",
):
    """Inserts a new proposal submission record into the PostgreSQL database."""
    normalized_status = status if status in VALID_PROPOSAL_STATUSES else "Draft"

    conn = get_proposal_db_connection()
    cur = conn.cursor()

    query = """
        INSERT INTO proposals 
        (proposal_reference, submitter_name, submitter_email, category, phone, file_path, summary, is_flagged, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """

    cur.execute(
        query,
        (
            title,
            submitter,
            email,
            category,
            phone,
            file_path,
            extracted_text,
            is_flagged,
            normalized_status,
        ),
    )

    proposal_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return proposal_id
