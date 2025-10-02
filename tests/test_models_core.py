"""
Unit tests for core data models.

Tests validation logic, business rules, and data integrity for all core data models.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from financial_portfolio_automation.models.core import (
    Quote,
    Position,
    Order,
    PortfolioSnapshot,
    OrderSide,
    OrderType,
    OrderStatus,
)


class TestQuote:
    """Test cases for Quote data model."""
    
    def test_valid_quote_creation(self):
        """Test creating a valid quote."""
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            bid=Decimal("150.00"),
            ask=Decimal("150.05"),
            bid_size=100,
            ask_size=200
        )
        
        assert quote.symbol == "AAPL"
        assert quote.bid == Decimal("150.00")
        assert quote.ask == Decimal("150.05")
        assert quote.spread == Decimal("0.05")
        assert quote.mid_price == Decimal("150.025")
    
    def test_invalid_symbol_format(self):
        """Test validation of invalid symbol formats."""
        with pytest.raises(ValueError, match="Invalid symbol format"):
            Quote(
                symbol="invalid_symbol",
                timestamp=datetime.now(),
                bid=Decimal("100"),
                ask=Decimal("101"),
                bid_size=100,
                ask_size=100
            )
    
    def test_empty_symbol(self):
        """Test validation of empty symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            Quote(
                symbol="",
                timestamp=datetime.now(),
                bid=Decimal("100"),
                ask=Decimal("101"),
                bid_size=100,
                ask_size=100
            )
    
    def test_negative_prices(self):
        """Test validation of negative prices."""
        with pytest.raises(ValueError, match="Bid and ask prices must be non-negative"):
            Quote(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=Decimal("-1"),
                ask=Decimal("101"),
                bid_size=100,
                ask_size=100
            )
    
    def test_ask_less_than_bid(self):
        """Test validation when ask is less than bid."""
        with pytest.raises(ValueError, match="Ask price cannot be less than bid price"):
            Quote(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=Decimal("101"),
                ask=Decimal("100"),
                bid_size=100,
                ask_size=100
            )
    
    def test_negative_sizes(self):
        """Test validation of negative sizes."""
        with pytest.raises(ValueError, match="Bid and ask sizes must be non-negative"):
            Quote(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=Decimal("100"),
                ask=Decimal("101"),
                bid_size=-1,
                ask_size=100
            )


