import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import toml

try:
    secrets = toml.load(".streamlit/secrets.toml")
    sender_email = secrets.get("SENDER_EMAIL")
    sender_password = secrets.get("SENDER_PASSWORD")

    print(f"[*] Attempting SSL connection to smtp.gmail.com:465 via {sender_email}...")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = sender_email
    msg['Subject'] = "Sovereign Intake Portal - Port 465 SSL Verification"
    msg.attach(MIMEText("Testing direct SSL connection on port 465.", "plain"))

    # Direct SSL connection
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, sender_email, msg.as_string())
    server.quit()

    print("[SUCCESS] Port 465 SSL Connection Successful! Test email delivered to " + sender_email)

except Exception as e:
    print("[ERROR] SSL Test Failed:", e)
