import logging
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import os
from config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER, MAIL_PORT

logger = logging.getLogger(__name__)

# Only configure FastMail if credentials exist (avoids crashing if missing)
conf = None
if MAIL_USERNAME and MAIL_PASSWORD:
    conf = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )
    fm = FastMail(conf)
else:
    logger.warning("[Mailer] Mail credentials not set. Emails will be mocked in logs.")
    fm = None

async def send_welcome_email(to_email: str):
    """Send a welcome email to new users after signup."""
    subject = "Welcome to SecureShield! 🛡️"
    
    html_content = f"""
    <html>
      <body style="font-family: 'Inter', sans-serif; color: #1E293B; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Welcome to SecureShield!</h2>
        <p>Hello,</p>
        <p>Thank you for signing up for SecureShield! You can now use our GenAI-powered engine to check your health insurance eligibility against IRDAI regulations instantly.</p>
        <div style="background-color: #EEF2FF; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <h4 style="margin-top: 0; color: #4338CA;">Get Started:</h4>
          <ol style="margin-bottom: 0;">
            <li>Upload your insurance policy PDF</li>
            <li>Run an eligibility check for any medical procedure</li>
            <li>Generate an official Grievance Package if your claim is unfairly denied</li>
          </ol>
        </div>
        <p>Stay protected,<br><strong>The SecureShield Team</strong></p>
      </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=html_content,
        subtype=MessageType.html
    )

    if fm:
        try:
            await fm.send_message(message)
            logger.info(f"[Mailer] Welcome email sent to {to_email}")
        except Exception as e:
            logger.error(f"[Mailer] Failed to send welcome email: {e}")
    else:
        logger.info(f"[Mailer Mock] Sending Welcome Email to {to_email}")


async def send_grievance_email(to_email: str, pdf_path: str):
    """Send the generated grievance PDF to the user."""
    subject = "Your SecureShield Grievance Package is Ready 🛡️"
    
    html_content = f"""
    <html>
      <body style="font-family: 'Inter', sans-serif; color: #1E293B; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4F46E5;">Your Grievance Package is Ready</h2>
        <p>Hello,</p>
        <p>The SecureShield Grievance Agent has successfully generated your official grievance report.</p>
        <p>This document includes a detailed analysis of your policy rules, IRDAI precedent rulings, and a formal letter drafted to your insurer.</p>
        <p><strong>Please find the PDF report attached to this email.</strong></p>
        <p>If you have any questions, you can ask the SecureShield AI Assistant from your dashboard.</p>
        <br/>
        <p>Stay protected,<br><strong>The SecureShield Team</strong></p>
      </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=html_content,
        subtype=MessageType.html,
        attachments=[pdf_path] if os.path.exists(pdf_path) else None
    )

    if fm:
        try:
            await fm.send_message(message)
            logger.info(f"[Mailer] Grievance package sent to {to_email}")
        except Exception as e:
            logger.error(f"[Mailer] Failed to send grievance package: {e}")
    else:
        logger.info(f"[Mailer Mock] Sending Grievance Email to {to_email} with attachment {pdf_path}")
