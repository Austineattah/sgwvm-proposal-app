import streamlit as st
import database as db

def render_portal_entry_selector():
    """
    Renders an elite entry gate allowing users to choose whether they are 
    submitting a proposal as an external vendor or logging into the internal MDA portal.
    """
    st.markdown("""
        <style>
            .entry-card {
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(14px);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 14px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 12px 30px rgba(0,0,0,0.5);
                transition: all 0.3s ease;
            }
            .entry-card:hover {
                border-color: #38bdf8;
                box-shadow: 0 0 20px rgba(56, 189, 248, 0.25);
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align: center; margin-bottom: 35px;">
            <h1 style="color: #ffffff; font-size: 28px; font-weight: 900; margin-bottom: 10px;">
                🛡️ NEXUSVAULT SOVEREIGN PLATFORM GATEWAY
            </h1>
            <p style="color: #94a3b8; font-size: 15px;">
                Select your secure access channel to proceed into the ecosystem.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
            <div class="entry-card">
                <h3 style="color: #38bdf8; margin-bottom: 15px;">🚀 Public Vendor Portal</h3>
                <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 25px;">
                    For external contractors, tech firms, and suppliers submitting unsolicited pitches or solicited tender responses under NITDA/BPP guidelines.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Vendor Submission Portal", use_container_width=True):
            st.session_state["portal_mode"] = "vendor_portal"
            st.rerun()

    with col2:
        st.markdown("""
            <div class="entry-card">
                <h3 style="color: #34d399; margin-bottom: 15px;">🏛️ Internal MDA & Directorate Login</h3>
                <p style="color: #cbd5e1; font-size: 14px; margin-bottom: 25px;">
                    For authorized public institution officers, evaluation committee members, and senior directors reviewing secure submissions.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Internal Agency Portal", use_container_width=True):
            st.session_state["portal_mode"] = "internal_portal"
            st.rerun()