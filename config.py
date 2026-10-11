import os
import streamlit as st

class Config:
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL", "sqlite:///proposal_portal.db"))
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
    
    # Payment Gateways
    PAYSTACK_PUBLIC_KEY = st.secrets.get("PAYSTACK_PUBLIC_KEY", os.environ.get("PAYSTACK_PUBLIC_KEY", ""))
    PAYSTACK_SECRET_KEY = st.secrets.get("PAYSTACK_SECRET_KEY", os.environ.get("PAYSTACK_SECRET_KEY", ""))
    FLW_PUBLIC_KEY = st.secrets.get("FLW_PUBLIC_KEY", os.environ.get("FLW_PUBLIC_KEY", ""))
    FLW_SECRET_KEY = st.secrets.get("FLW_SECRET_KEY", os.environ.get("FLW_SECRET_KEY", ""))

    # Twilio SMS Configuration
    TWILIO_ACCOUNT_SID = st.secrets.get("TWILIO_ACCOUNT_SID", os.environ.get("TWILIO_ACCOUNT_SID", ""))
    TWILIO_AUTH_TOKEN = st.secrets.get("TWILIO_AUTH_TOKEN", os.environ.get("TWILIO_AUTH_TOKEN", ""))
    TWILIO_PHONE_NUMBER = st.secrets.get("TWILIO_PHONE_NUMBER", os.environ.get("TWILIO_PHONE_NUMBER", ""))

    # Email / SMTP Configuration
    SMTP_SERVER = st.secrets.get("SMTP_SERVER", os.environ.get("SMTP_SERVER", "smtp.gmail.com"))
    SMTP_PORT = int(st.secrets.get("SMTP_PORT", os.environ.get("SMTP_PORT", 587)))
    SMTP_USER = st.secrets.get("SMTP_USER", os.environ.get("SMTP_USER", ""))
    SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", os.environ.get("SMTP_PASSWORD", ""))
    SENDER_EMAIL = st.secrets.get("SENDER_EMAIL", os.environ.get("SENDER_EMAIL", ""))

    @classmethod
    def is_payment_active(cls) -> bool:
        return bool((cls.PAYSTACK_PUBLIC_KEY and cls.PAYSTACK_SECRET_KEY) or (cls.FLW_PUBLIC_KEY and cls.FLW_SECRET_KEY))
