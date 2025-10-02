"""
Market data client for real-time quotes and historical data retrieval.

This module provides a comprehensive interface for fetching market data from
Alpaca Markets, including real-time quotes, historical data, and market status.
"""

import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta, timezone
import time

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError as AlpacaAPIError, TimeFrame

from ..models.config import AlpacaConfig, DataFeed
from ..models.core import Quote
from ..exceptions import (
    APIError, AuthenticationError, RateLimitError, NetworkError,
    DataError, ValidationError
)
from decimal import Decimal


logger = logging.getLogger(__name__)


class MarketDataClient:
    """
    Client for retrieving market data from Alpaca Markets.
    
    Provides methods for fetching real-time quotes, historical data,
    and market information using the Alpaca Markets REST API.
    """
    
    def __init__(self, config: AlpacaConfig):
        """
        Initialize the market data client.
        
        Args:
            config: Alpaca configuration containing API credentials and settings
        """
        self.config = config
        self._data_api: Optional[tradeapi.REST] = None
        self._last_request_time = 0.0
        self._rate_limit_delay = 0.1  # 100ms between requests for market data
        self._connection_verified = False
        
        logger.info(
            f"Initializing MarketDataClient for {config.environment.value} environment "
            f"with {config.data_feed.value} data feed"
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Alpaca Markets data API.
        
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
            NetworkError: If network connection fails
        """
        try:
            logger.info("Authenticating with Alpaca Markets data API...")
            
            # Create data API client
            self._data_api = tradeapi.REST(
                key_id=self.config.api_key,
                secret_key=self.config.secret_key,
                base_url=self.config.base_url,
                api_version='v2'
            )
            
            # Test authentication by getting a simple quote
            test_symbol = "AAPL"
            try:
                quote = self._data_api.get_latest_quote(test_symbol)
                if quote is None:
                    raise AuthenticationError("Failed to retrieve test market data")
            except Exception as e:
                # If quote fails, try getting market status instead
                clock = self._data_api.get_clock()
                if clock is None:
                    raise AuthenticationError("Failed to retrieve market status")
            
            self._connection_verified = True
            
            logger.info(
                f"Successfully authenticated with Alpaca data API using "
                f"{self.config.data_feed.value} data feed"
            )
            
            return True
            
        except AlpacaAPIError as e:
            error_msg = f"Alpaca data API authentication failed: {str(e)}"
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
            error_msg = f"Network error during data API authentication: {str(e)}"
            logger.error(error_msg)
            raise NetworkError(error_msg)
    
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest quote for a symbol.
        
        Args:
            symbol: Stock symbol to get quote for
            
        Returns:
            Dictionary containing quote data
            
        Raises:
            APIError: If API request fails
            ValidationError: If symbol is invalid
        """
        self._ensure_authenticated()
        self._validate_symbol(symbol)
        
        try:
            logger.debug(f"Retrieving latest quote for {symbol}...")
            
            quote = self._rate_limited_request(
                lambda: self._data_api.get_latest_quote(symbol)
            )
            
            if quote is None:
                raise DataError(f"No quote data available for {symbol}")
            
            quote_data = {
                'symbol': symbol,
                'timestamp': quote.timestamp.isoformat() if quote.timestamp else datetime.now(timezone.utc).isoformat(),
                'bid': float(quote.bid_price) if quote.bid_price else 0.0,
                'ask': float(quote.ask_price) if quote.ask_price else 0.0,
                'bid_size': int(quote.bid_size) if quote.bid_size else 0,
                'ask_size': int(quote.ask_size) if quote.ask_size else 0,
                'exchange': getattr(quote, 'bid_exchange', None),
                'conditions': getattr(quote, 'conditions', []),
                'data_feed': self.config.data_feed.value
            }
            
            logger.debug(f"Retrieved quote for {symbol}: bid={quote_data['bid']}, ask={quote_data['ask']}")
            
            return quote_data
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve quote for {symbol}: {str(e)}"
            logger.error(error_msg)
            
            if "404" in str(e) or "not found" in str(e).lower():
                raise DataError(f"Symbol {symbol} not found")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(
                    error_msg, 
                    status_code=429,
                    retry_after=60
                )
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_latest_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get latest quotes for multiple symbols.
        
        Args:
            symbols: List of stock symbols to get quotes for
            
        Returns:
            Dictionary mapping symbols to quote data
            
        Raises:
            APIError: If API request fails
            ValidationError: If any symbol is invalid
        """
        self._ensure_authenticated()
        
        if not symbols:
            raise ValidationError("Symbols list cannot be empty")
        
        for symbol in symbols:
            self._validate_symbol(symbol)
        
        try:
            logger.debug(f"Retrieving latest quotes for {len(symbols)} symbols...")
            
            quotes = self._rate_limited_request(
                lambda: self._data_api.get_latest_quotes(symbols)
            )
            
            if quotes is None:
                raise DataError("No quote data available for requested symbols")
            
            quote_data = {}
            for symbol in symbols:
                if symbol in quotes:
                    quote = quotes[symbol]
                    quote_data[symbol] = {
                        'symbol': symbol,
                        'timestamp': quote.timestamp.isoformat() if quote.timestamp else datetime.now(timezone.utc).isoformat(),
                        'bid': float(quote.bid_price) if quote.bid_price else 0.0,
                        'ask': float(quote.ask_price) if quote.ask_price else 0.0,
                        'bid_size': int(quote.bid_size) if quote.bid_size else 0,
                        'ask_size': int(quote.ask_size) if quote.ask_size else 0,
                        'exchange': getattr(quote, 'bid_exchange', None),
                        'conditions': getattr(quote, 'conditions', []),
                        'data_feed': self.config.data_feed.value
                    }
                else:
                    logger.warning(f"No quote data available for {symbol}")
                    quote_data[symbol] = None
            
            logger.debug(f"Retrieved quotes for {len([q for q in quote_data.values() if q is not None])} symbols")
            
            return quote_data
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve quotes for symbols {symbols}: {str(e)}"
            logger.error(error_msg)
            
            if "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(
                    error_msg, 
                    status_code=429,
                    retry_after=60
                )
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_historical_bars(self, symbol: str, timeframe: str, start: datetime, 
                           end: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get historical price bars for a symbol.
        
        Args:
            symbol: Stock symbol to get data for
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            start: Start date for historical data
            end: End date for historical data (defaults to now)
            limit: Maximum number of bars to return
            
        Returns:
            List of historical bar data
            
        Raises:
            APIError: If API request fails
            ValidationError: If parameters are invalid
        """
        self._ensure_authenticated()
        self._validate_symbol(symbol)
        
        if end is None:
            end = datetime.now(timezone.utc)
        
        # Validate timeframe
        valid_timeframes = ['1Min', '5Min', '15Min', '30Min', '1Hour', '1Day']
        if timeframe not in valid_timeframes:
            raise ValidationError(f"Invalid timeframe. Must be one of: {valid_timeframes}")
        
        # Convert timeframe to Alpaca TimeFrame
        timeframe_map = {
            '1Min': TimeFrame.Minute,
            '5Min': TimeFrame(5, TimeFrame.Minute.unit),
            '15Min': TimeFrame(15, TimeFrame.Minute.unit),
            '30Min': TimeFrame(30, TimeFrame.Minute.unit),
            '1Hour': TimeFrame.Hour,
            '1Day': TimeFrame.Day
        }
        
        alpaca_timeframe = timeframe_map[timeframe]
        
        try:
            logger.debug(f"Retrieving historical bars for {symbol} from {start} to {end}")
            
            bars = self._rate_limited_request(
                lambda: self._data_api.get_bars(
                    symbol,
                    alpaca_timeframe,
                    start=start,
                    end=end,
                    limit=limit,
                    adjustment='raw'
                )
            )
            
            if bars is None or len(bars) == 0:
                logger.warning(f"No historical data available for {symbol}")
                return []
            
            bar_data = []
            for bar in bars:
                bar_dict = {
                    'symbol': symbol,
                    'timestamp': bar.timestamp.isoformat() if bar.timestamp else None,
                    'open': float(bar.open) if bar.open else 0.0,
                    'high': float(bar.high) if bar.high else 0.0,
                    'low': float(bar.low) if bar.low else 0.0,
                    'close': float(bar.close) if bar.close else 0.0,
                    'volume': int(bar.volume) if bar.volume else 0,
                    'trade_count': getattr(bar, 'trade_count', None),
                    'vwap': float(getattr(bar, 'vwap', 0)) if hasattr(bar, 'vwap') and bar.vwap else None,
                    'timeframe': timeframe,
                    'data_feed': self.config.data_feed.value
                }
                bar_data.append(bar_dict)
            
            logger.debug(f"Retrieved {len(bar_data)} historical bars for {symbol}")
            
            return bar_data
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve historical data for {symbol}: {str(e)}"
            logger.error(error_msg)
            
            if "404" in str(e) or "not found" in str(e).lower():
                raise DataError(f"Symbol {symbol} not found")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(
                    error_msg, 
                    status_code=429,
                    retry_after=60
                )
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_latest_trade(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest trade for a symbol.
        
        Args:
            symbol: Stock symbol to get trade for
            
        Returns:
            Dictionary containing trade data
            
        Raises:
            APIError: If API request fails
            ValidationError: If symbol is invalid
        """
        self._ensure_authenticated()
        self._validate_symbol(symbol)
        
        try:
            logger.debug(f"Retrieving latest trade for {symbol}...")
            
            trade = self._rate_limited_request(
                lambda: self._data_api.get_latest_trade(symbol)
            )
            
            if trade is None:
                raise DataError(f"No trade data available for {symbol}")
            
            trade_data = {
                'symbol': symbol,
                'timestamp': trade.timestamp.isoformat() if trade.timestamp else datetime.now(timezone.utc).isoformat(),
                'price': float(trade.price) if trade.price else 0.0,
                'size': int(trade.size) if trade.size else 0,
                'exchange': getattr(trade, 'exchange', None),
                'conditions': getattr(trade, 'conditions', []),
                'data_feed': self.config.data_feed.value
            }
            
            logger.debug(f"Retrieved trade for {symbol}: price={trade_data['price']}, size={trade_data['size']}")
            
            return trade_data
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to retrieve trade for {symbol}: {str(e)}"
            logger.error(error_msg)
            
            if "404" in str(e) or "not found" in str(e).lower():
                raise DataError(f"Symbol {symbol} not found")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise RateLimitError(
                    error_msg, 
                    status_code=429,
                    retry_after=60
                )
            else:
                raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_quote_as_model(self, symbol: str) -> Quote:
        """
        Get latest quote and convert to internal Quote model.
        
        Args:
            symbol: Stock symbol to get quote for
            
        Returns:
            Quote model object
            
        Raises:
            APIError: If API request fails
            ValidationError: If quote data is invalid
        """
        quote_data = self.get_latest_quote(symbol)
        
        try:
            quote = Quote(
                symbol=quote_data['symbol'],
                timestamp=datetime.fromisoformat(quote_data['timestamp'].replace('Z', '+00:00')),
                bid=Decimal(str(quote_data['bid'])),
                ask=Decimal(str(quote_data['ask'])),
                bid_size=quote_data['bid_size'],
                ask_size=quote_data['ask_size']
            )
            
            return quote
            
        except Exception as e:
            error_msg = f"Failed to convert quote data to model: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(error_msg)
    
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
            clock = self._rate_limited_request(lambda: self._data_api.get_clock())
            return clock.is_open
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to get market status: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        Get comprehensive market status information.
        
        Returns:
            Dictionary containing market status details
            
        Raises:
            APIError: If API request fails
        """
        self._ensure_authenticated()
        
        try:
            clock = self._rate_limited_request(lambda: self._data_api.get_clock())
            
            status = {
                'is_open': clock.is_open,
                'timestamp': clock.timestamp.isoformat() if clock.timestamp else datetime.now(timezone.utc).isoformat(),
                'next_open': clock.next_open.isoformat() if clock.next_open else None,
                'next_close': clock.next_close.isoformat() if clock.next_close else None,
                'timezone': 'America/New_York'
            }
            
            return status
            
        except AlpacaAPIError as e:
            error_msg = f"Failed to get market status: {str(e)}"
            logger.error(error_msg)
            raise APIError(error_msg, status_code=getattr(e, 'status_code', None))
    
    def is_authenticated(self) -> bool:
        """
        Check if the client is authenticated and connection is verified.
        
        Returns:
            True if authenticated and connection verified, False otherwise
        """
        return self._data_api is not None and self._connection_verified
    
    def _ensure_authenticated(self) -> None:
        """
        Ensure the client is authenticated.
        
        Raises:
            APIError: If client is not authenticated
        """
        if not self.is_authenticated():
            raise APIError("Market data client not authenticated. Call authenticate() first.")
    
    def _validate_symbol(self, symbol: str) -> None:
        """
        Validate symbol format.
        
        Args:
            symbol: Symbol to validate
            
        Raises:
            ValidationError: If symbol is invalid
        """
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Symbol must be a non-empty string")
        
        if not symbol.isalpha() or len(symbol) > 5:
            raise ValidationError(f"Invalid symbol format: {symbol}")
        
        # Convert to uppercase for consistency
        symbol = symbol.upper()
    
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
        return f"MarketDataClient({self.config.environment.value}, {self.config.data_feed.value}, {status})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the client."""
        return (
            f"MarketDataClient(environment={self.config.environment.value}, "
            f"data_feed={self.config.data_feed.value}, "
            f"authenticated={self.is_authenticated()})"
        )