"""
Unit tests for the NotificationService class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from financial_portfolio_automation.notifications.notification_service import (
    NotificationService, NotificationConfig, NotificationMessage, 
    NotificationPriority, NotificationStatus
)
from financial_portfolio_automation.monitoring.portfolio_monitor import (
    MonitoringAlert, AlertSeverity
)


@pytest.fixture
def notification_config():
    """Create test notification configuration."""
    return NotificationConfig(
        enabled=True,
        max_retries=2,
        retry_delay=1,  # 1 second for faster tests
        throttle_window=60,  # 1 minute
        max_notifications_per_window=5
    )


@pytest.fixture
def notification_service(notification_config):
    """Create a NotificationService instance for testing."""
    return NotificationService(config=notification_config)


@pytest.fixture
def mock_provider():
    """Create a mock notification provider."""
    provider = Mock()
    provider.send_notification = AsyncMock(return_value=True)
    provider.get_provider_name.return_value = "test_provider"
    provider.is_available.return_value = True
    return provider


class TestNotificationService:
    """Test cases for NotificationService class."""
    
    def test_initialization(self, notification_service):
        """Test NotificationService initialization."""
        assert not notification_service._is_running
        assert len(notification_service.providers) == 0
        assert len(notification_service.pending_messages) == 0
        assert len(notification_service.message_history) == 0
    
    def test_register_unregister_provider(self, notification_service, mock_provider):
        """Test provider registration and unregistration."""
        # Register provider
        notification_service.register_provider("email", mock_provider)
        assert "email" in notification_service.providers
        assert notification_service.providers["email"] == mock_provider
        
        # Unregister provider
        notification_service.unregister_provider("email")
        assert "email" not in notification_service.providers
    
    @pytest.mark.asyncio
    async def test_start_stop_service(self, notification_service):
        """Test starting and stopping the notification service."""
        # Start service
        await notification_service.start()
        assert notification_service._is_running
        assert notification_service._retry_task is not None
        assert notification_service._cleanup_task is not None
        
        # Stop service
        await notification_service.stop()
        assert not notification_service._is_running
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, notification_service, mock_provider):
        """Test successful notification sending."""
        notification_service.register_provider("email", mock_provider)
        
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email"],
            priority=NotificationPriority.NORMAL
        )
        
        assert message_id != ""
        mock_provider.send_notification.assert_called_once()
        
        # Check message was moved to history
        assert message_id not in notification_service.pending_messages
        assert len(notification_service.message_history) == 1
        
        message = notification_service.message_history[0]
        assert message.status == NotificationStatus.SENT
    
    @pytest.mark.asyncio
    async def test_send_notification_disabled(self, notification_service, mock_provider):
        """Test notification sending when service is disabled."""
        notification_service.config.enabled = False
        notification_service.register_provider("email", mock_provider)
        
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email"]
        )
        
        assert message_id == ""
        mock_provider.send_notification.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_notification_no_provider(self, notification_service):
        """Test notification sending with no registered provider."""
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email"]
        )
        
        assert message_id != ""
        
        # Message should be in history with failed status
        assert len(notification_service.message_history) == 1
        message = notification_service.message_history[0]
        assert message.status == NotificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_notification_provider_failure(self, notification_service, mock_provider):
        """Test notification sending when provider fails."""
        mock_provider.send_notification.return_value = False
        notification_service.register_provider("email", mock_provider)
        
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email"]
        )
        
        assert message_id != ""
        
        # Message should be in history with failed status
        assert len(notification_service.message_history) == 1
        message = notification_service.message_history[0]
        assert message.status == NotificationStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_send_notification_partial_success(self, notification_service):
        """Test notification sending with partial success across channels."""
        # Set up two providers - one succeeds, one fails
        success_provider = Mock()
        success_provider.send_notification = AsyncMock(return_value=True)
        success_provider.is_available.return_value = True
        
        fail_provider = Mock()
        fail_provider.send_notification = AsyncMock(return_value=False)
        fail_provider.is_available.return_value = True
        
        notification_service.register_provider("email", success_provider)
        notification_service.register_provider("sms", fail_provider)
        
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email", "sms"]
        )
        
        assert message_id != ""
        
        # Message should be marked as sent (partial success)
        message = notification_service.message_history[0]
        assert message.status == NotificationStatus.SENT
        assert message.delivery_confirmations["email"] is True
        assert message.delivery_confirmations["sms"] is False
    
    @pytest.mark.asyncio
    async def test_throttling(self, notification_service, mock_provider):
        """Test notification throttling."""
        notification_service.register_provider("email", mock_provider)
        
        # Send notifications up to the limit
        for i in range(notification_service.config.max_notifications_per_window):
            await notification_service.send_notification(
                recipients=["test@example.com"],
                subject=f"Test {i}",
                body="Test Body",
                channels=["email"]
            )
        
        # Next notification should be throttled
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Throttled Message",
            body="Test Body",
            channels=["email"]
        )
        
        # Find the throttled message
        throttled_message = None
        for message in notification_service.message_history:
            if message.subject == "Throttled Message":
                throttled_message = message
                break
        
        assert throttled_message is not None
        assert throttled_message.status == NotificationStatus.THROTTLED
    
    @pytest.mark.asyncio
    async def test_send_alert_notification(self, notification_service, mock_provider):
        """Test sending alert notifications."""
        notification_service.register_provider("email", mock_provider)
        
        alert = MonitoringAlert(
            alert_id="test_alert_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            alert_type="price_movement",
            symbol="AAPL",
            message="AAPL price moved 5%",
            data={"change_percent": 5.0}
        )
        
        message_id = await notification_service.send_alert_notification(alert)
        
        assert message_id != ""
        mock_provider.send_notification.assert_called_once()
        
        # Check message content
        call_args = mock_provider.send_notification.call_args
        assert "Portfolio Alert: price_movement - AAPL" in call_args[1]['subject']
        assert "AAPL price moved 5%" in call_args[1]['body']
        assert call_args[1]['metadata']['alert_id'] == "test_alert_001"
    
    def test_format_alert_body(self, notification_service):
        """Test alert body formatting."""
        alert = MonitoringAlert(
            alert_id="test_alert_001",
            timestamp=datetime.now(),
            severity=AlertSeverity.CRITICAL,
            alert_type="drawdown_limit",
            symbol=None,
            message="Portfolio drawdown exceeded 10%",
            data={"drawdown_percent": 12.5, "threshold": 10.0}
        )
        
        body = notification_service._format_alert_body(alert)
        
        assert "Portfolio drawdown exceeded 10%" in body
        assert "CRITICAL" in body
        assert "drawdown_limit" in body
        assert "drawdown_percent: 12.5" in body
        assert "threshold: 10.0" in body
    
    def test_get_channels_for_severity(self, notification_service):
        """Test channel selection based on alert severity."""
        critical_channels = notification_service._get_channels_for_severity(AlertSeverity.CRITICAL)
        warning_channels = notification_service._get_channels_for_severity(AlertSeverity.WARNING)
        info_channels = notification_service._get_channels_for_severity(AlertSeverity.INFO)
        
        # Critical should use all channels
        assert 'email' in critical_channels
        assert 'sms' in critical_channels
        assert 'webhook' in critical_channels
        
        # Warning should use email and webhook
        assert 'email' in warning_channels
        assert 'webhook' in warning_channels
        
        # Info should use only email
        assert 'email' in info_channels
        assert len(info_channels) == 1
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self, notification_service, mock_provider):
        """Test notification retry mechanism."""
        # Set up provider to fail first, then succeed
        mock_provider.send_notification.side_effect = [False, True]
        notification_service.register_provider("email", mock_provider)
        
        await notification_service.start()
        
        # Send notification (will fail initially)
        message_id = await notification_service.send_notification(
            recipients=["test@example.com"],
            subject="Test Subject",
            body="Test Body",
            channels=["email"]
        )
        
        # Message should be pending for retry
        assert message_id in notification_service.pending_messages
        
        # Wait for retry (should succeed)
        await asyncio.sleep(2)  # Wait longer than retry_delay
        
        # Manually trigger retry for testing
        message = notification_service.pending_messages[message_id]
        await notification_service._attempt_delivery(message)
        
        # Message should now be successful
        assert message.status == NotificationStatus.SENT
        
        await notification_service.stop()
    
    def test_get_message_status(self, notification_service):
        """Test message status retrieval."""
        # Create a test message
        message = NotificationMessage(
            message_id="test_msg_001",
            timestamp=datetime.now(),
            priority=NotificationPriority.NORMAL,
            subject="Test Subject",
            body="Test Body",
            recipients=["test@example.com"],
            channels=["email"],
            status=NotificationStatus.SENT
        )
        
        notification_service.message_history.append(message)
        
        # Retrieve message status
        retrieved_message = notification_service.get_message_status("test_msg_001")
        assert retrieved_message is not None
        assert retrieved_message.message_id == "test_msg_001"
        assert retrieved_message.status == NotificationStatus.SENT
        
        # Test non-existent message
        non_existent = notification_service.get_message_status("non_existent")
        assert non_existent is None
    
    def test_get_notification_statistics(self, notification_service, mock_provider):
        """Test notification statistics retrieval."""
        notification_service.register_provider("email", mock_provider)
        
        # Add some test messages to history
        messages = [
            NotificationMessage(
                message_id="msg_001",
                timestamp=datetime.now(),
                priority=NotificationPriority.NORMAL,
                subject="Test 1",
                body="Body 1",
                recipients=["test@example.com"],
                channels=["email"],
                status=NotificationStatus.SENT,
                delivery_confirmations={"email": True}
            ),
            NotificationMessage(
                message_id="msg_002",
                timestamp=datetime.now(),
                priority=NotificationPriority.HIGH,
                subject="Test 2",
                body="Body 2",
                recipients=["test@example.com"],
                channels=["email"],
                status=NotificationStatus.FAILED,
                delivery_confirmations={"email": False}
            ),
            NotificationMessage(
                message_id="msg_003",
                timestamp=datetime.now(),
                priority=NotificationPriority.LOW,
                subject="Test 3",
                body="Body 3",
                recipients=["test@example.com"],
                channels=["email"],
                status=NotificationStatus.THROTTLED
            )
        ]
        
        notification_service.message_history.extend(messages)
        
        stats = notification_service.get_notification_statistics()
        
        assert stats['total_messages'] == 3
        assert stats['sent'] == 1
        assert stats['failed'] == 1
        assert stats['throttled'] == 1
        assert stats['success_rate'] == 1/3
        assert 'email' in stats['registered_providers']
        assert 'email' in stats['channel_statistics']
        assert stats['channel_statistics']['email']['sent'] == 1
        assert stats['channel_statistics']['email']['failed'] == 1


class TestNotificationConfig:
    """Test cases for NotificationConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = NotificationConfig()
        
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.retry_delay == 60
        assert config.throttle_window == 300
        assert config.max_notifications_per_window == 10
        assert NotificationPriority.URGENT in config.priority_multipliers
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = NotificationConfig(
            enabled=False,
            max_retries=5,
            retry_delay=30,
            throttle_window=600,
            max_notifications_per_window=20
        )
        
        assert config.enabled is False
        assert config.max_retries == 5
        assert config.retry_delay == 30
        assert config.throttle_window == 600
        assert config.max_notifications_per_window == 20


