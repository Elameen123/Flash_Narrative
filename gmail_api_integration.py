import smtplib
import ssl
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email_smtp(to_email, subject, body, attachments=None):
    """
    Sends email using standard Python SMTP (requires App Password).
    """
    # Load config from secrets
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    sender_email = st.secrets["email"]["sender_email"]
    password = st.secrets["email"]["app_password"]

    try:
        # Create Message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Add Attachments
        if attachments:
            for filename, content, mime_type in attachments:
                # content is likely bytes, so we wrap it
                part = MIMEApplication(content)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                message.attach(part)

        # Connect and Send
        context = ssl.create_default_context()
        print(f"🚀 Connecting to SMTP server {smtp_server}...")
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, to_email, message.as_string())
            
        print("✅ Email Sent via SMTP!")
        return True

    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

# Update the wrapper to use this new function
def send_report_email_with_attachments(to_email, subject, body, attachments):
    return send_email_smtp(to_email, subject, body, attachments)