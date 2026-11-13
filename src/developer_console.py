import textwrap
"""
NexusVault Developer Console & Seminar Training Portal (src/developer_console.py)
Empowers Lead Architect & CEO with master admin controls, blinking alert notifications, and tenant support controls.
"""

import logging
import sqlite3
import time

import streamlit as st

try:
    from src.developer_kb import NEXUSVAULT_EXECUTIVE_KB
    from src.kb_presentation import render_executive_document
except ImportError as exc:
    NEXUSVAULT_EXECUTIVE_KB = {}
    render_executive_document = None
    _KNOWLEDGE_BASE_IMPORT_ERROR: ImportError | None = exc
else:
    _KNOWLEDGE_BASE_IMPORT_ERROR = None

try:
    from src.nexus_db_adapter import (
        get_all_support_tickets as _get_all_support_tickets,
        respond_to_support_ticket as _respond_to_support_ticket,
    )
except ImportError as exc:
    _get_all_support_tickets = None
    _respond_to_support_ticket = None
    _SUPPORT_ADAPTER_IMPORT_ERROR: ImportError | None = exc
else:
    _SUPPORT_ADAPTER_IMPORT_ERROR = None


def _expire_developer_session():
    now = time.time()
    last_activity = st.session_state.get(
        "last_activity", st.session_state.get("last_activity_timestamp")
    )
    if not isinstance(last_activity, (int, float)) or now - last_activity <= 900:
        return False
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["last_activity"] = now
    st.session_state["session_expired_msg"] = (
        "Session expired due to 15 minutes of inactivity. Re-authentication required."
    )
    return True


def _monitor_developer_session():
    if _expire_developer_session():
        st.rerun()


