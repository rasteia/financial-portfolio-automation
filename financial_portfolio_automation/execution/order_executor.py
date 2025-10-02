"""
Order execution system with intelligent routing and order management.

This module provides comprehensive order execution capabilities including
smart order routing, partial fill handling, and order status monitoring.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import time
import threading
from dataclasses import dataclass, field

from ..models.core import Order, OrderSide, OrderType, OrderStatus, Quote
from ..api.alpaca_client import AlpacaClient
from ..exceptions import (
    TradingError, InvalidOrderError, InsufficientFundsError,
    APIError, RiskError
)


logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """Order execution strategy enumeration."""
    IMMEDIATE = "immediate"  # Execute immediately at market
    TWAP = "twap"  # Time-weighted average price
    VWAP = "vwap"  # Volume-weighted average price
    ICEBERG = "iceberg"  # Break large orders into smaller chunks
    SMART = "smart"  # Intelligent routing based on market conditions


@dataclass
class ExecutionResult:
    """Result of order execution attempt."""
    success: bool
    order_id: Optional[str] = None
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    remaining_quantity: int = 0
    error_message: Optional[str] = None
    execution_time: Optional[datetime] = None
    fees: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now(timezone.utc)


@dataclass
class OrderRequest:
    """Order execution request with routing parameters."""
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "day"
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SMART
    max_participation_rate: float = 0.1  # Maximum % of volume
    urgency: str = "normal"  # low, normal, high
    client_order_id: Optional[str] = None
    
    def validate(self) -> None:
        """Validate order request parameters."""
        if not self.symbol or not isinstance(self.symbol, str):
            raise InvalidOrderError("Symbol must be a non-empty string")
        
        if self.quantity <= 0:
            raise InvalidOrderError("Quantity must be positive")
        
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise InvalidOrderError("Limit orders must have a limit price")
        
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and self.stop_price is None:
            raise InvalidOrderError("Stop orders must have a stop price")
        
        if self.limit_price is not None and self.limit_price <= 0:
            raise InvalidOrderError("Limit price must be positive")
        
        if self.stop_price is not None and self.stop_price <= 0:
            raise InvalidOrderError("Stop price must be positive")
        
        if not 0 < self.max_participation_rate <= 1:
            raise InvalidOrderError("Max participation rate must be between 0 and 1")


class OrderExecutor:
    """
    Intelligent order execution system with smart routing and monitoring.
    
    Provides comprehensive order execution capabilities including multiple
    execution strategies, partial fill handling, and real-time monitoring.
    """
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize the order executor.
        
        Args:
            alpaca_client: Authenticated Alpaca API client
        """
        self.alpaca_client = alpaca_client
        self._active_orders: Dict[str, Order] = {}
        self._execution_callbacks: Dict[str, List[Callable]] = {}
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active = False
        self._order_lock = threading.Lock()
        
        # Execution statistics
        self._execution_stats = {
            'total_orders': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'partial_fills': 0,
            'average_execution_time': 0.0,
            'total_fees': Decimal('0')
        }
        
        logger.info("OrderExecutor initialized")
    
    def execute_order(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute an order using intelligent routing.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
            
        Raises:
            TradingError: If order execution fails
            InvalidOrderError: If order parameters are invalid
        """
        start_time = time.time()
        
        try:
            # Validate order request
            order_request.validate()
            
            logger.info(
                f"Executing {order_request.side.value} order for {order_request.quantity} "
                f"shares of {order_request.symbol} using {order_request.execution_strategy.value} strategy"
            )
            
            # Check market conditions and account status
            self._validate_market_conditions(order_request)
            self._validate_account_status(order_request)
            
            # Route order based on execution strategy
            execution_result = self._route_order(order_request)
            
            # Update statistics
            self._update_execution_stats(execution_result, time.time() - start_time)
            
            # Start monitoring if order is not immediately filled
            if execution_result.success and execution_result.remaining_quantity > 0:
                self._start_order_monitoring(execution_result.order_id)
            
            logger.info(
                f"Order execution completed. Success: {execution_result.success}, "
                f"Filled: {execution_result.filled_quantity}/{order_request.quantity}"
            )
            
            return execution_result
            
        except Exception as e:
            error_msg = f"Order execution failed: {str(e)}"
            logger.error(error_msg)
            
            execution_result = ExecutionResult(
                success=False,
                error_message=error_msg,
                remaining_quantity=order_request.quantity
            )
            
            self._update_execution_stats(execution_result, time.time() - start_time)
            
            if isinstance(e, (TradingError, InvalidOrderError)):
                raise
            else:
                raise TradingError(error_msg)
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            logger.info(f"Cancelling order {order_id}")
            
            # Cancel order via Alpaca API
            self.alpaca_client._api.cancel_order(order_id)
            
            # Update local order tracking
            with self._order_lock:
                if order_id in self._active_orders:
                    self._active_orders[order_id].status = OrderStatus.CANCELLED
                    self._active_orders[order_id].updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """
        Get current status of an order.
        
        Args:
            order_id: ID of the order
            
        Returns:
            Order object with current status, None if not found
        """
        try:
            # Get order from Alpaca API
            alpaca_order = self.alpaca_client._api.get_order(order_id)
            
            # Convert to internal Order model
            order = self._convert_alpaca_order_to_model(alpaca_order)
            
            # Update local tracking
            with self._order_lock:
                self._active_orders[order_id] = order
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {str(e)}")
            return None
    
    def get_active_orders(self) -> List[Order]:
        """
        Get all active orders.
        
        Returns:
            List of active Order objects
        """
        with self._order_lock:
            return list(self._active_orders.values())
    
    def register_execution_callback(self, order_id: str, callback: Callable[[Order], None]) -> None:
        """
        Register a callback for order execution events.
        
        Args:
            order_id: ID of the order to monitor
            callback: Function to call when order status changes
        """
        if order_id not in self._execution_callbacks:
            self._execution_callbacks[order_id] = []
        
        self._execution_callbacks[order_id].append(callback)
        logger.debug(f"Registered execution callback for order {order_id}")
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get order execution statistics.
        
        Returns:
            Dictionary containing execution metrics
        """
        stats = self._execution_stats.copy()
        
        # Calculate success rate
        if stats['total_orders'] > 0:
            stats['success_rate'] = stats['successful_executions'] / stats['total_orders']
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def _route_order(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Route order based on execution strategy.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        if order_request.execution_strategy == ExecutionStrategy.IMMEDIATE:
            return self._execute_immediate(order_request)
        elif order_request.execution_strategy == ExecutionStrategy.TWAP:
            return self._execute_twap(order_request)
        elif order_request.execution_strategy == ExecutionStrategy.VWAP:
            return self._execute_vwap(order_request)
        elif order_request.execution_strategy == ExecutionStrategy.ICEBERG:
            return self._execute_iceberg(order_request)
        elif order_request.execution_strategy == ExecutionStrategy.SMART:
            return self._execute_smart(order_request)
        else:
            raise InvalidOrderError(f"Unsupported execution strategy: {order_request.execution_strategy}")
    
    def _execute_immediate(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute order immediately using market or limit order.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            # Submit order to Alpaca
            alpaca_order = self.alpaca_client._api.submit_order(
                symbol=order_request.symbol,
                qty=order_request.quantity,
                side=order_request.side.value,
                type=order_request.order_type.value,
                time_in_force=order_request.time_in_force,
                limit_price=float(order_request.limit_price) if order_request.limit_price else None,
                stop_price=float(order_request.stop_price) if order_request.stop_price else None,
                client_order_id=order_request.client_order_id
            )
            
            # Convert to internal model and track
            order = self._convert_alpaca_order_to_model(alpaca_order)
            
            with self._order_lock:
                self._active_orders[order.order_id] = order
            
            return ExecutionResult(
                success=True,
                order_id=order.order_id,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                remaining_quantity=order.remaining_quantity
            )
            
        except Exception as e:
            logger.error(f"Immediate execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                error_message=str(e),
                remaining_quantity=order_request.quantity
            )
    
    def _execute_smart(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute order using intelligent routing based on market conditions.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        # For now, implement smart routing as immediate execution
        # In a full implementation, this would analyze:
        # - Market volatility
        # - Bid-ask spread
        # - Order size relative to average volume
        # - Time of day
        # - Market impact estimation
        
        logger.info(f"Using smart routing for {order_request.symbol}")
        
        # Analyze market conditions (simplified)
        market_conditions = self._analyze_market_conditions(order_request.symbol)
        
        # Choose execution strategy based on conditions
        if market_conditions.get('high_volatility', False):
            # Use limit orders in volatile markets
            if order_request.order_type == OrderType.MARKET:
                order_request.order_type = OrderType.LIMIT
                # Set limit price based on current quote
                quote = self._get_current_quote(order_request.symbol)
                if quote:
                    if order_request.side == OrderSide.BUY:
                        order_request.limit_price = quote.ask * Decimal('1.001')  # Slight premium
                    else:
                        order_request.limit_price = quote.bid * Decimal('0.999')  # Slight discount
        
        # For large orders, consider using iceberg strategy
        if order_request.quantity > market_conditions.get('average_volume', 1000) * 0.05:
            logger.info("Large order detected, considering iceberg execution")
            return self._execute_iceberg(order_request)
        
        # Default to immediate execution
        return self._execute_immediate(order_request)
    
    def _execute_twap(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute order using Time-Weighted Average Price strategy.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        # Simplified TWAP implementation
        # In production, this would split the order over time
        logger.info(f"TWAP execution not fully implemented, using immediate execution")
        return self._execute_immediate(order_request)
    
    def _execute_vwap(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute order using Volume-Weighted Average Price strategy.
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        # Simplified VWAP implementation
        logger.info(f"VWAP execution not fully implemented, using immediate execution")
        return self._execute_immediate(order_request)
    
    def _execute_iceberg(self, order_request: OrderRequest) -> ExecutionResult:
        """
        Execute large order using iceberg strategy (breaking into smaller chunks).
        
        Args:
            order_request: Order execution request
            
        Returns:
            ExecutionResult with execution details
        """
        # Simplified iceberg implementation
        # Break order into smaller chunks
        chunk_size = min(order_request.quantity // 4, 1000)  # Max 1000 shares per chunk
        if chunk_size == 0:
            chunk_size = order_request.quantity
        
        logger.info(f"Executing iceberg order with chunk size {chunk_size}")
        
        # For now, just execute the first chunk
        first_chunk = OrderRequest(
            symbol=order_request.symbol,
            quantity=chunk_size,
            side=order_request.side,
            order_type=order_request.order_type,
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            time_in_force=order_request.time_in_force,
            execution_strategy=ExecutionStrategy.IMMEDIATE
        )
        
        return self._execute_immediate(first_chunk)
    
    def _validate_market_conditions(self, order_request: OrderRequest) -> None:
        """
        Validate market conditions for order execution.
        
        Args:
            order_request: Order execution request
            
        Raises:
            TradingError: If market conditions are not suitable
        """
        # Check if market is open
        if not self.alpaca_client.is_market_open():
            # Allow orders to be placed when market is closed (they will be queued)
            logger.warning("Market is closed, order will be queued for next market open")
    
    def _validate_account_status(self, order_request: OrderRequest) -> None:
        """
        Validate account status for order execution.
        
        Args:
            order_request: Order execution request
            
        Raises:
            InsufficientFundsError: If insufficient buying power
            TradingError: If account restrictions prevent trading
        """
        try:
            account_info = self.alpaca_client.get_account_info()
            
            # Check if trading is blocked
            if account_info.get('trading_blocked', False):
                raise TradingError("Trading is blocked on this account")
            
            # Check buying power for buy orders
            if order_request.side == OrderSide.BUY:
                buying_power = Decimal(str(account_info['buying_power']))
                
                # Estimate order value
                if order_request.order_type == OrderType.MARKET:
                    # Use current ask price for estimation
                    quote = self._get_current_quote(order_request.symbol)
                    estimated_price = quote.ask if quote else Decimal('100')  # Fallback
                else:
                    estimated_price = order_request.limit_price or Decimal('100')
                
                estimated_value = estimated_price * order_request.quantity
                
                if estimated_value > buying_power:
                    raise InsufficientFundsError(
                        f"Insufficient buying power. Required: ${estimated_value}, "
                        f"Available: ${buying_power}"
                    )
            
        except APIError:
            logger.warning("Could not validate account status, proceeding with order")
    
    def _analyze_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze market conditions for a symbol.
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Dictionary with market condition metrics
        """
        # Simplified market analysis
        # In production, this would include:
        # - Volatility analysis
        # - Volume analysis
        # - Spread analysis
        # - Time of day factors
        
        conditions = {
            'high_volatility': False,
            'wide_spread': False,
            'low_volume': False,
            'average_volume': 10000  # Default assumption
        }
        
        try:
            quote = self._get_current_quote(symbol)
            if quote:
                # Simple spread analysis
                spread_percentage = (quote.spread / quote.mid_price) * 100
                conditions['wide_spread'] = spread_percentage > 0.5  # > 0.5%
                
        except Exception as e:
            logger.warning(f"Could not analyze market conditions for {symbol}: {str(e)}")
        
        return conditions
    
    def _get_current_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote object or None if not available
        """
        try:
            # This would typically come from the market data client
            # For now, return None to indicate quote not available
            return None
            
        except Exception as e:
            logger.warning(f"Could not get quote for {symbol}: {str(e)}")
            return None
    
    def _convert_alpaca_order_to_model(self, alpaca_order) -> Order:
        """
        Convert Alpaca API order object to internal Order model.
        
        Args:
            alpaca_order: Alpaca API order object
            
        Returns:
            Order model object
        """
        # Map Alpaca order status to internal status
        status_mapping = {
            'new': OrderStatus.NEW,
            'partially_filled': OrderStatus.PARTIALLY_FILLED,
            'filled': OrderStatus.FILLED,
            'done_for_day': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.EXPIRED,
            'replaced': OrderStatus.NEW,
            'pending_cancel': OrderStatus.CANCELLED,
            'pending_replace': OrderStatus.NEW,
            'rejected': OrderStatus.REJECTED,
            'suspended': OrderStatus.REJECTED,
            'calculated': OrderStatus.NEW
        }
        
        status = status_mapping.get(alpaca_order.status, OrderStatus.NEW)
        
        # Convert side
        side = OrderSide.BUY if alpaca_order.side == 'buy' else OrderSide.SELL
        
        # Convert order type
        type_mapping = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT,
            'stop': OrderType.STOP,
            'stop_limit': OrderType.STOP_LIMIT
        }
        order_type = type_mapping.get(alpaca_order.order_type, OrderType.MARKET)
        
        return Order(
            order_id=alpaca_order.id,
            symbol=alpaca_order.symbol,
            quantity=int(alpaca_order.qty),
            side=side,
            order_type=order_type,
            status=status,
            filled_quantity=int(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            average_fill_price=Decimal(str(alpaca_order.filled_avg_price)) if alpaca_order.filled_avg_price else None,
            limit_price=Decimal(str(alpaca_order.limit_price)) if alpaca_order.limit_price else None,
            stop_price=Decimal(str(alpaca_order.stop_price)) if alpaca_order.stop_price else None,
            time_in_force=alpaca_order.time_in_force,
            created_at=alpaca_order.created_at,
            updated_at=alpaca_order.updated_at
        )
    
    def _start_order_monitoring(self, order_id: str) -> None:
        """
        Start monitoring an order for status updates.
        
        Args:
            order_id: ID of the order to monitor
        """
        if not self._monitoring_active:
            self._monitoring_active = True
            self._monitoring_thread = threading.Thread(
                target=self._monitor_orders,
                daemon=True
            )
            self._monitoring_thread.start()
            logger.info("Started order monitoring thread")
    
    def _monitor_orders(self) -> None:
        """Monitor active orders for status updates."""
        logger.info("Order monitoring started")
        
        while self._monitoring_active:
            try:
                with self._order_lock:
                    active_order_ids = list(self._active_orders.keys())
                
                for order_id in active_order_ids:
                    try:
                        updated_order = self.get_order_status(order_id)
                        if updated_order:
                            # Check if order status changed
                            with self._order_lock:
                                old_order = self._active_orders.get(order_id)
                                if old_order and old_order.status != updated_order.status:
                                    logger.info(
                                        f"Order {order_id} status changed: "
                                        f"{old_order.status.value} -> {updated_order.status.value}"
                                    )
                                    
                                    # Call registered callbacks
                                    if order_id in self._execution_callbacks:
                                        for callback in self._execution_callbacks[order_id]:
                                            try:
                                                callback(updated_order)
                                            except Exception as e:
                                                logger.error(f"Callback error for order {order_id}: {str(e)}")
                                
                                # Remove completed orders from active tracking
                                if updated_order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, 
                                                           OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                                    self._active_orders.pop(order_id, None)
                                    self._execution_callbacks.pop(order_id, None)
                    
                    except Exception as e:
                        logger.error(f"Error monitoring order {order_id}: {str(e)}")
                
                # Sleep between monitoring cycles
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in order monitoring loop: {str(e)}")
                time.sleep(10)  # Longer sleep on error
        
        logger.info("Order monitoring stopped")
    
    def _update_execution_stats(self, result: ExecutionResult, execution_time: float) -> None:
        """
        Update execution statistics.
        
        Args:
            result: Execution result
            execution_time: Time taken for execution in seconds
        """
        self._execution_stats['total_orders'] += 1
        
        if result.success:
            self._execution_stats['successful_executions'] += 1
            if result.remaining_quantity > 0:
                self._execution_stats['partial_fills'] += 1
        else:
            self._execution_stats['failed_executions'] += 1
        
        # Update average execution time
        total_time = (self._execution_stats['average_execution_time'] * 
                     (self._execution_stats['total_orders'] - 1) + execution_time)
        self._execution_stats['average_execution_time'] = total_time / self._execution_stats['total_orders']
        
        if result.fees:
            self._execution_stats['total_fees'] += result.fees
    
    def stop_monitoring(self) -> None:
        """Stop order monitoring thread."""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=10)
            logger.info("Order monitoring stopped")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_monitoring()