"""
Execution API routes.

Provides endpoints for order placement, order management, and trade execution
with comprehensive risk controls and monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission
from financial_portfolio_automation.api.schemas.orders import (
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderUpdate,
    TradeExecution,
    RiskValidation
)

router = APIRouter()


@router.post("/orders", response_model=OrderResponse)
async def place_order(
    order: OrderRequest,
    dry_run: bool = Query(False, description="Simulate order without actual execution"),
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Place a new order with risk validation.
    
    Creates and submits a new order after performing comprehensive
    risk checks and validation.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        
        # Place order
        order_result = execution_tools.place_order(
            symbol=order.symbol,
            quantity=order.quantity,
            side=order.side,
            order_type=order.order_type,
            time_in_force=order.time_in_force,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            dry_run=dry_run
        )
        
        if not order_result:
            raise HTTPException(status_code=500, detail="Failed to place order")
        
        if not order_result.get('success'):
            raise HTTPException(
                status_code=400, 
                detail=f"Order rejected: {order_result.get('error', 'Unknown error')}"
            )
        
        return OrderResponse(**order_result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")


@router.get("/orders", response_model=List[OrderStatus])
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, description="Maximum number of orders to return"),
    offset: int = Query(0, description="Number of orders to skip"),
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    List orders with filtering and pagination.
    
    Returns a list of orders with optional filtering by status, symbol,
    and pagination support.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        orders_data = execution_tools.get_orders(
            status=status,
            symbol=symbol.upper() if symbol else None,
            limit=limit,
            offset=offset
        )
        
        if not orders_data:
            return []
        
        return [OrderStatus(**order) for order in orders_data]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve orders: {str(e)}")


@router.get("/orders/{order_id}", response_model=OrderStatus)
async def get_order(
    order_id: str,
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    Get specific order details.
    
    Returns detailed information about a specific order including
    execution status, fills, and timestamps.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        order_data = execution_tools.get_order(order_id=order_id)
        
        if not order_data:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return OrderStatus(**order_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve order: {str(e)}")


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def modify_order(
    order_id: str,
    update: OrderUpdate,
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Modify an existing order.
    
    Updates order parameters such as quantity, price, or time in force
    for orders that are still open.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        
        # Modify order
        modify_result = execution_tools.modify_order(
            order_id=order_id,
            quantity=update.quantity,
            limit_price=update.limit_price,
            stop_price=update.stop_price,
            time_in_force=update.time_in_force
        )
        
        if not modify_result:
            raise HTTPException(status_code=500, detail="Failed to modify order")
        
        if not modify_result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=f"Order modification rejected: {modify_result.get('error', 'Unknown error')}"
            )
        
        return OrderResponse(**modify_result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to modify order: {str(e)}")


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Cancel an existing order.
    
    Cancels an open order if it hasn't been filled yet.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        
        # Cancel order
        cancel_result = execution_tools.cancel_order(order_id=order_id)
        
        if not cancel_result:
            raise HTTPException(status_code=500, detail="Failed to cancel order")
        
        if not cancel_result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=f"Order cancellation rejected: {cancel_result.get('error', 'Unknown error')}"
            )
        
        return {
            "message": f"Order {order_id} cancelled successfully",
            "order_id": order_id,
            "status": "cancelled",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.get("/trades", response_model=List[TradeExecution])
async def list_trades(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Maximum number of trades to return"),
    offset: int = Query(0, description="Number of trades to skip"),
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    List trade executions with filtering.
    
    Returns a list of executed trades with optional filtering by symbol,
    date range, and pagination support.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        trades_data = execution_tools.get_trades(
            symbol=symbol.upper() if symbol else None,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        if not trades_data:
            return []
        
        return [TradeExecution(**trade) for trade in trades_data]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trades: {str(e)}")


@router.post("/orders/validate", response_model=RiskValidation)
async def validate_order_risk(
    order: OrderRequest,
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    Validate order against risk parameters.
    
    Performs comprehensive risk validation for an order without
    actually placing it.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        
        # Validate order risk
        validation_result = risk_tools.validate_order_risk(
            symbol=order.symbol,
            quantity=order.quantity,
            side=order.side,
            order_type=order.order_type,
            limit_price=order.limit_price
        )
        
        if not validation_result:
            raise HTTPException(status_code=500, detail="Failed to validate order risk")
        
        return RiskValidation(**validation_result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate order risk: {str(e)}")


@router.post("/orders/bracket")
async def place_bracket_order(
    symbol: str,
    quantity: int,
    side: str,
    entry_price: float,
    take_profit_price: float,
    stop_loss_price: float,
    dry_run: bool = Query(False, description="Simulate order without actual execution"),
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Place a bracket order (OCO - One Cancels Other).
    
    Places a main order with both take profit and stop loss orders
    that are automatically cancelled when one executes.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        
        # Place bracket order
        bracket_result = execution_tools.place_bracket_order(
            symbol=symbol.upper(),
            quantity=quantity,
            side=side,
            entry_price=entry_price,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            dry_run=dry_run
        )
        
        if not bracket_result:
            raise HTTPException(status_code=500, detail="Failed to place bracket order")
        
        if not bracket_result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=f"Bracket order rejected: {bracket_result.get('error', 'Unknown error')}"
            )
        
        return {
            "message": "Bracket order placed successfully",
            "parent_order_id": bracket_result.get('parent_order_id'),
            "take_profit_order_id": bracket_result.get('take_profit_order_id'),
            "stop_loss_order_id": bracket_result.get('stop_loss_order_id'),
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place bracket order: {str(e)}")


@router.get("/execution-stats")
async def get_execution_statistics(
    period: str = Query("1m", description="Statistics period"),
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    Get execution statistics and performance metrics.
    
    Returns statistics about order execution including fill rates,
    slippage, and execution quality metrics.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        stats_data = execution_tools.get_execution_statistics(period=period)
        
        if not stats_data:
            raise HTTPException(status_code=404, detail="Execution statistics not found")
        
        return stats_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve execution statistics: {str(e)}")


@router.get("/market-hours")
async def get_market_hours(
    current_user: AuthUser = Depends(require_permission("execution:read"))
):
    """
    Get current market hours and trading status.
    
    Returns information about market open/close times and current
    trading status.
    """
    try:
        from financial_portfolio_automation.mcp.market_data_tools import MarketDataTools
        
        market_data_tools = MarketDataTools()
        market_hours = market_data_tools.get_market_hours()
        
        if not market_hours:
            raise HTTPException(status_code=404, detail="Market hours information not found")
        
        return market_hours
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve market hours: {str(e)}")


@router.post("/orders/batch")
async def place_batch_orders(
    orders: List[OrderRequest],
    dry_run: bool = Query(False, description="Simulate orders without actual execution"),
    current_user: AuthUser = Depends(require_permission("execution:write"))
):
    """
    Place multiple orders in a batch.
    
    Submits multiple orders simultaneously with individual risk validation
    for each order.
    """
    try:
        from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
        
        execution_tools = ExecutionTools()
        
        # Place batch orders
        batch_result = execution_tools.place_batch_orders(
            orders=[order.dict() for order in orders],
            dry_run=dry_run
        )
        
        if not batch_result:
            raise HTTPException(status_code=500, detail="Failed to place batch orders")
        
        return {
            "message": f"Batch order {'simulation' if dry_run else 'execution'} completed",
            "total_orders": len(orders),
            "successful_orders": len(batch_result.get('successful_orders', [])),
            "failed_orders": len(batch_result.get('failed_orders', [])),
            "successful_orders": batch_result.get('successful_orders', []),
            "failed_orders": batch_result.get('failed_orders', []),
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place batch orders: {str(e)}")