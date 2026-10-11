@"
import streamlit as st
from modules.database import fetch_all_concept_notes, update_concept_note_status

def render_admin_portal():
    st.title("🔐 Legislative Admin Command Portal")
    st.markdown("Review, evaluate, and manage submitted vendor proposals.")

    notes = fetch_all_concept_notes()

    if not notes:
        st.info("No proposals have been submitted yet.")
        return

    st.subheader(f"Total Submissions: {len(notes)}")

    for note in notes:
        with st.expander(f"📁 #{note['id']} - {note['title']} ({note['org_name']})"):
            col1, col2 = st.altair_chart if False else st.columns(2)
            
            with col1:
                st.write(f"**Organization:** {note['org_name']}")
                st.write(f"**Email:** {note['email']}")
                st.write(f"**File Name:** {note['file_name']}")
                st.write(f"**Submitted At:** {note['created_at']}")
                st.write(f"**Review Status:** `{note['review_status']}`")

            with col2:
                st.write("**AI Executive Summary:**")
                st.info(note['ai_summary'] or "No summary available.")

            st.markdown("---")
            
            # Status Update Actions
            status_col1, status_col2, status_col3 = st.columns(3)
            with status_col1:
                if st.button(f"Approve #{note['id']}", key=f"approve_{note['id']}"):
                    update_concept_note_status(note['id'], "APPROVED")
                    st.success(f"Proposal #{note['id']} approved!")
                    st.rerun()
            with status_col2:
                if st.button(f"Reject #{note['id']}", key=f"reject_{note['id']}"):
                    update_concept_note_status(note['id'], "REJECTED")
                    st.warning(f"Proposal #{note['id']} rejected.")
                    st.rerun()
            with status_col3:
                if st.button(f"Mark Pending #{note['id']}", key=f"pending_{note['id']}"):
                    update_concept_note_status(note['id'], "PENDING_REVIEW")
                    st.info(f"Proposal #{note['id']} marked pending.")
                    st.rerun()
"@ | Out-File -FilePath views/admin_portal.py -Encoding utf8