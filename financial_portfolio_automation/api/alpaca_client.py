"""
Alpaca Markets API client for portfolio automation.

This module provides a comprehensive interface to the Alpaca Markets API,
handling authentication, connection management, and basic API operations.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import time

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError as AlpacaAPIError, TimeFrame

from ..models.config import AlpacaConfig, Environment
from ..models.core import Quote, Position, Order, PortfolioSnapshot
from ..exceptions import (
    APIError, AuthenticationError, RateLimitError, NetworkError,
    TradingError, ValidationError
)
from decimal import Decimal


logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Client for interacting with Alpaca Markets API.
    
    Provides authentication, connection management, and basic API operations
    for account data, positions, and order management.
    """
    
    def __init__(self, config: AlpacaConfig):
        """
        Initialize the Alpaca client.
        
        Args:
            config: Alpaca configuration containing API credentials and settings
        """
        self.config = config
        self._api: Optional[tradeapi.REST] = None
        self._last_request_time = 0.0
        self._rate_limit_delay = 0.2  # 200ms between requests to avoid rate limits
        self._connection_verified = False
        
        logger.info(
            f"Initializing Alpaca client for {config.environment.value} environment"
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Alpaca Markets API.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
            NetworkError: If network connection fails
        """
        try:
            logger.info("Authenticating with Alpaca Markets API...")
            
            # Create API client
            self._api = tradeapi.REST(
                key_id=self.config.api_key,
                secret_key=self.config.secret_key,
                base_url=self.config.base_url,
                api_version='v2'
            )
            
            # Test authentication by getting account info
            account = self._api.get_account()
            
            if account is None:
                raise AuthenticationError("Failed to retrieve account information")
            
            self._connection_verified = True
            
            logger.info(
                f"Successfully authenticated with Alpaca API. "
                f"Account ID: {account.id}, Status: {account.status}"
            )
            
            return True
            
        except AlpacaAPIError as e:
            error_msg = f"Alpaca API authentication failed: {str(e)}"
            logger.error(error_msg)
            
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise AuthenticationError(error_msg, status_code=401)
            elif "403" in str(e) or "forbidden" in str(e).lower():
                raise AuthenticationError(error_msg, status_code=403)
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
                
        except AuthenticationError:
            # Re-raise AuthenticationError as-is
            raise
        except Exception as e:
            error_msg = f"Network error during authentication: {str(e)}"
            logger.error(error_msg)
            raise NetworkError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Alpaca API and return status information.
        
        Returns:
            Dictionary containing connection status and account information
            
        Raises:
            APIError: If connection test fails
        """
        if not self._api:
            raise APIError("Client not authenticated. Call authenticate() first.")
        
        try:
            logger.info("Testing Alpaca API connection...")
            
            # Get account information
            account = self._api.get_account()
            
            # Get market clock
            clock = self._api.get_clock()
            
            # Calculate API response time
            start_time = time.time()
            self._api.get_account()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            connection_info = {
                'connected': True,
                'account_id': account.id,
                'account_status': account.status,
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'market_open': clock.is_open,
                'next_open': clock.next_open.isoformat() if clock.next_open else None,
                'next_close': clock.next_close.isoformat() if clock.next_close else None,
                'response_time_ms': round(response_time, 2),
                'environment': self.config.environment.value,
                'data_feed': self.config.data_feed.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                f"Connection test successful. Response time: {response_time:.2f}ms"
            )
            
            return connection_info
            
        except AlpacaAPIError as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg)
            
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(
                    error_msg, 
                    status_code=429,
                    retry_after=60
                )
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
                
        except Exception as e:
            error_msg = f"Unexpected error during connection test: {str(e)}"
            logger.error(error_msg)
            raise NetworkError(error_msg)
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieve account information from Alpaca API.
        
        Returns:
            Dictionary containing account details
            
        Raises:
            APIError: If API request fails
        """
        self._ensure_authenticated()
        
        try:
            logger.debug("Retrieving account information...")
            
            account = self._rate_limited_request(lambda: self._api.get_account())
            
            account_info = {
                'account_id': account.id,
                'account_number': account.account_number,
                'status': account.status,
                'currency': account.currency,
                'buying_power': float(account.buying_power),
                'regt_buying_power': float(account.regt_buying_power),
                'daytrading_buying_power': float(account.daytrading_buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'last_equity': float(account.last_equity),
                'multiplier': int(account.multiplier),
                'day_trade_count': int(account.daytrade_count),
                'daytrade_count': int(account.daytrade_count),
                'sma': float(account.sma) if account.sma else 0.0,
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'trade_suspended_by_user': account.trade_suspended_by_user,
                'shorting_enabled': account.shorting_enabled,
                'long_market_value': float(account.long_market_value) if account.long_market_value else 0.0,
                'short_market_value': float(account.short_market_value) if account.short_market_value else 0.0,
                'initial_margin': float(account.initial_margin) if account.initial_margin else 0.0,
                'maintenance_margin': float(account.maintenance_margin) if account.maintenance_margin else 0.0,
                'last_maintenance_margin': float(account.last_maintenance_margin) if account.last_maintenance_margin else 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Retrieved account info for account {account.id}")
            
            return account_info
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve account information: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve current positions from Alpaca API.
        
        Returns:
            List of position dictionaries
            
        Raises:
            APIError: If API request fails
        """
        self._ensure_authenticated()
        
        try:
            logger.debug("Retrieving current positions...")
            
            positions = self._rate_limited_request(lambda: self._api.list_positions())
            
            position_list = []
            for pos in positions:
                position_data = {
                    'symbol': pos.symbol,
                    'asset_id': pos.asset_id,
                    'asset_class': pos.asset_class,
                    'quantity': int(pos.qty),
                    'side': pos.side,
                    'market_value': float(pos.market_value) if pos.market_value else 0.0,
                    'cost_basis': float(pos.cost_basis) if pos.cost_basis else 0.0,
                    'unrealized_pnl': float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                    'unrealized_pnl_percent': float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
                    'unrealized_intraday_pnl': float(pos.unrealized_intraday_pl) if pos.unrealized_intraday_pl else 0.0,
                    'unrealized_intraday_pnl_percent': float(pos.unrealized_intraday_plpc) if pos.unrealized_intraday_plpc else 0.0,
                    'current_price': float(pos.current_price) if pos.current_price else 0.0,
                    'lastday_price': float(pos.lastday_price) if pos.lastday_price else 0.0,
                    'change_today': float(pos.change_today) if pos.change_today else 0.0,
                    'avg_entry_price': float(pos.avg_entry_price) if pos.avg_entry_price else 0.0,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                position_list.append(position_data)
            
            logger.debug(f"Retrieved {len(position_list)} positions")
            
            return position_list
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve positions: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated and connection is verified.
        
        Returns:
            True if authenticated and connection verified, False otherwise
        """
        return self._api is not None and self._connection_verified
    
    def is_market_open(self) -> bool:
        """
        Check if the market is currently open.
        
        Returns:
            True if market is open, False otherwise
            
        Raises:
            APIError: If API request fails
        """
        self._ensure_authenticated()
        
        try:
            clock = self._rate_limited_request(lambda: self._api.get_clock())
            return clock.is_open
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to get market status: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_market_calendar(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get market calendar information.
        
        Args:
            start_date: Start date for calendar (defaults to today)
            end_date: End date for calendar (defaults to 30 days from start)
            
        Returns:
            List of market calendar entries
            
        Raises:
            APIError: If API request fails
        """
        self._ensure_authenticated()
        
        if start_date is None:
            start_date = datetime.now().date()
        
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        try:
            calendar = self._rate_limited_request(
                lambda: self._api.get_calendar(start=start_date, end=end_date)
            )
            
            calendar_list = []
            for day in calendar:
                calendar_entry = {
                    'date': day.date.strftime('%Y-%m-%d'),
                    'open': day.open.isoformat(),
                    'close': day.close.isoformat(),
                    'session_open': day.session_open.isoformat() if hasattr(day, 'session_open') else None,
                    'session_close': day.session_close.isoformat() if hasattr(day, 'session_close') else None
                }
                calendar_list.append(calendar_entry)
            
            return calendar_list
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to get market calendar: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_positions_as_models(self) -> List[Position]:
        """
        Retrieve current positions and convert to internal Position models.
        
        Returns:
            List of Position model objects
            
        Raises:
            APIError: If API request fails
            ValidationError: If position data is invalid
        """
        self._ensure_authenticated()
        
        try:
            logger.debug("Retrieving positions as Position models...")
            
            positions = self._rate_limited_request(lambda: self._api.list_positions())
            
            position_models = []
            for pos in positions:
                try:
                    position_model = self._convert_alpaca_position_to_model(pos)
                    position_models.append(position_model)
                except Exception as e:
                    logger.warning(f"Failed to convert position {pos.symbol}: {str(e)}")
                    continue
            
            logger.debug(f"Converted {len(position_models)} positions to models")
            
            return position_models
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve positions: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """
        Create a portfolio snapshot with current account and position data.
        
        Returns:
            PortfolioSnapshot model object
            
        Raises:
            APIError: If API request fails
            ValidationError: If data conversion fails
        """
        self._ensure_authenticated()
        
        try:
            logger.debug("Creating portfolio snapshot...")
            
            # Get account information and positions in parallel
            account_info = self.get_account_info()
            positions = self.get_positions_as_models()
            
            # Calculate total P&L from positions
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            total_day_pnl = sum(pos.day_pnl for pos in positions)
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_value=Decimal(str(account_info['portfolio_value'])),
                buying_power=Decimal(str(account_info['buying_power'])),
                day_pnl=Decimal(str(total_day_pnl)),
                total_pnl=Decimal(str(total_unrealized_pnl)),
                positions=positions
            )
            
            logger.debug(f"Created portfolio snapshot with {len(positions)} positions")
            
            return snapshot
            
        except Exception as e:
            error_msg = f"Failed to create portfolio snapshot: {str(e)}"
            logger.error(error_msg)
            if isinstance(e, (APIError, ValidationError)):
                raise
            else:
                raise APIError(error_msg)
    
    def _convert_alpaca_position_to_model(self, alpaca_position) -> Position:
        """
        Convert Alpaca API position object to internal Position model.
        
        Args:
            alpaca_position: Alpaca API position object
            
        Returns:
            Position model object
            
        Raises:
            ValidationError: If position data is invalid
        """
        try:
            # Handle potential None values and convert to appropriate types
            quantity = int(alpaca_position.qty) if alpaca_position.qty else 0
            market_value = Decimal(str(alpaca_position.market_value)) if alpaca_position.market_value else Decimal('0')
            cost_basis = Decimal(str(alpaca_position.cost_basis)) if alpaca_position.cost_basis else Decimal('0')
            unrealized_pnl = Decimal(str(alpaca_position.unrealized_pl)) if alpaca_position.unrealized_pl else Decimal('0')
            
            # Calculate day P&L from intraday unrealized P&L
            day_pnl = Decimal(str(alpaca_position.unrealized_intraday_pl)) if alpaca_position.unrealized_intraday_pl else Decimal('0')
            
            position = Position(
                symbol=alpaca_position.symbol,
                quantity=quantity,
                market_value=market_value,
                cost_basis=cost_basis,
                unrealized_pnl=unrealized_pnl,
                day_pnl=day_pnl
            )
            
            return position
            
        except Exception as e:
            error_msg = f"Failed to convert Alpaca position to model: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
    
    def _ensure_authenticated(self) -> None:
        """
        Ensure the client is authenticated.
        
        Raises:
            APIError: If client is not authenticated
        """
        if not self.is_authenticated():
            raise APIError("Client not authenticated. Call authenticate() first.")
    
    def _rate_limited_request(self, request_func):
        """
        Execute a request with rate limiting.
        
        Args:
            request_func: Function to execute the API request
            
        Returns:
            Result of the API request
        """
        # Implement simple rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)
        
        try:
            result = request_func()
            self._last_request_time = time.time()
            return result
            
        except AlpacaAPIError as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                logger.warning("Rate limit exceeded, waiting before retry...")
                time.sleep(60)  # Wait 1 minute for rate limit reset
                result = request_func()
                self._last_request_time = time.time()
                return result
            else:
                raise
    
    def __str__(self) -> str:
        """String representation of the client."""
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"AlpacaClient({self.config.environment.value}, {status})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the client."""
        return (
            f"AlpacaClient(environment={self.config.environment.value}, "
            f"data_feed={self.config.data_feed.value}, "
            f"authenticated={self.is_authenticated()})"
        )