"""
Integration tests for OrderExecutor with Alpaca paper trading.

These tests use the Alpaca paper trading environment to test
real order execution scenarios safely.
"""

import pytest
import os
from decimal import Decimal
from datetime import datetime, timezone
import time

from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.execution.order_executor import (
    OrderExecutor, OrderRequest, ExecutionStrategy
)
from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.models.core import OrderSide, OrderType, OrderStatus


@pytest.mark.integration
class TestOrderExecutorIntegration:
    """Integration tests for OrderExecutor with Alpaca paper trading."""
    
    @pytest.fixture(scope="class")
    def alpaca_config(self):
        """Create Alpaca configuration for paper trading."""
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            pytest.skip("Alpaca API credentials not available")
        
        return AlpacaConfig(
            api_key=api_key,
            secret_key=secret_key,
            environment=Environment.PAPER,
            data_feed=DataFeed.IEX
        )
    
    @pytest.fixture(scope="class")
    def alpaca_client(self, alpaca_config):
        """Create and authenticate Alpaca client."""
        client = AlpacaClient(alpaca_config)
        
        # Authenticate
        success = client.authenticate()
        if not success:
            pytest.skip("Failed to authenticate with Alpaca API")
        
        return client
    
    @pytest.fixture
    def order_executor(self, alpaca_client):
        """Create OrderExecutor instance."""
        return OrderExecutor(alpaca_client)
    
    def test_market_buy_order_execution(self, order_executor, alpaca_client):
        """Test executing a market buy order."""
        # Skip if market is closed
        if not alpaca_client.is_market_open():
            pytest.skip("Market is closed, cannot test market orders")
        
        # Create market buy order request
        request = OrderRequest(
            symbol="SPY",  # Use liquid ETF
            quantity=1,    # Small quantity for testing
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution
        assert result.success is True
        assert result.order_id is not None
        assert result.filled_quantity >= 0
        
        # If order was filled, verify details
        if result.filled_quantity > 0:
            assert result.average_fill_price is not None
            assert result.average_fill_price > 0
        
        # Clean up - cancel if not filled
        if result.remaining_quantity > 0:
            order_executor.cancel_order(result.order_id)
    
    def test_limit_buy_order_execution(self, order_executor):
        """Test executing a limit buy order."""
        # Create limit buy order request with low price (unlikely to fill)
        request = OrderRequest(
            symbol="SPY",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('100.00'),  # Low price, unlikely to fill
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution
        assert result.success is True
        assert result.order_id is not None
        assert result.remaining_quantity > 0  # Should not fill at low price
        
        # Verify order status
        order_status = order_executor.get_order_status(result.order_id)
        assert order_status is not None
        assert order_status.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
        
        # Clean up
        cancel_result = order_executor.cancel_order(result.order_id)
        assert cancel_result is True
        
        # Verify cancellation
        time.sleep(1)  # Wait for cancellation to process
        final_status = order_executor.get_order_status(result.order_id)
        if final_status:
            assert final_status.status == OrderStatus.CANCELLED
    
    def test_limit_sell_order_execution(self, order_executor, alpaca_client):
        """Test executing a limit sell order."""
        # First check if we have any positions to sell
        positions = alpaca_client.get_positions()
        
        if not positions:
            pytest.skip("No positions available for sell order test")
        
        # Find a position with sufficient quantity
        position = None
        for pos in positions:
            if pos['quantity'] > 0:  # Long position
                position = pos
                break
        
        if not position:
            pytest.skip("No long positions available for sell order test")
        
        # Create limit sell order with high price (unlikely to fill)
        request = OrderRequest(
            symbol=position['symbol'],
            quantity=1,  # Sell 1 share
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=Decimal(str(position['current_price'])) * Decimal('2.0'),  # High price
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution
        assert result.success is True
        assert result.order_id is not None
        
        # Clean up
        order_executor.cancel_order(result.order_id)
    
    def test_smart_execution_strategy(self, order_executor):
        """Test smart execution strategy routing."""
        # Create order with smart strategy
        request = OrderRequest(
            symbol="SPY",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('200.00'),  # Reasonable price
            execution_strategy=ExecutionStrategy.SMART
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution
        assert result.success is True
        assert result.order_id is not None
        
        # Clean up
        order_executor.cancel_order(result.order_id)
    
    def test_iceberg_execution_strategy(self, order_executor):
        """Test iceberg execution strategy."""
        # Create large order with iceberg strategy
        request = OrderRequest(
            symbol="SPY",
            quantity=100,  # Larger quantity to trigger iceberg
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('100.00'),  # Low price
            execution_strategy=ExecutionStrategy.ICEBERG
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution (should execute first chunk)
        assert result.success is True
        assert result.order_id is not None
        
        # Clean up
        order_executor.cancel_order(result.order_id)
    
    def test_order_status_monitoring(self, order_executor):
        """Test order status monitoring functionality."""
        # Create limit order that won't fill immediately
        request = OrderRequest(
            symbol="SPY",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('100.00'),
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        assert result.success is True
        
        # Monitor order status
        initial_status = order_executor.get_order_status(result.order_id)
        assert initial_status is not None
        assert initial_status.status in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
        
        # Wait a moment and check again
        time.sleep(2)
        updated_status = order_executor.get_order_status(result.order_id)
        assert updated_status is not None
        
        # Clean up
        order_executor.cancel_order(result.order_id)
    
    def test_execution_callback_registration(self, order_executor):
        """Test execution callback registration and triggering."""
        callback_called = []
        
        def test_callback(order):
            callback_called.append(order)
        
        # Create order
        request = OrderRequest(
            symbol="SPY",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('100.00'),
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        assert result.success is True
        
        # Register callback
        order_executor.register_execution_callback(result.order_id, test_callback)
        
        # Cancel order to trigger status change
        order_executor.cancel_order(result.order_id)
        
        # Note: In a real scenario, we would wait for the monitoring thread
        # to detect the status change and call the callback
        # For this test, we just verify the callback was registered
        assert result.order_id in order_executor._execution_callbacks
        assert test_callback in order_executor._execution_callbacks[result.order_id]
    
    def test_execution_statistics(self, order_executor):
        """Test execution statistics tracking."""
        # Get initial statistics
        initial_stats = order_executor.get_execution_statistics()
        initial_total = initial_stats['total_orders']
        
        # Execute a few orders
        for i in range(3):
            request = OrderRequest(
                symbol="SPY",
                quantity=1,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                limit_price=Decimal('100.00'),
                execution_strategy=ExecutionStrategy.IMMEDIATE
            )
            
            result = order_executor.execute_order(request)
            if result.success:
                order_executor.cancel_order(result.order_id)
        
        # Get updated statistics
        final_stats = order_executor.get_execution_statistics()
        
        # Verify statistics were updated
        assert final_stats['total_orders'] >= initial_total + 3
        assert final_stats['successful_executions'] >= initial_stats.get('successful_executions', 0)
        assert 'success_rate' in final_stats
        assert 'average_execution_time' in final_stats
    
    def test_insufficient_funds_handling(self, order_executor, alpaca_client):
        """Test handling of insufficient funds scenario."""
        # Get account info
        account_info = alpaca_client.get_account_info()
        buying_power = Decimal(str(account_info['buying_power']))
        
        # Create order that exceeds buying power
        request = OrderRequest(
            symbol="SPY",
            quantity=int(buying_power) + 1000,  # Exceed buying power
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order should fail with insufficient funds
        with pytest.raises(Exception):  # Could be InsufficientFundsError or TradingError
            order_executor.execute_order(request)
    
    def test_invalid_symbol_handling(self, order_executor):
        """Test handling of invalid symbol."""
        # Create order with invalid symbol
        request = OrderRequest(
            symbol="INVALID_SYMBOL_XYZ",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order should fail
        result = order_executor.execute_order(request)
        assert result.success is False
        assert result.error_message is not None
    
    def test_market_closed_handling(self, order_executor, alpaca_client):
        """Test order execution when market is closed."""
        # This test will pass regardless of market status
        # When market is closed, orders are queued for next open
        
        request = OrderRequest(
            symbol="SPY",
            quantity=1,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('200.00'),
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Should succeed even if market is closed (order gets queued)
        assert result.success is True
        assert result.order_id is not None
        
        # Clean up
        order_executor.cancel_order(result.order_id)
    
    def teardown_method(self, method):
        """Clean up after each test method."""
        # This method runs after each test to ensure cleanup
        pass
    
    @classmethod
    def teardown_class(cls):
        """Clean up after all tests in this class."""
        # This method runs after all tests in the class
        pass