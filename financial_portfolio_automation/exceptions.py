"""
Base exception classes for the portfolio automation system.

This module defines the exception hierarchy used throughout the system
to handle various error conditions in a structured way.
"""

from typing import Optional, Dict, Any


class PortfolioAutomationError(Exception):
    """Base exception for all portfolio automation system errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}


class APIError(PortfolioAutomationError):
    """Exception raised for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 retry_after: Optional[int] = None, error_code: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, context)
        self.status_code = status_code
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limits are exceeded."""
    pass


class DataError(PortfolioAutomationError):
    """Exception raised for data quality or availability issues."""
    pass


class ValidationError(DataError):
    """Exception raised for data validation failures."""
    pass


class TradingError(PortfolioAutomationError):
    """Exception raised for trading execution errors."""
    pass


class InsufficientFundsError(TradingError):
    """Exception raised when there are insufficient funds for a trade."""
    pass


class InvalidOrderError(TradingError):
    """Exception raised for invalid order parameters."""
    pass


class RiskError(PortfolioAutomationError):
    """Exception raised for risk management violations."""
    pass


class PositionLimitError(RiskError):
    """Exception raised when position limits are exceeded."""
    pass


class DrawdownLimitError(RiskError):
    """Exception raised when drawdown limits are exceeded."""
    pass


class ConfigurationError(PortfolioAutomationError):
    """Exception raised for configuration-related errors."""
    pass


class SystemError(PortfolioAutomationError):
    """Exception raised for system-level errors."""
    pass


class DatabaseError(SystemError):
    """Exception raised for database connection or operation failures."""
    pass


class NetworkError(SystemError):
    """Exception raised for network connectivity issues."""
    pass


class MonitoringError(PortfolioAutomationError):
    """Exception raised for portfolio monitoring system errors."""
    pass