"""
Unit tests for the SMSProvider class.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from financial_portfolio_automation.notifications.sms_provider import (
    SMSProvider, SMSConfig, SMSError
)


@pytest.fixture
def twilio_config():
    """Create test Twilio SMS configuration."""
    return SMSConfig(
        provider="twilio",
        account_sid="test_account_sid",
        auth_token="test_auth_token",
        from_number="+1234567890"
    )


@pytest.fixture
def aws_sns_config():
    """Create test AWS SNS configuration."""
    return SMSConfig(
        provider="aws_sns",
        region="us-east-1"
    )


@pytest.fixture
def twilio_sms_provider(twilio_config):
    """Create a Twilio SMSProvider instance for testing."""
    return SMSProvider(config=twilio_config)


@pytest.fixture
def aws_sms_provider(aws_sns_config):
    """Create an AWS SNS SMSProvider instance for testing."""
    return SMSProvider(config=aws_sns_config)


class TestSMSProvider:
    """Test cases for SMSProvider class."""
    
    def test_initialization_twilio(self, twilio_sms_provider):
        """Test SMSProvider initialization with Twilio."""
        assert twilio_sms_provider.config.provider == "twilio"
        assert twilio_sms_provider.config.account_sid == "test_account_sid"
        assert twilio_sms_provider.config.from_number == "+1234567890"
    
    def test_initialization_aws_sns(self, aws_sms_provider):
        """Test SMSProvider initialization with AWS SNS."""
        assert aws_sms_provider.config.provider == "aws_sns"
        assert aws_sms_provider.config.region == "us-east-1"
    
    def test_invalid_config_no_provider(self):
        """Test initialization with invalid config - no provider."""
        config = SMSConfig(provider="")
        
        with pytest.raises(SMSError, match="SMS provider is required"):
            SMSProvider(config)
    
    def test_invalid_config_twilio_no_credentials(self):
        """Test initialization with invalid Twilio config - no credentials."""
        config = SMSConfig(
            provider="twilio",
            account_sid="",
            auth_token="test_token"
        )
        
        with pytest.raises(SMSError, match="Twilio account SID and auth token are required"):
            SMSProvider(config)
    
    def test_invalid_config_twilio_no_from_number(self):
        """Test initialization with invalid Twilio config - no from number."""
        config = SMSConfig(
            provider="twilio",
            account_sid="test_sid",
            auth_token="test_token",
            from_number=""
        )
        
        with pytest.raises(SMSError, match="From number is required for Twilio"):
            SMSProvider(config)
    
    def test_invalid_config_unsupported_provider(self):
        """Test initialization with unsupported provider."""
        config = SMSConfig(provider="unsupported_provider")
        
        with pytest.raises(SMSError, match="Unsupported SMS provider"):
            SMSProvider(config)
    
    @pytest.mark.asyncio
    async def test_send_notification_twilio_success(self, twilio_sms_provider):
        """Test successful SMS sending via Twilio."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._create_twilio_client') as mock_create_client:
            # Set up mock Twilio client
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = "test_message_sid"
            mock_client.messages.create.return_value = mock_message
            mock_create_client.return_value = mock_client
            
            result = await twilio_sms_provider.send_notification(
                recipients=["+1234567890"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            mock_client.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_aws_sns_success(self, aws_sms_provider):
        """Test successful SMS sending via AWS SNS."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._create_aws_sns_client') as mock_create_client:
            # Set up mock AWS SNS client
            mock_client = MagicMock()
            mock_client.publish.return_value = {'MessageId': 'test_message_id'}
            mock_create_client.return_value = mock_client
            
            result = await aws_sms_provider.send_notification(
                recipients=["+1234567890"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            mock_client.publish.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_no_recipients(self, twilio_sms_provider):
        """Test SMS sending with no recipients."""
        result = await twilio_sms_provider.send_notification(
            recipients=[],
            subject="Test Alert",
            body="Test message body"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_invalid_recipients(self, twilio_sms_provider):
        """Test SMS sending with invalid recipients."""
        result = await twilio_sms_provider.send_notification(
            recipients=["invalid_phone", "another_invalid"],
            subject="Test Alert",
            body="Test message body"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_mixed_recipients(self, twilio_sms_provider):
        """Test SMS sending with mixed valid/invalid recipients."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._create_twilio_client') as mock_create_client:
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = "test_message_sid"
            mock_client.messages.create.return_value = mock_message
            mock_create_client.return_value = mock_client
            
            result = await twilio_sms_provider.send_notification(
                recipients=["+1234567890", "invalid_phone", "+0987654321"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            # Should be called twice for valid numbers
            assert mock_client.messages.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_notification_twilio_error(self, twilio_sms_provider):
        """Test SMS sending with Twilio error."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._create_twilio_client') as mock_create_client:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("Twilio error")
            mock_create_client.return_value = mock_client
            
            result = await twilio_sms_provider.send_notification(
                recipients=["+1234567890"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is False
    
    def test_prepare_message_content(self, twilio_sms_provider):
        """Test SMS message content preparation."""
        # Test with subject and body
        content = twilio_sms_provider._prepare_message_content(
            "Alert", "Price moved 5%", {}
        )
        assert content == "Alert: Price moved 5%"
        
        # Test with only subject
        content = twilio_sms_provider._prepare_message_content(
            "Alert", "", {}
        )
        assert content == "Alert"
        
        # Test with only body
        content = twilio_sms_provider._prepare_message_content(
            "", "Price moved 5%", {}
        )
        assert content == "Price moved 5%"
    
    def test_prepare_message_content_truncation(self, twilio_sms_provider):
        """Test SMS message content truncation."""
        long_message = "A" * 200  # Longer than max_message_length (160)
        
        content = twilio_sms_provider._prepare_message_content(
            "Alert", long_message, {}
        )
        
        assert len(content) <= twilio_sms_provider.config.max_message_length
        assert content.endswith("...")
    
    def test_is_valid_phone(self, twilio_sms_provider):
        """Test phone number validation."""
        # Valid phone numbers
        assert twilio_sms_provider._is_valid_phone("+1234567890") is True
        assert twilio_sms_provider._is_valid_phone("1234567890") is True
        assert twilio_sms_provider._is_valid_phone("11234567890") is True
        assert twilio_sms_provider._is_valid_phone("+44123456789012") is True
        
        # Invalid phone numbers
        assert twilio_sms_provider._is_valid_phone("") is False
        assert twilio_sms_provider._is_valid_phone("123") is False
        assert twilio_sms_provider._is_valid_phone("12345678901234567") is False  # Too long
        assert twilio_sms_provider._is_valid_phone("abcdefghij") is False
    
    def test_normalize_phone(self, twilio_sms_provider):
        """Test phone number normalization."""
        # US numbers
        assert twilio_sms_provider._normalize_phone("1234567890") == "+11234567890"
        assert twilio_sms_provider._normalize_phone("11234567890") == "+11234567890"
        assert twilio_sms_provider._normalize_phone("+1234567890") == "+1234567890"
        
        # Formatted numbers
        assert twilio_sms_provider._normalize_phone("(123) 456-7890") == "+11234567890"
        assert twilio_sms_provider._normalize_phone("123-456-7890") == "+11234567890"
        assert twilio_sms_provider._normalize_phone("123.456.7890") == "+11234567890"
    
    def test_create_twilio_client_import_error(self, twilio_sms_provider):
        """Test Twilio client creation with import error."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'twilio'")):
            with pytest.raises(SMSError, match="Twilio library not installed"):
                twilio_sms_provider._create_twilio_client()
    
    def test_create_aws_sns_client_import_error(self, aws_sms_provider):
        """Test AWS SNS client creation with import error."""
        with patch('builtins.__import__', side_effect=ImportError("No module named 'boto3'")):
            with pytest.raises(SMSError, match="AWS boto3 library not installed"):
                aws_sms_provider._create_aws_sns_client()
    
    def test_is_available_twilio_success(self, twilio_sms_provider):
        """Test availability check for Twilio success."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = 'active'
            mock_client.api.accounts.return_value.fetch.return_value = mock_account
            mock_get_client.return_value = mock_client
            
            result = twilio_sms_provider.is_available()
            
            assert result is True
    
    def test_is_available_twilio_inactive(self, twilio_sms_provider):
        """Test availability check for Twilio with inactive account."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = 'suspended'
            mock_client.api.accounts.return_value.fetch.return_value = mock_account
            mock_get_client.return_value = mock_client
            
            result = twilio_sms_provider.is_available()
            
            assert result is False
    
    def test_is_available_aws_sns_success(self, aws_sms_provider):
        """Test availability check for AWS SNS success."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_sms_attributes.return_value = {}
            mock_get_client.return_value = mock_client
            
            result = aws_sms_provider.is_available()
            
            assert result is True
    
    def test_is_available_error(self, twilio_sms_provider):
        """Test availability check with error."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection error")
            
            result = twilio_sms_provider.is_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_twilio_success(self, twilio_sms_provider):
        """Test connection test for Twilio success."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_account = MagicMock()
            mock_account.status = 'active'
            mock_account.type = 'Full'
            mock_account.friendly_name = 'Test Account'
            mock_client.api.accounts.return_value.fetch.return_value = mock_account
            mock_get_client.return_value = mock_client
            
            result = await twilio_sms_provider.test_connection()
            
            assert result['success'] is True
            assert result['account_info']['status'] == 'active'
            assert result['provider_info']['provider'] == 'twilio'
    
    @pytest.mark.asyncio
    async def test_test_connection_aws_sns_success(self, aws_sms_provider):
        """Test connection test for AWS SNS success."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_sms_attributes.return_value = {
                'attributes': {'DefaultSMSType': 'Transactional'}
            }
            mock_get_client.return_value = mock_client
            
            result = await aws_sms_provider.test_connection()
            
            assert result['success'] is True
            assert 'DefaultSMSType' in result['account_info']
            assert result['provider_info']['provider'] == 'aws_sns'
    
    @pytest.mark.asyncio
    async def test_test_connection_error(self, twilio_sms_provider):
        """Test connection test with error."""
        with patch('financial_portfolio_automation.notifications.sms_provider.SMSProvider._get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            result = await twilio_sms_provider.test_connection()
            
            assert result['success'] is False
            assert "Connection failed" in result['error']
    
    def test_get_provider_name(self, twilio_sms_provider):
        """Test provider name."""
        assert twilio_sms_provider.get_provider_name() == "sms"
    
    def test_format_alert_message(self, twilio_sms_provider):
        """Test alert message formatting."""
        # With symbol
        formatted = twilio_sms_provider.format_alert_message(
            "price_movement", "AAPL", "Price moved 5%"
        )
        assert formatted == "ALERT AAPL: Price moved 5%"
        
        # Without symbol
        formatted = twilio_sms_provider.format_alert_message(
            "portfolio_alert", None, "Portfolio value changed"
        )
        assert formatted == "ALERT: Portfolio value changed"
    
    def test_format_alert_message_truncation(self, twilio_sms_provider):
        """Test alert message formatting with truncation."""
        long_message = "A" * 200  # Longer than max_message_length
        
        formatted = twilio_sms_provider.format_alert_message(
            "alert", "AAPL", long_message
        )
        
        assert len(formatted) <= twilio_sms_provider.config.max_message_length
        assert formatted.endswith("...")


class TestSMSConfig:
    """Test cases for SMSConfig class."""
    
    def test_default_config(self):
        """Test default SMS configuration."""
        config = SMSConfig()
        
        assert config.provider == "twilio"
        assert config.account_sid == ""
        assert config.auth_token == ""
        assert config.from_number == ""
        assert config.region == "us-east-1"
        assert config.max_message_length == 160
    
    def test_custom_config(self):
        """Test custom SMS configuration."""
        config = SMSConfig(
            provider="aws_sns",
            account_sid="custom_sid",
            auth_token="custom_token",
            from_number="+1987654321",
            region="eu-west-1",
            max_message_length=140
        )
        
        assert config.provider == "aws_sns"
        assert config.account_sid == "custom_sid"
        assert config.auth_token == "custom_token"
        assert config.from_number == "+1987654321"
        assert config.region == "eu-west-1"
        assert config.max_message_length == 140