"""
Unit tests for AlpacaClient class.

Tests authentication, connection management, and basic API operations
with mocked Alpaca API responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.exceptions import (
    APIError, AuthenticationError, RateLimitError, NetworkError
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
def alpaca_client(alpaca_config):
    """Create a test Alpaca client."""
    return AlpacaClient(alpaca_config)


@pytest.fixture
def mock_account():
    """Create a mock account object."""
    account = Mock()
    account.id = "test_account_id"
    account.account_number = "123456789"
    account.status = "ACTIVE"
    account.currency = "USD"
    account.buying_power = "10000.00"
    account.regt_buying_power = "10000.00"
    account.daytrading_buying_power = "40000.00"
    account.cash = "5000.00"
    account.portfolio_value = "15000.00"
    account.equity = "15000.00"
    account.last_equity = "14500.00"
    account.multiplier = "4"
    account.day_trade_count = "0"
    account.daytrade_count = "0"
    account.sma = "25000.00"
    account.pattern_day_trader = False
    account.trading_blocked = False
    account.transfers_blocked = False
    account.account_blocked = False
    account.created_at = datetime(2023, 1, 1, 12, 0, 0)
    account.trade_suspended_by_user = False
    account.shorting_enabled = True
    account.long_market_value = "10000.00"
    account.short_market_value = "0.00"
    account.initial_margin = "0.00"
    account.maintenance_margin = "0.00"
    account.last_maintenance_margin = "0.00"
    return account


@pytest.fixture
def mock_position():
    """Create a mock position object."""
    position = Mock()
    position.symbol = "AAPL"
    position.asset_id = "test_asset_id"
    position.asset_class = "us_equity"
    position.qty = "100"
    position.side = "long"
    position.market_value = "15000.00"
    position.cost_basis = "14000.00"
    position.unrealized_pl = "1000.00"
    position.unrealized_plpc = "0.0714"
    position.unrealized_intraday_pl = "500.00"
    position.unrealized_intraday_plpc = "0.0357"
    position.current_price = "150.00"
    position.lastday_price = "145.00"
    position.change_today = "5.00"
    position.avg_entry_price = "140.00"
    return position


@pytest.fixture
def mock_clock():
    """Create a mock market clock object."""
    clock = Mock()
    clock.is_open = True
    clock.next_open = datetime.now() + timedelta(hours=1)
    clock.next_close = datetime.now() + timedelta(hours=8)
    return clock


class TestAlpacaClientInitialization:
    """Test AlpacaClient initialization."""
    
    def test_init_with_valid_config(self, alpaca_config):
        """Test initialization with valid configuration."""
        client = AlpacaClient(alpaca_config)
        
        assert client.config == alpaca_config
        assert client._api is None
        assert not client._connection_verified
        assert client._rate_limit_delay == 0.2
    
    def test_init_sets_correct_attributes(self, alpaca_config):
        """Test that initialization sets correct attributes."""
        client = AlpacaClient(alpaca_config)
        
        assert client.config.environment == Environment.PAPER
        assert client.config.data_feed == DataFeed.IEX
        assert not client.is_authenticated()


class TestAlpacaClientAuthentication:
    """Test AlpacaClient authentication methods."""
    
    @patch('financial_portfolio_automation.api.alpaca_client.tradeapi.REST')
    def test_authenticate_success(self, mock_rest, alpaca_client, mock_account):
        """Test successful authentication."""
        # Setup mock
        mock_api = Mock()
        mock_api.get_account.return_value = mock_account
        mock_rest.return_value = mock_api
        
        # Test authentication
        result = alpaca_client.authenticate()
        
        assert result is True
        assert alpaca_client.is_authenticated()
        assert alpaca_client._connection_verified
        
        # Verify API client was created with correct parameters
        mock_rest.assert_called_once_with(
            key_id=alpaca_client.config.api_key,
            secret_key=alpaca_client.config.secret_key,
            base_url=alpaca_client.config.base_url,
            api_version='v2'
        )
    
    @patch('financial_portfolio_automation.api.alpaca_client.tradeapi.REST')
    def test_authenticate_api_error_401(self, mock_rest, alpaca_client):
        """Test authentication failure with 401 error."""
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        mock_rest.side_effect = AlpacaAPIError({"message": "401 Unauthorized"})
        
        with pytest.raises(AuthenticationError) as exc_info:
            alpaca_client.authenticate()
        
        assert "401" in str(exc_info.value)
        assert not alpaca_client.is_authenticated()
    
    @patch('financial_portfolio_automation.api.alpaca_client.tradeapi.REST')
    def test_authenticate_api_error_403(self, mock_rest, alpaca_client):
        """Test authentication failure with 403 error."""
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        mock_rest.side_effect = AlpacaAPIError({"message": "403 Forbidden"})
        
        with pytest.raises(AuthenticationError) as exc_info:
            alpaca_client.authenticate()
        
        assert "403" in str(exc_info.value)
        assert not alpaca_client.is_authenticated()
    
    @patch('financial_portfolio_automation.api.alpaca_client.tradeapi.REST')
    def test_authenticate_network_error(self, mock_rest, alpaca_client):
        """Test authentication failure with network error."""
        mock_rest.side_effect = ConnectionError("Network error")
        
        with pytest.raises(NetworkError) as exc_info:
            alpaca_client.authenticate()
        
        assert "Network error" in str(exc_info.value)
        assert not alpaca_client.is_authenticated()
    
    @patch('financial_portfolio_automation.api.alpaca_client.tradeapi.REST')
    def test_authenticate_account_none(self, mock_rest, alpaca_client):
        """Test authentication failure when account is None."""
        mock_api = Mock()
        mock_api.get_account.return_value = None
        mock_rest.return_value = mock_api
        
        with pytest.raises(AuthenticationError) as exc_info:
            alpaca_client.authenticate()
        
        assert "Failed to retrieve account information" in str(exc_info.value)
        assert not alpaca_client.is_authenticated()


class TestAlpacaClientConnectionTesting:
    """Test AlpacaClient connection testing methods."""
    
    def test_test_connection_not_authenticated(self, alpaca_client):
        """Test connection test when not authenticated."""
        with pytest.raises(APIError) as exc_info:
            alpaca_client.test_connection()
        
        assert "not authenticated" in str(exc_info.value)
    
    @patch('time.time')
    def test_test_connection_success(self, mock_time, alpaca_client, mock_account, mock_clock):
        """Test successful connection test."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        # Setup mocks
        mock_time.side_effect = [1000.0, 1000.1]  # 100ms response time
        alpaca_client._api.get_account.return_value = mock_account
        alpaca_client._api.get_clock.return_value = mock_clock
        
        # Test connection
        result = alpaca_client.test_connection()
        
        assert result['connected'] is True
        assert result['account_id'] == "test_account_id"
        assert result['account_status'] == "ACTIVE"
        assert result['buying_power'] == 10000.0
        assert result['portfolio_value'] == 15000.0
        assert result['market_open'] is True
        assert result['response_time_ms'] == 100.0
        assert result['environment'] == "paper"
        assert result['data_feed'] == "iex"
        assert 'timestamp' in result
    
    def test_test_connection_rate_limit_error(self, alpaca_client):
        """Test connection test with rate limit error."""
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_account.side_effect = AlpacaAPIError({"message": "429 Rate limit exceeded"})
        
        with pytest.raises(RateLimitError) as exc_info:
            alpaca_client.test_connection()
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60


