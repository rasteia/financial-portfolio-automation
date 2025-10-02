"""
Email notification provider supporting SMTP and cloud email services.
"""

import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..exceptions import PortfolioAutomationError


@dataclass
class EmailConfig:
    """Configuration for email provider."""
    smtp_server: str
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    from_address: str = ""
    from_name: str = "Portfolio Automation"
    timeout: int = 30


class EmailError(PortfolioAutomationError):
    """Exception raised for email-related errors."""
    pass


class EmailProvider:
    """
    Email notification provider that supports SMTP and various email services.
    """
    
    def __init__(self, config: EmailConfig):
        """
        Initialize the email provider.
        
        Args:
            config: Email configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate email configuration."""
        if not self.config.smtp_server:
            raise EmailError("SMTP server is required")
        
        if not self.config.from_address:
            raise EmailError("From address is required")
        
        if self.config.use_ssl and self.config.use_tls:
            raise EmailError("Cannot use both SSL and TLS")
        
        if self.config.use_ssl and self.config.smtp_port == 587:
            self.logger.warning("SSL typically uses port 465, not 587")
    
    async def send_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            body: Email body content
            metadata: Additional metadata (can include html_body, attachments, etc.)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Validate recipients
            if not recipients:
                self.logger.error("No recipients provided")
                return False
            
            # Filter valid email addresses
            valid_recipients = [email for email in recipients if self._is_valid_email(email)]
            if not valid_recipients:
                self.logger.error("No valid email addresses found")
                return False
            
            # Create message
            message = self._create_message(
                recipients=valid_recipients,
                subject=subject,
                body=body,
                metadata=metadata or {}
            )
            
            # Send email in executor to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._send_email_sync,
                message,
                valid_recipients
            )
            
            if success:
                self.logger.info(f"Email sent successfully to {len(valid_recipients)} recipients")
            else:
                self.logger.error("Failed to send email")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return False
    
    def _create_message(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        metadata: Dict[str, Any]
    ) -> MIMEMultipart:
        """Create email message."""
        message = MIMEMultipart('alternative')
        
        # Set headers
        message['From'] = f"{self.config.from_name} <{self.config.from_address}>"
        message['To'] = ', '.join(recipients)
        message['Subject'] = subject
        
        # Add custom headers from metadata
        if 'headers' in metadata:
            for key, value in metadata['headers'].items():
                message[key] = value
        
        # Add text body
        text_part = MIMEText(body, 'plain', 'utf-8')
        message.attach(text_part)
        
        # Add HTML body if provided
        if 'html_body' in metadata:
            html_part = MIMEText(metadata['html_body'], 'html', 'utf-8')
            message.attach(html_part)
        
        return message
    
    def _send_email_sync(self, message: MIMEMultipart, recipients: List[str]) -> bool:
        """Send email synchronously (runs in executor)."""
        try:
            # Create SMTP connection
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
                
                if self.config.use_tls:
                    server.starttls()
            
            # Authenticate if credentials provided
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            
            # Send email
            server.send_message(message, to_addrs=recipients)
            server.quit()
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            self.logger.error(f"Recipients refused: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            self.logger.error(f"SMTP server disconnected: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        if not email or '@' not in email:
            return False
        
        parts = email.split('@')
        if len(parts) != 2:
            return False
        
        local, domain = parts
        if not local or not domain or '.' not in domain:
            return False
        
        return True
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "email"
    
    def is_available(self) -> bool:
        """Check if the email provider is available."""
        try:
            # Basic connectivity test
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=5
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=5
                )
            
            server.noop()  # Send no-op command
            server.quit()
            return True
            
        except Exception as e:
            self.logger.debug(f"Email provider availability check failed: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test email connection and return detailed results."""
        result = {
            'success': False,
            'error': None,
            'server_info': {},
            'auth_success': False
        }
        
        try:
            # Test connection
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    timeout=self.config.timeout
                )
                
                if self.config.use_tls:
                    server.starttls()
            
            # Get server info
            result['server_info'] = {
                'server': self.config.smtp_server,
                'port': self.config.smtp_port,
                'use_tls': self.config.use_tls,
                'use_ssl': self.config.use_ssl
            }
            
            # Test authentication if credentials provided
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
                result['auth_success'] = True
            
            server.quit()
            result['success'] = True
            
        except smtplib.SMTPAuthenticationError as e:
            result['error'] = f"Authentication failed: {e}"
        except smtplib.SMTPConnectError as e:
            result['error'] = f"Connection failed: {e}"
        except Exception as e:
            result['error'] = f"Unexpected error: {e}"
        
        return result
    
    def create_html_body(self, text_body: str, alert_data: Optional[Dict[str, Any]] = None) -> str:
        """Create HTML version of email body."""
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            ".alert-header { background-color: #f8f9fa; padding: 10px; border-left: 4px solid #007bff; }",
            ".alert-critical { border-left-color: #dc3545; }",
            ".alert-warning { border-left-color: #ffc107; }",
            ".alert-info { border-left-color: #17a2b8; }",
            ".alert-details { margin-top: 15px; }",
            ".detail-item { margin: 5px 0; }",
            ".timestamp { color: #6c757d; font-size: 0.9em; }",
            "</style>",
            "</head>",
            "<body>"
        ]
        
        # Add alert header if alert data provided
        if alert_data:
            severity = alert_data.get('severity', 'info')
            alert_class = f"alert-header alert-{severity}"
            html_lines.extend([
                f'<div class="{alert_class}">',
                f'<h3>Portfolio Alert: {alert_data.get("alert_type", "Unknown")}</h3>',
                '</div>'
            ])
        
        # Convert text body to HTML
        html_body = text_body.replace('\n', '<br>')
        html_lines.append(f'<div class="alert-details">{html_body}</div>')
        
        # Add timestamp
        html_lines.extend([
            '<div class="timestamp">',
            f'Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '</div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_lines)