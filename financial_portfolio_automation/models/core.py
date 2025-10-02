"""
Core data models for the financial portfolio automation system.

This module contains the fundamental data structures used throughout the system
for representing market data, positions, orders, and portfolio snapshots.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
import re


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status enumeration."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Quote:
    """Represents a market quote with bid/ask prices and sizes, or OHLCV data."""
    
    symbol: str
    timestamp: datetime
    # Real-time quote data (optional)
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    # Historical OHLCV data (optional)
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[int] = None
    
    def __post_init__(self):
        """Validate quote data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate quote data integrity and business rules."""
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        if not re.match(r'^[A-Z]{1,5}$', self.symbol):
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
        
        # Validate bid/ask data if present
        if self.bid is not None and self.ask is not None:
            if self.bid < 0 or self.ask < 0:
                raise ValueError("Bid and ask prices must be non-negative")
            
            if self.ask < self.bid:
                raise ValueError("Ask price cannot be less than bid price")
        
        if self.bid_size is not None and self.bid_size < 0:
            raise ValueError("Bid size must be non-negative")
            
        if self.ask_size is not None and self.ask_size < 0:
            raise ValueError("Ask size must be non-negative")
            
        # Validate OHLCV data if present
        if self.open is not None and self.open < 0:
            raise ValueError("Open price must be non-negative")
            
        if self.high is not None and self.high < 0:
            raise ValueError("High price must be non-negative")
            
        if self.low is not None and self.low < 0:
            raise ValueError("Low price must be non-negative")
            
        if self.close is not None and self.close < 0:
            raise ValueError("Close price must be non-negative")
            
        if self.volume is not None and self.volume < 0:
            raise ValueError("Volume must be non-negative")
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate the bid-ask spread."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate the mid-point price."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return None


@dataclass
class Position:
    """Represents a portfolio position in a security."""
    
    symbol: str
    quantity: Decimal  # Changed to Decimal to match test usage
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    day_pnl: Decimal
    
    def __post_init__(self):
        """Validate position data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate position data integrity and business rules."""
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        if not re.match(r'^[A-Z]{1,5}$', self.symbol):
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        
        if not isinstance(self.quantity, (int, Decimal)):
            raise ValueError("Quantity must be an integer or Decimal")
        
        if self.quantity == 0:
            raise ValueError("Position quantity cannot be zero")
        
        if self.cost_basis < 0:
            raise ValueError("Cost basis cannot be negative")
        
        if self.market_value < 0:
            raise ValueError("Market value cannot be negative")
    
    @property
    def average_cost(self) -> Decimal:
        """Calculate average cost per share."""
        if self.quantity == 0:
            return Decimal('0')
        return abs(self.cost_basis / self.quantity)
    
    @property
    def current_price(self) -> Decimal:
        """Calculate current price per share."""
        if self.quantity == 0:
            return Decimal('0')
        return abs(self.market_value / self.quantity)
    
    def is_long(self) -> bool:
        """Check if this is a long position."""
        return self.quantity > 0
    
    def is_short(self) -> bool:
        """Check if this is a short position."""
        return self.quantity < 0


@dataclass
class Order:
    """Represents a trading order."""
    
    order_id: str
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    filled_quantity: int = 0
    average_fill_price: Optional[Decimal] = None
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "day"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None  # Add filled_at field
    
    def __post_init__(self):
        """Validate order data after initialization."""
        # Convert string enums to enum objects if needed
        if isinstance(self.side, str):
            self.side = OrderSide(self.side.lower())
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type.lower())
        if isinstance(self.status, str):
            self.status = OrderStatus(self.status.lower())
        
        # Convert Decimal quantities to int if needed
        if isinstance(self.quantity, Decimal):
            self.quantity = int(self.quantity)
        if isinstance(self.filled_quantity, Decimal):
            self.filled_quantity = int(self.filled_quantity)
            
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        self.validate()
    
    def validate(self) -> None:
        """Validate order data integrity and business rules."""
        if not self.order_id or not isinstance(self.order_id, str):
            raise ValueError("Order ID must be a non-empty string")
        
        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("Symbol must be a non-empty string")
        
        if not re.match(r'^[A-Z]{1,5}$', self.symbol):
            raise ValueError(f"Invalid symbol format: {self.symbol}")
        
        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("Quantity must be a positive integer")
        
        if not isinstance(self.side, OrderSide):
            raise ValueError("Side must be an OrderSide enum value")
        
        if not isinstance(self.order_type, OrderType):
            raise ValueError("Order type must be an OrderType enum value")
        
        if not isinstance(self.status, OrderStatus):
            raise ValueError("Status must be an OrderStatus enum value")
        
        if self.filled_quantity < 0 or self.filled_quantity > self.quantity:
            raise ValueError("Filled quantity must be between 0 and order quantity")
        
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Limit orders must have a limit price")
        
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and self.stop_price is None:
            raise ValueError("Stop orders must have a stop price")
        
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("Limit price must be positive")
        
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("Stop price must be positive")
        
        if self.time_in_force not in ["day", "gtc", "ioc", "fok"]:
            raise ValueError("Invalid time in force value")
    
    @property
    def remaining_quantity(self) -> int:
        """Calculate remaining unfilled quantity."""
        return self.quantity - self.filled_quantity
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        return (self.filled_quantity / self.quantity) * 100 if self.quantity > 0 else 0
    
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_quantity == self.quantity
    
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return 0 < self.filled_quantity < self.quantity


@dataclass
class PortfolioSnapshot:
    """Represents a snapshot of portfolio state at a specific time."""
    
    timestamp: datetime
    total_value: Decimal
    buying_power: Decimal
    day_pnl: Decimal
    total_pnl: Decimal
    positions: List[Position] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate portfolio snapshot data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate portfolio snapshot data integrity and business rules."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
        
        if self.total_value < 0:
            raise ValueError("Total value cannot be negative")
        
        if self.buying_power < 0:
            raise ValueError("Buying power cannot be negative")
        
        if not isinstance(self.positions, list):
            raise ValueError("Positions must be a list")
        
        # Validate all positions
        for position in self.positions:
            if not isinstance(position, Position):
                raise ValueError("All positions must be Position objects")
            position.validate()
        
        # Check for duplicate symbols
        symbols = [pos.symbol for pos in self.positions]
        if len(symbols) != len(set(symbols)):
            raise ValueError("Portfolio cannot have duplicate positions for the same symbol")
    
    @property
    def position_count(self) -> int:
        """Get the number of positions in the portfolio."""
        return len(self.positions)
    
    @property
    def long_positions(self) -> List[Position]:
        """Get all long positions."""
        return [pos for pos in self.positions if pos.is_long()]
    
    @property
    def short_positions(self) -> List[Position]:
        """Get all short positions."""
        return [pos for pos in self.positions if pos.is_short()]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None
    
    def calculate_allocation(self, symbol: str) -> float:
        """Calculate allocation percentage for a symbol."""
        position = self.get_position(symbol)
        if position is None or self.total_value == 0:
            return 0.0
        return float(abs(position.market_value) / self.total_value * 100)