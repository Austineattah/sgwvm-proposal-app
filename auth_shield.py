import streamlit as st
import database as db

def check_attempts_and_lockout(gate_name):
    """
    Tracks failed password attempts and locks the portal if attempts exceed 3.
    """
    attempt_key = f"attempts_{gate_name}"
    lock_key = f"locked_{gate_name}"

    if attempt_key not in st.session_state:
        st.session_state[attempt_key] = 0
    if lock_key not in st.session_state:
        st.session_state[lock_key] = False

    return st.session_state[lock_key], st.session_state[attempt_key]

def register_failed_attempt(gate_name):
    """Increments failed attempt count and triggers hard lockout on 3rd strike."""
    attempt_key = f"attempts_{gate_name}"
    lock_key = f"locked_{gate_name}"

    st.session_state[attempt_key] += 1
    attempts = st.session_state[attempt_key]

    if attempts >= 3:
        st.session_state[lock_key] = True
        db.log_event("Security Firewall", "NODE_LOCKOUT", gate_name, f"3/3 Failed Attempts Exceeded on Gate '{gate_name}'. System Locked.")
        return 0, True
    
    remaining = 3 - attempts
    return remaining, False

def reset_attempts(gate_name):
    """Resets attempts upon successful login or admin override."""
    st.session_state[f"attempts_{gate_name}"] = 0
    st.session_state[f"locked_{gate_name}"] = False

def render_portal_entry_selector():
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
                    For external contractors and suppliers submitting unsolicited pitches or solicited tender responses.
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
                    For authorized public institution staff, front desk officers, and senior management reviewing proposals.
                </p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Internal Agency Portal", use_container_width=True):
            st.session_state["portal_mode"] = "internal_portal"
            st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
    if st.button("⚙️ Master Developer Console Login"):
        st.session_state["portal_mode"] = "developer_portal"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)