class TestAlpacaClientAccountData:
    """Test AlpacaClient account data retrieval methods."""
    
    def test_get_account_info_not_authenticated(self, alpaca_client):
        """Test get_account_info when not authenticated."""
        with pytest.raises(APIError) as exc_info:
            alpaca_client.get_account_info()
        
        assert "not authenticated" in str(exc_info.value)
    
    def test_get_account_info_success(self, alpaca_client, mock_account):
        """Test successful account info retrieval."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_account.return_value = mock_account
        
        # Test account info retrieval
        result = alpaca_client.get_account_info()
        
        assert result['account_id'] == "test_account_id"
        assert result['account_number'] == "123456789"
        assert result['status'] == "ACTIVE"
        assert result['currency'] == "USD"
        assert result['buying_power'] == 10000.0
        assert result['cash'] == 5000.0
        assert result['portfolio_value'] == 15000.0
        assert result['equity'] == 15000.0
        assert result['multiplier'] == 4
        assert result['pattern_day_trader'] is False
        assert result['trading_blocked'] is False
        assert 'timestamp' in result
    
    def test_get_positions_success(self, alpaca_client, mock_position):
        """Test successful positions retrieval."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.list_positions.return_value = [mock_position]
        
        # Test positions retrieval
        result = alpaca_client.get_positions()
        
        assert len(result) == 1
        position = result[0]
        assert position['symbol'] == "AAPL"
        assert position['quantity'] == 100
        assert position['side'] == "long"
        assert position['market_value'] == 15000.0
        assert position['cost_basis'] == 14000.0
        assert position['unrealized_pnl'] == 1000.0
        assert position['current_price'] == 150.0
        assert position['avg_entry_price'] == 140.0
        assert 'timestamp' in position
    
    def test_get_positions_empty(self, alpaca_client):
        """Test positions retrieval with no positions."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.list_positions.return_value = []
        
        # Test positions retrieval
        result = alpaca_client.get_positions()
        
        assert result == []


class TestAlpacaClientMarketData:
    """Test AlpacaClient market data methods."""
    
    def test_is_market_open_success(self, alpaca_client, mock_clock):
        """Test successful market open check."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_clock.return_value = mock_clock
        
        # Test market open check
        result = alpaca_client.is_market_open()
        
        assert result is True
    
    def test_is_market_open_closed(self, alpaca_client):
        """Test market open check when market is closed."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        mock_clock = Mock()
        mock_clock.is_open = False
        alpaca_client._api.get_clock.return_value = mock_clock
        
        # Test market open check
        result = alpaca_client.is_market_open()
        
        assert result is False
    
    def test_get_market_calendar_success(self, alpaca_client):
        """Test successful market calendar retrieval."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        # Create mock calendar entry
        mock_calendar_entry = Mock()
        mock_calendar_entry.date = datetime(2023, 12, 1).date()
        mock_calendar_entry.open = datetime(2023, 12, 1, 9, 30)
        mock_calendar_entry.close = datetime(2023, 12, 1, 16, 0)
        
        alpaca_client._api.get_calendar.return_value = [mock_calendar_entry]
        
        # Test calendar retrieval
        result = alpaca_client.get_market_calendar()
        
        assert len(result) == 1
        entry = result[0]
        assert entry['date'] == "2023-12-01"
        assert entry['open'] == "2023-12-01T09:30:00"
        assert entry['close'] == "2023-12-01T16:00:00"


