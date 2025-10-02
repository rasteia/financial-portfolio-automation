"""
Execution tools for MCP integration.

This module provides AI assistants with access to trade execution capabilities
with comprehensive safety controls and risk management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

from ..execution.order_executor import OrderExecutor
from ..execution.risk_controller import RiskController
from ..execution.trade_logger import TradeLogger
from ..models.core import Order, OrderType, OrderStatus, Position
from ..config.settings import Settings
from ..exceptions import ValidationError, ExecutionError

logger = logging.getLogger(__name__)


class ExecutionTools:
    """MCP tools for trade execution and order management."""
    
    def __init__(self, settings: Settings):
        """Initialize execution tools with required services."""
        self.settings = settings
        self.order_executor = OrderExecutor(settings)
        self.risk_controller = RiskController(settings)
        self.trade_logger = TradeLogger(settings)
        
    async def place_order(
        self,
        symbol: str,
        quantity: float,
        order_type: str = "market",
        side: str = "buy",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place a new order with comprehensive validation and risk checks.
        
        Args:
            symbol: Stock symbol to trade
            quantity: Number of shares to trade
            order_type: Type of order (market, limit, stop, stop_limit)
            side: Order side (buy, sell)
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: Order duration (day, gtc, ioc, fok)
            
        Returns:
            Dict containing order details and execution status
        """
        try:
            # Validate input parameters
            if not symbol or not isinstance(symbol, str):
                raise ValidationError("Symbol must be a non-empty string")
                
            if quantity <= 0:
                raise ValidationError("Quantity must be positive")
                
            if order_type not in ["market", "limit", "stop", "stop_limit"]:
                raise ValidationError(f"Invalid order type: {order_type}")
                
            if side not in ["buy", "sell"]:
                raise ValidationError(f"Invalid order side: {side}")
                
            # Create order object
            order = Order(
                symbol=symbol,
                quantity=Decimal(str(quantity)),
                order_type=OrderType(order_type.upper()),
                side=side.upper(),
                limit_price=Decimal(str(limit_price)) if limit_price else None,
                stop_price=Decimal(str(stop_price)) if stop_price else None,
                time_in_force=time_in_force.upper()
            )
            
            # Perform pre-trade risk checks
            risk_check = await self.risk_controller.validate_order(order)
            if not risk_check.approved:
                return {
                    "success": False,
                    "error": f"Risk check failed: {risk_check.reason}",
                    "risk_details": risk_check.details
                }
            
            # Execute the order
            execution_result = await self.order_executor.place_order(order)
            
            # Log the trade
            await self.trade_logger.log_order(order, execution_result)
            
            return {
                "success": True,
                "order_id": execution_result.order_id,
                "status": execution_result.status.value,
                "filled_quantity": float(execution_result.filled_quantity),
                "average_price": float(execution_result.average_price) if execution_result.average_price else None,
                "timestamp": execution_result.timestamp.isoformat(),
                "commission": float(execution_result.commission) if execution_result.commission else None
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an existing order.
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            Dict containing cancellation status
        """
        try:
            if not order_id:
                raise ValidationError("Order ID is required")
                
            result = await self.order_executor.cancel_order(order_id)
            
            # Log the cancellation
            await self.trade_logger.log_cancellation(order_id, result)
            
            return {
                "success": True,
                "order_id": order_id,
                "status": result.status.value,
                "timestamp": result.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order.
        
        Args:
            order_id: ID of the order to modify
            quantity: New quantity (optional)
            limit_price: New limit price (optional)
            stop_price: New stop price (optional)
            
        Returns:
            Dict containing modification status
        """
        try:
            if not order_id:
                raise ValidationError("Order ID is required")
                
            # Get current order details
            current_order = await self.order_executor.get_order(order_id)
            if not current_order:
                raise ExecutionError(f"Order {order_id} not found")
            
            # Create modified order
            modifications = {}
            if quantity is not None:
                if quantity <= 0:
                    raise ValidationError("Quantity must be positive")
                modifications['quantity'] = Decimal(str(quantity))
                
            if limit_price is not None:
                modifications['limit_price'] = Decimal(str(limit_price))
                
            if stop_price is not None:
                modifications['stop_price'] = Decimal(str(stop_price))
            
            # Validate modifications with risk controller
            risk_check = await self.risk_controller.validate_modification(
                current_order, modifications
            )
            if not risk_check.approved:
                return {
                    "success": False,
                    "error": f"Risk check failed: {risk_check.reason}",
                    "risk_details": risk_check.details
                }
            
            # Execute the modification
            result = await self.order_executor.modify_order(order_id, modifications)
            
            # Log the modification
            await self.trade_logger.log_modification(order_id, modifications, result)
            
            return {
                "success": True,
                "order_id": order_id,
                "status": result.status.value,
                "modifications": {k: float(v) if isinstance(v, Decimal) else v 
                                for k, v in modifications.items()},
                "timestamp": result.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get current status and details of an order.
        
        Args:
            order_id: ID of the order to check
            
        Returns:
            Dict containing order status and details
        """
        try:
            if not order_id:
                raise ValidationError("Order ID is required")
                
            order = await self.order_executor.get_order(order_id)
            if not order:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            # Get execution details
            executions = await self.order_executor.get_order_executions(order_id)
            
            return {
                "success": True,
                "order_id": order_id,
                "symbol": order.symbol,
                "quantity": float(order.quantity),
                "order_type": order.order_type.value,
                "side": order.side,
                "status": order.status.value,
                "filled_quantity": float(order.filled_quantity),
                "remaining_quantity": float(order.quantity - order.filled_quantity),
                "average_price": float(order.average_price) if order.average_price else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "time_in_force": order.time_in_force,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "executions": [
                    {
                        "price": float(exec.price),
                        "quantity": float(exec.quantity),
                        "timestamp": exec.timestamp.isoformat()
                    }
                    for exec in executions
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_strategy(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a trading strategy with safety controls.
        
        Args:
            strategy_name: Name of the strategy to execute
            parameters: Strategy parameters
            dry_run: Whether to execute in simulation mode
            
        Returns:
            Dict containing execution results
        """
        try:
            if not strategy_name:
                raise ValidationError("Strategy name is required")
                
            # Validate strategy exists and parameters
            from ..strategy.registry import StrategyRegistry
            registry = StrategyRegistry()
            
            if not registry.is_registered(strategy_name):
                raise ValidationError(f"Strategy '{strategy_name}' not found")
            
            # Get strategy instance
            strategy = registry.get_strategy(strategy_name)
            
            # Validate parameters
            validation_result = strategy.validate_parameters(parameters)
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "error": f"Invalid parameters: {validation_result.errors}"
                }
            
            # Perform risk assessment
            risk_assessment = await self.risk_controller.assess_strategy_risk(
                strategy_name, parameters
            )
            if not risk_assessment.approved:
                return {
                    "success": False,
                    "error": f"Strategy risk check failed: {risk_assessment.reason}",
                    "risk_details": risk_assessment.details
                }
            
            # Execute strategy
            from ..strategy.executor import StrategyExecutor
            executor = StrategyExecutor(self.settings)
            
            execution_result = await executor.execute_strategy(
                strategy_name, 
                parameters, 
                dry_run=dry_run
            )
            
            # Log strategy execution
            await self.trade_logger.log_strategy_execution(
                strategy_name, parameters, execution_result, dry_run
            )
            
            return {
                "success": True,
                "strategy_name": strategy_name,
                "dry_run": dry_run,
                "orders_generated": len(execution_result.orders),
                "orders": [
                    {
                        "symbol": order.symbol,
                        "quantity": float(order.quantity),
                        "side": order.side,
                        "order_type": order.order_type.value,
                        "expected_price": float(order.limit_price) if order.limit_price else None
                    }
                    for order in execution_result.orders
                ],
                "expected_return": float(execution_result.expected_return) if execution_result.expected_return else None,
                "risk_metrics": execution_result.risk_metrics,
                "timestamp": execution_result.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }