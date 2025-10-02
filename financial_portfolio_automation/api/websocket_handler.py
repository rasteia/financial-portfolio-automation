"""
WebSocket handler for real-time data streaming from Alpaca Markets.
"""

import asyncio
import json
import ssl
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    websockets = None
    ConnectionClosed = Exception
    WebSocketException = Exception

from financial_portfolio_automation.models.core import Quote
from financial_portfolio_automation.config.settings import get_config
from financial_portfolio_automation.utils.logging import get_logger
from financial_portfolio_automation.exceptions import APIError, DataError


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    SUBSCRIBING = "subscribing"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketHandler:
    """Handles WebSocket connections for real-time market data streaming."""
    
    def __init__(self, 
                 on_quote: Optional[Callable[[Quote], None]] = None,
                 on_trade: Optional[Callable[[Dict], None]] = None,
                 on_error: Optional[Callable[[Exception], None]] = None):
        """Initialize WebSocket handler."""
        if websockets is None:
            raise ImportError("websockets library is required for WebSocket functionality")
        
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._websocket = None
        self._connection_url = self._build_connection_url()
        
        # Callbacks
        self._on_quote = on_quote
        self._on_trade = on_trade
        self._on_error = on_error
        
        # Subscriptions
        self._subscribed_symbols: Set[str] = set()
        self._subscription_channels: Set[str] = set()
        
        # Reconnection settings
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 1.0
        self._reconnect_attempts = 0
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 30.0
        
        # Message handling
        self._message_handlers: Dict[str, Callable] = {
            MessageType.QUOTE.value: self._handle_quote,
            MessageType.TRADE.value: self._handle_trade,
            MessageType.STATUS.value: self._handle_status,
            MessageType.ERROR.value: self._handle_error_message
        }
        
        # Statistics
        self._messages_received = 0
        self._last_message_time = None
        self._connection_start_time = None
    
    def _build_connection_url(self) -> str:
        """Build WebSocket connection URL based on configuration."""
        if "paper" in self.config.alpaca.base_url:
            return "wss://stream.data.alpaca.markets/v2/iex"
        else:
            return "wss://stream.data.alpaca.markets/v2/sip"
    
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and authenticated."""
        return self._state in [ConnectionState.AUTHENTICATED, ConnectionState.STREAMING]
    
    @property
    def subscribed_symbols(self) -> Set[str]:
        """Get currently subscribed symbols."""
        return self._subscribed_symbols.copy()
    
    async def connect(self) -> bool:
        """Establish WebSocket connection and authenticate."""
        if self._state != ConnectionState.DISCONNECTED:
            self.logger.warning("WebSocket already connected or connecting")
            return self.is_connected
        
        try:
            self._state = ConnectionState.CONNECTING
            self.logger.info("Connecting to WebSocket", url=self._connection_url)
            
            # Create SSL context for secure connection
            ssl_context = ssl.create_default_context()
            
            # Connect to WebSocket
            self._websocket = await websockets.connect(
                self._connection_url,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self._state = ConnectionState.CONNECTED
            self._connection_start_time = time.time()
            self.logger.info("WebSocket connected successfully")
            
            # Authenticate
            if await self._authenticate():
                self._state = ConnectionState.AUTHENTICATED
                self._reconnect_attempts = 0
                self.logger.info("WebSocket authenticated successfully")
                
                # Start message handling task
                asyncio.create_task(self._message_loop())
                asyncio.create_task(self._heartbeat_loop())
                
                return True
            else:
                await self.disconnect()
                return False
                
        except Exception as e:
            self._state = ConnectionState.ERROR
            self.logger.error("Failed to connect WebSocket", error=str(e))
            if self._on_error:
                self._on_error(APIError(f"WebSocket connection failed: {e}"))
            return False
    
    async def _authenticate(self) -> bool:
        """Authenticate with the WebSocket server."""
        try:
            self._state = ConnectionState.AUTHENTICATING
            
            auth_message = {
                "action": "auth",
                "key": self.config.alpaca.api_key,
                "secret": self.config.alpaca.secret_key
            }
            
            await self._send_message(auth_message)
            
            # Wait for authentication response
            response = await asyncio.wait_for(
                self._websocket.recv(), 
                timeout=10.0
            )
            
            auth_response = json.loads(response)
            self.logger.info("Authentication response received", response=auth_response)
            
            # Handle response as list or single object
            if isinstance(auth_response, list):
                auth_response = auth_response[0] if auth_response else {}
            
            if auth_response.get("T") == "success":
                self.logger.info("WebSocket authentication successful")
                return True
            else:
                error_msg = auth_response.get("msg", "Authentication failed")
                self.logger.error("WebSocket authentication failed", 
                                error=error_msg, 
                                response=auth_response)
                return False
                
        except asyncio.TimeoutError:
            self.logger.error("WebSocket authentication timeout")
            return False
        except Exception as e:
            self.logger.error("WebSocket authentication error", error=str(e))
            return False
    
    async def subscribe(self, symbols: List[str], channels: List[str] = None) -> bool:
        """Subscribe to market data for specified symbols."""
        if not self.is_connected:
            self.logger.error("Cannot subscribe: WebSocket not connected")
            return False
        
        if channels is None:
            channels = ["quotes", "trades"]
        
        try:
            self._state = ConnectionState.SUBSCRIBING
            
            subscribe_message = {
                "action": "subscribe",
                "quotes": symbols if "quotes" in channels else [],
                "trades": symbols if "trades" in channels else [],
                "bars": symbols if "bars" in channels else []
            }
            
            await self._send_message(subscribe_message)
            
            # Update subscriptions
            self._subscribed_symbols.update(symbols)
            self._subscription_channels.update(channels)
            
            self._state = ConnectionState.STREAMING
            self.logger.info("Subscribed to symbols", 
                           symbols=symbols, 
                           channels=channels)
            return True
            
        except Exception as e:
            self.logger.error("Failed to subscribe", error=str(e))
            if self._on_error:
                self._on_error(APIError(f"Subscription failed: {e}"))
            return False
    
    async def unsubscribe(self, symbols: List[str], channels: List[str] = None) -> bool:
        """Unsubscribe from market data for specified symbols."""
        if not self.is_connected:
            self.logger.error("Cannot unsubscribe: WebSocket not connected")
            return False
        
        if channels is None:
            channels = ["quotes", "trades"]
        
        try:
            unsubscribe_message = {
                "action": "unsubscribe",
                "quotes": symbols if "quotes" in channels else [],
                "trades": symbols if "trades" in channels else [],
                "bars": symbols if "bars" in channels else []
            }
            
            await self._send_message(unsubscribe_message)
            
            # Update subscriptions
            self._subscribed_symbols.difference_update(symbols)
            
            self.logger.info("Unsubscribed from symbols", 
                           symbols=symbols, 
                           channels=channels)
            return True
            
        except Exception as e:
            self.logger.error("Failed to unsubscribe", error=str(e))
            if self._on_error:
                self._on_error(APIError(f"Unsubscription failed: {e}"))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self._websocket and not self._websocket.closed:
            try:
                await self._websocket.close()
                self.logger.info("WebSocket disconnected")
            except Exception as e:
                self.logger.error("Error during disconnect", error=str(e))
        
        self._state = ConnectionState.DISCONNECTED
        self._websocket = None
        self._subscribed_symbols.clear()
        self._subscription_channels.clear()
    
    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send message to WebSocket server."""
        if not self._websocket or self._websocket.closed:
            raise APIError("WebSocket not connected")
        
        message_str = json.dumps(message)
        await self._websocket.send(message_str)
        self.logger.debug("Sent WebSocket message", websocket_message=message_str[:200])
    
    async def _message_loop(self) -> None:
        """Main message processing loop."""
        try:
            while self._websocket and not self._websocket.closed:
                try:
                    message = await asyncio.wait_for(
                        self._websocket.recv(), 
                        timeout=60.0
                    )
                    
                    await self._process_message(message)
                    self._messages_received += 1
                    self._last_message_time = time.time()
                    
                except asyncio.TimeoutError:
                    self.logger.warning("WebSocket message timeout")
                    continue
                except ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    break
                    
        except Exception as e:
            self.logger.error("Error in message loop", error=str(e))
        finally:
            await self._handle_disconnection()
    
    async def _process_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Handle array of messages
            if isinstance(data, list):
                for item in data:
                    await self._handle_single_message(item)
            else:
                await self._handle_single_message(data)
                
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse WebSocket message", 
                            message=message[:200], 
                            error=str(e))
            if self._on_error:
                self._on_error(DataError(f"Invalid JSON message: {e}"))
        except Exception as e:
            self.logger.error("Error processing message", error=str(e))
            if self._on_error:
                self._on_error(DataError(f"Message processing error: {e}"))
    
    async def _handle_single_message(self, data: Dict[str, Any]) -> None:
        """Handle a single parsed message."""
        message_type = data.get("T")
        
        if message_type in self._message_handlers:
            await self._message_handlers[message_type](data)
        else:
            self.logger.debug("Unknown message type", 
                            message_type=message_type, 
                            data=str(data)[:200])
    
    async def _handle_quote(self, data: Dict[str, Any]) -> None:
        """Handle quote message."""
        try:
            quote = Quote(
                symbol=data["S"],
                timestamp=datetime.fromtimestamp(data["t"] / 1000000000, tz=timezone.utc),
                bid=Decimal(str(data["bp"])),
                ask=Decimal(str(data["ap"])),
                bid_size=data["bs"],
                ask_size=data["as"]
            )
            
            self.logger.debug("Received quote", 
                            symbol=quote.symbol, 
                            bid=float(quote.bid), 
                            ask=float(quote.ask))
            
            if self._on_quote:
                self._on_quote(quote)
                
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error("Invalid quote data", data=data, error=str(e))
            if self._on_error:
                self._on_error(DataError(f"Invalid quote data: {e}"))
    
    async def _handle_trade(self, data: Dict[str, Any]) -> None:
        """Handle trade message."""
        try:
            trade_data = {
                "symbol": data["S"],
                "timestamp": datetime.fromtimestamp(data["t"] / 1000000000, tz=timezone.utc),
                "price": Decimal(str(data["p"])),
                "size": data["s"],
                "conditions": data.get("c", [])
            }
            
            self.logger.debug("Received trade", 
                            symbol=trade_data["symbol"], 
                            price=float(trade_data["price"]), 
                            size=trade_data["size"])
            
            if self._on_trade:
                self._on_trade(trade_data)
                
        except (KeyError, ValueError, TypeError) as e:
            self.logger.error("Invalid trade data", data=data, error=str(e))
            if self._on_error:
                self._on_error(DataError(f"Invalid trade data: {e}"))
    
    async def _handle_status(self, data: Dict[str, Any]) -> None:
        """Handle status message."""
        status = data.get("msg", "Unknown status")
        self.logger.info("WebSocket status", status=status)
    
    async def _handle_error_message(self, data: Dict[str, Any]) -> None:
        """Handle error message from server."""
        error_msg = data.get("msg", "Unknown error")
        error_code = data.get("code")
        
        self.logger.error("WebSocket server error", 
                        error=error_msg, 
                        code=error_code)
        
        if self._on_error:
            self._on_error(APIError(f"Server error: {error_msg}", status_code=error_code))
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop to monitor connection health."""
        while self.is_connected:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                # Check if we've received messages recently
                if (self._last_message_time and 
                    time.time() - self._last_message_time > self._heartbeat_interval * 2):
                    self.logger.warning("No messages received recently, connection may be stale")
                
                # Update heartbeat timestamp
                self._last_heartbeat = time.time()
                
            except Exception as e:
                self.logger.error("Error in heartbeat loop", error=str(e))
                break
    
    async def _handle_disconnection(self) -> None:
        """Handle WebSocket disconnection and attempt reconnection."""
        self.logger.warning("WebSocket disconnected, attempting reconnection")
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            await self._attempt_reconnection()
        else:
            self.logger.error("Max reconnection attempts reached, giving up")
            self._state = ConnectionState.ERROR
            if self._on_error:
                self._on_error(APIError("WebSocket connection lost and reconnection failed"))
    
    async def _attempt_reconnection(self) -> None:
        """Attempt to reconnect to WebSocket server."""
        self._state = ConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        
        # Exponential backoff
        delay = min(self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)), 60)
        
        self.logger.info("Attempting reconnection", 
                        attempt=self._reconnect_attempts, 
                        delay=delay)
        
        await asyncio.sleep(delay)
        
        # Store current subscriptions
        symbols_to_resubscribe = self._subscribed_symbols.copy()
        channels_to_resubscribe = self._subscription_channels.copy()
        
        # Reset state
        await self.disconnect()
        
        # Attempt reconnection
        if await self.connect():
            # Resubscribe to previous symbols
            if symbols_to_resubscribe:
                await self.subscribe(list(symbols_to_resubscribe), 
                                   list(channels_to_resubscribe))
            
            self.logger.info("WebSocket reconnection successful")
        else:
            self.logger.error("WebSocket reconnection failed")
            # Will retry in next iteration if attempts remain
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection and message statistics."""
        uptime = None
        if self._connection_start_time:
            uptime = time.time() - self._connection_start_time
        
        return {
            "state": self._state.value,
            "connected": self.is_connected,
            "uptime_seconds": uptime,
            "messages_received": self._messages_received,
            "last_message_time": self._last_message_time,
            "subscribed_symbols": len(self._subscribed_symbols),
            "reconnect_attempts": self._reconnect_attempts,
            "last_heartbeat": self._last_heartbeat
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


class MessageType(Enum):
    """WebSocket message types."""
    AUTH = "auth"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    QUOTE = "q"
    TRADE = "t"
    BAR = "b"
    STATUS = "status"
    ERROR = "error"