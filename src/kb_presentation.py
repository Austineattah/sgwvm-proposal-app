"""Shared presentation for executive knowledge-base documents."""

import streamlit as st


def render_executive_document(documentation: str) -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .nv-kb-document-marker),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nv-kb-document-marker) {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(30, 27, 75, 0.90));
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 14px;
            padding: 25px;
            color: #f8fafc;
        }
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .nv-kb-document-marker) :is(h3, h4),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nv-kb-document-marker) :is(h3, h4) {
            color: #38bdf8;
        }
        div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .nv-kb-document-marker) :is(p, li),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nv-kb-document-marker) :is(p, li) {
            color: #f8fafc;
        }
        .nv-kb-executive-badge {
            display: inline-block;
            color: #38bdf8;
            background: rgba(37, 99, 235, 0.2);
            border: 1px solid #2563eb;
            border-radius: 999px;
            padding: 4px 12px;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        st.markdown(
            '<span class="nv-kb-document-marker"></span>'
            '<span class="nv-kb-executive-badge">EXECUTIVE BRIEFING</span>',
            unsafe_allow_html=True,
        )
        st.markdown(documentation)
