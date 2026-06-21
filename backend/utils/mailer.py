"""
PolicyEye — Email Service (Resend)
Uses the Resend HTTP API instead of SMTP, which works on Hugging Face Spaces
(HF blocks all outbound SMTP ports 25/465/587).
"""

import logging
import os
import base64
from typing import Optional

import resend
from core.config import RESEND_API_KEY, MAIL_FROM

logger = logging.getLogger(__name__)

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("[Mailer] Resend API configured successfully.")
else:
    logger.warning("[Mailer] RESEND_API_KEY not set. Emails will be mocked in logs.")


def _build_welcome_html(to_email: str) -> str:
    """Build a professional, spam-filter-friendly welcome email."""
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Welcome to PolicyEye</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f4f5; font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5; padding:40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e1b4b,#3b82f6); padding:32px 40px; text-align:center;">
              <h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700; letter-spacing:-0.5px;">PolicyEye</h1>
              <p style="margin:8px 0 0; color:rgba(255,255,255,0.85); font-size:13px;">AI-Powered Insurance Eligibility Engine</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <h2 style="margin:0 0 16px; color:#1e293b; font-size:20px; font-weight:600;">Welcome aboard! 🎉</h2>
              <p style="margin:0 0 12px; color:#475569; font-size:15px; line-height:1.6;">
                Your PolicyEye account has been successfully verified.
              </p>
              <p style="margin:0 0 12px; color:#475569; font-size:15px; line-height:1.6;">
                You can now upload your health insurance policy documents and check claim eligibility using our AI-powered engine with zero-hallucination verdicts.
              </p>
              <p style="margin:0 0 24px; color:#475569; font-size:15px; line-height:1.6;">
                Our system uses 5 specialized agents and 18 custom tools, all compliant with IRDAI 2024 regulations.
              </p>
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#3b82f6; border-radius:8px;">
                    <a href="https://policyeye.app" target="_blank" style="display:inline-block; padding:12px 28px; color:#ffffff; font-size:14px; font-weight:600; text-decoration:none;">
                      Go to Dashboard →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px; background-color:#f8fafc; border-top:1px solid #e2e8f0;">
              <p style="margin:0; color:#94a3b8; font-size:12px; line-height:1.5;">
                This email was sent by PolicyEye because you created an account at
                <a href="https://policyeye.app" style="color:#3b82f6; text-decoration:none;">policyeye.app</a>.
                If you did not create this account, please ignore this email.
              </p>
              <p style="margin:8px 0 0; color:#94a3b8; font-size:12px;">
                © 2026 PolicyEye. Built with transparency in mind.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_grievance_html() -> str:
    """Build a professional grievance notification email."""
    return """\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light" />
  <meta name="supported-color-schemes" content="light" />
  <title>Your Grievance Report — PolicyEye</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f4f5; font-family:'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5; padding:40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e1b4b,#3b82f6); padding:32px 40px; text-align:center;">
              <h1 style="margin:0; color:#ffffff; font-size:24px; font-weight:700; letter-spacing:-0.5px;">PolicyEye</h1>
              <p style="margin:8px 0 0; color:rgba(255,255,255,0.85); font-size:13px;">AI-Powered Insurance Eligibility Engine</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <h2 style="margin:0 0 16px; color:#1e293b; font-size:20px; font-weight:600;">Your Grievance Report is Ready 📋</h2>
              <p style="margin:0 0 12px; color:#475569; font-size:15px; line-height:1.6;">
                The PolicyEye Grievance Agent has completed its analysis of your claim and generated an official grievance report.
              </p>
              <p style="margin:0 0 12px; color:#475569; font-size:15px; line-height:1.6;">
                The attached PDF includes:
              </p>
              <ul style="margin:0 0 16px; padding-left:20px; color:#475569; font-size:15px; line-height:1.8;">
                <li>Detailed breakdown of your policy rules</li>
                <li>IRDAI regulatory compliance analysis</li>
                <li>Precedent rulings from the Insurance Ombudsman</li>
                <li>A formal grievance letter addressed to your insurer</li>
              </ul>
              <p style="margin:0 0 24px; color:#475569; font-size:15px; line-height:1.6;">
                <strong>Please find the PDF report attached to this email.</strong>
                You may forward this email directly to your insurer's Grievance Redressal Officer.
              </p>
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#3b82f6; border-radius:8px;">
                    <a href="https://policyeye.app" target="_blank" style="display:inline-block; padding:12px 28px; color:#ffffff; font-size:14px; font-weight:600; text-decoration:none;">
                      View on Dashboard →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px; background-color:#f8fafc; border-top:1px solid #e2e8f0;">
              <p style="margin:0; color:#94a3b8; font-size:12px; line-height:1.5;">
                This grievance report was generated by PolicyEye's AI Grievance Agent.
                It is provided for informational purposes and does not constitute legal advice.
              </p>
              <p style="margin:8px 0 0; color:#94a3b8; font-size:12px;">
                © 2026 PolicyEye. Built with transparency in mind.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def send_welcome_email(to_email: str):
    """Send a welcome email to new users after signup."""
    if not RESEND_API_KEY:
        logger.info(f"[Mailer Mock] Welcome email → {to_email}")
        return

    try:
        params: resend.Emails.SendParams = {
            "from": MAIL_FROM,
            "to": [to_email],
            "subject": "Welcome to PolicyEye — Account Verified ✓",
            "html": _build_welcome_html(to_email),
            "headers": {
                "X-Entity-Ref-ID": f"welcome-{to_email}",
            },
            "tags": [
                {"name": "category", "value": "welcome"},
                {"name": "app", "value": "policyeye"},
            ],
        }
        email_resp = resend.Emails.send(params)
        logger.info(f"[Mailer] Welcome email sent to {to_email} (id: {email_resp.get('id', 'n/a')})")
    except Exception as e:
        logger.error(f"[Mailer] Failed to send welcome email: {e}")


async def send_grievance_email(to_email: str, pdf_path: str, cc_email: str = None):
    """Send the generated grievance PDF to the user and optionally CC the insurer."""
    if not RESEND_API_KEY:
        logger.info(f"[Mailer Mock] Grievance email → {to_email} (attachment: {pdf_path})")
        return

    try:
        # Read and encode the PDF attachment
        attachments = []
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            attachments.append({
                "filename": os.path.basename(pdf_path),
                "content": list(pdf_data),
            })

        params: resend.Emails.SendParams = {
            "from": MAIL_FROM,
            "to": [to_email],
            "subject": "Your PolicyEye Grievance Report is Ready 📋",
            "html": _build_grievance_html(),
            "headers": {
                "X-Entity-Ref-ID": f"grievance-{to_email}",
            },
            "tags": [
                {"name": "category", "value": "grievance"},
                {"name": "app", "value": "policyeye"},
            ],
        }

        if cc_email:
            params["cc"] = [cc_email]

        if attachments:
            params["attachments"] = attachments

        email_resp = resend.Emails.send(params)
        logger.info(f"[Mailer] Grievance package sent to {to_email} (id: {email_resp.get('id', 'n/a')})")
    except Exception as e:
        logger.error(f"[Mailer] Failed to send grievance package: {e}")