class TestAlpacaClientRateLimiting:
    """Test AlpacaClient rate limiting functionality."""
    
    @patch('time.time')
    @patch('time.sleep')
    def test_rate_limited_request_with_delay(self, mock_sleep, mock_time, alpaca_client):
        """Test rate limited request with delay."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        # Setup time mocks to simulate rapid requests
        mock_time.side_effect = [1000.0, 1000.1, 1000.3]  # Second request too soon
        alpaca_client._last_request_time = 1000.0
        
        # Create a test request function
        test_func = Mock(return_value="test_result")
        
        # Execute rate limited request
        result = alpaca_client._rate_limited_request(test_func)
        
        # Verify sleep was called to enforce rate limit
        mock_sleep.assert_called_once()
        assert result == "test_result"
    
    @patch('time.sleep')
    def test_rate_limited_request_with_rate_limit_error(self, mock_sleep, alpaca_client):
        """Test rate limited request handling API rate limit error."""
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        # Create a test function that raises rate limit error first, then succeeds
        test_func = Mock()
        test_func.side_effect = [
            AlpacaAPIError({"message": "429 Rate limit exceeded"}),
            "success_result"
        ]
        
        # Execute rate limited request
        result = alpaca_client._rate_limited_request(test_func)
        
        # Verify sleep was called for rate limit handling
        mock_sleep.assert_called_once_with(60)
        assert result == "success_result"
        assert test_func.call_count == 2


class TestAlpacaClientUtilityMethods:
    """Test AlpacaClient utility methods."""
    
    def test_is_authenticated_false(self, alpaca_client):
        """Test is_authenticated when not authenticated."""
        assert alpaca_client.is_authenticated() is False
    
    def test_is_authenticated_true(self, alpaca_client):
        """Test is_authenticated when authenticated."""
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        assert alpaca_client.is_authenticated() is True
    
    def test_str_representation(self, alpaca_client):
        """Test string representation of client."""
        result = str(alpaca_client)
        assert "AlpacaClient(paper, not authenticated)" == result
        
        # Test authenticated state
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        result = str(alpaca_client)
        assert "AlpacaClient(paper, authenticated)" == result
    
    def test_repr_representation(self, alpaca_client):
        """Test detailed string representation of client."""
        result = repr(alpaca_client)
        expected = "AlpacaClient(environment=paper, data_feed=iex, authenticated=False)"
        assert result == expected


class TestAlpacaClientDataTransformation:
    """Test AlpacaClient data transformation methods."""
    
    def test_get_positions_as_models_success(self, alpaca_client, mock_position):
        """Test successful conversion of positions to models."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.list_positions.return_value = [mock_position]
        
        # Test positions as models
        result = alpaca_client.get_positions_as_models()
        
        assert len(result) == 1
        position = result[0]
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.market_value == Decimal('15000.00')
        assert position.cost_basis == Decimal('14000.00')
        assert position.unrealized_pnl == Decimal('1000.00')
        assert position.day_pnl == Decimal('500.00')
    
    def test_get_positions_as_models_empty(self, alpaca_client):
        """Test positions as models with no positions."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.list_positions.return_value = []
        
        # Test positions as models
        result = alpaca_client.get_positions_as_models()
        
        assert result == []
    
    def test_get_positions_as_models_invalid_data(self, alpaca_client):
        """Test positions as models with invalid position data."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        
        # Create mock position with invalid data
        invalid_position = Mock()
        invalid_position.symbol = ""  # Invalid empty symbol
        invalid_position.qty = "100"
        invalid_position.market_value = "15000.00"
        invalid_position.cost_basis = "14000.00"
        invalid_position.unrealized_pl = "1000.00"
        invalid_position.unrealized_intraday_pl = "500.00"
        
        alpaca_client._api.list_positions.return_value = [invalid_position]
        
        # Test positions as models - should skip invalid positions
        result = alpaca_client.get_positions_as_models()
        
        assert result == []  # Invalid position should be skipped
    
    def test_get_portfolio_snapshot_success(self, alpaca_client, mock_account, mock_position):
        """Test successful portfolio snapshot creation."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_account.return_value = mock_account
        alpaca_client._api.list_positions.return_value = [mock_position]
        
        # Test portfolio snapshot
        result = alpaca_client.get_portfolio_snapshot()
        
        assert isinstance(result.timestamp, datetime)
        assert result.total_value == Decimal('15000.00')
        assert result.buying_power == Decimal('10000.00')
        assert result.day_pnl == Decimal('500.00')  # From position
        assert result.total_pnl == Decimal('1000.00')  # From position
        assert len(result.positions) == 1
        assert result.positions[0].symbol == "AAPL"
    
    def test_get_portfolio_snapshot_no_positions(self, alpaca_client, mock_account):
        """Test portfolio snapshot with no positions."""
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_account.return_value = mock_account
        alpaca_client._api.list_positions.return_value = []
        
        # Test portfolio snapshot
        result = alpaca_client.get_portfolio_snapshot()
        
        assert result.total_value == Decimal('15000.00')
        assert result.buying_power == Decimal('10000.00')
        assert result.day_pnl == Decimal('0')  # No positions
        assert result.total_pnl == Decimal('0')  # No positions
        assert len(result.positions) == 0
    
    def test_convert_alpaca_position_to_model_success(self, alpaca_client, mock_position):
        """Test successful conversion of Alpaca position to model."""
        result = alpaca_client._convert_alpaca_position_to_model(mock_position)
        
        assert result.symbol == "AAPL"
        assert result.quantity == 100
        assert result.market_value == Decimal('15000.00')
        assert result.cost_basis == Decimal('14000.00')
        assert result.unrealized_pnl == Decimal('1000.00')
        assert result.day_pnl == Decimal('500.00')
    
    def test_convert_alpaca_position_to_model_none_values(self, alpaca_client):
        """Test conversion with None values in Alpaca position."""
        # Create position with None values
        position_with_nones = Mock()
        position_with_nones.symbol = "AAPL"
        position_with_nones.qty = "100"
        position_with_nones.market_value = None
        position_with_nones.cost_basis = None
        position_with_nones.unrealized_pl = None
        position_with_nones.unrealized_intraday_pl = None
        
        result = alpaca_client._convert_alpaca_position_to_model(position_with_nones)
        
        assert result.symbol == "AAPL"
        assert result.quantity == 100
        assert result.market_value == Decimal('0')
        assert result.cost_basis == Decimal('0')
        assert result.unrealized_pnl == Decimal('0')
        assert result.day_pnl == Decimal('0')
    
    def test_convert_alpaca_position_to_model_invalid_symbol(self, alpaca_client):
        """Test conversion with invalid symbol."""
        from financial_portfolio_automation.exceptions import ValidationError
        
        # Create position with invalid symbol
        invalid_position = Mock()
        invalid_position.symbol = ""  # Invalid empty symbol
        invalid_position.qty = "100"
        invalid_position.market_value = "15000.00"
        invalid_position.cost_basis = "14000.00"
        invalid_position.unrealized_pl = "1000.00"
        invalid_position.unrealized_intraday_pl = "500.00"
        
        with pytest.raises(ValidationError):
            alpaca_client._convert_alpaca_position_to_model(invalid_position)


class TestAlpacaClientErrorHandling:
    """Test AlpacaClient error handling."""
    
    def test_ensure_authenticated_raises_error(self, alpaca_client):
        """Test _ensure_authenticated raises error when not authenticated."""
        with pytest.raises(APIError) as exc_info:
            alpaca_client._ensure_authenticated()
        
        assert "not authenticated" in str(exc_info.value)
    
    def test_api_error_handling(self, alpaca_client):
        """Test API error handling in account info retrieval."""
        from alpaca_trade_api.rest import APIError as AlpacaAPIError
        
        # Setup authenticated client
        alpaca_client._api = Mock()
        alpaca_client._connection_verified = True
        alpaca_client._api.get_account.side_effect = AlpacaAPIError({"message": "500 Internal Server Error"})
        
        with pytest.raises(APIError) as exc_info:
            alpaca_client.get_account_info()
        
        assert "Failed to retrieve account information" in str(exc_info.value)