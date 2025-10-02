"""
Unit tests for MarketDataClient.

Tests the market data client functionality with mocked API responses
to ensure proper data retrieval and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from financial_portfolio_automation.api.market_data_client import MarketDataClient
from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.models.core import Quote
from financial_portfolio_automation.exceptions import (
    APIError, AuthenticationError, RateLimitError, NetworkError,
    DataError, ValidationError
)


@pytest.fixture
def alpaca_config():
    """Create a test Alpaca configuration."""
    return AlpacaConfig(
        api_key="test_api_key_12345678901234567890",
        secret_key="test_secret_key_1234567890123456789012345678901234567890",
        base_url="https://paper-api.alpaca.markets",
        data_feed=DataFeed.IEX,
        environment=Environment.PAPER
    )


@pytest.fixture
def market_data_client(alpaca_config):
    """Create a MarketDataClient instance for testing."""
    return MarketDataClient(alpaca_config)


@pytest.fixture
def mock_quote():
    """Create a mock quote object."""
    quote = Mock()
    quote.timestamp = datetime.now(timezone.utc)
    quote.bid_price = 150.25
    quote.ask_price = 150.30
    quote.bid_size = 100
    quote.ask_size = 200
    quote.bid_exchange = 'NASDAQ'
    quote.conditions = []
    return quote


@pytest.fixture
def mock_trade():
    """Create a mock trade object."""
    trade = Mock()
    trade.timestamp = datetime.now(timezone.utc)
    trade.price = 150.28
    trade.size = 150
    trade.exchange = 'NASDAQ'
    trade.conditions = []
    return trade


@pytest.fixture
def mock_bar():
    """Create a mock bar object."""
    bar = Mock()
    bar.timestamp = datetime.now(timezone.utc)
    bar.open = 150.00
    bar.high = 151.00
    bar.low = 149.50
    bar.close = 150.75
    bar.volume = 1000000
    bar.trade_count = 5000
    bar.vwap = 150.40
    return bar


class TestMarketDataClientInitialization:
    """Test MarketDataClient initialization and configuration."""
    
    def test_init_with_valid_config(self, alpaca_config):
        """Test initialization with valid configuration."""
        client = MarketDataClient(alpaca_config)
        
        assert client.config == alpaca_config
        assert client._data_api is None
        assert not client._connection_verified
        assert client._rate_limit_delay == 0.1
    
    def test_init_sets_correct_attributes(self, alpaca_config):
        """Test that initialization sets all required attributes."""
        client = MarketDataClient(alpaca_config)
        
        assert hasattr(client, 'config')
        assert hasattr(client, '_data_api')
        assert hasattr(client, '_last_request_time')
        assert hasattr(client, '_rate_limit_delay')
        assert hasattr(client, '_connection_verified')


class TestMarketDataClientAuthentication:
    """Test MarketDataClient authentication functionality."""
    
    @patch('financial_portfolio_automation.api.market_data_client.tradeapi.REST')
    def test_authenticate_success(self, mock_rest_class, market_data_client, mock_quote):
        """Test successful authentication."""
        # Setup mock
        mock_api = Mock()
        mock_rest_class.return_value = mock_api
        mock_api.get_latest_quote.return_value = mock_quote
        
        # Test authentication
        result = market_data_client.authenticate()
        
        assert result is True
        assert market_data_client.is_authenticated()
        assert market_data_client._connection_verified
        
        # Verify API client was created with correct parameters
        mock_rest_class.assert_called_once_with(
            key_id=market_data_client.config.api_key,
            secret_key=market_data_client.config.secret_key,
            base_url=market_data_client.config.base_url,
            api_version='v2'
        )
    
    @patch('financial_portfolio_automation.api.market_data_client.tradeapi.REST')
    def test_authenticate_fallback_to_clock(self, mock_rest_class, market_data_client):
        """Test authentication fallback to clock when quote fails."""
        # Setup mock
        mock_api = Mock()
        mock_rest_class.return_value = mock_api
        mock_api.get_latest_quote.side_effect = Exception("Quote failed")
        
        mock_clock = Mock()
        mock_clock.is_open = True
        mock_api.get_clock.return_value = mock_clock
        
        # Test authentication
        result = market_data_client.authenticate()
        
        assert result is True
        assert market_data_client.is_authenticated()
    
    @patch('financial_portfolio_automation.api.market_data_client.tradeapi.REST')
    def test_authenticate_api_error_401(self, mock_rest_class, market_data_client):
        """Test authentication failure with 401 error."""
        # Setup mock
        mock_api = Mock()
        mock_rest_class.return_value = mock_api
        
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        mock_api.get_latest_quote.side_effect = AlpacaAPIError({"message": "401 Unauthorized"})
        mock_api.get_clock.side_effect = AlpacaAPIError({"message": "401 Unauthorized"})
        
        # Test authentication failure
        with pytest.raises(AuthenticationError) as exc_info:
            market_data_client.authenticate()
        
        assert "401" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()
        assert not market_data_client.is_authenticated()
    
    @patch('financial_portfolio_automation.api.market_data_client.tradeapi.REST')
    def test_authenticate_network_error(self, mock_rest_class, market_data_client):
        """Test authentication failure with network error."""
        # Setup mock
        mock_rest_class.side_effect = ConnectionError("Network unreachable")
        
        # Test authentication failure
        with pytest.raises(NetworkError):
            market_data_client.authenticate()
        
        assert not market_data_client.is_authenticated()


class TestMarketDataClientQuotes:
    """Test MarketDataClient quote retrieval functionality."""
    
    def test_get_latest_quote_success(self, market_data_client, mock_quote):
        """Test successful quote retrieval."""
        # Setup authenticated client
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_latest_quote.return_value = mock_quote
        
        # Test quote retrieval
        result = market_data_client.get_latest_quote("AAPL")
        
        assert result['symbol'] == "AAPL"
        assert result['bid'] == 150.25
        assert result['ask'] == 150.30
        assert result['bid_size'] == 100
        assert result['ask_size'] == 200
        assert result['data_feed'] == 'iex'
        assert 'timestamp' in result
    
    def test_get_latest_quote_not_authenticated(self, market_data_client):
        """Test quote retrieval when not authenticated."""
        with pytest.raises(APIError, match="not authenticated"):
            market_data_client.get_latest_quote("AAPL")
    
    def test_get_latest_quote_invalid_symbol(self, market_data_client):
        """Test quote retrieval with invalid symbol."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        with pytest.raises(ValidationError, match="Invalid symbol format"):
            market_data_client.get_latest_quote("INVALID123")
    
    def test_get_latest_quote_no_data(self, market_data_client):
        """Test quote retrieval when no data available."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_latest_quote.return_value = None
        
        with pytest.raises(DataError, match="No quote data available"):
            market_data_client.get_latest_quote("AAPL")
    
    def test_get_latest_quotes_multiple_symbols(self, market_data_client, mock_quote):
        """Test retrieval of quotes for multiple symbols."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        # Setup mock response
        quotes_response = {
            'AAPL': mock_quote,
            'GOOGL': mock_quote
        }
        market_data_client._data_api.get_latest_quotes.return_value = quotes_response
        
        # Test multiple quotes retrieval
        result = market_data_client.get_latest_quotes(['AAPL', 'GOOGL'])
        
        assert len(result) == 2
        assert 'AAPL' in result
        assert 'GOOGL' in result
        assert result['AAPL']['symbol'] == 'AAPL'
        assert result['GOOGL']['symbol'] == 'GOOGL'
    
    def test_get_latest_quotes_empty_list(self, market_data_client):
        """Test quotes retrieval with empty symbol list."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        with pytest.raises(ValidationError, match="Symbols list cannot be empty"):
            market_data_client.get_latest_quotes([])
    
    def test_get_quote_as_model(self, market_data_client, mock_quote):
        """Test conversion of quote data to Quote model."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_latest_quote.return_value = mock_quote
        
        # Test quote model conversion
        result = market_data_client.get_quote_as_model("AAPL")
        
        assert isinstance(result, Quote)
        assert result.symbol == "AAPL"
        assert result.bid == Decimal('150.25')
        assert result.ask == Decimal('150.30')
        assert result.bid_size == 100
        assert result.ask_size == 200


