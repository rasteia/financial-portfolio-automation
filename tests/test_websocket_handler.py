"""
Tests for WebSocket handler functionality.

This module contains unit and integration tests for the WebSocket handler,
including connection management, message processing, and error handling.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from financial_portfolio_automation.api.websocket_handler import (
    WebSocketHandler, ConnectionState
)
from financial_portfolio_automation.models.core import Quote
from financial_portfolio_automation.exceptions import APIError, DataError


class TestWebSocketHandler:
    """Test cases for WebSocketHandler class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.alpaca.api_key = "test_api_key"
        config.alpaca.secret_key = "test_secret_key"
        config.alpaca.base_url = "https://paper-api.alpaca.markets"
        return config
    
    @pytest.fixture
    def websocket_handler(self, mock_config):
        """Create WebSocket handler instance for testing."""
        with patch('financial_portfolio_automation.api.websocket_handler.get_config', return_value=mock_config):
            with patch('financial_portfolio_automation.api.websocket_handler.get_logger') as mock_logger:
                mock_logger.return_value = Mock()
                handler = WebSocketHandler()
                return handler
    
    def test_initialization(self, websocket_handler):
        """Test WebSocket handler initialization."""
        assert websocket_handler.state == ConnectionState.DISCONNECTED
        assert not websocket_handler.is_connected
        assert len(websocket_handler.subscribed_symbols) == 0
        assert websocket_handler._connection_url == "wss://stream.data.alpaca.markets/v2/iex"
    
    def test_build_connection_url_paper(self, mock_config):
        """Test connection URL building for paper trading."""
        mock_config.alpaca.base_url = "https://paper-api.alpaca.markets"
        with patch('financial_portfolio_automation.api.websocket_handler.get_config', return_value=mock_config):
            handler = WebSocketHandler()
            assert handler._connection_url == "wss://stream.data.alpaca.markets/v2/iex"
    
    def test_build_connection_url_live(self, mock_config):
        """Test connection URL building for live trading."""
        mock_config.alpaca.base_url = "https://api.alpaca.markets"
        with patch('financial_portfolio_automation.api.websocket_handler.get_config', return_value=mock_config):
            handler = WebSocketHandler()
            assert handler._connection_url == "wss://stream.data.alpaca.markets/v2/sip"
    
    @pytest.mark.asyncio
    async def test_connect_success(self, websocket_handler):
        """Test successful WebSocket connection."""
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        
        async def mock_connect_func(*args, **kwargs):
            return mock_websocket
        
        with patch('websockets.connect', side_effect=mock_connect_func) as mock_connect:
            with patch.object(websocket_handler, '_authenticate', return_value=True) as mock_auth:
                with patch('asyncio.create_task'):
                    result = await websocket_handler.connect()
                    
                    assert result is True
                    mock_auth.assert_called_once()
                    assert websocket_handler.state == ConnectionState.AUTHENTICATED
                    assert websocket_handler.is_connected
                    mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, websocket_handler):
        """Test WebSocket connection with authentication failure."""
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        
        async def mock_connect_func(*args, **kwargs):
            return mock_websocket
        
        with patch('websockets.connect', side_effect=mock_connect_func):
            with patch.object(websocket_handler, '_authenticate', return_value=False):
                with patch.object(websocket_handler, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                    result = await websocket_handler.connect()
                    
                    assert result is False
                    mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self, websocket_handler):
        """Test connecting when already connected."""
        websocket_handler._state = ConnectionState.CONNECTED
        
        result = await websocket_handler.connect()
        assert result is False  # Should return current connection status
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, websocket_handler):
        """Test successful authentication."""
        mock_websocket = AsyncMock()
        mock_websocket.recv.return_value = json.dumps({"T": "success"})
        mock_websocket.closed = False
        websocket_handler._websocket = mock_websocket
        
        result = await websocket_handler._authenticate()
        
        assert result is True
        mock_websocket.send.assert_called_once()
        mock_websocket.recv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, websocket_handler):
        """Test authentication failure."""
        mock_websocket = AsyncMock()
        mock_websocket.recv.return_value = json.dumps({"T": "error", "msg": "Invalid credentials"})
        websocket_handler._websocket = mock_websocket
        
        result = await websocket_handler._authenticate()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_authenticate_timeout(self, websocket_handler):
        """Test authentication timeout."""
        mock_websocket = AsyncMock()
        mock_websocket.recv.side_effect = asyncio.TimeoutError()
        websocket_handler._websocket = mock_websocket
        
        result = await websocket_handler._authenticate()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_subscribe_success(self, websocket_handler):
        """Test successful subscription."""
        websocket_handler._state = ConnectionState.AUTHENTICATED
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        websocket_handler._websocket = mock_websocket
        
        result = await websocket_handler.subscribe(["AAPL", "GOOGL"], ["quotes", "trades"])
        
        assert result is True
        assert websocket_handler.state == ConnectionState.STREAMING
        assert "AAPL" in websocket_handler.subscribed_symbols
        assert "GOOGL" in websocket_handler.subscribed_symbols
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, websocket_handler):
        """Test subscription when not connected."""
        result = await websocket_handler.subscribe(["AAPL"])
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_unsubscribe_success(self, websocket_handler):
        """Test successful unsubscription."""
        websocket_handler._state = ConnectionState.STREAMING
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        websocket_handler._websocket = mock_websocket
        websocket_handler._subscribed_symbols = {"AAPL", "GOOGL"}
        
        result = await websocket_handler.unsubscribe(["AAPL"])
        
        assert result is True
        assert "AAPL" not in websocket_handler.subscribed_symbols
        assert "GOOGL" in websocket_handler.subscribed_symbols
        mock_websocket.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, websocket_handler):
        """Test WebSocket disconnection."""
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        websocket_handler._websocket = mock_websocket
        websocket_handler._subscribed_symbols = {"AAPL"}
        
        await websocket_handler.disconnect()
        
        assert websocket_handler.state == ConnectionState.DISCONNECTED
        assert len(websocket_handler.subscribed_symbols) == 0
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message(self, websocket_handler):
        """Test sending message to WebSocket."""
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        websocket_handler._websocket = mock_websocket
        
        message = {"action": "test"}
        await websocket_handler._send_message(message)
        
        mock_websocket.send.assert_called_once_with(json.dumps(message))
    
    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, websocket_handler):
        """Test sending message when not connected."""
        with pytest.raises(APIError):
            await websocket_handler._send_message({"action": "test"})
    
    @pytest.mark.asyncio
    async def test_process_message_single(self, websocket_handler):
        """Test processing single message."""
        quote_data = {
            "T": "q",
            "S": "AAPL",
            "t": 1640995200000000000,  # nanoseconds
            "bp": 150.50,
            "ap": 150.55,
            "bs": 100,
            "as": 200
        }
        
        mock_callback = Mock()
        websocket_handler._on_quote = mock_callback
        
        await websocket_handler._process_message(json.dumps(quote_data))
        
        mock_callback.assert_called_once()
        quote = mock_callback.call_args[0][0]
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.bid == Decimal("150.50")
        assert quote.ask == Decimal("150.55")
    
    @pytest.mark.asyncio
    async def test_process_message_array(self, websocket_handler):
        """Test processing array of messages."""
        messages = [
            {"T": "q", "S": "AAPL", "t": 1640995200000000000, "bp": 150.50, "ap": 150.55, "bs": 100, "as": 200},
            {"T": "q", "S": "GOOGL", "t": 1640995200000000000, "bp": 2800.00, "ap": 2800.50, "bs": 50, "as": 75}
        ]
        
        mock_callback = Mock()
        websocket_handler._on_quote = mock_callback
        
        await websocket_handler._process_message(json.dumps(messages))
        
        assert mock_callback.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_invalid_json(self, websocket_handler):
        """Test processing invalid JSON message."""
        mock_error_callback = Mock()
        websocket_handler._on_error = mock_error_callback
        
        await websocket_handler._process_message("invalid json")
        
        mock_error_callback.assert_called_once()
        error = mock_error_callback.call_args[0][0]
        assert isinstance(error, DataError)
    
    @pytest.mark.asyncio
    async def test_handle_quote_valid(self, websocket_handler):
        """Test handling valid quote message."""
        quote_data = {
            "T": "q",
            "S": "AAPL",
            "t": 1640995200000000000,
            "bp": 150.50,
            "ap": 150.55,
            "bs": 100,
            "as": 200
        }
        
        mock_callback = Mock()
        websocket_handler._on_quote = mock_callback
        
        await websocket_handler._handle_quote(quote_data)
        
        mock_callback.assert_called_once()
        quote = mock_callback.call_args[0][0]
        assert quote.symbol == "AAPL"
        assert quote.bid == Decimal("150.50")
        assert quote.ask == Decimal("150.55")
        assert quote.bid_size == 100
        assert quote.ask_size == 200
    
    @pytest.mark.asyncio
    async def test_handle_quote_invalid(self, websocket_handler):
        """Test handling invalid quote message."""
        invalid_quote_data = {"T": "q", "S": "AAPL"}  # Missing required fields
        
        mock_error_callback = Mock()
        websocket_handler._on_error = mock_error_callback
        
        await websocket_handler._handle_quote(invalid_quote_data)
        
        mock_error_callback.assert_called_once()
        error = mock_error_callback.call_args[0][0]
        assert isinstance(error, DataError)
    
    @pytest.mark.asyncio
    async def test_handle_trade_valid(self, websocket_handler):
        """Test handling valid trade message."""
        trade_data = {
            "T": "t",
            "S": "AAPL",
            "t": 1640995200000000000,
            "p": 150.75,
            "s": 100,
            "c": ["@"]
        }
        
        mock_callback = Mock()
        websocket_handler._on_trade = mock_callback
        
        await websocket_handler._handle_trade(trade_data)
        
        mock_callback.assert_called_once()
        trade = mock_callback.call_args[0][0]
        assert trade["symbol"] == "AAPL"
        assert trade["price"] == Decimal("150.75")
        assert trade["size"] == 100
        assert trade["conditions"] == ["@"]
    
    @pytest.mark.asyncio
    async def test_handle_status_message(self, websocket_handler):
        """Test handling status message."""
        status_data = {"T": "status", "msg": "Connected successfully"}
        
        # Should not raise any exceptions
        await websocket_handler._handle_status(status_data)
    
    @pytest.mark.asyncio
    async def test_handle_error_message(self, websocket_handler):
        """Test handling error message from server."""
        error_data = {"T": "error", "msg": "Invalid symbol", "code": 400}
        
        mock_error_callback = Mock()
        websocket_handler._on_error = mock_error_callback
        
        await websocket_handler._handle_error_message(error_data)
        
        mock_error_callback.assert_called_once()
        error = mock_error_callback.call_args[0][0]
        assert isinstance(error, APIError)
        assert "Invalid symbol" in str(error)
    
    def test_get_statistics(self, websocket_handler):
        """Test getting connection statistics."""
        websocket_handler._messages_received = 100
        websocket_handler._reconnect_attempts = 2
        
        stats = websocket_handler.get_statistics()
        
        assert stats["state"] == ConnectionState.DISCONNECTED.value
        assert stats["connected"] is False
        assert stats["messages_received"] == 100
        assert stats["reconnect_attempts"] == 2
        assert "uptime_seconds" in stats
        assert "subscribed_symbols" in stats
    
    @pytest.mark.asyncio
    async def test_context_manager(self, websocket_handler):
        """Test WebSocket handler as async context manager."""
        with patch.object(websocket_handler, 'connect', return_value=True) as mock_connect:
            with patch.object(websocket_handler, 'disconnect') as mock_disconnect:
                async with websocket_handler as handler:
                    assert handler is websocket_handler
                
                mock_connect.assert_called_once()
                mock_disconnect.assert_called_once()


