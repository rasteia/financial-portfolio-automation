"""
Unit tests for the WebhookProvider class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
from datetime import datetime

from financial_portfolio_automation.notifications.webhook_provider import (
    WebhookProvider, WebhookConfig, WebhookError
)


@pytest.fixture
def webhook_config():
    """Create test webhook configuration."""
    return WebhookConfig(
        webhook_urls=["https://example.com/webhook", "https://api.example.com/alerts"],
        timeout=10,
        max_retries=2,
        retry_delay=1,
        headers={"X-Custom-Header": "test-value"},
        auth_token="test_token"
    )


@pytest.fixture
def webhook_provider(webhook_config):
    """Create a WebhookProvider instance for testing."""
    return WebhookProvider(config=webhook_config)


class TestWebhookProvider:
    """Test cases for WebhookProvider class."""
    
    def test_initialization(self, webhook_provider):
        """Test WebhookProvider initialization."""
        assert len(webhook_provider.config.webhook_urls) == 2
        assert webhook_provider.config.timeout == 10
        assert webhook_provider.config.max_retries == 2
        assert webhook_provider.config.auth_token == "test_token"
    
    def test_invalid_config_no_urls(self):
        """Test initialization with invalid config - no URLs."""
        config = WebhookConfig(webhook_urls=[])
        
        with pytest.raises(WebhookError, match="At least one webhook URL is required"):
            WebhookProvider(config)
    
    def test_invalid_config_invalid_url(self):
        """Test initialization with invalid config - invalid URL."""
        config = WebhookConfig(webhook_urls=["invalid-url", "ftp://example.com"])
        
        with pytest.raises(WebhookError, match="Invalid webhook URL"):
            WebhookProvider(config)
    
    def test_get_default_headers(self, webhook_provider):
        """Test default headers generation."""
        headers = webhook_provider._get_default_headers()
        
        assert headers['Content-Type'] == 'application/json'
        assert headers['User-Agent'] == 'Portfolio-Automation-Webhook/1.0'
        assert headers['X-Custom-Header'] == 'test-value'
        assert headers['Authorization'] == 'Bearer test_token'
    
    def test_create_webhook_payload(self, webhook_provider):
        """Test webhook payload creation."""
        metadata = {
            'alert_id': 'alert_001',
            'alert_type': 'price_movement',
            'severity': 'warning',
            'symbol': 'AAPL'
        }
        
        payload = webhook_provider._create_webhook_payload(
            "Test Alert", "Test message body", metadata
        )
        
        assert payload['subject'] == "Test Alert"
        assert payload['body'] == "Test message body"
        assert payload['source'] == 'portfolio-automation'
        assert payload['version'] == '1.0'
        assert 'timestamp' in payload
        assert payload['metadata'] == metadata
        assert payload['alert']['id'] == 'alert_001'
        assert payload['alert']['type'] == 'price_movement'
        assert payload['alert']['severity'] == 'warning'
        assert payload['alert']['symbol'] == 'AAPL'
    
    def test_create_webhook_payload_no_alert(self, webhook_provider):
        """Test webhook payload creation without alert metadata."""
        payload = webhook_provider._create_webhook_payload(
            "Test Subject", "Test body", {}
        )
        
        assert payload['subject'] == "Test Subject"
        assert payload['body'] == "Test body"
        assert 'alert' not in payload
        assert payload['metadata'] == {}
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, webhook_provider):
        """Test successful webhook sending."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Set up mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response
            
            result = await webhook_provider.send_notification(
                recipients=[],  # Will use config URLs
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            # Should be called twice (once for each URL in config)
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_notification_custom_recipients(self, webhook_provider):
        """Test webhook sending with custom recipient URLs."""
        custom_urls = ["https://custom.example.com/webhook"]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response
            
            result = await webhook_provider.send_notification(
                recipients=custom_urls,
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            # Should be called once for custom URL
            assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_notification_no_urls(self, webhook_provider):
        """Test webhook sending with no URLs."""
        result = await webhook_provider.send_notification(
            recipients=[],
            subject="Test Alert",
            body="Test message body"
        )
        
        # Should succeed since config has URLs
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_notification_http_error(self, webhook_provider):
        """Test webhook sending with HTTP error."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response
            
            result = await webhook_provider.send_notification(
                recipients=[],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_notification_client_error_no_retry(self, webhook_provider):
        """Test webhook sending with client error (4xx) - should not retry."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = "Bad Request"
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response
            
            result = await webhook_provider.send_notification(
                recipients=["https://example.com/webhook"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is False
            # Should only be called once (no retries for 4xx errors)
            assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_notification_timeout_with_retry(self, webhook_provider):
        """Test webhook sending with timeout and retry."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # First call times out, second succeeds
            mock_post.side_effect = [
                asyncio.TimeoutError("Request timeout"),
                AsyncMock(status=200, __aenter__=AsyncMock(return_value=AsyncMock(status=200)), __aexit__=AsyncMock(return_value=None))
            ]
            
            result = await webhook_provider.send_notification(
                recipients=["https://example.com/webhook"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is True
            # Should be called twice (initial + 1 retry)
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_notification_max_retries_exceeded(self, webhook_provider):
        """Test webhook sending with max retries exceeded."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # All calls time out
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await webhook_provider.send_notification(
                recipients=["https://example.com/webhook"],
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is False
            # Should be called max_retries + 1 times
            assert mock_post.call_count == webhook_provider.config.max_retries + 1
    
    @pytest.mark.asyncio
    async def test_send_notification_partial_success(self, webhook_provider):
        """Test webhook sending with partial success."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # First URL succeeds, second fails
            responses = [
                AsyncMock(status=200, __aenter__=AsyncMock(return_value=AsyncMock(status=200)), __aexit__=AsyncMock(return_value=None)),
                AsyncMock(status=500, text=AsyncMock(return_value="Server Error"), __aenter__=AsyncMock(return_value=AsyncMock(status=500, text=AsyncMock(return_value="Server Error"))), __aexit__=AsyncMock(return_value=None))
            ]
            mock_post.side_effect = responses
            
            result = await webhook_provider.send_notification(
                recipients=[],  # Uses config URLs
                subject="Test Alert",
                body="Test message body"
            )
            
            assert result is False  # Not all webhooks succeeded
    
    @pytest.mark.asyncio
    async def test_close_session(self, webhook_provider):
        """Test closing HTTP session."""
        # Create a session first
        await webhook_provider._get_session()
        assert webhook_provider._session is not None
        
        # Close the session
        await webhook_provider.close()
        
        # Session should be closed
        assert webhook_provider._session.closed
    
    def test_get_provider_name(self, webhook_provider):
        """Test provider name."""
        assert webhook_provider.get_provider_name() == "webhook"
    
    def test_is_available(self, webhook_provider):
        """Test availability check."""
        assert webhook_provider.is_available() is True
        
        # Test with no URLs
        empty_config = WebhookConfig(webhook_urls=[])
        with pytest.raises(WebhookError):
            WebhookProvider(empty_config)
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, webhook_provider):
        """Test connection test success."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_post.return_value = mock_response
            
            result = await webhook_provider.test_connection()
            
            assert result['success'] is True
            assert result['total_webhooks'] == 2
            assert result['successful_webhooks'] == 2
            assert len(result['webhook_results']) == 2
            
            for webhook_result in result['webhook_results']:
                assert webhook_result['success'] is True
                assert webhook_result['status_code'] == 200
                assert webhook_result['response_time'] is not None
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, webhook_provider):
        """Test connection test failure."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Connection failed")
            
            result = await webhook_provider.test_connection()
            
            assert result['success'] is False
            assert result['successful_webhooks'] == 0
            
            for webhook_result in result['webhook_results']:
                assert webhook_result['success'] is False
                assert "Connection failed" in webhook_result['error']
    
    @pytest.mark.asyncio
    async def test_test_connection_mixed_results(self, webhook_provider):
        """Test connection test with mixed results."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # First succeeds, second fails
            responses = [
                AsyncMock(status=200, __aenter__=AsyncMock(return_value=AsyncMock(status=200)), __aexit__=AsyncMock(return_value=None)),
                Exception("Connection failed")
            ]
            mock_post.side_effect = responses
            
            result = await webhook_provider.test_connection()
            
            assert result['success'] is True  # At least one succeeded
            assert result['successful_webhooks'] == 1
            assert result['webhook_results'][0]['success'] is True
            assert result['webhook_results'][1]['success'] is False
    
    def test_create_slack_payload(self, webhook_provider):
        """Test Slack payload creation."""
        metadata = {
            'severity': 'critical',
            'alert_type': 'price_movement',
            'symbol': 'AAPL'
        }
        
        payload = webhook_provider.create_slack_payload(
            "Portfolio Alert", "AAPL price moved 10%", metadata
        )
        
        assert payload['text'] == "Portfolio Alert: Portfolio Alert"
        assert len(payload['attachments']) == 1
        
        attachment = payload['attachments'][0]
        assert attachment['color'] == 'danger'  # Critical severity
        assert attachment['title'] == "Portfolio Alert"
        assert attachment['text'] == "AAPL price moved 10%"
        assert len(attachment['fields']) == 3  # alert_type, symbol, severity
    
    def test_create_slack_payload_info_severity(self, webhook_provider):
        """Test Slack payload creation with info severity."""
        metadata = {
            'severity': 'info',
            'alert_type': 'portfolio_update'
        }
        
        payload = webhook_provider.create_slack_payload(
            "Info Alert", "Portfolio updated", metadata
        )
        
        attachment = payload['attachments'][0]
        assert attachment['color'] == 'good'  # Info severity
    
    def test_create_discord_payload(self, webhook_provider):
        """Test Discord payload creation."""
        metadata = {
            'severity': 'warning',
            'alert_type': 'volatility_alert',
            'symbol': 'TSLA'
        }
        
        payload = webhook_provider.create_discord_payload(
            "Volatility Alert", "TSLA volatility increased", metadata
        )
        
        assert payload['content'] == "**Portfolio Alert**"
        assert len(payload['embeds']) == 1
        
        embed = payload['embeds'][0]
        assert embed['title'] == "Volatility Alert"
        assert embed['description'] == "TSLA volatility increased"
        assert embed['color'] == 0xFFA500  # Orange for warning
        assert len(embed['fields']) == 3  # alert_type, symbol, severity
    
    def test_create_discord_payload_critical_severity(self, webhook_provider):
        """Test Discord payload creation with critical severity."""
        metadata = {
            'severity': 'critical',
            'alert_type': 'risk_limit'
        }
        
        payload = webhook_provider.create_discord_payload(
            "Risk Alert", "Risk limit exceeded", metadata
        )
        
        embed = payload['embeds'][0]
        assert embed['color'] == 0xFF0000  # Red for critical


class TestWebhookConfig:
    """Test cases for WebhookConfig class."""
    
    def test_default_config(self):
        """Test default webhook configuration."""
        config = WebhookConfig(webhook_urls=["https://example.com/webhook"])
        
        assert len(config.webhook_urls) == 1
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 5
        assert config.headers is None
        assert config.auth_token == ""
        assert config.auth_header == "Authorization"
        assert config.verify_ssl is True
    
    def test_custom_config(self):
        """Test custom webhook configuration."""
        custom_headers = {"X-API-Key": "secret"}
        
        config = WebhookConfig(
            webhook_urls=["https://api1.com/hook", "https://api2.com/hook"],
            timeout=60,
            max_retries=5,
            retry_delay=10,
            headers=custom_headers,
            auth_token="custom_token",
            auth_header="X-Auth-Token",
            verify_ssl=False
        )
        
        assert len(config.webhook_urls) == 2
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 10
        assert config.headers == custom_headers
        assert config.auth_token == "custom_token"
        assert config.auth_header == "X-Auth-Token"
        assert config.verify_ssl is False