class TestMarketDataClientHistoricalData:
    """Test MarketDataClient historical data functionality."""
    
    def test_get_historical_bars_success(self, market_data_client, mock_bar):
        """Test successful historical bars retrieval."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_bars.return_value = [mock_bar, mock_bar]
        
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Test historical bars retrieval
        result = market_data_client.get_historical_bars("AAPL", "1Day", start_date)
        
        assert len(result) == 2
        assert result[0]['symbol'] == "AAPL"
        assert result[0]['open'] == 150.00
        assert result[0]['high'] == 151.00
        assert result[0]['low'] == 149.50
        assert result[0]['close'] == 150.75
        assert result[0]['volume'] == 1000000
        assert result[0]['timeframe'] == "1Day"
    
    def test_get_historical_bars_invalid_timeframe(self, market_data_client):
        """Test historical bars with invalid timeframe."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        with pytest.raises(ValidationError, match="Invalid timeframe"):
            market_data_client.get_historical_bars("AAPL", "InvalidTimeframe", start_date)
    
    def test_get_historical_bars_no_data(self, market_data_client):
        """Test historical bars when no data available."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_bars.return_value = []
        
        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Test with no data
        result = market_data_client.get_historical_bars("AAPL", "1Day", start_date)
        
        assert result == []


class TestMarketDataClientTrades:
    """Test MarketDataClient trade data functionality."""
    
    def test_get_latest_trade_success(self, market_data_client, mock_trade):
        """Test successful trade retrieval."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_latest_trade.return_value = mock_trade
        
        # Test trade retrieval
        result = market_data_client.get_latest_trade("AAPL")
        
        assert result['symbol'] == "AAPL"
        assert result['price'] == 150.28
        assert result['size'] == 150
        assert result['exchange'] == 'NASDAQ'
        assert result['data_feed'] == 'iex'
        assert 'timestamp' in result
    
    def test_get_latest_trade_no_data(self, market_data_client):
        """Test trade retrieval when no data available."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        market_data_client._data_api.get_latest_trade.return_value = None
        
        with pytest.raises(DataError, match="No trade data available"):
            market_data_client.get_latest_trade("AAPL")


class TestMarketDataClientMarketStatus:
    """Test MarketDataClient market status functionality."""
    
    def test_is_market_open_true(self, market_data_client):
        """Test market open status when market is open."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        mock_clock = Mock()
        mock_clock.is_open = True
        market_data_client._data_api.get_clock.return_value = mock_clock
        
        result = market_data_client.is_market_open()
        assert result is True
    
    def test_is_market_open_false(self, market_data_client):
        """Test market open status when market is closed."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        mock_clock = Mock()
        mock_clock.is_open = False
        market_data_client._data_api.get_clock.return_value = mock_clock
        
        result = market_data_client.is_market_open()
        assert result is False
    
    def test_get_market_status(self, market_data_client):
        """Test comprehensive market status retrieval."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        mock_clock = Mock()
        mock_clock.is_open = True
        mock_clock.timestamp = datetime.now(timezone.utc)
        mock_clock.next_open = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_clock.next_close = datetime.now(timezone.utc) + timedelta(hours=8)
        market_data_client._data_api.get_clock.return_value = mock_clock
        
        result = market_data_client.get_market_status()
        
        assert result['is_open'] is True
        assert 'timestamp' in result
        assert 'next_open' in result
        assert 'next_close' in result
        assert result['timezone'] == 'America/New_York'