class TestPosition:
    """Test cases for Position data model."""
    
    def test_valid_long_position(self):
        """Test creating a valid long position."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal("15000"),
            cost_basis=Decimal("14500"),
            unrealized_pnl=Decimal("500"),
            day_pnl=Decimal("100")
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.is_long()
        assert not position.is_short()
        assert position.average_cost == Decimal("145")
        assert position.current_price == Decimal("150")
    
    def test_valid_short_position(self):
        """Test creating a valid short position."""
        position = Position(
            symbol="TSLA",
            quantity=-50,
            market_value=Decimal("10000"),
            cost_basis=Decimal("11000"),
            unrealized_pnl=Decimal("1000"),
            day_pnl=Decimal("-200")
        )
        
        assert position.quantity == -50
        assert not position.is_long()
        assert position.is_short()
        assert position.average_cost == Decimal("220")
        assert position.current_price == Decimal("200")
    
    def test_zero_quantity_validation(self):
        """Test validation of zero quantity."""
        with pytest.raises(ValueError, match="Position quantity cannot be zero"):
            Position(
                symbol="AAPL",
                quantity=0,
                market_value=Decimal("0"),
                cost_basis=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                day_pnl=Decimal("0")
            )
    
    def test_negative_cost_basis(self):
        """Test validation of negative cost basis."""
        with pytest.raises(ValueError, match="Cost basis cannot be negative"):
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal("15000"),
                cost_basis=Decimal("-1000"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("100")
            )
    
    def test_negative_market_value(self):
        """Test validation of negative market value."""
        with pytest.raises(ValueError, match="Market value cannot be negative"):
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal("-1000"),
                cost_basis=Decimal("15000"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("100")
            )


class TestOrder:
    """Test cases for Order data model."""
    
    def test_valid_market_order(self):
        """Test creating a valid market order."""
        order = Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
        
        assert order.order_id == "order_123"
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.side == OrderSide.BUY
        assert order.remaining_quantity == 100
        assert order.fill_percentage == 0
        assert not order.is_filled()
        assert not order.is_partially_filled()
    
    def test_valid_limit_order(self):
        """Test creating a valid limit order."""
        order = Order(
            order_id="order_456",
            symbol="TSLA",
            quantity=50,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal("200.00")
        )
        
        assert order.limit_price == Decimal("200.00")
        assert order.order_type == OrderType.LIMIT
    
    def test_partially_filled_order(self):
        """Test order with partial fills."""
        order = Order(
            order_id="order_789",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.PARTIALLY_FILLED,
            filled_quantity=30,
            average_fill_price=Decimal("150.00")
        )
        
        assert order.remaining_quantity == 70
        assert order.fill_percentage == 30
        assert not order.is_filled()
        assert order.is_partially_filled()
    
    def test_filled_order(self):
        """Test completely filled order."""
        order = Order(
            order_id="order_999",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_fill_price=Decimal("150.00")
        )
        
        assert order.remaining_quantity == 0
        assert order.fill_percentage == 100
        assert order.is_filled()
        assert not order.is_partially_filled()
    
    def test_limit_order_without_limit_price(self):
        """Test validation of limit order without limit price."""
        with pytest.raises(ValueError, match="Limit orders must have a limit price"):
            Order(
                order_id="order_bad",
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.NEW
            )
    
    def test_stop_order_without_stop_price(self):
        """Test validation of stop order without stop price."""
        with pytest.raises(ValueError, match="Stop orders must have a stop price"):
            Order(
                order_id="order_bad",
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.STOP,
                status=OrderStatus.NEW
            )
    
    def test_invalid_filled_quantity(self):
        """Test validation of invalid filled quantity."""
        with pytest.raises(ValueError, match="Filled quantity must be between 0 and order quantity"):
            Order(
                order_id="order_bad",
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.NEW,
                filled_quantity=150
            )
    
    def test_negative_quantity(self):
        """Test validation of negative quantity."""
        with pytest.raises(ValueError, match="Quantity must be a positive integer"):
            Order(
                order_id="order_bad",
                symbol="AAPL",
                quantity=-100,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.NEW
            )


class TestPortfolioSnapshot:
    """Test cases for PortfolioSnapshot data model."""
    
    def test_valid_portfolio_snapshot(self):
        """Test creating a valid portfolio snapshot."""
        positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal("15000"),
                cost_basis=Decimal("14500"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("100")
            ),
            Position(
                symbol="TSLA",
                quantity=50,
                market_value=Decimal("10000"),
                cost_basis=Decimal("9500"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("200")
            )
        ]
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime(2024, 1, 1, 16, 0, 0),
            total_value=Decimal("30000"),
            buying_power=Decimal("5000"),
            day_pnl=Decimal("300"),
            total_pnl=Decimal("1000"),
            positions=positions
        )
        
        assert snapshot.position_count == 2
        assert len(snapshot.long_positions) == 2
        assert len(snapshot.short_positions) == 0
        assert snapshot.get_position("AAPL") is not None
        assert snapshot.get_position("NVDA") is None
        assert snapshot.calculate_allocation("AAPL") == 50.0  # 15000/30000 * 100
    
    def test_empty_portfolio_snapshot(self):
        """Test creating an empty portfolio snapshot."""
        snapshot = PortfolioSnapshot(
            timestamp=datetime(2024, 1, 1, 16, 0, 0),
            total_value=Decimal("10000"),
            buying_power=Decimal("10000"),
            day_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            positions=[]
        )
        
        assert snapshot.position_count == 0
        assert len(snapshot.long_positions) == 0
        assert len(snapshot.short_positions) == 0
    
    def test_mixed_long_short_positions(self):
        """Test portfolio with both long and short positions."""
        positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal("15000"),
                cost_basis=Decimal("14500"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("100")
            ),
            Position(
                symbol="TSLA",
                quantity=-50,
                market_value=Decimal("10000"),
                cost_basis=Decimal("11000"),
                unrealized_pnl=Decimal("1000"),
                day_pnl=Decimal("-200")
            )
        ]
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime(2024, 1, 1, 16, 0, 0),
            total_value=Decimal("30000"),
            buying_power=Decimal("5000"),
            day_pnl=Decimal("300"),
            total_pnl=Decimal("1500"),
            positions=positions
        )
        
        assert len(snapshot.long_positions) == 1
        assert len(snapshot.short_positions) == 1
        assert snapshot.long_positions[0].symbol == "AAPL"
        assert snapshot.short_positions[0].symbol == "TSLA"
    
    def test_duplicate_symbols_validation(self):
        """Test validation of duplicate symbols in positions."""
        positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal("15000"),
                cost_basis=Decimal("14500"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("100")
            ),
            Position(
                symbol="AAPL",  # Duplicate symbol
                quantity=50,
                market_value=Decimal("7500"),
                cost_basis=Decimal("7000"),
                unrealized_pnl=Decimal("500"),
                day_pnl=Decimal("50")
            )
        ]
        
        with pytest.raises(ValueError, match="Portfolio cannot have duplicate positions for the same symbol"):
            PortfolioSnapshot(
                timestamp=datetime(2024, 1, 1, 16, 0, 0),
                total_value=Decimal("30000"),
                buying_power=Decimal("5000"),
                day_pnl=Decimal("300"),
                total_pnl=Decimal("1000"),
                positions=positions
            )
    
    def test_negative_total_value(self):
        """Test validation of negative total value."""
        with pytest.raises(ValueError, match="Total value cannot be negative"):
            PortfolioSnapshot(
                timestamp=datetime(2024, 1, 1, 16, 0, 0),
                total_value=Decimal("-1000"),
                buying_power=Decimal("5000"),
                day_pnl=Decimal("300"),
                total_pnl=Decimal("1000"),
                positions=[]
            )
    
    def test_negative_buying_power(self):
        """Test validation of negative buying power."""
        with pytest.raises(ValueError, match="Buying power cannot be negative"):
            PortfolioSnapshot(
                timestamp=datetime(2024, 1, 1, 16, 0, 0),
                total_value=Decimal("30000"),
                buying_power=Decimal("-1000"),
                day_pnl=Decimal("300"),
                total_pnl=Decimal("1000"),
                positions=[]
            )