"""
Unit tests for DataValidator implementation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from financial_portfolio_automation.data.validator import DataValidator, ValidationRule, ValidationResult
from financial_portfolio_automation.models.core import (
    Quote, Position, Order, PortfolioSnapshot,
    OrderSide, OrderType, OrderStatus
)
from financial_portfolio_automation.exceptions import ValidationError


class TestValidationRule:
    
    def test_validation_rule_creation(self):
        """Test creating a validation rule."""
        rule = ValidationRule(
            name="test_rule",
            description="Test rule description",
            severity="error",
            validator=lambda x: True
        )
        
        assert rule.name == "test_rule"
        assert rule.description == "Test rule description"
        assert rule.severity == "error"
        assert rule.validator(None) is True


class TestValidationResult:
    
    def test_validation_result_creation(self):
        """Test creating a validation result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["warning1"],
            info=["info1"]
        )
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == ["warning1"]
        assert result.info == ["info1"]
    
    def test_validation_result_auto_valid_setting(self):
        """Test automatic is_valid setting based on errors."""
        # No errors - should be valid
        result = ValidationResult(
            is_valid=False,  # This should be overridden
            errors=[],
            warnings=[],
            info=[]
        )
        assert result.is_valid is True
        
        # With errors - should be invalid
        result = ValidationResult(
            is_valid=True,  # This should be overridden
            errors=["error1"],
            warnings=[],
            info=[]
        )
        assert result.is_valid is False


