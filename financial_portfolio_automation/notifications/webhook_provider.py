"""
Webhook notification provider for custom integrations and third-party services.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import aiohttp

from ..exceptions import PortfolioAutomationError


@dataclass
class WebhookConfig:
    """Configuration for webhook provider."""
    webhook_urls: List[str]
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    headers: Dict[str, str] = None
    auth_token: str = ""
    auth_header: str = "Authorization"
    verify_ssl: bool = True


class WebhookError(PortfolioAutomationError):
    """Exception raised for webhook-related errors."""
    pass


class WebhookProvider:
    """
    Webhook notification provider that sends HTTP POST requests to configured endpoints.
    """
    
    def __init__(self, config: WebhookConfig):
        """
        Initialize the webhook provider.
        
        Args:
            config: Webhook configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate webhook configuration."""
        if not self.config.webhook_urls:
            raise WebhookError("At least one webhook URL is required")
        
        for url in self.config.webhook_urls:
            if not url.startswith(('http://', 'https://')):
                raise WebhookError(f"Invalid webhook URL: {url}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self.config.verify_ssl,
                limit=10,
                limit_per_host=5
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_default_headers()
            )
        
        return self._session
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for webhook requests."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Portfolio-Automation-Webhook/1.0'
        }
        
        # Add custom headers from config
        if self.config.headers:
            headers.update(self.config.headers)
        
        # Add authentication header if token provided
        if self.config.auth_token:
            headers[self.config.auth_header] = f"Bearer {self.config.auth_token}"
        
        return headers
    
    async def send_notification(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a webhook notification.
        
        Args:
            recipients: List of webhook URLs (overrides config if provided)
            subject: Notification subject
            body: Notification body content
            metadata: Additional metadata
            
        Returns:
            True if webhook was sent successfully, False otherwise
        """
        try:
            # Use provided recipients or config URLs
            webhook_urls = recipients if recipients else self.config.webhook_urls
            
            if not webhook_urls:
                self.logger.error("No webhook URLs provided")
                return False
            
            # Prepare webhook payload
            payload = self._create_webhook_payload(subject, body, metadata or {})
            
            # Send to all webhooks
            success_count = 0
            for url in webhook_urls:
                if await self._send_webhook(url, payload):
                    success_count += 1
            
            success = success_count == len(webhook_urls)
            
            if success:
                self.logger.info(f"Webhook sent successfully to {len(webhook_urls)} endpoints")
            else:
                self.logger.warning(f"Webhook partially sent ({success_count}/{len(webhook_urls)})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
            return False
    
    def _create_webhook_payload(
        self,
        subject: str,
        body: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create webhook payload."""
        payload = {
            'timestamp': datetime.now().isoformat(),
            'subject': subject,
            'body': body,
            'source': 'portfolio-automation',
            'version': '1.0'
        }
        
        # Add metadata
        if metadata:
            payload['metadata'] = metadata
        
        # Add alert-specific fields if this is an alert
        if 'alert_id' in metadata:
            payload['alert'] = {
                'id': metadata['alert_id'],
                'type': metadata.get('alert_type'),
                'severity': metadata.get('severity'),
                'symbol': metadata.get('symbol')
            }
        
        return payload
    
    async def _send_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send webhook to a specific URL with retry logic."""
        for attempt in range(self.config.max_retries + 1):
            try:
                session = await self._get_session()
                
                async with session.post(url, json=payload) as response:
                    if response.status < 400:
                        self.logger.debug(f"Webhook sent successfully to {url} (status: {response.status})")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.warning(f"Webhook failed to {url} (status: {response.status}): {error_text}")
                        
                        # Don't retry for client errors (4xx)
                        if 400 <= response.status < 500:
                            return False
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Webhook timeout to {url} (attempt {attempt + 1})")
            except aiohttp.ClientError as e:
                self.logger.warning(f"Webhook client error to {url} (attempt {attempt + 1}): {e}")
            except Exception as e:
                self.logger.error(f"Unexpected webhook error to {url} (attempt {attempt + 1}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        self.logger.error(f"Webhook failed to {url} after {self.config.max_retries + 1} attempts")
        return False
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return "webhook"
    
    def is_available(self) -> bool:
        """Check if the webhook provider is available."""
        # Webhook provider is available if URLs are configured
        return bool(self.config.webhook_urls)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test webhook connections and return detailed results."""
        results = {
            'success': False,
            'webhook_results': [],
            'total_webhooks': len(self.config.webhook_urls),
            'successful_webhooks': 0
        }
        
        test_payload = {
            'timestamp': datetime.now().isoformat(),
            'subject': 'Test Connection',
            'body': 'This is a test webhook from Portfolio Automation',
            'source': 'portfolio-automation',
            'test': True
        }
        
        for url in self.config.webhook_urls:
            webhook_result = {
                'url': url,
                'success': False,
                'status_code': None,
                'error': None,
                'response_time': None
            }
            
            try:
                start_time = datetime.now()
                session = await self._get_session()
                
                async with session.post(url, json=test_payload) as response:
                    end_time = datetime.now()
                    webhook_result['response_time'] = (end_time - start_time).total_seconds()
                    webhook_result['status_code'] = response.status
                    
                    if response.status < 400:
                        webhook_result['success'] = True
                        results['successful_webhooks'] += 1
                    else:
                        webhook_result['error'] = f"HTTP {response.status}"
                
            except Exception as e:
                webhook_result['error'] = str(e)
            
            results['webhook_results'].append(webhook_result)
        
        results['success'] = results['successful_webhooks'] > 0
        return results
    
    def create_slack_payload(
        self,
        subject: str,
        body: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Slack-compatible webhook payload."""
        # Determine color based on severity
        color_map = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }
        
        severity = metadata.get('severity', 'info')
        color = color_map.get(severity, 'good')
        
        # Create Slack attachment
        attachment = {
            'color': color,
            'title': subject,
            'text': body,
            'timestamp': int(datetime.now().timestamp()),
            'fields': []
        }
        
        # Add alert fields
        if 'alert_type' in metadata:
            attachment['fields'].append({
                'title': 'Alert Type',
                'value': metadata['alert_type'],
                'short': True
            })
        
        if 'symbol' in metadata and metadata['symbol']:
            attachment['fields'].append({
                'title': 'Symbol',
                'value': metadata['symbol'],
                'short': True
            })
        
        if 'severity' in metadata:
            attachment['fields'].append({
                'title': 'Severity',
                'value': metadata['severity'].upper(),
                'short': True
            })
        
        return {
            'text': f"Portfolio Alert: {subject}",
            'attachments': [attachment]
        }
    
    def create_discord_payload(
        self,
        subject: str,
        body: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Discord-compatible webhook payload."""
        # Determine color based on severity
        color_map = {
            'critical': 0xFF0000,  # Red
            'warning': 0xFFA500,   # Orange
            'info': 0x0099FF       # Blue
        }
        
        severity = metadata.get('severity', 'info')
        color = color_map.get(severity, 0x0099FF)
        
        # Create Discord embed
        embed = {
            'title': subject,
            'description': body,
            'color': color,
            'timestamp': datetime.now().isoformat(),
            'fields': []
        }
        
        # Add alert fields
        if 'alert_type' in metadata:
            embed['fields'].append({
                'name': 'Alert Type',
                'value': metadata['alert_type'],
                'inline': True
            })
        
        if 'symbol' in metadata and metadata['symbol']:
            embed['fields'].append({
                'name': 'Symbol',
                'value': metadata['symbol'],
                'inline': True
            })
        
        if 'severity' in metadata:
            embed['fields'].append({
                'name': 'Severity',
                'value': metadata['severity'].upper(),
                'inline': True
            })
        
        return {
            'content': f"**Portfolio Alert**",
            'embeds': [embed]
        }