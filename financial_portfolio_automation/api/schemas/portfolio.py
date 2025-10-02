"""
Portfolio-related Pydantic schemas for API models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class PortfolioOverview(BaseModel):
    """Portfolio overview response model."""
    total_value: float = Field(..., description="Total portfolio value")
    buying_power: float = Field(..., description="Available buying power")
    day_pnl: float = Field(..., description="Day profit/loss")
    total_pnl: float = Field(..., description="Total profit/loss")
    position_count: int = Field(..., description="Number of positions")
    last_updated: str = Field(..., description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "total_value": 150000.0,
                "buying_power": 30000.0,
                "day_pnl": 2500.0,
                "total_pnl": 15000.0,
                "position_count": 12,
                "last_updated": "2024-01-01T15:30:00Z"
            }
        }


class Position(BaseModel):
    """Portfolio position model."""
    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares")
    market_value: float = Field(..., description="Current market value")
    cost_basis: float = Field(..., description="Cost basis")
    unrealized_pnl: float = Field(..., description="Unrealized profit/loss")
    day_pnl: float = Field(..., description="Day profit/loss")
    allocation_percent: float = Field(..., description="Portfolio allocation percentage")
    current_price: Optional[float] = Field(None, description="Current price per share")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 100,
                "market_value": 15000.0,
                "cost_basis": 14000.0,
                "unrealized_pnl": 1000.0,
                "day_pnl": 150.0,
                "allocation_percent": 10.0,
                "current_price": 150.0
            }
        }


class BenchmarkComparison(BaseModel):
    """Benchmark comparison model."""
    benchmark_symbol: str = Field(..., description="Benchmark symbol")
    benchmark_return: float = Field(..., description="Benchmark return")
    alpha: float = Field(..., description="Alpha vs benchmark")
    beta: float = Field(..., description="Beta vs benchmark")
    correlation: float = Field(..., description="Correlation with benchmark")
    tracking_error: float = Field(..., description="Tracking error")
    information_ratio: Optional[float] = Field(None, description="Information ratio")


class PortfolioPerformance(BaseModel):
    """Portfolio performance model."""
    total_return: float = Field(..., description="Total return")
    annualized_return: float = Field(..., description="Annualized return")
    volatility: float = Field(..., description="Volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: Optional[float] = Field(None, description="Sortino ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    win_rate: float = Field(..., description="Win rate")
    best_day: Optional[float] = Field(None, description="Best single day return")
    worst_day: Optional[float] = Field(None, description="Worst single day return")
    benchmark_comparison: Optional[BenchmarkComparison] = Field(None, description="Benchmark comparison")
    
    class Config:
        schema_extra = {
            "example": {
                "total_return": 0.15,
                "annualized_return": 0.12,
                "volatility": 0.18,
                "sharpe_ratio": 1.2,
                "sortino_ratio": 1.5,
                "max_drawdown": 0.08,
                "win_rate": 0.65,
                "best_day": 0.05,
                "worst_day": -0.03
            }
        }


class AllocationItem(BaseModel):
    """Allocation item model."""
    name: str = Field(..., description="Name of the allocation item")
    value: float = Field(..., description="Value of the allocation")
    allocation_percent: float = Field(..., description="Allocation percentage")
    position_count: Optional[int] = Field(None, description="Number of positions (for sectors/asset classes)")


class AllocationBreakdown(BaseModel):
    """Portfolio allocation breakdown model."""
    allocation_type: str = Field(..., description="Type of allocation (position, sector, asset_class)")
    allocations: List[AllocationItem] = Field(..., description="List of allocation items")
    total_shown_percent: float = Field(..., description="Total percentage shown")
    item_count: int = Field(..., description="Number of items")
    
    class Config:
        schema_extra = {
            "example": {
                "allocation_type": "position",
                "allocations": [
                    {
                        "name": "AAPL",
                        "value": 15000.0,
                        "allocation_percent": 10.0
                    },
                    {
                        "name": "GOOGL",
                        "value": 12000.0,
                        "allocation_percent": 8.0
                    }
                ],
                "total_shown_percent": 18.0,
                "item_count": 2
            }
        }


class RebalanceRequest(BaseModel):
    """Rebalancing request model."""
    target_weights: Optional[Dict[str, float]] = Field(None, description="Target allocation weights")
    rebalance_threshold: float = Field(0.05, description="Minimum deviation threshold for rebalancing")
    
    class Config:
        schema_extra = {
            "example": {
                "target_weights": {
                    "AAPL": 0.15,
                    "GOOGL": 0.12,
                    "MSFT": 0.10,
                    "SPY": 0.20
                },
                "rebalance_threshold": 0.05
            }
        }


class RebalanceTrade(BaseModel):
    """Rebalancing trade model."""
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="Trade side (buy/sell)")
    quantity: int = Field(..., description="Number of shares")
    estimated_value: float = Field(..., description="Estimated trade value")
    reason: str = Field(..., description="Reason for the trade")


class RebalanceResponse(BaseModel):
    """Rebalancing response model."""
    current_allocation: Dict[str, float] = Field(..., description="Current allocation percentages")
    target_allocation: Dict[str, float] = Field(..., description="Target allocation percentages")
    trades_needed: List[RebalanceTrade] = Field(..., description="Required trades")
    total_trade_value: float = Field(..., description="Total value of trades")
    
    class Config:
        schema_extra = {
            "example": {
                "current_allocation": {
                    "AAPL": 18.0,
                    "GOOGL": 8.0,
                    "MSFT": 12.0
                },
                "target_allocation": {
                    "AAPL": 15.0,
                    "GOOGL": 12.0,
                    "MSFT": 10.0
                },
                "trades_needed": [
                    {
                        "symbol": "AAPL",
                        "side": "sell",
                        "quantity": 20,
                        "estimated_value": 3000.0,
                        "reason": "Reduce overweight position"
                    }
                ],
                "total_trade_value": 3000.0
            }
        }