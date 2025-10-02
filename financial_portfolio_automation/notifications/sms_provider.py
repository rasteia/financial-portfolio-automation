"""
SMS notification provider supporting Twilio and other SMS services.
"""

import asyncio
import logging
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..exceptions import PortfolioAutomationError


@dataclass
class SMSConfig:
    """Configuration for SMS provider."""
    provider: str = "twilio"  # twilio, aws_sns, etc.
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""
    region: str = "us-east-1"  # For AWS SNS
    max_message_length: int = 160


class SMSError(PortfolioAutomationError):
    """Exception raised for SMS-related errors."""
    pass


class SMSProvider:
    """
    SMS notification provider that supports multiple SMS services.
    """
    
    def __init__(self, config: SMSConfig):
        """
        Initialize the SMS provider.
        
        Args:
            config: SMS configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._client = None
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate SMS configuration."""
        if not self.config.provider:
            raise SMSError("SMS provider is required")
        
        if self.config.provider == "twilio":
            if not self.config.account_sid or not self.config.auth_token:
                raise SMSError("Twilio account SID and auth token are required")
            if not self.config.from_number:
                raise SMSError("From number is required for Twilio")
        
        elif self.config.provider == "aws_sns":
            # AWS credentials should be configured via environment or IAM roles
            pass
        
        else:
            raise SMSError(f"Unsupported SMS provider: {self.config.provider}")
    
    def _get_client(self):
        """Get or create SMS client."""
        if self._client is None:
            if self.config.provider == "twilio":
                self._client = self._create_twilio_client()
            elif self.config.provider == "aws_sns":
                self._client = self._create_aws_sns_client()
        
        return self._client
    
    def _create_twilio_client(self):
        """Create Twilio client."""
        try:
            from twilio.rest import Client
            return Client(self.config.account_sid, self.config.auth_token)
        except ImportError:
            raise SMSError("Twilio library not installed. Install with: pip install twilio")
        except Exception as e:
            raise SMSError(f"Failed to create Twilio client: {e}")
    
    def _create_aws_sns_client(self):
        """Create AWS SNS client."""
        try:
            import boto3
            return boto3.client('sns', region_name=self.config.region)
        except ImportError:
            raise SMSError("AWS boto3 library not installed. Install with: pip install boto3")
        except Exception as e:
            raise SMSError(f"Failed to create AWS SNS client: {e}")
    
    async def send_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an SMS notification.
        
        Args:
            recipients: List of phone numbers
            subject: Message subject (may be included in body for SMS)
            body: Message body content
            metadata: Additional metadata
            
        Returns:
            True if SMS was sent successfully, False otherwise
        """
        try:
            # Validate recipients
            if not recipients:
                self.logger.error("No recipients provided")
                return False
            
            # Filter valid phone numbers
            valid_recipients = [phone for phone in recipients if self._is_valid_phone(phone)]
            if not valid_recipients:
                self.logger.error("No valid phone numbers found")
                return False
            
            # Prepare message content
            message_content = self._prepare_message_content(subject, body, metadata or {})
            
            # Send SMS in executor to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._send_sms_sync,
                valid_recipients,
                message_content
            )
            
            if success:
                self.logger.info(f"SMS sent successfully to {len(valid_recipients)} recipients")
            else:
                self.logger.error("Failed to send SMS")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending SMS notification: {e}")
            return False
    
    def _prepare_message_content(
        self,
        subject: str,
        body: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Prepare SMS message content."""
        # For SMS, combine subject and body
        if subject and body:
            content = f"{subject}: {body}"
        elif subject:
            content = subject
        else:
            content = body
        
        # Truncate if too long
        if len(content) > self.config.max_message_length:
            content = content[:self.config.max_message_length - 3] + "..."
            self.logger.warning(f"SMS message truncated to {self.config.max_message_length} characters")
        
        return content
    
    def _send_sms_sync(self, recipients: List[str], message: str) -> bool:
        """Send SMS synchronously (runs in executor)."""
        try:
            client = self._get_client()
            success_count = 0
            
            for recipient in recipients:
                try:
                    if self.config.provider == "twilio":
                        success = self._send_twilio_sms(client, recipient, message)
                    elif self.config.provider == "aws_sns":
                        success = self._send_aws_sns_sms(client, recipient, message)
                    else:
                        success = False
                    
                    if success:
                        success_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error sending SMS to {recipient}: {e}")
            
            return success_count == len(recipients)
            
        except Exception as e:
            self.logger.error(f"Unexpected error sending SMS: {e}")
            return False
    
    def _send_twilio_sms(self, client, recipient: str, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            message_obj = client.messages.create(
                body=message,
                from_=self.config.from_number,
                to=recipient
            )
            
            self.logger.debug(f"Twilio SMS sent: {message_obj.sid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Twilio SMS error for {recipient}: {e}")
            return False
    
    def _send_aws_sns_sms(self, client, recipient: str, message: str) -> bool:
        """Send SMS via AWS SNS."""
        try:
            response = client.publish(
                PhoneNumber=recipient,
                Message=message
            )
            
            self.logger.debug(f"AWS SNS SMS sent: {response['MessageId']}")
            return True
            
        except Exception as e:
            self.logger.error(f"AWS SNS SMS error for {recipient}: {e}")
            return False
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Basic phone number validation."""
        if not phone:
            return False
        
        # Remove common formatting characters
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Check for valid international format
        if cleaned.startswith('+'):
            # International format: +1234567890 (10-15 digits after +)
            return len(cleaned) >= 11 and len(cleaned) <= 16
        else:
            # Assume US format: 1234567890 (10 digits)
            return len(cleaned) == 10 or (len(cleaned) == 11 and cleaned.startswith('1'))
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format."""
        # Remove formatting characters
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Add + if not present and assume US number
        if not cleaned.startswith('+'):
            if len(cleaned) == 10:
                cleaned = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                cleaned = '+' + cleaned
        
        return cleaned
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "sms"
    
    def is_available(self) -> bool:
        """Check if the SMS provider is available."""
        try:
            client = self._get_client()
            
            if self.config.provider == "twilio":
                # Test Twilio connection
                account = client.api.accounts(self.config.account_sid).fetch()
                return account.status == 'active'
            
            elif self.config.provider == "aws_sns":
                # Test AWS SNS connection
                client.get_sms_attributes()
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"SMS provider availability check failed: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SMS connection and return detailed results."""
        result = {
            'success': False,
            'error': None,
            'provider_info': {},
            'account_info': {}
        }
        
        try:
            client = self._get_client()
            
            result['provider_info'] = {
                'provider': self.config.provider,
                'from_number': self.config.from_number
            }
            
            if self.config.provider == "twilio":
                # Get Twilio account info
                account = client.api.accounts(self.config.account_sid).fetch()
                result['account_info'] = {
                    'status': account.status,
                    'type': account.type,
                    'friendly_name': account.friendly_name
                }
                result['success'] = account.status == 'active'
                
            elif self.config.provider == "aws_sns":
                # Get AWS SNS info
                attrs = client.get_sms_attributes()
                result['account_info'] = attrs.get('attributes', {})
                result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def format_alert_message(self, alert_type: str, symbol: str, message: str) -> str:
        """Format alert message for SMS."""
        # Keep SMS messages concise
        if symbol:
            formatted = f"ALERT {symbol}: {message}"
        else:
            formatted = f"ALERT: {message}"
        
        # Truncate if needed
        if len(formatted) > self.config.max_message_length:
            formatted = formatted[:self.config.max_message_length - 3] + "..."
        
        return formatted