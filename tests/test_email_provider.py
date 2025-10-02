"""
Unit tests for the EmailProvider class.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import smtplib
from email.mime.multipart import MIMEMultipart

from financial_portfolio_automation.notifications.email_provider import (
    EmailProvider, EmailConfig, EmailError
)


@pytest.fixture
def email_config():
    """Create test email configuration."""
    return EmailConfig(
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="test@example.com",
        password="test_password",
        use_tls=True,
        from_address="test@example.com",
        from_name="Test Portfolio"
    )


@pytest.fixture
def email_provider(email_config):
    """Create an EmailProvider instance for testing."""
    return EmailProvider(config=email_config)


class TestEmailProvider:
    """Test cases for EmailProvider class."""
    
    def test_initialization(self, email_provider):
        """Test EmailProvider initialization."""
        assert email_provider.config.smtp_server == "smtp.example.com"
        assert email_provider.config.smtp_port == 587
        assert email_provider.config.use_tls is True
        assert email_provider.config.from_address == "test@example.com"
    
    def test_invalid_config_no_smtp_server(self):
        """Test initialization with invalid config - no SMTP server."""
        config = EmailConfig(
            smtp_server="",
            from_address="test@example.com"
        )
        
        with pytest.raises(EmailError, match="SMTP server is required"):
            EmailProvider(config)
    
    def test_invalid_config_no_from_address(self):
        """Test initialization with invalid config - no from address."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            from_address=""
        )
        
        with pytest.raises(EmailError, match="From address is required"):
            EmailProvider(config)
    
    def test_invalid_config_ssl_and_tls(self):
        """Test initialization with invalid config - both SSL and TLS."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            from_address="test@example.com",
            use_ssl=True,
            use_tls=True
        )
        
        with pytest.raises(EmailError, match="Cannot use both SSL and TLS"):
            EmailProvider(config)
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, email_provider):
        """Test successful email sending."""
        with patch('smtplib.SMTP') as mock_smtp:
            # Set up mock SMTP server
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await email_provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is True
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_no_recipients(self, email_provider):
        """Test email sending with no recipients."""
        result = await email_provider.send_notification(
            recipients=[],
            subject="Test Subject",
            body="Test Body"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_invalid_recipients(self, email_provider):
        """Test email sending with invalid recipients."""
        result = await email_provider.send_notification(
            recipients=["invalid_email", "another_invalid"],
            subject="Test Subject",
            body="Test Body"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_mixed_recipients(self, email_provider):
        """Test email sending with mixed valid/invalid recipients."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await email_provider.send_notification(
                recipients=["valid@example.com", "invalid_email", "another@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is True
            # Should only send to valid emails
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_with_html(self, email_provider):
        """Test email sending with HTML body."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            metadata = {
                'html_body': '<html><body><h1>Test HTML</h1></body></html>'
            }
            
            result = await email_provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body",
                metadata=metadata
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_smtp_auth_error(self, email_provider):
        """Test email sending with SMTP authentication error."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
            mock_smtp.return_value = mock_server
            
            result = await email_provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_recipients_refused(self, email_provider):
        """Test email sending with recipients refused error."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused({})
            mock_smtp.return_value = mock_server
            
            result = await email_provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_server_disconnected(self, email_provider):
        """Test email sending with server disconnected error."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.send_message.side_effect = smtplib.SMTPServerDisconnected("Connection lost")
            mock_smtp.return_value = mock_server
            
            result = await email_provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_ssl_config(self):
        """Test email sending with SSL configuration."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=465,
            use_ssl=True,
            from_address="test@example.com"
        )
        provider = EmailProvider(config)
        
        with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
            mock_server = MagicMock()
            mock_smtp_ssl.return_value = mock_server
            
            result = await provider.send_notification(
                recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body"
            )
            
            assert result is True
            mock_smtp_ssl.assert_called_once()
            mock_server.starttls.assert_not_called()  # SSL doesn't use STARTTLS
    
    def test_is_valid_email(self, email_provider):
        """Test email validation."""
        # Valid emails
        assert email_provider._is_valid_email("test@example.com") is True
        assert email_provider._is_valid_email("user.name@domain.co.uk") is True
        assert email_provider._is_valid_email("test+tag@example.org") is True
        
        # Invalid emails
        assert email_provider._is_valid_email("") is False
        assert email_provider._is_valid_email("invalid") is False
        assert email_provider._is_valid_email("@example.com") is False
        assert email_provider._is_valid_email("test@") is False
        assert email_provider._is_valid_email("test@domain") is False
        assert email_provider._is_valid_email("test@@example.com") is False
    
    def test_create_message(self, email_provider):
        """Test email message creation."""
        recipients = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test Body"
        metadata = {"custom_header": "custom_value"}
        
        message = email_provider._create_message(recipients, subject, body, metadata)
        
        assert isinstance(message, MIMEMultipart)
        assert message['Subject'] == subject
        assert message['To'] == "recipient@example.com"
        assert "Test Portfolio <test@example.com>" in message['From']
    
    def test_create_message_with_html(self, email_provider):
        """Test email message creation with HTML body."""
        recipients = ["recipient@example.com"]
        subject = "Test Subject"
        body = "Test Body"
        metadata = {
            "html_body": "<html><body><h1>Test HTML</h1></body></html>",
            "headers": {"X-Custom-Header": "custom_value"}
        }
        
        message = email_provider._create_message(recipients, subject, body, metadata)
        
        assert isinstance(message, MIMEMultipart)
        assert message['X-Custom-Header'] == "custom_value"
        # Should have both text and HTML parts
        assert len(message.get_payload()) == 2
    
    def test_is_available_success(self, email_provider):
        """Test availability check success."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = email_provider.is_available()
            
            assert result is True
            mock_server.noop.assert_called_once()
            mock_server.quit.assert_called_once()
    
    def test_is_available_failure(self, email_provider):
        """Test availability check failure."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("Connection failed")
            
            result = email_provider.is_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, email_provider):
        """Test connection test success."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await email_provider.test_connection()
            
            assert result['success'] is True
            assert result['auth_success'] is True
            assert 'server_info' in result
            assert result['server_info']['server'] == "smtp.example.com"
    
    @pytest.mark.asyncio
    async def test_test_connection_auth_failure(self, email_provider):
        """Test connection test with authentication failure."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
            mock_smtp.return_value = mock_server
            
            result = await email_provider.test_connection()
            
            assert result['success'] is False
            assert "Authentication failed" in result['error']
    
    @pytest.mark.asyncio
    async def test_test_connection_connect_failure(self, email_provider):
        """Test connection test with connection failure."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Service not available")
            
            result = await email_provider.test_connection()
            
            assert result['success'] is False
            assert "Connection failed" in result['error']
    
    def test_get_provider_name(self, email_provider):
        """Test provider name."""
        assert email_provider.get_provider_name() == "email"
    
    def test_create_html_body(self, email_provider):
        """Test HTML body creation."""
        text_body = "This is a test alert\nWith multiple lines"
        alert_data = {
            'severity': 'critical',
            'alert_type': 'price_movement',
            'symbol': 'AAPL'
        }
        
        html_body = email_provider.create_html_body(text_body, alert_data)
        
        assert '<html>' in html_body
        assert '<body>' in html_body
        assert 'alert-critical' in html_body
        assert 'price_movement' in html_body
        assert 'This is a test alert<br>With multiple lines' in html_body
    
    def test_create_html_body_no_alert_data(self, email_provider):
        """Test HTML body creation without alert data."""
        text_body = "Simple text body"
        
        html_body = email_provider.create_html_body(text_body)
        
        assert '<html>' in html_body
        assert '<body>' in html_body
        assert 'Simple text body' in html_body
        assert 'alert-header' not in html_body


class TestEmailConfig:
    """Test cases for EmailConfig class."""
    
    def test_default_config(self):
        """Test default email configuration."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            from_address="test@example.com"
        )
        
        assert config.smtp_server == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.use_tls is True
        assert config.use_ssl is False
        assert config.from_address == "test@example.com"
        assert config.from_name == "Portfolio Automation"
        assert config.timeout == 30
    
    def test_custom_config(self):
        """Test custom email configuration."""
        config = EmailConfig(
            smtp_server="mail.example.com",
            smtp_port=465,
            username="user@example.com",
            password="secret",
            use_tls=False,
            use_ssl=True,
            from_address="sender@example.com",
            from_name="Custom Sender",
            timeout=60
        )
        
        assert config.smtp_server == "mail.example.com"
        assert config.smtp_port == 465
        assert config.username == "user@example.com"
        assert config.password == "secret"
        assert config.use_tls is False
        assert config.use_ssl is True
        assert config.from_address == "sender@example.com"
        assert config.from_name == "Custom Sender"
        assert config.timeout == 60