class TestDataValidator:
    
    @pytest.fixture
    def validator(self):
        """Create a DataValidator instance for testing."""
        return DataValidator()
    
    @pytest.fixture
    def valid_quote(self):
        """Create a valid quote for testing."""
        return Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("150.00"),
            ask=Decimal("150.05"),
            bid_size=100,
            ask_size=200
        )
    
    @pytest.fixture
    def valid_position(self):
        """Create a valid position for testing."""
        return Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal("15000.00"),
            cost_basis=Decimal("14500.00"),
            unrealized_pnl=Decimal("500.00"),
            day_pnl=Decimal("50.00")
        )
    
    @pytest.fixture
    def valid_order(self):
        """Create a valid order for testing."""
        return Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            filled_quantity=0,
            limit_price=Decimal("149.50"),
            time_in_force="day"
        )
    
    @pytest.fixture
    def valid_portfolio_snapshot(self, valid_position):
        """Create a valid portfolio snapshot for testing."""
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal("25000.00"),
            buying_power=Decimal("10000.00"),
            day_pnl=Decimal("250.00"),
            total_pnl=Decimal("1500.00"),
            positions=[valid_position]
        )
    
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert 'quote' in validator.rules
        assert 'position' in validator.rules
        assert 'order' in validator.rules
        assert 'portfolio' in validator.rules
        
        # Check that rules are properly structured
        for rule_type, rules in validator.rules.items():
            assert isinstance(rules, list)
            for rule in rules:
                assert isinstance(rule, ValidationRule)
                assert rule.name
                assert rule.description
                assert rule.severity in ['error', 'warning', 'info']
                assert callable(rule.validator)
    
    def test_validate_valid_quote(self, validator, valid_quote):
        """Test validating a valid quote."""
        result = validator.validate_quote(valid_quote)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_quote_with_invalid_symbol(self, validator):
        """Test validating quote with invalid symbol."""
        # Test empty symbol - this will fail at Quote creation due to validation
        with pytest.raises(ValueError):
            Quote(
                symbol="",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("150.00"),
                ask=Decimal("150.05"),
                bid_size=100,
                ask_size=200
            )
        
        # Test invalid symbol format - this will also fail at Quote creation
        with pytest.raises(ValueError):
            Quote(
                symbol="invalid123",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("150.00"),
                ask=Decimal("150.05"),
                bid_size=100,
                ask_size=200
            )
    
    def test_validate_quote_with_invalid_prices(self, validator):
        """Test validating quote with invalid prices."""
        # Test negative prices - this will fail at Quote creation
        with pytest.raises(ValueError):
            Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("-150.00"),
                ask=Decimal("150.05"),
                bid_size=100,
                ask_size=200
            )
        
        # Test ask < bid - this will fail at Quote creation
        with pytest.raises(ValueError):
            Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("150.05"),
                ask=Decimal("150.00"),
                bid_size=100,
                ask_size=200
            )
    
    def test_validate_quote_with_large_spread(self, validator):
        """Test validating quote with large bid-ask spread."""
        # Create quote with large spread (should generate warning)
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("100.00"),
            ask=Decimal("120.00"),  # 20% spread
            bid_size=100,
            ask_size=200
        )
        
        result = validator.validate_quote(quote)
        assert result.is_valid is True  # Should still be valid
        assert len(result.warnings) > 0  # But should have warnings
    
    def test_validate_valid_position(self, validator, valid_position):
        """Test validating a valid position."""
        result = validator.validate_position(valid_position)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_position_with_zero_quantity(self, validator):
        """Test validating position with zero quantity."""
        # This will fail at Position creation due to validation
        with pytest.raises(ValueError):
            Position(
                symbol="AAPL",
                quantity=0,
                market_value=Decimal("0.00"),
                cost_basis=Decimal("0.00"),
                unrealized_pnl=Decimal("0.00"),
                day_pnl=Decimal("0.00")
            )
    
    def test_validate_position_with_inconsistent_pnl(self, validator):
        """Test validating position with inconsistent P&L calculation."""
        # Create position where unrealized_pnl != market_value - cost_basis
        position = Position(
            symbol="AAPL",
            quantity=100,
            market_value=Decimal("15000.00"),
            cost_basis=Decimal("14500.00"),
            unrealized_pnl=Decimal("1000.00"),  # Should be 500.00
            day_pnl=Decimal("50.00")
        )
        
        result = validator.validate_position(position)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_valid_order(self, validator, valid_order):
        """Test validating a valid order."""
        result = validator.validate_order(valid_order)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_order_with_invalid_filled_quantity(self, validator):
        """Test validating order with invalid filled quantity."""
        # Since Order model validates on creation, we test this will fail at creation
        with pytest.raises(ValueError):
            Order(
                order_id="order_123",
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.PARTIALLY_FILLED,
                filled_quantity=150,  # More than order quantity
                time_in_force="day"
            )
    
    def test_validate_order_limit_without_limit_price(self, validator):
        """Test validating limit order without limit price."""
        # This should fail at Order creation due to validation
        with pytest.raises(ValueError):
            Order(
                order_id="order_123",
                symbol="AAPL",
                quantity=100,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                status=OrderStatus.NEW,
                filled_quantity=0,
                limit_price=None,  # Required for limit orders
                time_in_force="day"
            )
    
    def test_validate_valid_portfolio_snapshot(self, validator, valid_portfolio_snapshot):
        """Test validating a valid portfolio snapshot."""
        result = validator.validate_portfolio_snapshot(valid_portfolio_snapshot)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_portfolio_snapshot_with_negative_values(self, validator):
        """Test validating portfolio snapshot with negative values."""
        # This should fail at PortfolioSnapshot creation due to validation
        with pytest.raises(ValueError):
            PortfolioSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_value=Decimal("-1000.00"),  # Negative total value
                buying_power=Decimal("10000.00"),
                day_pnl=Decimal("250.00"),
                total_pnl=Decimal("1500.00"),
                positions=[]
            )
    
    def test_validate_price_bounds(self, validator):
        """Test price bounds validation."""
        # Valid prices
        assert validator.validate_price_bounds("AAPL", Decimal("150.00")) is True
        assert validator.validate_price_bounds("AAPL", Decimal("0.01")) is True
        
        # Invalid prices
        assert validator.validate_price_bounds("AAPL", Decimal("0.00")) is False
        assert validator.validate_price_bounds("AAPL", Decimal("-10.00")) is False
        assert validator.validate_price_bounds("AAPL", Decimal("200000.00")) is False
    
    def test_validate_timestamp_consistency(self, validator):
        """Test timestamp consistency validation."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)
        
        # Valid timestamps (all in the past)
        result = validator.validate_timestamp_consistency([past, now])
        assert result.is_valid is True
        
        # Future timestamps (should generate errors)
        result = validator.validate_timestamp_consistency([now, future])
        assert result.is_valid is False
        assert len(result.errors) > 0
        
        # Unordered timestamps (should generate warnings)
        result = validator.validate_timestamp_consistency([now, past])
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0  # But has warnings
        
        # Duplicate timestamps (should generate warnings)
        result = validator.validate_timestamp_consistency([now, now])
        assert result.is_valid is True
        assert len(result.warnings) > 0
    
    def test_validate_timestamp_consistency_empty_list(self, validator):
        """Test timestamp consistency validation with empty list."""
        result = validator.validate_timestamp_consistency([])
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validate_data_consistency(self, validator):
        """Test data consistency validation between quotes."""
        # Valid quotes
        quote1 = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("150.00"),
            ask=Decimal("150.05"),
            bid_size=100,
            ask_size=200
        )
        
        quote2 = Quote(
            symbol="GOOGL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("2500.00"),
            ask=Decimal("2500.10"),
            bid_size=50,
            ask_size=75
        )
        
        result = validator.validate_data_consistency([quote1, quote2])
        assert result.is_valid is True
        
        # Quote with large spread (should generate warning)
        quote_large_spread = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            bid=Decimal("100.00"),
            ask=Decimal("120.00"),  # 20% spread
            bid_size=100,
            ask_size=200
        )
        
        result = validator.validate_data_consistency([quote_large_spread])
        assert result.is_valid is True  # Still valid
        assert len(result.warnings) > 0  # But has warnings
    
    def test_validate_data_consistency_empty_list(self, validator):
        """Test data consistency validation with empty list."""
        result = validator.validate_data_consistency([])
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_quote_validation_rules(self, validator):
        """Test individual quote validation rules."""
        quote_rules = validator.rules['quote']
        
        # Find specific rules
        symbol_rule = next((r for r in quote_rules if r.name == "symbol_format"), None)
        price_bounds_rule = next((r for r in quote_rules if r.name == "price_bounds"), None)
        bid_ask_rule = next((r for r in quote_rules if r.name == "bid_ask_order"), None)
        
        assert symbol_rule is not None
        assert price_bounds_rule is not None
        assert bid_ask_rule is not None
        
        # Test symbol format rule
        valid_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150"), Decimal("150.05"), 100, 200)
        assert symbol_rule.validator(valid_quote) is True
        
        # Test price bounds rule
        assert price_bounds_rule.validator(valid_quote) is True
        
        # Test bid-ask order rule
        assert bid_ask_rule.validator(valid_quote) is True
    
    def test_position_validation_rules(self, validator):
        """Test individual position validation rules."""
        position_rules = validator.rules['position']
        
        # Find specific rules
        pnl_rule = next((r for r in position_rules if r.name == "pnl_consistency"), None)
        quantity_rule = next((r for r in position_rules if r.name == "quantity_nonzero"), None)
        
        assert pnl_rule is not None
        assert quantity_rule is not None
        
        # Test with valid position
        valid_position = Position("AAPL", 100, Decimal("15000"), Decimal("14500"), Decimal("500"), Decimal("50"))
        assert pnl_rule.validator(valid_position) is True
        assert quantity_rule.validator(valid_position) is True
        
        # Test with invalid P&L
        invalid_position = Position("AAPL", 100, Decimal("15000"), Decimal("14500"), Decimal("1000"), Decimal("50"))
        assert pnl_rule.validator(invalid_position) is False
    
    def test_order_validation_rules(self, validator):
        """Test individual order validation rules."""
        order_rules = validator.rules['order']
        
        # Find specific rules
        filled_qty_rule = next((r for r in order_rules if r.name == "filled_quantity_valid"), None)
        qty_rule = next((r for r in order_rules if r.name == "quantity_positive"), None)
        
        assert filled_qty_rule is not None
        assert qty_rule is not None
        
        # Test with valid order
        valid_order = Order("123", "AAPL", 100, OrderSide.BUY, OrderType.MARKET, OrderStatus.NEW, 0, time_in_force="day")
        assert filled_qty_rule.validator(valid_order) is True
        assert qty_rule.validator(valid_order) is True
        
        # Test with invalid filled quantity - create a mock order to test the rule directly
        class MockOrder:
            def __init__(self):
                self.quantity = 100
                self.filled_quantity = 150  # Invalid - more than quantity
        
        mock_invalid_order = MockOrder()
        assert filled_qty_rule.validator(mock_invalid_order) is False
    
    def test_portfolio_validation_rules(self, validator):
        """Test individual portfolio validation rules."""
        portfolio_rules = validator.rules['portfolio']
        
        # Find specific rules
        value_rule = next((r for r in portfolio_rules if r.name == "total_value_reasonable"), None)
        buying_power_rule = next((r for r in portfolio_rules if r.name == "buying_power_nonnegative"), None)
        
        assert value_rule is not None
        assert buying_power_rule is not None
        
        # Test with valid portfolio
        valid_portfolio = PortfolioSnapshot(
            datetime.now(timezone.utc), Decimal("25000"), Decimal("10000"), 
            Decimal("250"), Decimal("1500"), []
        )
        assert value_rule.validator(valid_portfolio) is True
        assert buying_power_rule.validator(valid_portfolio) is True
    
    def test_validation_with_exception_in_rule(self, validator):
        """Test validation behavior when a rule raises an exception."""
        # Create a rule that raises an exception
        def failing_validator(obj):
            raise Exception("Test exception")
        
        # Add the failing rule temporarily
        failing_rule = ValidationRule("failing_rule", "Test failing rule", "error", failing_validator)
        validator.rules['quote'].append(failing_rule)
        
        try:
            valid_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150"), Decimal("150.05"), 100, 200)
            result = validator.validate_quote(valid_quote)
            
            # Should have an error from the failing rule
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert any("Test exception" in error for error in result.errors)
        finally:
            # Clean up - remove the failing rule
            validator.rules['quote'].remove(failing_rule)
    
    def test_validation_severity_levels(self, validator):
        """Test that validation properly handles different severity levels."""
        # Create rules with different severities
        error_rule = ValidationRule("error_rule", "Error rule", "error", lambda x: False)
        warning_rule = ValidationRule("warning_rule", "Warning rule", "warning", lambda x: False)
        info_rule = ValidationRule("info_rule", "Info rule", "info", lambda x: False)
        
        # Add rules temporarily
        validator.rules['quote'].extend([error_rule, warning_rule, info_rule])
        
        try:
            valid_quote = Quote("AAPL", datetime.now(timezone.utc), Decimal("150"), Decimal("150.05"), 100, 200)
            result = validator.validate_quote(valid_quote)
            
            # Should be invalid due to error rule
            assert result.is_valid is False
            assert len(result.errors) >= 1
            assert len(result.warnings) >= 1
            assert len(result.info) >= 1
            
            # Check that messages contain rule names
            assert any("error_rule" in error for error in result.errors)
            assert any("warning_rule" in warning for warning in result.warnings)
            assert any("info_rule" in info for info in result.info)
        finally:
            # Clean up
            for rule in [error_rule, warning_rule, info_rule]:
                if rule in validator.rules['quote']:
                    validator.rules['quote'].remove(rule)