class TestWebSocketHandlerIntegration:
    """Integration tests for WebSocket handler."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_connection_flow(self):
        """Test complete connection, subscription, and disconnection flow."""
        # This would require actual WebSocket server or mock server
        # For now, we'll test the flow with mocked components
        
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        mock_websocket.recv.side_effect = [
            json.dumps({"T": "success"}),  # Auth response
            json.dumps({"T": "status", "msg": "subscribed"}),  # Subscribe response
        ]
        
        quote_received = []
        
        def on_quote(quote):
            quote_received.append(quote)
        
        async def mock_connect_func(*args, **kwargs):
            return mock_websocket
        
        with patch('websockets.connect', side_effect=mock_connect_func):
            with patch('financial_portfolio_automation.api.websocket_handler.get_config') as mock_get_config:
                # Setup mock config
                mock_config = Mock()
                mock_config.alpaca.api_key = "test_key"
                mock_config.alpaca.secret_key = "test_secret"
                mock_config.alpaca.base_url = "https://paper-api.alpaca.markets"
                mock_get_config.return_value = mock_config
                
                handler = WebSocketHandler(on_quote=on_quote)
                
                # Test connection
                connected = await handler.connect()
                assert connected is True
                assert handler.is_connected
                
                # Test subscription
                subscribed = await handler.subscribe(["AAPL"], ["quotes"])
                assert subscribed is True
                assert "AAPL" in handler.subscribed_symbols
                
                # Test disconnection
                await handler.disconnect()
                assert handler.state == ConnectionState.DISCONNECTED
                assert len(handler.subscribed_symbols) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_reconnection_logic(self):
        """Test automatic reconnection logic."""
        mock_websocket = AsyncMock()
        mock_websocket.closed = False
        
        # First connection succeeds, then fails, then succeeds again
        connect_calls = 0
        
        async def mock_connect(*args, **kwargs):
            nonlocal connect_calls
            connect_calls += 1
            if connect_calls == 1:
                return mock_websocket
            elif connect_calls == 2:
                raise ConnectionError("Connection failed")
            else:
                return mock_websocket
        
        with patch('websockets.connect', side_effect=mock_connect):
            with patch('financial_portfolio_automation.api.websocket_handler.get_config') as mock_get_config:
                mock_config = Mock()
                mock_config.alpaca.api_key = "test_key"
                mock_config.alpaca.secret_key = "test_secret"
                mock_config.alpaca.base_url = "https://paper-api.alpaca.markets"
                mock_get_config.return_value = mock_config
                
                handler = WebSocketHandler()
                handler._max_reconnect_attempts = 3
                handler._reconnect_delay = 0.1  # Fast reconnection for testing
                
                # Mock authentication response
                mock_websocket.recv.return_value = json.dumps({"T": "success"})
                
                # Initial connection should succeed
                with patch('asyncio.create_task'):
                    connected = await handler.connect()
                    assert connected is True
                
                # Simulate disconnection and test reconnection
                with patch.object(handler, '_authenticate', return_value=True):
                    await handler._handle_disconnection()
                    
                    # Should eventually reconnect
                    await asyncio.sleep(0.5)  # Allow time for reconnection attempts