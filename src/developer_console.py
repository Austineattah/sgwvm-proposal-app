"""
NexusVault Developer Console & Seminar Training Portal (src/developer_console.py)
Empowers the Lead Architect & CEO with master admin controls and simulated client tenant UI slide decks.
"""

import streamlit as st
from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB

def render_developer_console():
    st.markdown("## 🛡️ NexusVault Sovereign Developer Console")
    st.markdown("Master Administrative Oversight & Executive Seminar Training Environment")
    
    tab_admin, tab_seminar = st.tabs(["⚙️ Master Administration & Database Controls", "🎓 Executive Seminar Training & UI Simulation"])
    
    with tab_admin:
        st.markdown("### Master Administrative Operations")
        st.info("Operating under Sovereign Master Credentials — Lead Architect / CEO: Augustine Attah.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Tenant Nodes", "24", "+3 this week")
        with col2:
            st.metric("Secured Cryptographic Tokens", "142", "0 revoked")
        with col3:
            st.metric("Cron Watchdog Status", "ONLINE", "Healthy")
            
        st.markdown("---")
        st.markdown("#### Tenant Activation Override & Registry Management")
        st.text_input("Search Tenant Slug or Admin Email:", placeholder="e.g. wiseventuresltd_7c6c24ae")
        st.button("🔄 Refresh Sovereign Database State", use_container_width=True)

    with tab_seminar:
        render_seminar_training_suite()


def render_seminar_training_suite():
    st.markdown("### 🎓 Executive Seminar Training & Client Tenant UI Simulator")
    st.markdown(
        "Project this interactive training suite during live executive briefings to walk through "
        "system components inside a simulated client tenant UI environment."
    )
    
    mode = st.radio(
        "Select Training Mode:",
        ["🖥️ Vivid Tenant UI Simulation Deck", "🔍 Interactive Knowledge Base Lookup"],
        horizontal=True
    )
    
    slides = []
    for topic_name, topic_data in NEXUSVAULT_EXECUTIVE_KB.items():
        for qa in topic_data["qa_pairs"]:
            slides.append({
                "topic": topic_name,
                "category": topic_data["category"],
                "tenant_context": topic_data["tenant_context"],
                "status_badge": topic_data["status_badge"],
                "summary": topic_data["summary"],
                "question": qa["question"],
                "answer": qa["answer"]
            })
            
    if mode == "🖥️ Vivid Tenant UI Simulation Deck":
        if "seminar_slide_idx" not in st.session_state:
            st.session_state.seminar_slide_idx = 0
            
        total_slides = len(slides)
        
        c_prev, c_pos, c_next = st.columns([1, 4, 1])
        with c_prev:
            if st.button("⬅️ Previous Slide", use_container_width=True) and st.session_state.seminar_slide_idx > 0:
                st.session_state.seminar_slide_idx -= 1
                st.rerun()
        with c_pos:
            st.progress((st.session_state.seminar_slide_idx + 1) / total_slides)
            st.caption(f"Slide {st.session_state.seminar_slide_idx + 1} of {total_slides} — **Module:** {slides[st.session_state.seminar_slide_idx]['topic']}")
        with c_next:
            if st.button("Next Slide ➡️", use_container_width=True) and st.session_state.seminar_slide_idx < total_slides - 1:
                st.session_state.seminar_slide_idx += 1
                st.rerun()
                
        current = slides[st.session_state.seminar_slide_idx]
        
        st.markdown(
            f"""
            <div style="border: 2px solid #3b82f6; border-radius: 14px; background: #090d16; padding: 0px; box-shadow: 0 12px 30px rgba(0,0,0,0.5); margin-top: 15px; margin-bottom: 20px; overflow: hidden; font-family: sans-serif;">
                <div style="background: #1e293b; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155;">
                    <div>
                        <span style="height: 12px; width: 12px; background-color: #ef4444; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                        <span style="height: 12px; width: 12px; background-color: #f59e0b; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                        <span style="height: 12px; width: 12px; background-color: #10b981; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                        <span style="color: #94a3b8; font-size: 13px; margin-left: 10px; font-family: monospace;">{current['tenant_context']}</span>
                    </div>
                    <div style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid #3b82f6;">
                        🔒 {current['status_badge']}
                    </div>
                </div>
                
                <div style="padding: 30px; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: #f8fafc;">
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <span style="background-color: #2563eb; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">{current['category']}</span>
                        <span style="background-color: #334155; color: #cbd5e1; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 500;">{current['topic']}</span>
                    </div>
                    
                    <h2 style="color: #38bdf8; font-size: 24px; margin-top: 10px; margin-bottom: 15px; font-weight: 700;">{current['question']}</h2>
                    <p style="color: #94a3b8; font-size: 14px; font-style: italic; margin-bottom: 20px;">{current['summary']}</p>
                    
                    <hr style="border-color: #334155; margin: 20px 0;" />
                    
                    <div style="font-size: 15px; line-height: 1.8; color: #e2e8f0; background: rgba(15, 23, 42, 0.6); padding: 20px; border-radius: 8px; border-left: 4px solid #38bdf8;">
                        {current['answer'].replace(chr(10), '<br>')}
                    </div>
                </div>
                
                <div style="background: #0f172a; padding: 10px 20px; border-top: 1px solid #1e293b; text-align: right; color: #64748b; font-size: 12px;">
                    NexusVault Sovereign GovTech OS &bull; Secure Executive Briefing Mode
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        jump_idx = st.selectbox(
            "Jump to Slide:",
            options=range(total_slides),
            format_func=lambda i: f"Slide {i+1}: {slides[i]['question']}",
            index=st.session_state.seminar_slide_idx
        )
        if jump_idx != st.session_state.seminar_slide_idx:
            st.session_state.seminar_slide_idx = jump_idx
            st.rerun()
            
    else:
        topic_names = list(NEXUSVAULT_EXECUTIVE_KB.keys())
        selected_topic = st.selectbox("Select System Component / Module for Deep Dive:", topic_names)
        if selected_topic:
            topic_data = NEXUSVAULT_EXECUTIVE_KB[selected_topic]
            st.info(f"**Category:** {topic_data['category']}  \n**Summary:** {topic_data['summary']}")
            for idx, qa in enumerate(topic_data["qa_pairs"], start=1):
                with st.expander(f"Q{idx}: {qa['question']}", expanded=(idx == 1)):
                    st.markdown(qa["answer"])
