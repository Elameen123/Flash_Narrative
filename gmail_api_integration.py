import os.path
import base64
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Define Scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """
    Gets Gmail Service.
    PRIORITY 1: Streamlit Secrets (Cloud Deployment)
    PRIORITY 2: Local token.json (Local Development)
    """
    creds = None

    # 1. Try loading from Streamlit Secrets (Best for Cloud)
    if "google_oauth" in st.secrets:
        print("☁️ Loading credentials from Streamlit Secrets...")
        try:
            # Reconstruct credentials from the dictionary in secrets
            oauth_info = st.secrets["google_oauth"]
            creds = Credentials.from_authorized_user_info(oauth_info, SCOPES)
        except Exception as e:
            print(f"⚠️ Secrets found but failed to load: {e}")

    # 2. If no secrets, try local file (Best for Local Dev)
    elif os.path.exists('token.json'):
        print("💻 Loading credentials from local token.json...")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # 3. Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            print("🔄 Refreshing access token...")
            creds.refresh(Request())
        except Exception as e:
            print(f"❌ Failed to refresh token: {e}")
            return None

    # 4. If we still have no valid creds, we cannot run on Cloud
    if not creds or not creds.valid:
        print("❌ No valid credentials found. On Cloud, configure Secrets. Locally, run flow to generate token.json.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Failed to build Gmail service: {e}")
        return None

def send_email_google(to_email, subject, body, attachments=None):
    """
    Sends email via Official Google API (HTTPS).
    """
    service = get_gmail_service()
    if not service:
        print("❌ Email Service unavailable.")
        return False

    try:
        # Create Email Message
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        
        # Add Body
        msg = MIMEText(body)
        message.attach(msg)

        # Add Attachments
        if attachments:
            for filename, content, mime_type in attachments:
                part = MIMEApplication(content)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                message.attach(part)

        # Encode for Gmail API (base64url)
        raw_string = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw_string}

        # Send
        print(f"🚀 Sending via Google API to {to_email}...")
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"✅ Email Sent! Message Id: {sent_message['id']}")
        return True

    except Exception as e:
        print(f"❌ Google API Error: {e}")
        return False

# --- Wrapper for Dashboard Compatibility ---
def send_report_email_with_attachments(to_email, subject, body, attachments):
    return send_email_google(to_email, subject, body, attachments)

def send_alert(msg, channel='#alerts', to_email=None):
    if to_email:
        send_email_google(to_email, "FlashNarrative Alert", msg)