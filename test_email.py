import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load .env values
load_dotenv()

smtp_server = os.getenv("SMTP_SERVER")
smtp_port = int(os.getenv("SMTP_PORT"))
smtp_user = os.getenv("SMTP_USER")
smtp_pass = os.getenv("SMTP_PASS")
email_to = os.getenv("EMAIL_TO")

# Create message
msg = MIMEText("✅ This is a test email from your bus-bot script!")
msg["Subject"] = "Bus-Bot Email Test"
msg["From"] = smtp_user
msg["To"] = email_to

try:
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    print(f"✅ Test email sent successfully to {email_to}")
except Exception as e:
    print("❌ Failed to send email:", e)
