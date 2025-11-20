import os
import requests
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from slack_sdk import WebClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
SENDER_EMAIL = os.getenv('EMAIL_ADDRESS')
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
BREVO_API_KEY = os.getenv('BREVO_API_KEY')

def send_via_sendgrid(to_email, subject, body, attachments=None):
    """Attempts to send via SendGrid API."""
    if not SENDGRID_API_KEY: return False
    
    try:
        print(f"🚀 Attempting SendGrid to {to_email}...")
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=f"<p>{body}</p>"
        )

        if attachments:
            for filename, content_bytes, mime_type in attachments:
                encoded_file = base64.b64encode(content_bytes).decode()
                attachment = Attachment()
                attachment.file_content = FileContent(encoded_file)
                attachment.file_type = FileType(mime_type)
                attachment.file_name = FileName(filename)
                attachment.disposition = Disposition('attachment')
                message.add_attachment(attachment)

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ SendGrid Success! Status: {response.status_code}")
            return True
        return False
    except Exception as e:
        print(f"⚠️ SendGrid Failed: {e}")
        return False

def send_via_brevo(to_email, subject, body, attachments=None):
    """Attempts to send via Brevo (Sendinblue) API."""
    if not BREVO_API_KEY: return False

    try:
        print(f"🚀 Falling back to Brevo (HTTPS) for {to_email}...")
        url = "https://api.brevo.com/v3/smtp/email"
        
        # Prepare Attachments for Brevo
        brevo_attachments = []
        if attachments:
            for filename, content_bytes, mime_type in attachments:
                b64_content = base64.b64encode(content_bytes).decode()
                brevo_attachments.append({"content": b64_content, "name": filename})

        payload = {
            "sender": {"name": "FlashNarrative AI", "email": SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": f"<p>{body}</p>",
            "textContent": body
        }
        
        if brevo_attachments:
            payload["attachment"] = brevo_attachments

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Brevo Success! ID: {response.json().get('messageId')}")
            print(response.status_code, response.text)
            return True
        else:
            print(f"❌ Brevo Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Brevo Connection Error: {e}")
        return False

def send_email_smart(to_email, subject, body, attachments=None):
    """
    MASTER FUNCTION: Tries SendGrid, falls back to Brevo.
    """
    if not SENDER_EMAIL:
        print("❌ Missing EMAIL_ADDRESS in .env")
        return False

    # 1. Try SendGrid
    if send_via_sendgrid(to_email, subject, body, attachments):
        return True
    
    # 2. If SendGrid failed (or returned False), Try Brevo
    print("⚠️ Switching to Fallback Provider (Brevo)...")
    if send_via_brevo(to_email, subject, body, attachments):
        return True
        
    print("❌ All email providers failed.")
    return False

# --- WRAPPERS ---
def send_report_email_with_attachments(to_email, subject, body, attachments):
    return send_email_smart(to_email, subject, body, attachments)

def send_alert(msg, channel='#alerts', to_email=None):
    # Slack Alert Logic
    token = os.getenv('SLACK_TOKEN')
    if token:
        try:
            client = WebClient(token=token)
            client.chat_postMessage(channel=channel, text=msg)
            print("[Slack Alert Sent]")
            return
        except: pass

    # Email Alert Logic
    if to_email:
        send_email_smart(to_email, "FlashNarrative Alert", msg)
    else:
        print(f"[Alert] {msg}")

def create_servicenow_ticket(title, description, urgency='2', impact='2'):
    # Mock ticket creation
    print(f"[Mock Ticket] {title}")
    return "INC-MOCK-DUAL"