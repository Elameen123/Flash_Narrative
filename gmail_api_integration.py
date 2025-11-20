import os.path
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: 'credentials.json' missing. Download it from Google Cloud Console.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Failed to build Gmail service: {e}")
        return None

def send_email_google(to_email, subject, body, attachments=None):
    """
    Sends email via Official Google API (HTTPS).
    Bypasses Port blocking AND DMARC issues.
    """
    service = get_gmail_service()
    if not service:
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
    else:
        print(f"[Alert] {msg}")