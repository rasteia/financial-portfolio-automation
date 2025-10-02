"""
Multi-channel notification service with priority handling and throttling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from ..monitoring.portfolio_monitor import MonitoringAlert, AlertSeverity
from ..exceptions import PortfolioAutomationError


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    THROTTLED = "throttled"


@dataclass
class NotificationConfig:
    """Configuration for notification delivery."""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    throttle_window: int = 300  # 5 minutes
    max_notifications_per_window: int = 10
    priority_multipliers: Dict[NotificationPriority, int] = field(default_factory=lambda: {
        NotificationPriority.LOW: 1,
        NotificationPriority.NORMAL: 2,
        NotificationPriority.HIGH: 5,
        NotificationPriority.URGENT: 10
    })


@dataclass
class NotificationMessage:
    """Represents a notification message."""
    message_id: str
    timestamp: datetime
    priority: NotificationPriority
    subject: str
    body: str
    recipients: List[str]
    channels: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    status: NotificationStatus = NotificationStatus.PENDING
    last_attempt: Optional[datetime] = None
    delivery_confirmations: Dict[str, bool] = field(default_factory=dict)


class NotificationProvider(Protocol):
    """Protocol for notification providers."""
    
    async def send_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification through this provider."""
        ...
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        ...
    
    def is_available(self) -> bool:
        """Check if this provider is available."""
        ...


