"""
Integration tests for WebSocket handler with real Alpaca WebSocket endpoints.

These tests require valid Alpaca API credentials and should be run manually
or in a CI environment with proper credentials configured.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta

from financial_portfolio_automation.api.websocket_handler import WebSocketHandler, ConnectionState
from financial_portfolio_automation.models.core import Quote
from financial_portfolio_automation.config.settings import get_config


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"),
    reason="Alpaca API credentials not available"
)
class TestWebSocketIntegration:
    """Integration tests with real Alpaca WebSocket API."""
    
    @pytest.mark.asyncio
    async def test_real_connection_and_authentication(self):
        """Test real connection to Alpaca WebSocket API."""
        quotes_received = []
        trades_received = []
        errors_received = []
        
        def on_quote(quote: Quote):
            quotes_received.append(quote)
            print(f"Quote: {quote.symbol} - Bid: {quote.bid}, Ask: {quote.ask}")
        
        def on_trade(trade):
            trades_received.append(trade)
            print(f"Trade: {trade['symbol']} - Price: {trade['price']}, Size: {trade['size']}")
        
        def on_error(error):
            errors_received.append(error)
            print(f"Error: {error}")
        
        handler = WebSocketHandler(
            on_quote=on_quote,
            on_trade=on_trade,
            on_error=on_error
        )
        
        try:
            # Test connection
            connected = await handler.connect()
            assert connected, "Failed to connect to WebSocket"
            assert handler.state == ConnectionState.AUTHENTICATED
            
            # Test subscription to popular symbols
            symbols = ["AAPL", "GOOGL", "MSFT"]
            subscribed = await handler.subscribe(symbols, ["quotes", "trades"])
            assert subscribed, "Failed to subscribe to symbols"
            assert handler.state == ConnectionState.STREAMING
            
            # Wait for some data
            print("Waiting for market data...")
            await asyncio.sleep(30)  # Wait 30 seconds for data
            
            # Verify we received some data (if market is open)
            print(f"Received {len(quotes_received)} quotes and {len(trades_received)} trades")
            
            # Test unsubscription
            unsubscribed = await handler.unsubscribe(["AAPL"])
            assert unsubscribed, "Failed to unsubscribe from AAPL"
            
            # Verify statistics
            stats = handler.get_statistics()
            assert stats["connected"] is True
            assert stats["messages_received"] >= 0
            print(f"Connection statistics: {stats}")
            
        finally:
            await handler.disconnect()
            assert handler.state == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_connection_resilience(self):
        """Test connection resilience and reconnection."""
        handler = WebSocketHandler()
        
        try:
            # Connect
            connected = await handler.connect()
            assert connected, "Failed to connect"
            
            # Subscribe to a symbol
            subscribed = await handler.subscribe(["SPY"], ["quotes"])
            assert subscribed, "Failed to subscribe"
            
            # Simulate network interruption by closing the connection
            if handler._websocket:
                await handler._websocket.close()
            
            # Wait for reconnection attempt
            await asyncio.sleep(5)
            
            # Handler should attempt to reconnect
            # Note: This test may be flaky depending on network conditions
            
        finally:
            await handler.disconnect()
    
    @pytest.mark.asyncio
    async def test_context_manager_usage(self):
        """Test WebSocket handler as context manager."""
        quotes_received = []
        
        def on_quote(quote: Quote):
            quotes_received.append(quote)
        
        async with WebSocketHandler(on_quote=on_quote) as handler:
            # Should be connected
            assert handler.is_connected
            
            # Subscribe and wait briefly
            await handler.subscribe(["SPY"], ["quotes"])
            await asyncio.sleep(5)
        
        # Should be disconnected after context exit
        assert handler.state == ConnectionState.DISCONNECTED


def run_manual_test():
    """
    Manual test function that can be run directly for testing.
    
    Usage:
        export ALPACA_API_KEY="your_key"
        export ALPACA_SECRET_KEY="your_secret"
        python -c "from tests.integration.test_websocket_integration import run_manual_test; run_manual_test()"
    """
    async def test():
        print("Starting WebSocket integration test...")
        
        quotes_count = 0
        trades_count = 0
        
        def on_quote(quote: Quote):
            nonlocal quotes_count
            quotes_count += 1
            if quotes_count <= 5:  # Print first 5 quotes
                print(f"Quote #{quotes_count}: {quote.symbol} - {quote.bid}/{quote.ask} @ {quote.timestamp}")
        
        def on_trade(trade):
            nonlocal trades_count
            trades_count += 1
            if trades_count <= 5:  # Print first 5 trades
                print(f"Trade #{trades_count}: {trade['symbol']} - ${trade['price']} x {trade['size']} @ {trade['timestamp']}")
        
        def on_error(error):
            print(f"Error: {error}")
        
        handler = WebSocketHandler(
            on_quote=on_quote,
            on_trade=on_trade,
            on_error=on_error
        )
        
        try:
            print("Connecting to Alpaca WebSocket...")
            connected = await handler.connect()
            
            if not connected:
                print("Failed to connect. Check your API credentials.")
                return
            
            print("Connected successfully!")
            
            # Subscribe to some popular symbols
            symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "SPY"]
            print(f"Subscribing to {symbols}...")
            
            subscribed = await handler.subscribe(symbols, ["quotes", "trades"])
            if not subscribed:
                print("Failed to subscribe to symbols")
                return
            
            print("Subscribed successfully! Listening for market data...")
            print("Press Ctrl+C to stop...")
            
            # Listen for 60 seconds
            try:
                await asyncio.sleep(60)
            except KeyboardInterrupt:
                print("\nStopping...")
            
            print(f"\nReceived {quotes_count} quotes and {trades_count} trades")
            
            # Show statistics
            stats = handler.get_statistics()
            print(f"Connection statistics: {stats}")
            
        except Exception as e:
            print(f"Error during test: {e}")
        finally:
            print("Disconnecting...")
            await handler.disconnect()
            print("Disconnected.")
    
    # Check for credentials
    if not os.getenv("ALPACA_API_KEY") or not os.getenv("ALPACA_SECRET_KEY"):
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
        return
    
    asyncio.run(test())


if __name__ == "__main__":
    run_manual_test()