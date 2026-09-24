import streamlit as st


def apply_custom_theme():
    """Injects custom CSS to apply a corporate dark-mode glassmorphism theme."""
    st.markdown(
        """
        <style>
        /* 1. Main Background - Modern Corporate Mesh Gradient */
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            color: #f8fafc;
        }

        /* 2. Glassmorphism Form Container */
        div[data-testid="stForm"] {
            background: rgba(30, 41, 59, 0.7) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 16px !important;
            padding: 2rem !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3) !important;
        }

        /* 3. Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.95) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* 4. Custom Submit Button */
        div[data-testid="stForm"] button {
            background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.2rem !important;
            transition: all 0.3s ease !important;
        }

        div[data-testid="stForm"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
        }

        /* 5. Input Field Glow Effects */
        input, select, textarea {
            border-radius: 8px !important;
            border: 1px solid #334155 !important;
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }
        
        input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_header(logo_path_or_url="https://via.placeholder.com/150x50.png?text=LOGO"):
    """Renders a consistent corporate header with logo across portal pages."""
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(logo_path_or_url, width=120)
    with col2:
        st.markdown(
            """
            <div style="padding-top: 5px;">
                <h2 style="margin:0; padding:0; color:#f8fafc;">Enterprise Proposal Intake Portal</h2>
                <p style="margin:0; color:#94a3b8; font-size: 0.9rem;">Automated AI Triage & KYB Verification System</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("---")
