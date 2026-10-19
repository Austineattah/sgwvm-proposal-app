import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import toml

try:
    secrets = toml.load(".streamlit/secrets.toml")
    sender_email = secrets.get("SENDER_EMAIL")
    sender_password = secrets.get("SENDER_PASSWORD")
    smtp_server = secrets.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(secrets.get("SMTP_PORT", 587))

    print(f"[*] Attempting SMTP connection to {smtp_server}:{smtp_port} via {sender_email}...")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = sender_email
    msg['Subject'] = "Sovereign Intake Portal - SMTP Verification Test"
    msg.attach(MIMEText("This is an automated test verifying local SMTP dispatch capabilities.", "plain"))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, sender_email, msg.as_string())
    server.quit()

    print("[SUCCESS] SMTP Connection Successful! Test email delivered to " + sender_email)

except Exception as e:
    print("[ERROR] SMTP Test Failed:", e)