class TestNotificationMessage:
    """Test cases for NotificationMessage class."""
    
    def test_message_creation(self):
        """Test notification message creation."""
        message = NotificationMessage(
            message_id="test_msg_001",
            timestamp=datetime.now(),
            priority=NotificationPriority.HIGH,
            subject="Test Subject",
            body="Test Body",
            recipients=["test@example.com"],
            channels=["email", "sms"]
        )
        
        assert message.message_id == "test_msg_001"
        assert message.priority == NotificationPriority.HIGH
        assert message.subject == "Test Subject"
        assert message.body == "Test Body"
        assert len(message.recipients) == 1
        assert len(message.channels) == 2
        assert message.status == NotificationStatus.PENDING
        assert message.retry_count == 0
    
    def test_message_with_metadata(self):
        """Test message creation with metadata."""
        metadata = {
            'alert_id': 'alert_001',
            'severity': 'critical',
            'custom_field': 'custom_value'
        }
        
        message = NotificationMessage(
            message_id="test_msg_002",
            timestamp=datetime.now(),
            priority=NotificationPriority.URGENT,
            subject="Alert Message",
            body="Alert Body",
            recipients=["admin@example.com"],
            channels=["email"],
            metadata=metadata
        )
        
        assert message.metadata['alert_id'] == 'alert_001'
        assert message.metadata['severity'] == 'critical'
        assert message.metadata['custom_field'] == 'custom_value'


class TestNotificationPriority:
    """Test cases for NotificationPriority enum."""
    
    def test_priority_values(self):
        """Test notification priority enum values."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestNotificationStatus:
    """Test cases for NotificationStatus enum."""
    
    def test_status_values(self):
        """Test notification status enum values."""
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SENT.value == "sent"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.THROTTLED.value == "throttled"