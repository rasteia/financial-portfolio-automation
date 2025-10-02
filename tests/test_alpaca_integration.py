"""
Integration tests for AlpacaClient using Alpaca paper trading environment.

These tests require valid Alpaca API credentials and use the paper trading
environment to test real API interactions safely.
"""

import pytest
import os
from datetime import datetime, timezone
from decimal import Decimal

from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.models.core import Position, PortfolioSnapshot
from financial_portfolio_automation.exceptions import (
    APIError, AuthenticationError, ValidationError
)


# Skip integration tests if credentials are not available
pytestmark = pytest.mark.skipif(
    not (os.getenv('ALPACA_API_KEY') and os.getenv('ALPACA_SECRET_KEY')),
    reason="Alpaca API credentials not available"
)


@pytest.fixture
def integration_config():
    """Create integration test configuration using environment variables."""
    return AlpacaConfig(
        api_key=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY'),
        base_url="https://paper-api.alpaca.markets",
        data_feed=DataFeed.IEX,
        environment=Environment.PAPER
    )


@pytest.fixture
def authenticated_client(integration_config):
    """Create and authenticate an AlpacaClient for integration testing."""
    client = AlpacaClient(integration_config)
    client.authenticate()
    return client


class TestAlpacaClientIntegration:
    """Integration tests for AlpacaClient with real Alpaca API."""
    
    def test_authentication_success(self, integration_config):
        """Test successful authentication with real API."""
        client = AlpacaClient(integration_config)
        
        result = client.authenticate()
        
        assert result is True
        assert client.is_authenticated()
    
    def test_authentication_invalid_credentials(self):
        """Test authentication failure with invalid credentials."""
        invalid_config = AlpacaConfig(
            api_key="invalid_key",
            secret_key="invalid_secret",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX,
            environment=Environment.PAPER
        )
        
        client = AlpacaClient(invalid_config)
        
        with pytest.raises(AuthenticationError):
            client.authenticate()
    
    def test_connection_test(self, authenticated_client):
        """Test connection test with real API."""
        result = authenticated_client.test_connection()
        
        assert result['connected'] is True
        assert 'account_id' in result
        assert 'account_status' in result
        assert 'buying_power' in result
        assert 'portfolio_value' in result
        assert 'market_open' in result
        assert 'response_time_ms' in result
        assert result['environment'] == "paper"
        assert result['data_feed'] == "iex"
        assert 'timestamp' in result
    
    def test_get_account_info_integration(self, authenticated_client):
        """Test account info retrieval with real API."""
        result = authenticated_client.get_account_info()
        
        # Verify required fields are present
        required_fields = [
            'account_id', 'account_number', 'status', 'currency',
            'buying_power', 'cash', 'portfolio_value', 'equity',
            'multiplier', 'pattern_day_trader', 'trading_blocked',
            'timestamp'
        ]
        
        for field in required_fields:
            assert field in result
        
        # Verify data types
        assert isinstance(result['buying_power'], float)
        assert isinstance(result['cash'], float)
        assert isinstance(result['portfolio_value'], float)
        assert isinstance(result['equity'], float)
        assert isinstance(result['multiplier'], int)
        assert isinstance(result['pattern_day_trader'], bool)
        assert isinstance(result['trading_blocked'], bool)
        
        # Verify account is active for paper trading
        assert result['status'] == 'ACTIVE'
        assert result['currency'] == 'USD'
    
    def test_get_positions_integration(self, authenticated_client):
        """Test positions retrieval with real API."""
        result = authenticated_client.get_positions()
        
        # Result should be a list (may be empty for new accounts)
        assert isinstance(result, list)
        
        # If positions exist, verify structure
        for position in result:
            required_fields = [
                'symbol', 'asset_id', 'asset_class', 'quantity', 'side',
                'market_value', 'cost_basis', 'unrealized_pnl',
                'current_price', 'avg_entry_price', 'timestamp'
            ]
            
            for field in required_fields:
                assert field in position
            
            # Verify data types
            assert isinstance(position['symbol'], str)
            assert isinstance(position['quantity'], int)
            assert isinstance(position['market_value'], float)
            assert isinstance(position['cost_basis'], float)
            assert isinstance(position['unrealized_pnl'], float)
            assert isinstance(position['current_price'], float)
            assert isinstance(position['avg_entry_price'], float)
            
            # Verify business rules
            assert position['symbol']  # Symbol should not be empty
            assert position['asset_class'] in ['us_equity', 'crypto', 'forex']
            assert position['side'] in ['long', 'short']
    
    def test_get_positions_as_models_integration(self, authenticated_client):
        """Test positions as models with real API."""
        result = authenticated_client.get_positions_as_models()
        
        # Result should be a list of Position objects
        assert isinstance(result, list)
        
        # If positions exist, verify they are Position model objects
        for position in result:
            assert isinstance(position, Position)
            
            # Verify Position model validation passes
            position.validate()
            
            # Verify calculated properties work
            assert isinstance(position.average_cost, Decimal)
            assert isinstance(position.current_price, Decimal)
            assert isinstance(position.is_long(), bool)
            assert isinstance(position.is_short(), bool)
    
    def test_get_portfolio_snapshot_integration(self, authenticated_client):
        """Test portfolio snapshot creation with real API."""
        result = authenticated_client.get_portfolio_snapshot()
        
        # Verify it's a PortfolioSnapshot object
        assert isinstance(result, PortfolioSnapshot)
        
        # Verify PortfolioSnapshot validation passes
        result.validate()
        
        # Verify required fields
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.total_value, Decimal)
        assert isinstance(result.buying_power, Decimal)
        assert isinstance(result.day_pnl, Decimal)
        assert isinstance(result.total_pnl, Decimal)
        assert isinstance(result.positions, list)
        
        # Verify timestamp is recent (within last minute)
        time_diff = datetime.now(timezone.utc) - result.timestamp
        assert time_diff.total_seconds() < 60
        
        # Verify all positions are Position objects
        for position in result.positions:
            assert isinstance(position, Position)
        
        # Verify calculated properties work
        assert isinstance(result.position_count, int)
        assert isinstance(result.long_positions, list)
        assert isinstance(result.short_positions, list)
        
        # Verify position count matches
        assert result.position_count == len(result.positions)
        assert len(result.long_positions) + len(result.short_positions) == len(result.positions)
    
    def test_market_status_integration(self, authenticated_client):
        """Test market status check with real API."""
        result = authenticated_client.is_market_open()
        
        # Result should be a boolean
        assert isinstance(result, bool)
    
    def test_market_calendar_integration(self, authenticated_client):
        """Test market calendar retrieval with real API."""
        result = authenticated_client.get_market_calendar()
        
        # Result should be a list
        assert isinstance(result, list)
        
        # Should have at least some calendar entries
        assert len(result) > 0
        
        # Verify structure of calendar entries
        for entry in result:
            required_fields = ['date', 'open', 'close']
            
            for field in required_fields:
                assert field in entry
            
            # Verify date format
            assert isinstance(entry['date'], str)
            assert len(entry['date']) == 10  # YYYY-MM-DD format
            
            # Verify time format
            assert isinstance(entry['open'], str)
            assert isinstance(entry['close'], str)
    
    def test_rate_limiting_integration(self, authenticated_client):
        """Test rate limiting behavior with real API."""
        # Make multiple rapid requests to test rate limiting
        results = []
        
        for _ in range(5):
            result = authenticated_client.get_account_info()
            results.append(result)
        
        # All requests should succeed (rate limiting should handle this)
        assert len(results) == 5
        
        # All results should have the same account ID
        account_ids = [result['account_id'] for result in results]
        assert len(set(account_ids)) == 1  # All should be the same
    
    def test_error_handling_integration(self, authenticated_client):
        """Test error handling with real API."""
        # Test with invalid date range for calendar
        from datetime import date
        
        # This should work without errors
        result = authenticated_client.get_market_calendar(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 31)
        )
        
        assert isinstance(result, list)