class NotificationService:
    """
    Multi-channel notification service with priority handling, throttling,
    and delivery confirmation.
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        """
        Initialize the notification service.
        
        Args:
            config: Notification configuration
        """
        self.config = config or NotificationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Provider registry
        self.providers: Dict[str, NotificationProvider] = {}
        
        # Message tracking
        self.pending_messages: Dict[str, NotificationMessage] = {}
        self.message_history: List[NotificationMessage] = []
        
        # Throttling tracking
        self.throttle_counters: Dict[str, deque] = defaultdict(deque)
        
        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    def register_provider(self, channel: str, provider: NotificationProvider) -> None:
        """Register a notification provider for a specific channel."""
        self.providers[channel] = provider
        self.logger.info(f"Registered notification provider for channel: {channel}")
    
    def unregister_provider(self, channel: str) -> None:
        """Unregister a notification provider."""
        if channel in self.providers:
            del self.providers[channel]
            self.logger.info(f"Unregistered notification provider for channel: {channel}")
    
    async def start(self) -> None:
        """Start the notification service background tasks."""
        if self._is_running:
            return
        
        self._is_running = True
        self.logger.info("Starting notification service")
        
        # Start background tasks
        self._retry_task = asyncio.create_task(self._retry_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self) -> None:
        """Stop the notification service background tasks."""
        if not self._is_running:
            return
        
        self.logger.info("Stopping notification service")
        self._is_running = False
        
        # Cancel background tasks
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def send_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        channels: List[str],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send a notification through specified channels.
        
        Args:
            recipients: List of recipient addresses/numbers
            subject: Notification subject
            body: Notification body content
            channels: List of channels to send through
            priority: Notification priority
            metadata: Additional metadata
            
        Returns:
            Message ID for tracking
        """
        if not self.config.enabled:
            self.logger.debug("Notifications are disabled")
            return ""
        
        # Generate message ID
        message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Create notification message
        message = NotificationMessage(
            message_id=message_id,
            timestamp=datetime.now(),
            priority=priority,
            subject=subject,
            body=body,
            recipients=recipients,
            channels=channels,
            metadata=metadata or {}
        )
        
        # Check throttling
        if self._is_throttled(channels, priority):
            message.status = NotificationStatus.THROTTLED
            self.logger.warning(f"Notification {message_id} throttled")
            self.message_history.append(message)
            return message_id
        
        # Add to pending messages
        self.pending_messages[message_id] = message
        
        # Attempt immediate delivery
        await self._attempt_delivery(message)
        
        return message_id
    
    async def send_alert_notification(self, alert: MonitoringAlert) -> str:
        """
        Send a notification for a monitoring alert.
        
        Args:
            alert: Monitoring alert to send
            
        Returns:
            Message ID for tracking
        """
        # Map alert severity to notification priority
        priority_mapping = {
            AlertSeverity.INFO: NotificationPriority.LOW,
            AlertSeverity.WARNING: NotificationPriority.NORMAL,
            AlertSeverity.CRITICAL: NotificationPriority.URGENT
        }
        
        priority = priority_mapping.get(alert.severity, NotificationPriority.NORMAL)
        
        # Format alert message
        subject = f"Portfolio Alert: {alert.alert_type}"
        if alert.symbol:
            subject += f" - {alert.symbol}"
        
        body = self._format_alert_body(alert)
        
        # Determine channels based on severity
        channels = self._get_channels_for_severity(alert.severity)
        
        # Get recipients (this would typically come from configuration)
        recipients = self._get_alert_recipients(alert)
        
        return await self.send_notification(
            recipients=recipients,
            subject=subject,
            body=body,
            channels=channels,
            priority=priority,
            metadata={
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type,
                'severity': alert.severity.value,
                'symbol': alert.symbol
            }
        )
    
    def _format_alert_body(self, alert: MonitoringAlert) -> str:
        """Format alert body for notification."""
        lines = [
            f"Alert: {alert.message}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Severity: {alert.severity.value.upper()}",
            f"Type: {alert.alert_type}"
        ]
        
        if alert.symbol:
            lines.append(f"Symbol: {alert.symbol}")
        
        if alert.data:
            lines.append("\nDetails:")
            for key, value in alert.data.items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
    
    def _get_channels_for_severity(self, severity: AlertSeverity) -> List[str]:
        """Get notification channels based on alert severity."""
        # This would typically be configurable
        if severity == AlertSeverity.CRITICAL:
            return ['email', 'sms', 'webhook']
        elif severity == AlertSeverity.WARNING:
            return ['email', 'webhook']
        else:
            return ['email']
    
    def _get_alert_recipients(self, alert: MonitoringAlert) -> List[str]:
        """Get recipients for alert notifications."""
        # This would typically come from configuration
        # For now, return placeholder recipients
        return ['user@example.com']
    
    def _is_throttled(self, channels: List[str], priority: NotificationPriority) -> bool:
        """Check if notification should be throttled."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.throttle_window)
        
        for channel in channels:
            # Clean old entries
            counter = self.throttle_counters[channel]
            while counter and counter[0] < window_start:
                counter.popleft()
            
            # Calculate effective count with priority multiplier
            multiplier = self.config.priority_multipliers.get(priority, 1)
            effective_count = len(counter) * multiplier
            
            if effective_count >= self.config.max_notifications_per_window:
                return True
        
        return False
    
    async def _attempt_delivery(self, message: NotificationMessage) -> None:
        """Attempt to deliver a notification message."""
        message.last_attempt = datetime.now()
        success_count = 0
        
        for channel in message.channels:
            if channel not in self.providers:
                self.logger.warning(f"No provider registered for channel: {channel}")
                message.delivery_confirmations[channel] = False
                continue
            
            provider = self.providers[channel]
            
            if not provider.is_available():
                self.logger.warning(f"Provider {channel} is not available")
                message.delivery_confirmations[channel] = False
                continue
            
            try:
                success = await provider.send_notification(
                    recipients=message.recipients,
                    subject=message.subject,
                    body=message.body,
                    metadata=message.metadata
                )
                
                message.delivery_confirmations[channel] = success
                if success:
                    success_count += 1
                    # Update throttle counter
                    self.throttle_counters[channel].append(datetime.now())
                
            except Exception as e:
                self.logger.error(f"Error sending notification via {channel}: {e}")
                message.delivery_confirmations[channel] = False
        
        # Update message status
        if success_count == len(message.channels):
            message.status = NotificationStatus.SENT
            self.logger.info(f"Notification {message.message_id} sent successfully")
        elif success_count > 0:
            message.status = NotificationStatus.SENT
            self.logger.warning(f"Notification {message.message_id} partially sent ({success_count}/{len(message.channels)})")
        else:
            message.status = NotificationStatus.FAILED
            message.retry_count += 1
            self.logger.error(f"Notification {message.message_id} failed to send")
        
        # Move to history if completed or max retries reached
        if (message.status == NotificationStatus.SENT or 
            message.retry_count >= self.config.max_retries):
            if message.message_id in self.pending_messages:
                del self.pending_messages[message.message_id]
            self.message_history.append(message)
    
    async def _retry_loop(self) -> None:
        """Background task to retry failed notifications."""
        while self._is_running:
            try:
                now = datetime.now()
                retry_cutoff = now - timedelta(seconds=self.config.retry_delay)
                
                # Find messages ready for retry
                retry_messages = []
                for message in self.pending_messages.values():
                    if (message.status == NotificationStatus.FAILED and
                        message.retry_count < self.config.max_retries and
                        (message.last_attempt is None or message.last_attempt < retry_cutoff)):
                        retry_messages.append(message)
                
                # Retry messages
                for message in retry_messages:
                    self.logger.info(f"Retrying notification {message.message_id} (attempt {message.retry_count + 1})")
                    await self._attempt_delivery(message)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in retry loop: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up old message history."""
        while self._is_running:
            try:
                # Keep only last 1000 messages in history
                if len(self.message_history) > 1000:
                    self.message_history = self.message_history[-1000:]
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    def get_message_status(self, message_id: str) -> Optional[NotificationMessage]:
        """Get the status of a notification message."""
        # Check pending messages first
        if message_id in self.pending_messages:
            return self.pending_messages[message_id]
        
        # Check message history
        for message in reversed(self.message_history):
            if message.message_id == message_id:
                return message
        
        return None
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification service statistics."""
        total_sent = sum(1 for msg in self.message_history if msg.status == NotificationStatus.SENT)
        total_failed = sum(1 for msg in self.message_history if msg.status == NotificationStatus.FAILED)
        total_throttled = sum(1 for msg in self.message_history if msg.status == NotificationStatus.THROTTLED)
        
        # Channel statistics
        channel_stats = {}
        for channel in self.providers.keys():
            channel_sent = 0
            channel_failed = 0
            for msg in self.message_history:
                if channel in msg.delivery_confirmations:
                    if msg.delivery_confirmations[channel]:
                        channel_sent += 1
                    else:
                        channel_failed += 1
            
            channel_stats[channel] = {
                'sent': channel_sent,
                'failed': channel_failed,
                'success_rate': channel_sent / (channel_sent + channel_failed) if (channel_sent + channel_failed) > 0 else 0
            }
        
        return {
            'total_messages': len(self.message_history),
            'pending_messages': len(self.pending_messages),
            'sent': total_sent,
            'failed': total_failed,
            'throttled': total_throttled,
            'success_rate': total_sent / len(self.message_history) if self.message_history else 0,
            'registered_providers': list(self.providers.keys()),
            'channel_statistics': channel_stats,
            'is_running': self._is_running
        }