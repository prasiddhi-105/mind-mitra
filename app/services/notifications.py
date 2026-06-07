import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import httpx
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("notifications")


class NotificationService:
    """Service for sending notifications via SMS, email, and push"""
    
    def __init__(self):
        self.twilio_client = None
        self._initialize_twilio()
    
    def _initialize_twilio(self):
        """Initialize Twilio client for SMS"""
        try:
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                from twilio.rest import Client
                self.twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info("Twilio client initialized successfully")
            else:
                logger.warning("Twilio credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {e}")
    
    async def send_sms(self, to: str, message: str) -> bool:
        """Send SMS via Twilio"""
        try:
            if not self.twilio_client:
                logger.warning("Twilio client not available")
                return False
            
            if not settings.TWILIO_PHONE_NUMBER:
                logger.warning("Twilio phone number not configured")
                return False
            
            # Send SMS
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to
            )
            
            logger.info(f"SMS sent successfully: {message_obj.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    async def send_email(self, to: str, subject: str, message: str, html_message: Optional[str] = None) -> bool:
        """Send email via SMTP"""
        try:
            if not all([settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.SMTP_SERVER]):
                logger.warning("SMTP configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.SMTP_USERNAME
            msg['To'] = to
            
            # Add text and HTML parts
            text_part = MIMEText(message, 'plain')
            msg.attach(text_part)
            
            if html_message:
                html_part = MIMEText(html_message, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_push_notification(self, user_id: str, title: str, message: str, data: Optional[dict] = None) -> bool:
        """Send push notification via Firebase Cloud Messaging"""
        try:
            # This would integrate with Firebase Cloud Messaging
            # For now, just log the notification
            logger.info(f"Push notification for user {user_id}: {title} - {message}")
            
            # Placeholder for FCM integration
            # fcm_message = {
            #     "message": {
            #         "token": user_fcm_token,
            #         "notification": {
            #             "title": title,
            #             "body": message
            #         },
            #         "data": data or {}
            #     }
            # }
            # 
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         "https://fcm.googleapis.com/fcm/send",
            #         headers={"Authorization": f"key={settings.FIREBASE_SERVER_KEY}"},
            #         json=fcm_message
            #     )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False
    
    async def send_emergency_notification(self, user_name: str, severity: str, reason: Optional[str] = None) -> bool:
        """Send emergency notification template"""
        try:
            subject = f"URGENT: {user_name} Emergency Alert"
            
            message = f"""
            EMERGENCY ALERT
            
            User: {user_name}
            Severity: {severity}
            Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            
            """
            
            if reason:
                message += f"Reason: {reason}\n\n"
            
            message += """
            This is an automated emergency alert from MindMitra.
            Please check on this person immediately.
            
            If this is a life-threatening emergency, call emergency services immediately.
            """
            
            # This would be sent to emergency contacts
            logger.info(f"Emergency notification prepared for {user_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare emergency notification: {e}")
            return False
    
    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Send welcome email to new users"""
        try:
            subject = "Welcome to MindMitra - Your Mental Wellness Companion"
            
            html_message = f"""
            <html>
            <body>
                <h2>Welcome to MindMitra, {user_name}!</h2>
                <p>Thank you for joining our community of mental wellness support.</p>
                
                <h3>What you can do with MindMitra:</h3>
                <ul>
                    <li>Track your mood and emotions through journaling</li>
                    <li>Get AI-powered emotional support and guidance</li>
                    <li>Receive personalized CBT-based therapy sessions</li>
                    <li>Set up emergency contacts for crisis situations</li>
                    <li>Monitor your emotional patterns over time</li>
                </ul>
                
                <p>Your mental health matters, and we're here to support you every step of the way.</p>
                
                <p>Best regards,<br>The MindMitra Team</p>
            </body>
            </html>
            """
            
            return await self.send_email(
                to=user_email,
                subject=subject,
                message=f"Welcome to MindMitra, {user_name}!",
                html_message=html_message
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False
    
    async def send_password_reset_email(
        self, user_email: str, user_name: str, reset_link: str
    ) -> bool:
        """Send password reset link email."""
        try:
            subject = "MindMitra - Reset Your Password"
            expire_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    
            message = f"""
    Hi {user_name},
    
    We received a request to reset your MindMitra password.
    
    Reset your password by visiting this link (expires in {expire_minutes} minutes):
    {reset_link}
    
    If you did not request this, you can safely ignore this email.
    
    Best regards,
    The MindMitra Team
    """
    
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #1e293b;">
                <h2 style="color: #134e4a;">Reset Your Password</h2>
                <p>Hi {user_name},</p>
                <p>We received a request to reset your MindMitra password.</p>
                <p>
                    <a href="{reset_link}"
                       style="display: inline-block; padding: 12px 24px;
                              background-color: #134e4a;
                              color: #ffffff;
                              text-decoration: none;
                              border-radius: 8px;
                              font-weight: 600;">
                        Reset Password
                    </a>
                </p>
                <p style="color: #64748b; font-size: 14px;">
                    This link expires in {expire_minutes} minutes.
                    If you did not request a password reset, you can safely ignore this email.
                </p>
                <p>Best regards,<br>The MindMitra Team</p>
            </body>
            </html>
            """
    
            return await self.send_email(
                to=user_email,
                subject=subject,
                message=message,
                html_message=html_message,
            )
    
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False


    async def send_depression_threshold_user_email(
        self,
        user_email: str,
        user_name: str,
        flag_count: int,
        threshold: int,
        resources: List[str],
    ) -> bool:
        """Send a supportive check-in email when the depression flag threshold is reached."""
        try:
            subject = "MindMitra: We're here for you"
    
            resources_text = "\n".join(
                f"- {resource}" for resource in resources
            )
            resources_html = "".join(
                f"<li>{resource}</li>" for resource in resources
            )
    
            message = f"""Hi {user_name},
    
    We've noticed you've been going through a difficult stretch lately. Over the past day, MindMitra has recorded {flag_count} moments of emotional distress.
    
    Helpful resources:
    {resources_text}
    
    If you added emergency contacts in your profile, they have also been gently notified.
    
    With care,
    The MindMitra Team
    """
    
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4a6fa5;">We're here for you, {user_name}</h2>
                <p>We've noticed you've been going through a difficult stretch lately.</p>
                <p>MindMitra has recorded <strong>{flag_count}</strong> moments of emotional distress.</p>
    
                <h3 style="color: #4a6fa5;">Helpful resources</h3>
                <ul>{resources_html}</ul>
    
                <p>With care,<br><strong>The MindMitra Team</strong></p>
            </body>
            </html>
            """
    
            return await self.send_email(
                to=user_email,
                subject=subject,
                message=message,
                html_message=html_message,
            )
    
        except Exception as e:
            logger.error(
                f"Failed to send depression threshold user email: {e}"
            )
            return False


    async def send_depression_threshold_contact_email(
        self,
        contact_email: str,
        contact_name: str,
        user_name: str,
        flag_count: int,
        threshold: int,
        resources: List[str],
    ) -> bool:
        """Notify an emergency contact with a calm, supportive message."""
        try:
            subject = f"MindMitra: A gentle check-in about {user_name}"
    
            resources_text = "\n".join(
                f"- {resource}" for resource in resources
            )
            resources_html = "".join(
                f"<li>{resource}</li>" for resource in resources
            )
    
            message = f"""Hi {contact_name},
    
    {user_name}, who listed you as an emergency contact on MindMitra, may be going through a difficult time.
    
    Over the past day, our system has noticed {flag_count} signs of emotional distress (threshold: {threshold}).
    
    A simple message or call from you could mean a lot right now.
    
    Helpful resources:
    {resources_text}
    
    With care,
    The MindMitra Team
    """
    
            html_message = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4a6fa5;">A gentle check-in about {user_name}</h2>
                <p>Hi {contact_name},</p>
    
                <h3 style="color: #4a6fa5;">Helpful resources</h3>
                <ul>{resources_html}</ul>
    
                <p>With care,<br><strong>The MindMitra Team</strong></p>
            </body>
            </html>
            """
    
            return await self.send_email(
                to=contact_email,
                subject=subject,
                message=message,
                html_message=html_message,
            )
    
        except Exception as e:
            logger.error(
                f"Failed to send depression threshold contact email: {e}"
            )
            return False

    async def send_daily_reminder(self, user_email: str, user_name: str) -> bool:
        """Send daily journaling reminder"""
        try:
            subject = "MindMitra Daily Check-in Reminder"
            
            message = f"""
            Hi {user_name},
            
            It's time for your daily mental wellness check-in!
            
            Taking a few minutes to reflect on your day can help you:
            - Understand your emotional patterns
            - Identify triggers and coping strategies
            - Track your progress over time
            - Get personalized support when needed
            
            Open the MindMitra app and share how you're feeling today.
            
            Take care,
            The MindMitra Team
            """
            
            return await self.send_email(
                to=user_email,
                subject=subject,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Failed to send daily reminder: {e}")
            return False


# Global notification service instance
notification_service = NotificationService() 