class TestMarketDataClientErrorHandling:
    """Test MarketDataClient error handling."""
    
    def test_rate_limit_error_handling(self, market_data_client):
        """Test rate limit error handling."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        market_data_client._data_api.get_latest_quote.side_effect = AlpacaAPIError({"message": "429 Rate limit exceeded"})
        
        with pytest.raises(RateLimitError):
            market_data_client.get_latest_quote("AAPL")
    
    def test_symbol_not_found_error(self, market_data_client):
        """Test symbol not found error handling."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        market_data_client._data_api.get_latest_quote.side_effect = AlpacaAPIError({"message": "404 Symbol not found"})
        
        with pytest.raises(DataError, match="Symbol .* not found"):
            market_data_client.get_latest_quote("AAPL")
    
    @patch('time.sleep')
    def test_rate_limited_request_with_retry(self, mock_sleep, market_data_client):
        """Test rate limited request with automatic retry."""
        market_data_client._data_api = Mock()
        market_data_client._connection_verified = True
        
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        # First call raises rate limit, second succeeds
        mock_quote = Mock()
        mock_quote.bid_price = 150.25
        mock_quote.ask_price = 150.30
        mock_quote.bid_size = 100
        mock_quote.ask_size = 200
        mock_quote.timestamp = datetime.now(timezone.utc)
        
        market_data_client._data_api.get_latest_quote.side_effect = [
            AlpacaAPIError({"message": "429 Rate limit exceeded"}),
            mock_quote
        ]
        
        # Should succeed after retry
        result = market_data_client.get_latest_quote("AAPL")
        
        assert result['symbol'] == "AAPL"
        mock_sleep.assert_called_once_with(60)  # Should wait 60 seconds


class TestMarketDataClientUtilityMethods:
    """Test MarketDataClient utility methods."""
    
    def test_string_representation(self, market_data_client):
        """Test string representation of client."""
        str_repr = str(market_data_client)
        assert "MarketDataClient" in str_repr
        assert "paper" in str_repr
        assert "iex" in str_repr
        assert "not authenticated" in str_repr
    
    def test_detailed_representation(self, market_data_client):
        """Test detailed string representation of client."""
        repr_str = repr(market_data_client)
        assert "MarketDataClient" in repr_str
        assert "environment=paper" in repr_str
        assert "data_feed=iex" in repr_str
        assert "authenticated=False" in repr_str
    
    def test_validate_symbol_valid(self, market_data_client):
        """Test symbol validation with valid symbols."""
        # These should not raise exceptions
        market_data_client._validate_symbol("AAPL")
        market_data_client._validate_symbol("GOOGL")
        market_data_client._validate_symbol("MSFT")
        market_data_client._validate_symbol("A")
    
    def test_validate_symbol_invalid(self, market_data_client):
        """Test symbol validation with invalid symbols."""
        with pytest.raises(ValidationError):
            market_data_client._validate_symbol("")
        
        with pytest.raises(ValidationError):
            market_data_client._validate_symbol("TOOLONG")
        
        with pytest.raises(ValidationError):
            market_data_client._validate_symbol("123")
        
        with pytest.raises(ValidationError):
            market_data_client._validate_symbol("AA-PL")


if __name__ == '__main__':
    pytest.main([__file__])