def render_developer_console(*, get_tickets=None, respond_to_ticket=None):
    if _expire_developer_session():
        st.rerun()
    st.session_state["last_activity"] = time.time()
    if not hasattr(st, "fragment"):
        st.error("Session security requires Streamlit 1.37 or newer.")
        return
    st.fragment(run_every="1s")(_monitor_developer_session)()
    expired_message = st.session_state.pop("session_expired_msg", None)
    if expired_message:
        st.warning(expired_message)
    if st.session_state.get("dev_authenticated") is not True:
        st.error("Developer authentication is required.")
        return
    st.markdown("## 🛡️ NexusVault Sovereign Developer Console")
    st.markdown(
        "Master Administrative Oversight & Executive Seminar Training Environment"
    )

    ticket_reader = get_tickets or _get_all_support_tickets
    ticket_responder = respond_to_ticket or _respond_to_support_ticket
    tickets = None
    if ticket_reader is not None:
        try:
            tickets = ticket_reader()
        except (OSError, RuntimeError, sqlite3.Error, ValueError):
            logging.exception("Support tickets could not be loaded.")
            st.error("Support tickets could not be loaded.")
    elif _SUPPORT_ADAPTER_IMPORT_ERROR is not None:
        st.error(f"Support ticket storage is unavailable: {_SUPPORT_ADAPTER_IMPORT_ERROR}")

    unanswered_count = sum(
        1 for ticket in (tickets or []) if ticket["status"] == "OPEN"
    )

    feedback_label = "📩 Client Tenant Feedback & Complaints"
    if unanswered_count > 0:
        feedback_label = f"🔴 📩 Feedback & Complaints ({unanswered_count} PENDING)"

    tab_admin, tab_feedback, tab_seminar = st.tabs(
        [
            "⚙️ Master Administration & Database Controls",
            feedback_label,
            "🎓 Executive Seminar Training & UI Simulation",
        ]
    )

    with tab_admin:
        st.markdown("### Master Administrative Operations")
        st.info(
            "Operating under Sovereign Master Credentials — Lead Architect / CEO: Augustine Attah."
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Tenant Nodes", "24", "+3 this week")
        with col2:
            st.metric("Secured Cryptographic Tokens", "142", "0 revoked")
        with col3:
            st.metric(
                "Pending Inquiries (Action Required)",
                f"{unanswered_count}",
                "Needs CEO Response" if unanswered_count > 0 else "All Resolved",
            )

        st.markdown("---")
        st.markdown("#### Tenant Activation Override & Registry Management")
        st.text_input(
            "Search Tenant Slug or Admin Email:",
            placeholder="e.g. wiseventuresltd_7c6c24ae",
        )
        st.button("🔄 Refresh Sovereign Database State", use_container_width=True)

    with tab_feedback:
        if tickets is None:
            st.error("Support history is unavailable; no ticket actions are enabled.")
        else:
            render_tenant_feedback_tab(
                tickets,
                unanswered_count,
                respond_to_ticket=ticket_responder,
            )

    with tab_seminar:
        if _KNOWLEDGE_BASE_IMPORT_ERROR is not None:
            st.error(
                "The Executive Knowledge Base is unavailable: "
                f"{_KNOWLEDGE_BASE_IMPORT_ERROR}"
            )
        else:
            render_seminar_training_suite()


def render_tenant_feedback_tab(
    tickets,
    unanswered_count,
    *,
    respond_to_ticket=None,
):
    st.markdown("### 📩 Client Tenant Inquiries & Escalation Gateway")

    # Blinking Pulsing CSS Notification Banner for Unanswered Tickets
    if unanswered_count > 0:
        st.markdown(
            textwrap.dedent(f"""
            <style>
            @keyframes pulse-red {{
                0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); background-color: rgba(239, 68, 68, 0.15); }}
                70% {{ box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); background-color: rgba(239, 68, 68, 0.35); }}
                100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); background-color: rgba(239, 68, 68, 0.15); }}
            }}
            .blinking-alert-box {{
                animation: pulse-red 1.5s infinite;
                border: 2px solid #ef4444;
                border-radius: 10px;
                padding: 16px;
                color: #fca5a5;
                font-weight: bold;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            </style>
            <div class="blinking-alert-box">
                <span style="font-size: 24px;">🚨</span>
                <div>
                    <span style="font-size: 16px; color: #ffffff;">URGENT ATTENTION REQUIRED ({unanswered_count} OUT-OF-SCOPE INQUIRY)</span><br>
                    <span style="font-size: 13px; color: #f87171;">Client tenant submitted a inquiry outside standard AI Knowledge Base logic. Visual alert will pulse until resolved.</span>
                </div>
            </div>
            """).strip(),
            unsafe_allow_html=True,
        )
    else:
        st.success(
            "🟢 All client tenant inquiries have been answered or resolved by AI Auto-Reply!"
        )

    if respond_to_ticket is None:
        st.error("Ticket responses are unavailable because ticket storage is missing.")
        return

    if not tickets:
        st.info("No active inquiries or complaints recorded from client tenants.")
        return

    for t in tickets:
        is_open = t["status"] == "OPEN"
        status_label = (
            "🚨 ATTENTION REQUIRED (UNANSWERED)" if is_open else f"🟢 {t['status']}"
        )

        with st.expander(
            f"[{status_label}] {t['org_name']} (Ref: {t['tenant_slug']}) — {t['created_at']}",
            expanded=is_open,
        ):
            st.markdown(f"**Tenant Reference Slug:** `{t['tenant_slug']}`")
            st.markdown(f"**Sender Email:** `{t['sender_email']}`")
            st.markdown(f"**Submitted Inquiry:**\n> {t['message']}")

            if t["response"]:
                st.info(
                    f"**Dispatched Response ({t['responded_at']}):**\n\n{t['response']}"
                )
            else:
                st.markdown("---")
                st.warning(
                    "This inquiry requires a direct manual response from Lead Architect / CEO Augustine Attah."
                )
                reply_text = st.text_area(
                    f"Type response to {t['org_name']}:", key=f"reply_{t['ticket_id']}"
                )
                if st.button(
                    "📤 SEND EXECUTIVE RESPONSE",
                    key=f"btn_{t['ticket_id']}",
                    type="primary",
                ):
                    if reply_text.strip():
                        try:
                            responded = respond_to_ticket(
                                t["ticket_id"],
                                reply_text.strip(),
                            )
                        except (OSError, RuntimeError, sqlite3.Error, ValueError):
                            logging.exception(
                                "Could not respond to support ticket %s.",
                                t["ticket_id"],
                            )
                            st.error("Failed to record the executive response.")
                            continue
                        if responded:
                            st.success(
                                "Executive response sent! Visual blinking alert cleared."
                            )
                            st.rerun()
                        else:
                            st.error("Failed to record response. Check database logs.")
                    else:
                        st.warning("Please type a response before sending.")


def render_seminar_training_suite():
    st.markdown("### 🎓 Executive Seminar Training & Client Tenant UI Simulator")
    st.markdown(
        "Project this interactive training suite during live executive briefings to walk through "
        "system components inside a simulated client tenant UI environment."
    )

    mode = st.radio(
        "Select Training Mode:",
        ["🖥️ Vivid Tenant UI Simulation Deck", "🔍 Interactive Knowledge Base Lookup"],
        horizontal=True,
    )

    slides = []
    for topic_name, topic_data in NEXUSVAULT_EXECUTIVE_KB.items():
        for qa in topic_data["qa_pairs"]:
            slides.append(
                {
                    "topic": topic_name,
                    "category": topic_data["category"],
                    "tenant_context": topic_data["tenant_context"],
                    "status_badge": topic_data["status_badge"],
                    "summary": topic_data["summary"],
                    "question": qa["question"],
                    "answer": qa["answer"],
                }
            )

    if mode == "🖥️ Vivid Tenant UI Simulation Deck":
        if "seminar_slide_idx" not in st.session_state:
            st.session_state.seminar_slide_idx = 0

        total_slides = len(slides)

        c_prev, c_pos, c_next = st.columns([1, 4, 1])
        with c_prev:
            if (
                st.button("⬅️ Previous Slide", use_container_width=True)
                and st.session_state.seminar_slide_idx > 0
            ):
                st.session_state.seminar_slide_idx -= 1
                st.rerun()
        with c_pos:
            st.progress((st.session_state.seminar_slide_idx + 1) / total_slides)
            st.caption(
                f"Slide {st.session_state.seminar_slide_idx + 1} of {total_slides} — **Module:** {slides[st.session_state.seminar_slide_idx]['topic']}"
            )
        with c_next:
            if (
                st.button("Next Slide ➡️", use_container_width=True)
                and st.session_state.seminar_slide_idx < total_slides - 1
            ):
                st.session_state.seminar_slide_idx += 1
                st.rerun()

        current = slides[st.session_state.seminar_slide_idx]

        st.markdown(
            textwrap.dedent(f"""
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
            """).strip(),
            unsafe_allow_html=True,
        )

        jump_idx = st.selectbox(
            "Jump to Slide:",
            options=range(total_slides),
            format_func=lambda i: f"Slide {i+1}: {slides[i]['question']}",
            index=st.session_state.seminar_slide_idx,
        )
        if jump_idx != st.session_state.seminar_slide_idx:
            st.session_state.seminar_slide_idx = jump_idx
            st.rerun()

    else:
        topic_names = list(NEXUSVAULT_EXECUTIVE_KB.keys())
        selected_topic = st.selectbox(
            "Select System Component / Module for Deep Dive:", topic_names
        )
        if selected_topic:
            topic_data = NEXUSVAULT_EXECUTIVE_KB[selected_topic]
            if "documentation" in topic_data:
                render_executive_document(topic_data["documentation"])
            else:
                st.info(
                    f"**Category:** {topic_data['category']}  \n**Summary:** {topic_data['summary']}"
                )
                for idx, qa in enumerate(topic_data["qa_pairs"], start=1):
                    with st.expander(f"Q{idx}: {qa['question']}", expanded=(idx == 1)):
                        st.markdown(qa["answer"])
