import streamlit as st
import pandas as pd
import plotly.express as px
from modules import database, notifications

def render():
    st.title("🛡️ Legislative Admin & Committee Review Dashboard")
    st.markdown("Manage vendor proposals, inspect AI summaries, track statuses, and view pipeline analytics.")

    # Fetch proposals from database
    proposals = database.get_all_proposals()

    if not proposals:
        st.info("No proposals submitted in the database yet.")
        return

    # Convert to DataFrame for analytics
    df = pd.DataFrame(proposals)

    # --- TOP METRICS ROW ---
    col1, col2, col3, col4 = st.columns(4)
    total_count = len(df)
    pending_count = len(df[df['status'].str.lower() == 'pending']) if 'status' in df.columns else 0
    approved_count = len(df[df['status'].str.lower() == 'approved']) if 'status' in df.columns else 0
    declined_count = len(df[df['status'].str.lower() == 'declined']) if 'status' in df.columns else 0

    col1.metric("Total Proposals", total_count)
    col2.metric("Pending Review", pending_count)
    col3.metric("Approved", approved_count)
    col4.metric("Declined", declined_count)

    st.markdown("---")

    # --- PLOTLY ANALYTICS CHARTS ---
    st.subheader("📊 Pipeline Analytics")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if 'status' in df.columns and not df['status'].empty:
            status_counts = df['status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_status = px.pie(
                status_counts, 
                names='Status', 
                values='Count', 
                title='Proposal Status Distribution',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_status, use_container_width=True)

    with chart_col2:
        category_col = 'project_category' if 'project_category' in df.columns else ('category' if 'category' in df.columns else None)
        if category_col and not df[category_col].empty:
            cat_counts = df[category_col].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            fig_cat = px.bar(
                cat_counts, 
                x='Category', 
                y='Count', 
                title='Proposals by Project Category',
                color='Category',
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category analytics data unavailable.")

    st.markdown("---")

    # --- EXPORT COMMITTEE REPORT ---
    st.subheader("📥 Export Committee Report")
    col_exp1, col_exp2 = st.columns([2, 2])
    with col_exp1:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Proposals as CSV",
            data=csv_data,
            file_name="sgwvm_legislative_proposals_report.csv",
            mime="text/csv",
            help="Download all proposal records, contact info, and AI summaries for offline committee review."
        )

    st.markdown("---")

    # --- PROPOSAL MANAGEMENT TABLE & ACTIONS ---
    st.subheader("📋 Proposal Review & Management")
    
    selected_id = st.selectbox("Select Proposal ID to Review", options=df['id'].tolist() if 'id' in df.columns else [])
    
    if selected_id:
        prop = df[df['id'] == selected_id].iloc[0]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Company:** {prop.get('company_name', 'N/A')}")
            st.markdown(f"**Vendor Email:** {prop.get('email', 'N/A')}")
            st.markdown(f"**Project Title:** {prop.get('project_title', 'N/A')}")
        with col_b:
            st.markdown(f"**Current Status:** `{prop.get('status', 'Pending')}`")
            st.markdown(f"**Submitted At:** {prop.get('created_at', 'N/A')}")

        st.markdown("### 🤖 AI Summary & Insights")
        st.info(prop.get('ai_summary', 'No AI summary generated.'))

        # Status Update Form
        with st.form("status_update_form"):
            new_status = st.selectbox("Update Status", ["Pending", "Under Review", "Approved", "Declined"], index=["Pending", "Under Review", "Approved", "Declined"].index(prop.get('status', 'Pending')) if prop.get('status', 'Pending') in ["Pending", "Under Review", "Approved", "Declined"] else 0)
            admin_notes = st.text_area("Committee / Admin Notes", value=prop.get('admin_notes', ''))
            
            submit_update = st.form_submit_button("Save Status & Notify Vendor")
            
            if submit_update:
                database.update_proposal_status(selected_id, new_status, admin_notes)
                
                # Send email notification to vendor
                vendor_email = prop.get('email')
                if vendor_email:
                    subject = f"Update on your SGWVM Proposal: {prop.get('project_title', 'Submission')}"
                    body = f"Hello {prop.get('company_name', 'Vendor')},\n\nYour proposal status has been updated to: {new_status}.\n\nAdmin Notes:\n{admin_notes}\n\nThank you for partnering with SGWVM Technology Limited."
                    notifications.send_email(vendor_email, subject, body)
                
                st.success(f"Proposal #{selected_id} updated successfully and notification triggered!")
                st.rerun()