class TestAlpacaClientDataValidation:
    """Test data validation in integration scenarios."""
    
    def test_position_model_validation_integration(self, authenticated_client):
        """Test that real position data passes model validation."""
        positions = authenticated_client.get_positions_as_models()
        
        # All positions should pass validation
        for position in positions:
            # This should not raise any exceptions
            position.validate()
            
            # Verify calculated properties are reasonable
            if position.quantity != 0:
                assert position.average_cost >= 0
                assert position.current_price >= 0
    
    def test_portfolio_snapshot_validation_integration(self, authenticated_client):
        """Test that real portfolio snapshot passes model validation."""
        snapshot = authenticated_client.get_portfolio_snapshot()
        
        # This should not raise any exceptions
        snapshot.validate()
        
        # Verify business rules
        assert snapshot.total_value >= 0
        assert snapshot.buying_power >= 0
        
        # Verify no duplicate symbols
        symbols = [pos.symbol for pos in snapshot.positions]
        assert len(symbols) == len(set(symbols))
    
    def test_data_consistency_integration(self, authenticated_client):
        """Test data consistency between different API calls."""
        # Get data from different methods
        account_info = authenticated_client.get_account_info()
        positions_dict = authenticated_client.get_positions()
        positions_models = authenticated_client.get_positions_as_models()
        snapshot = authenticated_client.get_portfolio_snapshot()
        
        # Portfolio values should be consistent
        assert account_info['portfolio_value'] == float(snapshot.total_value)
        assert account_info['buying_power'] == float(snapshot.buying_power)
        
        # Position counts should match
        assert len(positions_dict) == len(positions_models)
        assert len(positions_dict) == len(snapshot.positions)
        
        # Position symbols should match
        dict_symbols = sorted([pos['symbol'] for pos in positions_dict])
        model_symbols = sorted([pos.symbol for pos in positions_models])
        snapshot_symbols = sorted([pos.symbol for pos in snapshot.positions])
        
        assert dict_symbols == model_symbols
        assert dict_symbols == snapshot_symbols