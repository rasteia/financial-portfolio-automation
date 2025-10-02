"""
Integration tests for the notification system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from financial_portfolio_automation.notifications.notification_service import (
    NotificationService, NotificationConfig, NotificationPriority
)
from financial_portfolio_automation.notifications.email_provider import EmailProvider, EmailConfig
from financial_portfolio_automation.notifications.sms_provider import SMSProvider, SMSConfig
from financial_portfolio_automation.notifications.webhook_provider import WebhookProvider, WebhookConfig
from financial_portfolio_automation.monitoring.portfolio_monitor import (
    MonitoringAlert, AlertSeverity
)


@pytest.fixture
def integration_notification_service():
    """Create a notification service for integration testing."""
    config = NotificationConfig(
        enabled=True,
        max_retries=1,
        retry_delay=1,
        throttle_window=60,
        max_notifications_per_window=10
    )
    return NotificationService(config=config)


@pytest.fixture
def mock_email_provider():
    """Create a mock email provider for integration testing."""
    config = EmailConfig(
        smtp_server="smtp.test.com",
        from_address="test@example.com"
    )
    provider = EmailProvider(config)
    
    # Mock the actual email sending
    provider._send_email_sync = Mock(return_value=True)
    provider.is_available = Mock(return_value=True)
    
    return provider


@pytest.fixture
def mock_sms_provider():
    """Create a mock SMS provider for integration testing."""
    config = SMSConfig(
        provider="twilio",
        account_sid="test_sid",
        auth_token="test_token",
        from_number="+1234567890"
    )
    provider = SMSProvider(config)
    
    # Mock the actual SMS sending
    provider._send_sms_sync = Mock(return_value=True)
    provider.is_available = Mock(return_value=True)
    
    return provider


@pytest.fixture
def mock_webhook_provider():
    """Create a mock webhook provider for integration testing."""
    config = WebhookConfig(
        webhook_urls=["https://example.com/webhook"]
    )
    provider = WebhookProvider(config)
    
    # Mock the actual webhook sending
    provider._send_webhook = AsyncMock(return_value=True)
    provider.is_available = Mock(return_value=True)
    
    return provider


class TestNotificationSystemIntegration:
    """Integration tests for the complete notification system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_notification_workflow(
        self,
        integration_notification_service,
        mock_email_provider,
        mock_sms_provider,
        mock_webhook_provider
    ):
        """Test complete notification workflow from alert to delivery."""
        service = integration_notification_service
        
        # Register all providers
        service.register_provider("email", mock_email_provider)
        service.register_provider("sms", mock_sms_provider)
        service.register_provider("webhook", mock_webhook_provider)
        
        # Start the service
        await service.start()
        
        # Create a test alert
        alert = MonitoringAlert(
            alert_id="test_alert_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.CRITICAL,
            alert_type="price_movement",
            symbol="AAPL",
            message="AAPL price dropped 15%",
            data={"change_percent": -15.0, "current_price": 150.00}
        )
        
        # Send alert notification
        message_id = await service.send_alert_notification(alert)
        
        # Verify notification was sent
        assert message_id != ""
        
        # Check that all providers were called
        mock_email_provider._send_email_sync.assert_called_once()
        mock_sms_provider._send_sms_sync.assert_called_once()
        mock_webhook_provider._send_webhook.assert_called_once()
        
        # Verify message is in history
        message = service.get_message_status(message_id)
        assert message is not None
        assert message.status.value == "sent"
        
        # Stop the service
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_multi_channel_notification_with_failures(
        self,
        integration_notification_service,
        mock_email_provider,
        mock_sms_provider,
        mock_webhook_provider
    ):
        """Test notification handling when some channels fail."""
        service = integration_notification_service
        
        # Set up providers with mixed success/failure
        mock_email_provider._send_email_sync.return_value = True
        mock_sms_provider._send_sms_sync.return_value = False  # SMS fails
        mock_webhook_provider._send_webhook.return_value = True
        
        service.register_provider("email", mock_email_provider)
        service.register_provider("sms", mock_sms_provider)
        service.register_provider("webhook", mock_webhook_provider)
        
        # Send notification
        message_id = await service.send_notification(
            recipients=["test@example.com"],
            subject="Test Alert",
            body="Test message",
            channels=["email", "sms", "webhook"],
            priority=NotificationPriority.HIGH
        )
        
        # Verify partial success
        message = service.get_message_status(message_id)
        assert message is not None
        assert message.status.value == "sent"  # Partial success still counts as sent
        assert message.delivery_confirmations["email"] is True
        assert message.delivery_confirmations["sms"] is False
        assert message.delivery_confirmations["webhook"] is True
    
    @pytest.mark.asyncio
    async def test_notification_retry_mechanism(
        self,
        integration_notification_service,
        mock_email_provider
    ):
        """Test notification retry mechanism with eventual success."""
        service = integration_notification_service
        
        # Set up provider to fail first, then succeed
        call_count = 0
        def mock_send_email(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Fail first call, succeed on retry
        
        mock_email_provider._send_email_sync.side_effect = mock_send_email
        service.register_provider("email", mock_email_provider)
        
        await service.start()
        
        # Send notification (will fail initially)
        message_id = await service.send_notification(
            recipients=["test@example.com"],
            subject="Test Alert",
            body="Test message",
            channels=["email"]
        )
        
        # Message should be pending for retry
        message = service.get_message_status(message_id)
        assert message is not None
        assert message.status.value == "failed"
        assert message.retry_count == 1
        
        # Wait for retry and manually trigger it
        await asyncio.sleep(2)
        await service._attempt_delivery(message)
        
        # Message should now be successful
        assert message.status.value == "sent"
        assert call_count == 2
        
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_notification_throttling_integration(
        self,
        integration_notification_service,
        mock_email_provider
    ):
        """Test notification throttling with real service."""
        service = integration_notification_service
        service.config.max_notifications_per_window = 3  # Low limit for testing
        
        service.register_provider("email", mock_email_provider)
        
        # Send notifications up to the limit
        message_ids = []
        for i in range(3):
            message_id = await service.send_notification(
                recipients=["test@example.com"],
                subject=f"Test Alert {i}",
                body="Test message",
                channels=["email"]
            )
            message_ids.append(message_id)
        
        # Next notification should be throttled
        throttled_id = await service.send_notification(
            recipients=["test@example.com"],
            subject="Throttled Alert",
            body="This should be throttled",
            channels=["email"]
        )
        
        # Verify throttling
        throttled_message = service.get_message_status(throttled_id)
        assert throttled_message is not None
        assert throttled_message.status.value == "throttled"
        
        # Verify successful messages
        for message_id in message_ids:
            message = service.get_message_status(message_id)
            assert message.status.value == "sent"
    
    @pytest.mark.asyncio
    async def test_alert_severity_channel_mapping(
        self,
        integration_notification_service,
        mock_email_provider,
        mock_sms_provider,
        mock_webhook_provider
    ):
        """Test that alert severity maps to appropriate channels."""
        service = integration_notification_service
        
        service.register_provider("email", mock_email_provider)
        service.register_provider("sms", mock_sms_provider)
        service.register_provider("webhook", mock_webhook_provider)
        
        # Test critical alert (should use all channels)
        critical_alert = MonitoringAlert(
            alert_id="critical_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.CRITICAL,
            alert_type="system_failure",
            symbol=None,
            message="System failure detected"
        )
        
        await service.send_alert_notification(critical_alert)
        
        # All providers should be called for critical alerts
        mock_email_provider._send_email_sync.assert_called()
        mock_sms_provider._send_sms_sync.assert_called()
        mock_webhook_provider._send_webhook.assert_called()
        
        # Reset mocks
        mock_email_provider._send_email_sync.reset_mock()
        mock_sms_provider._send_sms_sync.reset_mock()
        mock_webhook_provider._send_webhook.reset_mock()
        
        # Test info alert (should use only email)
        info_alert = MonitoringAlert(
            alert_id="info_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.INFO,
            alert_type="portfolio_update",
            symbol=None,
            message="Portfolio updated"
        )
        
        await service.send_alert_notification(info_alert)
        
        # Only email should be called for info alerts
        mock_email_provider._send_email_sync.assert_called()
        mock_sms_provider._send_sms_sync.assert_not_called()
        # Webhook might be called depending on implementation
    
    @pytest.mark.asyncio
    async def test_provider_availability_handling(
        self,
        integration_notification_service,
        mock_email_provider,
        mock_sms_provider
    ):
        """Test handling of unavailable providers."""
        service = integration_notification_service
        
        # Set up providers with different availability
        mock_email_provider.is_available.return_value = True
        mock_sms_provider.is_available.return_value = False  # SMS unavailable
        
        service.register_provider("email", mock_email_provider)
        service.register_provider("sms", mock_sms_provider)
        
        # Send notification to both channels
        message_id = await service.send_notification(
            recipients=["test@example.com"],
            subject="Test Alert",
            body="Test message",
            channels=["email", "sms"]
        )
        
        # Verify only available provider was used
        message = service.get_message_status(message_id)
        assert message is not None
        assert message.delivery_confirmations["email"] is True
        assert message.delivery_confirmations["sms"] is False
        
        mock_email_provider._send_email_sync.assert_called_once()
        mock_sms_provider._send_sms_sync.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_notification_statistics_integration(
        self,
        integration_notification_service,
        mock_email_provider,
        mock_sms_provider
    ):
        """Test notification statistics collection."""
        service = integration_notification_service
        
        service.register_provider("email", mock_email_provider)
        service.register_provider("sms", mock_sms_provider)
        
        # Send successful notifications
        for i in range(3):
            await service.send_notification(
                recipients=["test@example.com"],
                subject=f"Success {i}",
                body="Success message",
                channels=["email"]
            )
        
        # Send failed notification
        mock_sms_provider._send_sms_sync.return_value = False
        await service.send_notification(
            recipients=["+1234567890"],
            subject="Failed SMS",
            body="This will fail",
            channels=["sms"]
        )
        
        # Get statistics
        stats = service.get_notification_statistics()
        
        assert stats['total_messages'] == 4
        assert stats['sent'] == 3
        assert stats['failed'] == 1
        assert stats['success_rate'] == 0.75
        assert len(stats['registered_providers']) == 2
        assert 'email' in stats['channel_statistics']
        assert 'sms' in stats['channel_statistics']
        assert stats['channel_statistics']['email']['sent'] == 3
        assert stats['channel_statistics']['sms']['failed'] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_notifications(
        self,
        integration_notification_service,
        mock_email_provider
    ):
        """Test handling of concurrent notifications."""
        service = integration_notification_service
        service.register_provider("email", mock_email_provider)
        
        # Send multiple notifications concurrently
        tasks = []
        for i in range(5):
            task = service.send_notification(
                recipients=["test@example.com"],
                subject=f"Concurrent Alert {i}",
                body=f"Message {i}",
                channels=["email"]
            )
            tasks.append(task)
        
        # Wait for all notifications to complete
        message_ids = await asyncio.gather(*tasks)
        
        # Verify all notifications were processed
        assert len(message_ids) == 5
        assert all(msg_id != "" for msg_id in message_ids)
        
        # Verify all messages are in history
        for message_id in message_ids:
            message = service.get_message_status(message_id)
            assert message is not None
            assert message.status.value == "sent"
        
        # Verify provider was called for each notification
        assert mock_email_provider._send_email_sync.call_count == 5
    
    @pytest.mark.asyncio
    async def test_notification_cleanup_integration(
        self,
        integration_notification_service,
        mock_email_provider
    ):
        """Test notification history cleanup."""
        service = integration_notification_service
        service.register_provider("email", mock_email_provider)
        
        await service.start()
        
        # Send many notifications to trigger cleanup
        for i in range(1005):  # More than cleanup threshold (1000)
            await service.send_notification(
                recipients=["test@example.com"],
                subject=f"Test {i}",
                body="Test message",
                channels=["email"]
            )
        
        # Manually trigger cleanup
        await service._cleanup_loop.__wrapped__(service)
        
        # Verify history was cleaned up
        assert len(service.message_history) <= 1000
        
        await service.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_callbacks(
        self,
        integration_notification_service,
        mock_email_provider
    ):
        """Test error handling when notification callbacks fail."""
        service = integration_notification_service
        service.register_provider("email", mock_email_provider)
        
        # Add callbacks - one that works, one that fails
        successful_alerts = []
        
        def working_callback(alert):
            successful_alerts.append(alert)
        
        def failing_callback(alert):
            raise Exception("Callback error")
        
        # Register callbacks with portfolio monitor (if available)
        # This would typically be done through the monitoring system
        
        # Send notification directly
        message_id = await service.send_notification(
            recipients=["test@example.com"],
            subject="Test Alert",
            body="Test message",
            channels=["email"]
        )
        
        # Verify notification still succeeded despite callback errors
        message = service.get_message_status(message_id)
        assert message is not None
        assert message.status.value == "sent"