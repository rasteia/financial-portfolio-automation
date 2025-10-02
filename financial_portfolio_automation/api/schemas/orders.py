"""
Order and execution-related Pydantic schemas for API models.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    """Time in force enumeration."""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


class OrderStatusEnum(str, Enum):
    """Order status enumeration."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PENDING_CANCEL = "pending_cancel"
    EXPIRED = "expired"


class OrderRequest(BaseModel):
    """Order request model."""
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., gt=0, description="Number of shares")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(..., description="Order type")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price (for limit orders)")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price (for stop orders)")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper().strip()
    
    @validator('limit_price')
    def validate_limit_price(cls, v, values):
        if values.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('Limit price is required for limit orders')
        return v
    
    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        if values.get('order_type') in [OrderType.STOP, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('Stop price is required for stop orders')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 100,
                "side": "buy",
                "order_type": "limit",
                "time_in_force": "day",
                "limit_price": 150.0
            }
        }


class OrderResponse(BaseModel):
    """Order response model."""
    success: bool = Field(..., description="Whether order was successful")
    order_id: Optional[str] = Field(None, description="Order ID")
    message: str = Field(..., description="Response message")
    timestamp: str = Field(..., description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "order_id": "12345678-1234-1234-1234-123456789012",
                "message": "Order placed successfully",
                "timestamp": "2024-01-01T15:30:00Z"
            }
        }


class OrderFill(BaseModel):
    """Order fill model."""
    fill_id: str = Field(..., description="Fill ID")
    quantity: int = Field(..., description="Filled quantity")
    price: float = Field(..., description="Fill price")
    timestamp: str = Field(..., description="Fill timestamp")
    commission: Optional[float] = Field(None, description="Commission paid")


class OrderStatus(BaseModel):
    """Order status model."""
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Order quantity")
    filled_quantity: int = Field(..., description="Filled quantity")
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    status: OrderStatusEnum = Field(..., description="Order status")
    time_in_force: TimeInForce = Field(..., description="Time in force")
    limit_price: Optional[float] = Field(None, description="Limit price")
    stop_price: Optional[float] = Field(None, description="Stop price")
    average_fill_price: Optional[float] = Field(None, description="Average fill price")
    created_at: str = Field(..., description="Order creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    fills: Optional[List[OrderFill]] = Field(None, description="Order fills")
    
    class Config:
        schema_extra = {
            "example": {
                "order_id": "12345678-1234-1234-1234-123456789012",
                "symbol": "AAPL",
                "quantity": 100,
                "filled_quantity": 100,
                "side": "buy",
                "order_type": "limit",
                "status": "filled",
                "time_in_force": "day",
                "limit_price": 150.0,
                "average_fill_price": 149.95,
                "created_at": "2024-01-01T15:30:00Z",
                "updated_at": "2024-01-01T15:31:00Z"
            }
        }


class OrderUpdate(BaseModel):
    """Order update model."""
    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    limit_price: Optional[float] = Field(None, gt=0, description="New limit price")
    stop_price: Optional[float] = Field(None, gt=0, description="New stop price")
    time_in_force: Optional[TimeInForce] = Field(None, description="New time in force")
    
    class Config:
        schema_extra = {
            "example": {
                "quantity": 150,
                "limit_price": 148.0
            }
        }


class TradeExecution(BaseModel):
    """Trade execution model."""
    trade_id: str = Field(..., description="Trade ID")
    order_id: str = Field(..., description="Related order ID")
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Executed quantity")
    price: float = Field(..., description="Execution price")
    side: OrderSide = Field(..., description="Trade side")
    timestamp: str = Field(..., description="Execution timestamp")
    commission: Optional[float] = Field(None, description="Commission paid")
    fees: Optional[float] = Field(None, description="Additional fees")
    
    class Config:
        schema_extra = {
            "example": {
                "trade_id": "87654321-4321-4321-4321-210987654321",
                "order_id": "12345678-1234-1234-1234-123456789012",
                "symbol": "AAPL",
                "quantity": 100,
                "price": 149.95,
                "side": "buy",
                "timestamp": "2024-01-01T15:31:00Z",
                "commission": 1.0
            }
        }


class RiskCheck(BaseModel):
    """Risk check model."""
    check_name: str = Field(..., description="Risk check name")
    passed: bool = Field(..., description="Whether check passed")
    message: str = Field(..., description="Check result message")
    severity: str = Field(..., description="Severity level")


class RiskValidation(BaseModel):
    """Risk validation model."""
    valid: bool = Field(..., description="Overall validation result")
    risk_score: float = Field(..., description="Risk score (0-10)")
    checks: List[RiskCheck] = Field(..., description="Individual risk checks")
    warnings: List[str] = Field(..., description="Risk warnings")
    estimated_impact: Optional[Dict[str, float]] = Field(None, description="Estimated portfolio impact")
    
    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "risk_score": 3.5,
                "checks": [
                    {
                        "check_name": "Position Size Limit",
                        "passed": True,
                        "message": "Order within position size limits",
                        "severity": "info"
                    },
                    {
                        "check_name": "Portfolio Concentration",
                        "passed": True,
                        "message": "Order will not exceed concentration limits",
                        "severity": "info"
                    }
                ],
                "warnings": [],
                "estimated_impact": {
                    "portfolio_value_change": 15000.0,
                    "allocation_change": 0.05,
                    "risk_contribution": 0.02
                }
            }
        }