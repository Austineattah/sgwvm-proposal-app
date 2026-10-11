import streamlit as st
import pandas as pd
from modules.database import get_all_proposals, update_proposal_status

def render_admin_portal():
    st.title("🔒 Legislative Admin Review Dashboard")
    st.write("Manage, inspect, and evaluate submitted vendor proposals.")
    
    proposals = get_all_proposals()
    
    if not proposals:
        st.info("No proposal submissions found in the database yet.")
        return
    
    df = pd.DataFrame(proposals)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Submissions", len(df))
    col2.metric("Pending Review", len(df[df['status'] == 'Pending']) if 'status' in df.columns else len(df))
    col3.metric("Categories Active", df['category'].nunique() if 'category' in df.columns else 1)
    
    st.divider()
    st.subheader("Incoming Proposals Directory")
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    st.subheader("Proposal Evaluation & Status Update")
    
    proposal_ids = df['id'].tolist() if 'id' in df.columns else []
    if proposal_ids:
        selected_id = st.selectbox("Select Proposal ID to Review", proposal_ids)
        selected_row = df[df['id'] == selected_id].iloc[0]
        
        st.write(f"**Company:** {selected_row.get('company_name', 'N/A')} | **Project:** {selected_row.get('project_title', 'N/A')}")
        st.write(f"**Abstract:** {selected_row.get('proposal_abstract', 'N/A')}")
        st.write(f"**AI Summary Extracted:** {selected_row.get('ai_summary', 'N/A')}")
        
        new_status = st.selectbox("Update Status", ["Pending", "Under Review", "Approved", "Rejected"], index=0)
        
        if st.button("Save Status Update"):
            update_proposal_status(selected_id, new_status)
            st.success(f"Proposal #{selected_id} status updated to {new_status}!")
            st.rerun()
