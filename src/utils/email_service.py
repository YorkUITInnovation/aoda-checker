"""Email notification service for scheduled scans."""
import logging
from typing import List, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from src.config import settings
from src.database.models import User

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str = None
    ):
        """Send an email using SMTP."""
        if not settings.smtp_host or not to_email:
            logger.warning("Email not configured or no recipient email")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Add text version (fallback)
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML version
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
                use_tls=settings.smtp_use_tls,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    async def send_scan_violation_notification(
        user: User,
        scan_id: str,
        start_url: str,
        total_violations: int,
        error_count: int,
        warning_count: int,
        pages_scanned: int
    ):
        """Send notification email when violations are found in a scheduled scan."""
        if not user.email:
            logger.warning(f"User {user.username} has no email address")
            return False

        # Generate HTML email
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #dc3545;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 20px;
            border: 1px solid #dee2e6;
        }}
        .violation-summary {{
            background-color: white;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #dc3545;
            border-radius: 3px;
        }}
        .stat {{
            margin: 10px 0;
            padding: 10px;
            background-color: #fff;
            border-radius: 3px;
        }}
        .stat-label {{
            font-weight: bold;
            color: #6c757d;
        }}
        .stat-value {{
            font-size: 1.2em;
            color: #dc3545;
            font-weight: bold;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }}
        .url {{
            color: #007bff;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Accessibility Violations Detected</h1>
        </div>
        <div class="content">
            <p>Hello {user.first_name or user.username},</p>
            
            <p>A scheduled accessibility scan has been completed for:</p>
            <p class="url"><strong>{start_url}</strong></p>
            
            <div class="violation-summary">
                <h3>Scan Summary</h3>
                
                <div class="stat">
                    <span class="stat-label">Total Violations:</span>
                    <span class="stat-value">{total_violations}</span>
                </div>
                
                <div class="stat">
                    <span class="stat-label">Errors:</span>
                    <span class="stat-value">{error_count}</span>
                </div>
                
                <div class="stat">
                    <span class="stat-label">Warnings:</span>
                    <span class="stat-value">{warning_count}</span>
                </div>
                
                <div class="stat">
                    <span class="stat-label">Pages Scanned:</span>
                    <span class="stat-value">{pages_scanned}</span>
                </div>
            </div>
            
            <p>Please review the scan results to address these accessibility issues.</p>
            
            <center>
                <a href="{settings.app_url}/results/{scan_id}" class="button">
                    View Full Report
                </a>
            </center>
            
            <p style="margin-top: 20px; font-size: 0.9em; color: #6c757d;">
                <strong>Note:</strong> This is an automated notification from your scheduled scan.
                You can manage your scheduled scans and notification preferences in your scan history.
            </p>
        </div>
        <div class="footer">
            <p>This email was sent by {settings.app_name}</p>
            <p>If you no longer wish to receive these notifications, you can disable them in your scheduled scan settings.</p>
        </div>
    </div>
</body>
</html>
"""

        # Generate text version
        text_content = f"""
Accessibility Violations Detected

Hello {user.first_name or user.username},

A scheduled accessibility scan has been completed for: {start_url}

Scan Summary:
- Total Violations: {total_violations}
- Errors: {error_count}
- Warnings: {warning_count}
- Pages Scanned: {pages_scanned}

Please review the scan results to address these accessibility issues.

View the full report at: {settings.app_url}/results/{scan_id}

Note: This is an automated notification from your scheduled scan.
You can manage your scheduled scans and notification preferences in your scan history.

---
This email was sent by {settings.app_name}
If you no longer wish to receive these notifications, you can disable them in your scheduled scan settings.
"""

        subject = f"⚠️ Accessibility Violations Found - {start_url}"

        return await EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_scan_completion_notification(
        user: User,
        scan_id: str,
        start_url: str,
        pages_scanned: int,
        scan_status: str
    ):
        """Send notification email when a scheduled scan completes successfully with no violations."""
        if not user.email:
            logger.warning(f"User {user.username} has no email address")
            return False

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #28a745;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f8f9fa;
            padding: 20px;
            border: 1px solid #dee2e6;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }}
        .url {{
            color: #007bff;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Scan Completed Successfully</h1>
        </div>
        <div class="content">
            <p>Hello {user.first_name or user.username},</p>
            
            <p>A scheduled accessibility scan has been completed for:</p>
            <p class="url"><strong>{start_url}</strong></p>
            
            <p>Pages Scanned: <strong>{pages_scanned}</strong></p>
            <p>Status: <strong>{scan_status}</strong></p>
            
            <center>
                <a href="{settings.app_url}/results/{scan_id}" style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 15px 0;">
                    View Full Report
                </a>
            </center>
        </div>
        <div class="footer">
            <p>This email was sent by {settings.app_name}</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Scan Completed Successfully

Hello {user.first_name or user.username},

A scheduled accessibility scan has been completed for: {start_url}

Pages Scanned: {pages_scanned}
Status: {scan_status}

---
This email was sent by {settings.app_name}
"""

        subject = f"✅ Scan Completed - {start_url}"

        return await EmailService.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

