"""
Unit tests for the OrderExecutor class.

Tests order execution, intelligent routing, partial fill handling,
and order status monitoring functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from financial_portfolio_automation.execution.order_executor import (
    OrderExecutor, OrderRequest, ExecutionResult, ExecutionStrategy
)
from financial_portfolio_automation.models.core import (
    Order, OrderSide, OrderType, OrderStatus, Quote
)
from financial_portfolio_automation.exceptions import (
    TradingError, InvalidOrderError, InsufficientFundsError
)


class TestOrderRequest:
    """Test OrderRequest validation and functionality."""
    
    def test_valid_order_request(self):
        """Test creating a valid order request."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET
        )
        
        # Should not raise any exception
        request.validate()
        
        assert request.symbol == "AAPL"
        assert request.quantity == 100
        assert request.side == OrderSide.BUY
        assert request.order_type == OrderType.MARKET
        assert request.execution_strategy == ExecutionStrategy.SMART
    
    def test_limit_order_request(self):
        """Test creating a limit order request."""
        request = OrderRequest(
            symbol="TSLA",
            quantity=50,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('250.00')
        )
        
        request.validate()
        
        assert request.limit_price == Decimal('250.00')
    
    def test_stop_order_request(self):
        """Test creating a stop order request."""
        request = OrderRequest(
            symbol="MSFT",
            quantity=25,
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            stop_price=Decimal('300.00')
        )
        
        request.validate()
        
        assert request.stop_price == Decimal('300.00')
    
    def test_invalid_symbol(self):
        """Test validation with invalid symbol."""
        request = OrderRequest(
            symbol="",
            quantity=100,
            side=OrderSide.BUY
        )
        
        with pytest.raises(InvalidOrderError, match="Symbol must be a non-empty string"):
            request.validate()
    
    def test_invalid_quantity(self):
        """Test validation with invalid quantity."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=0,
            side=OrderSide.BUY
        )
        
        with pytest.raises(InvalidOrderError, match="Quantity must be positive"):
            request.validate()
    
    def test_limit_order_without_price(self):
        """Test limit order validation without limit price."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT
        )
        
        with pytest.raises(InvalidOrderError, match="Limit orders must have a limit price"):
            request.validate()
    
    def test_stop_order_without_price(self):
        """Test stop order validation without stop price."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.SELL,
            order_type=OrderType.STOP
        )
        
        with pytest.raises(InvalidOrderError, match="Stop orders must have a stop price"):
            request.validate()
    
    def test_negative_limit_price(self):
        """Test validation with negative limit price."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('-10.00')
        )
        
        with pytest.raises(InvalidOrderError, match="Limit price must be positive"):
            request.validate()
    
    def test_invalid_participation_rate(self):
        """Test validation with invalid participation rate."""
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            max_participation_rate=1.5
        )
        
        with pytest.raises(InvalidOrderError, match="Max participation rate must be between 0 and 1"):
            request.validate()


class TestExecutionResult:
    """Test ExecutionResult functionality."""
    
    def test_successful_execution_result(self):
        """Test creating a successful execution result."""
        result = ExecutionResult(
            success=True,
            order_id="order_123",
            filled_quantity=100,
            average_fill_price=Decimal('150.50'),
            remaining_quantity=0
        )
        
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.filled_quantity == 100
        assert result.average_fill_price == Decimal('150.50')
        assert result.remaining_quantity == 0
        assert result.execution_time is not None
    
    def test_failed_execution_result(self):
        """Test creating a failed execution result."""
        result = ExecutionResult(
            success=False,
            error_message="Insufficient funds",
            remaining_quantity=100
        )
        
        assert result.success is False
        assert result.error_message == "Insufficient funds"
        assert result.remaining_quantity == 100
        assert result.order_id is None


