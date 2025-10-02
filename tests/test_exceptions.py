"""Tests for exception classes."""

import pytest
from financial_portfolio_automation.exceptions import (
    PortfolioAutomationError,
    APIError,
    AuthenticationError,
    RateLimitError,
    DataError,
    ValidationError,
    TradingError,
    InsufficientFundsError,
    InvalidOrderError,
    RiskError,
    PositionLimitError,
    DrawdownLimitError,
    ConfigurationError,
    SystemError,
    DatabaseError,
    NetworkError
)


class TestPortfolioAutomationError:
    """Test base exception class."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        error = PortfolioAutomationError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code is None
        assert error.context == {}
    
    def test_exception_with_code_and_context(self):
        """Test exception with error code and context."""
        context = {"symbol": "AAPL", "quantity": 100}
        error = PortfolioAutomationError("Test error", "E001", context)
        assert error.error_code == "E001"
        assert error.context == context


class TestAPIError:
    """Test API-related exceptions."""
    
    def test_api_error_basic(self):
        """Test basic API error."""
        error = APIError("API request failed")
        assert str(error) == "API request failed"
        assert error.status_code is None
        assert error.retry_after is None
    
    def test_api_error_with_status_code(self):
        """Test API error with status code."""
        error = APIError("Rate limit exceeded", status_code=429, retry_after=60)
        assert error.status_code == 429
        assert error.retry_after == 60
    
    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Invalid API key")
        assert isinstance(error, APIError)
        assert str(error) == "Invalid API key"
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError("Too many requests", retry_after=30)
        assert isinstance(error, APIError)
        assert error.retry_after == 30


class TestDataError:
    """Test data-related exceptions."""
    
    def test_data_error(self):
        """Test basic data error."""
        error = DataError("Invalid market data")
        assert str(error) == "Invalid market data"
    
    def test_validation_error(self):
        """Test validation error."""
        error = ValidationError("Price cannot be negative")
        assert isinstance(error, DataError)
        assert str(error) == "Price cannot be negative"


class TestTradingError:
    """Test trading-related exceptions."""
    
    def test_trading_error(self):
        """Test basic trading error."""
        error = TradingError("Order execution failed")
        assert str(error) == "Order execution failed"
    
    def test_insufficient_funds_error(self):
        """Test insufficient funds error."""
        error = InsufficientFundsError("Not enough buying power")
        assert isinstance(error, TradingError)
        assert str(error) == "Not enough buying power"
    
    def test_invalid_order_error(self):
        """Test invalid order error."""
        error = InvalidOrderError("Invalid order quantity")
        assert isinstance(error, TradingError)
        assert str(error) == "Invalid order quantity"


class TestRiskError:
    """Test risk-related exceptions."""
    
    def test_risk_error(self):
        """Test basic risk error."""
        error = RiskError("Risk limit exceeded")
        assert str(error) == "Risk limit exceeded"
    
    def test_position_limit_error(self):
        """Test position limit error."""
        error = PositionLimitError("Position size too large")
        assert isinstance(error, RiskError)
        assert str(error) == "Position size too large"
    
    def test_drawdown_limit_error(self):
        """Test drawdown limit error."""
        error = DrawdownLimitError("Maximum drawdown exceeded")
        assert isinstance(error, RiskError)
        assert str(error) == "Maximum drawdown exceeded"


class TestSystemError:
    """Test system-related exceptions."""
    
    def test_configuration_error(self):
        """Test configuration error."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
    
    def test_system_error(self):
        """Test basic system error."""
        error = SystemError("System failure")
        assert str(error) == "System failure"
    
    def test_database_error(self):
        """Test database error."""
        error = DatabaseError("Database connection failed")
        assert isinstance(error, SystemError)
        assert str(error) == "Database connection failed"
    
    def test_network_error(self):
        """Test network error."""
        error = NetworkError("Network timeout")
        assert isinstance(error, SystemError)
        assert str(error) == "Network timeout"