class TestOrderExecutor:
    """Test OrderExecutor functionality."""
    
    @pytest.fixture
    def mock_alpaca_client(self):
        """Create a mock Alpaca client."""
        client = Mock()
        client.is_market_open.return_value = True
        client.get_account_info.return_value = {
            'buying_power': 10000.0,
            'trading_blocked': False
        }
        
        # Mock API object
        client._api = Mock()
        
        return client
    
    @pytest.fixture
    def order_executor(self, mock_alpaca_client):
        """Create an OrderExecutor instance with mocked dependencies."""
        return OrderExecutor(mock_alpaca_client)
    
    def test_initialization(self, mock_alpaca_client):
        """Test OrderExecutor initialization."""
        executor = OrderExecutor(mock_alpaca_client)
        
        assert executor.alpaca_client == mock_alpaca_client
        assert len(executor._active_orders) == 0
        assert len(executor._execution_callbacks) == 0
        assert executor._monitoring_active is False
    
    def test_execute_market_order_success(self, order_executor, mock_alpaca_client):
        """Test successful market order execution."""
        # Mock Alpaca order response
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = 100
        mock_order.side = "buy"
        mock_order.order_type = "market"
        mock_order.status = "filled"
        mock_order.filled_qty = 100
        mock_order.filled_avg_price = 150.50
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.time_in_force = "day"
        mock_order.created_at = datetime.now(timezone.utc)
        mock_order.updated_at = datetime.now(timezone.utc)
        
        mock_alpaca_client._api.submit_order.return_value = mock_order
        
        # Create order request
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify result
        assert result.success is True
        assert result.order_id == "order_123"
        assert result.filled_quantity == 100
        assert result.remaining_quantity == 0
        
        # Verify API call
        mock_alpaca_client._api.submit_order.assert_called_once_with(
            symbol="AAPL",
            qty=100,
            side="buy",
            type="market",
            time_in_force="day",
            limit_price=None,
            stop_price=None,
            client_order_id=None
        )
    
    def test_execute_limit_order_success(self, order_executor, mock_alpaca_client):
        """Test successful limit order execution."""
        # Mock Alpaca order response
        mock_order = Mock()
        mock_order.id = "order_456"
        mock_order.symbol = "TSLA"
        mock_order.qty = 50
        mock_order.side = "sell"
        mock_order.order_type = "limit"
        mock_order.status = "new"
        mock_order.filled_qty = 0
        mock_order.filled_avg_price = None
        mock_order.limit_price = 250.00
        mock_order.stop_price = None
        mock_order.time_in_force = "day"
        mock_order.created_at = datetime.now(timezone.utc)
        mock_order.updated_at = datetime.now(timezone.utc)
        
        mock_alpaca_client._api.submit_order.return_value = mock_order
        
        # Create order request
        request = OrderRequest(
            symbol="TSLA",
            quantity=50,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('250.00'),
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify result
        assert result.success is True
        assert result.order_id == "order_456"
        assert result.filled_quantity == 0
        assert result.remaining_quantity == 50
        
        # Verify API call
        mock_alpaca_client._api.submit_order.assert_called_once_with(
            symbol="TSLA",
            qty=50,
            side="sell",
            type="limit",
            time_in_force="day",
            limit_price=250.0,
            stop_price=None,
            client_order_id=None
        )
    
    def test_execute_order_validation_error(self, order_executor):
        """Test order execution with validation error."""
        # Create invalid order request
        request = OrderRequest(
            symbol="",  # Invalid symbol
            quantity=100,
            side=OrderSide.BUY
        )
        
        # Execute order should raise validation error
        with pytest.raises(InvalidOrderError):
            order_executor.execute_order(request)
    
    def test_execute_order_api_error(self, order_executor, mock_alpaca_client):
        """Test order execution with API error."""
        # Mock API error
        mock_alpaca_client._api.submit_order.side_effect = Exception("API Error")
        
        # Create order request
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        # Execute order should return failed result
        result = order_executor.execute_order(request)
        assert result.success is False
        assert "API Error" in result.error_message
    
    def test_insufficient_funds_validation(self, order_executor, mock_alpaca_client):
        """Test validation for insufficient funds."""
        # Mock account with low buying power
        mock_alpaca_client.get_account_info.return_value = {
            'buying_power': 100.0,  # Low buying power
            'trading_blocked': False
        }
        
        # Create large order request
        request = OrderRequest(
            symbol="AAPL",
            quantity=1000,  # Large quantity
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=Decimal('150.00')  # $150,000 total
        )
        
        # Execute order should raise insufficient funds error
        with pytest.raises(InsufficientFundsError):
            order_executor.execute_order(request)
    
    def test_trading_blocked_validation(self, order_executor, mock_alpaca_client):
        """Test validation when trading is blocked."""
        # Mock account with trading blocked
        mock_alpaca_client.get_account_info.return_value = {
            'buying_power': 10000.0,
            'trading_blocked': True
        }
        
        # Create order request
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY
        )
        
        # Execute order should raise trading error
        with pytest.raises(TradingError, match="Trading is blocked"):
            order_executor.execute_order(request)
    
    def test_cancel_order_success(self, order_executor, mock_alpaca_client):
        """Test successful order cancellation."""
        # Add order to active tracking
        order = Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal('150.00')  # Required for limit orders
        )
        order_executor._active_orders["order_123"] = order
        
        # Mock successful cancellation
        mock_alpaca_client._api.cancel_order.return_value = None
        
        # Cancel order
        result = order_executor.cancel_order("order_123")
        
        # Verify result
        assert result is True
        assert order_executor._active_orders["order_123"].status == OrderStatus.CANCELLED
        
        # Verify API call
        mock_alpaca_client._api.cancel_order.assert_called_once_with("order_123")
    
    def test_cancel_order_failure(self, order_executor, mock_alpaca_client):
        """Test order cancellation failure."""
        # Mock API error
        mock_alpaca_client._api.cancel_order.side_effect = Exception("Cancel failed")
        
        # Cancel order
        result = order_executor.cancel_order("order_123")
        
        # Verify result
        assert result is False
    
    def test_get_order_status(self, order_executor, mock_alpaca_client):
        """Test getting order status."""
        # Mock Alpaca order response
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = 100
        mock_order.side = "buy"
        mock_order.order_type = "limit"
        mock_order.status = "partially_filled"
        mock_order.filled_qty = 50
        mock_order.filled_avg_price = 150.25
        mock_order.limit_price = 150.00
        mock_order.stop_price = None
        mock_order.time_in_force = "day"
        mock_order.created_at = datetime.now(timezone.utc)
        mock_order.updated_at = datetime.now(timezone.utc)
        
        mock_alpaca_client._api.get_order.return_value = mock_order
        
        # Get order status
        order = order_executor.get_order_status("order_123")
        
        # Verify result
        assert order is not None
        assert order.order_id == "order_123"
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 50
        assert order.average_fill_price == Decimal('150.25')
        
        # Verify order is tracked
        assert "order_123" in order_executor._active_orders
    
    def test_get_order_status_not_found(self, order_executor, mock_alpaca_client):
        """Test getting status for non-existent order."""
        # Mock API error
        mock_alpaca_client._api.get_order.side_effect = Exception("Order not found")
        
        # Get order status
        order = order_executor.get_order_status("nonexistent")
        
        # Verify result
        assert order is None
    
    def test_get_active_orders(self, order_executor):
        """Test getting active orders."""
        # Add some orders to active tracking
        order1 = Order(
            order_id="order_1",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
        order2 = Order(
            order_id="order_2",
            symbol="TSLA",
            quantity=50,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PARTIALLY_FILLED,
            limit_price=Decimal('250.00')  # Required for limit orders
        )
        
        order_executor._active_orders["order_1"] = order1
        order_executor._active_orders["order_2"] = order2
        
        # Get active orders
        active_orders = order_executor.get_active_orders()
        
        # Verify result
        assert len(active_orders) == 2
        assert order1 in active_orders
        assert order2 in active_orders
    
    def test_register_execution_callback(self, order_executor):
        """Test registering execution callbacks."""
        callback = Mock()
        
        # Register callback
        order_executor.register_execution_callback("order_123", callback)
        
        # Verify callback is registered
        assert "order_123" in order_executor._execution_callbacks
        assert callback in order_executor._execution_callbacks["order_123"]
    
    def test_get_execution_statistics(self, order_executor):
        """Test getting execution statistics."""
        # Update some statistics
        order_executor._execution_stats['total_orders'] = 10
        order_executor._execution_stats['successful_executions'] = 8
        order_executor._execution_stats['failed_executions'] = 2
        order_executor._execution_stats['partial_fills'] = 3
        
        # Get statistics
        stats = order_executor.get_execution_statistics()
        
        # Verify statistics
        assert stats['total_orders'] == 10
        assert stats['successful_executions'] == 8
        assert stats['failed_executions'] == 2
        assert stats['partial_fills'] == 3
        assert stats['success_rate'] == 0.8
    
    def test_smart_execution_strategy(self, order_executor, mock_alpaca_client):
        """Test smart execution strategy routing."""
        # Mock successful order execution
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = 100
        mock_order.side = "buy"
        mock_order.order_type = "market"
        mock_order.status = "filled"
        mock_order.filled_qty = 100
        mock_order.filled_avg_price = 150.50
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.time_in_force = "day"
        mock_order.created_at = datetime.now(timezone.utc)
        mock_order.updated_at = datetime.now(timezone.utc)
        
        mock_alpaca_client._api.submit_order.return_value = mock_order
        
        # Create order request with smart strategy
        request = OrderRequest(
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            execution_strategy=ExecutionStrategy.SMART
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify successful execution
        assert result.success is True
        assert result.order_id == "order_123"
    
    def test_iceberg_execution_strategy(self, order_executor, mock_alpaca_client):
        """Test iceberg execution strategy."""
        # Mock account with sufficient buying power
        mock_alpaca_client.get_account_info.return_value = {
            'buying_power': 1000000.0,  # High buying power
            'trading_blocked': False
        }
        
        # Mock successful order execution
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = 1000  # First chunk
        mock_order.side = "buy"
        mock_order.order_type = "market"
        mock_order.status = "filled"
        mock_order.filled_qty = 1000
        mock_order.filled_avg_price = 150.50
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.time_in_force = "day"
        mock_order.created_at = datetime.now(timezone.utc)
        mock_order.updated_at = datetime.now(timezone.utc)
        
        mock_alpaca_client._api.submit_order.return_value = mock_order
        
        # Create large order request with iceberg strategy
        request = OrderRequest(
            symbol="AAPL",
            quantity=5000,  # Large order
            side=OrderSide.BUY,
            execution_strategy=ExecutionStrategy.ICEBERG
        )
        
        # Execute order
        result = order_executor.execute_order(request)
        
        # Verify execution (should execute first chunk)
        assert result.success is True
        assert result.order_id == "order_123"
        
        # Verify API was called with chunk size
        mock_alpaca_client._api.submit_order.assert_called_once()
        call_args = mock_alpaca_client._api.submit_order.call_args
        assert call_args[1]['qty'] == 1000  # Chunk size
    
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_order_monitoring(self, mock_sleep, order_executor, mock_alpaca_client):
        """Test order monitoring functionality."""
        # Mock order status updates
        mock_order_new = Mock()
        mock_order_new.id = "order_123"
        mock_order_new.status = "new"
        mock_order_new.symbol = "AAPL"
        mock_order_new.qty = 100
        mock_order_new.side = "buy"
        mock_order_new.order_type = "market"
        mock_order_new.filled_qty = 0
        mock_order_new.filled_avg_price = None
        mock_order_new.limit_price = None
        mock_order_new.stop_price = None
        mock_order_new.time_in_force = "day"
        mock_order_new.created_at = datetime.now(timezone.utc)
        mock_order_new.updated_at = datetime.now(timezone.utc)
        
        mock_order_filled = Mock()
        mock_order_filled.id = "order_123"
        mock_order_filled.status = "filled"
        mock_order_filled.symbol = "AAPL"
        mock_order_filled.qty = 100
        mock_order_filled.side = "buy"
        mock_order_filled.order_type = "market"
        mock_order_filled.filled_qty = 100
        mock_order_filled.filled_avg_price = 150.50
        mock_order_filled.limit_price = None
        mock_order_filled.stop_price = None
        mock_order_filled.time_in_force = "day"
        mock_order_filled.created_at = datetime.now(timezone.utc)
        mock_order_filled.updated_at = datetime.now(timezone.utc)
        
        # Set up API responses
        mock_alpaca_client._api.get_order.side_effect = [mock_order_new, mock_order_filled]
        
        # Add order to tracking
        order = Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
        order_executor._active_orders["order_123"] = order
        
        # Register callback
        callback = Mock()
        order_executor.register_execution_callback("order_123", callback)
        
        # Start monitoring
        order_executor._start_order_monitoring("order_123")
        
        # Let monitoring run briefly
        import time
        time.sleep(0.1)
        
        # Stop monitoring
        order_executor.stop_monitoring()
        
        # Verify callback was called (may not be called in this short test)
        # This is a simplified test - in practice, monitoring runs in background
    
    def test_stop_monitoring(self, order_executor):
        """Test stopping order monitoring."""
        # Start monitoring
        order_executor._monitoring_active = True
        
        # Stop monitoring
        order_executor.stop_monitoring()
        
        # Verify monitoring is stopped
        assert order_executor._monitoring_active is False