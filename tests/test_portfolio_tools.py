"""
Unit tests for Portfolio Tools.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
from financial_portfolio_automation.exceptions import PortfolioAutomationError


class TestPortfolioTools:
    """Test cases for Portfolio Tools."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'alpaca_config': {
                'api_key': 'test_key',
                'secret_key': 'test_secret',
                'base_url': 'https://paper-api.alpaca.markets'
            },
            'cache_config': {
                'ttl': 300
            }
        }
    
    @pytest.fixture
    def portfolio_tools(self, mock_config):
        """Create portfolio tools instance for testing."""
        with patch('financial_portfolio_automation.mcp.portfolio_tools.AnalyticsService'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioAnalyzer'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.RiskManager'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.AlpacaClient'):
            return PortfolioTools(mock_config)
    
    @pytest.mark.asyncio
    async def test_get_portfolio_summary_success(self, portfolio_tools):
        """Test successful portfolio summary retrieval."""
        # Mock account info
        mock_account = {
            'portfolio_value': '150000.00',
            'buying_power': '50000.00',
            'unrealized_pl': '5000.00',
            'status': 'ACTIVE',
            'cash': '25000.00',
            'equity': '125000.00'
        }
        
        # Mock positions
        mock_positions = [
            {
                'symbol': 'AAPL',
                'qty': '100',
                'market_value': '15000.00',
                'cost_basis': '14000.00',
                'unrealized_pl': '1000.00',
                'unrealized_plpc': '0.0714',
                'side': 'long'
            },
            {
                'symbol': 'GOOGL',
                'qty': '50',
                'market_value': '10000.00',
                'cost_basis': '9500.00',
                'unrealized_pl': '500.00',
                'unrealized_plpc': '0.0526',
                'side': 'long'
            }
        ]
        
        # Mock performance data
        mock_performance = {
            'total_return': 8.5,
            'sharpe_ratio': 1.2,
            'volatility': 15.3
        }
        
        # Set up mocks
        portfolio_tools.alpaca_client.get_account_info = AsyncMock(return_value=mock_account)
        portfolio_tools.alpaca_client.get_positions = AsyncMock(return_value=mock_positions)
        portfolio_tools.analytics_service.get_portfolio_metrics = AsyncMock(return_value=mock_performance)
        
        # Execute test
        result = await portfolio_tools.get_portfolio_summary(
            include_positions=True,
            include_performance=True
        )
        
        # Verify results
        assert result['portfolio_value'] == 150000.0
        assert result['buying_power'] == 50000.0
        assert result['day_pnl'] == 5000.0
        assert result['position_count'] == 2
        assert result['account_status'] == 'ACTIVE'
        
        # Check positions
        assert len(result['positions']) == 2
        assert result['positions'][0]['symbol'] == 'AAPL'
        assert result['positions'][0]['quantity'] == 100.0
        assert result['positions'][0]['market_value'] == 15000.0
        
        # Check performance data
        assert result['performance'] == mock_performance
    
    @pytest.mark.asyncio
    async def test_get_portfolio_summary_minimal(self, portfolio_tools):
        """Test portfolio summary with minimal data."""
        mock_account = {
            'portfolio_value': '100000.00',
            'buying_power': '30000.00',
            'unrealized_pl': '0.00',
            'status': 'ACTIVE'
        }
        
        portfolio_tools.alpaca_client.get_account_info = AsyncMock(return_value=mock_account)
        portfolio_tools.alpaca_client.get_positions = AsyncMock(return_value=[])
        
        result = await portfolio_tools.get_portfolio_summary(
            include_positions=False,
            include_performance=False
        )
        
        assert result['portfolio_value'] == 100000.0
        assert result['position_count'] == 0
        assert 'positions' not in result
        assert 'performance' not in result
    
    @pytest.mark.asyncio
    async def test_get_portfolio_performance_success(self, portfolio_tools):
        """Test successful portfolio performance calculation."""
        mock_performance_data = {
            'total_return': 12.5,
            'annualized_return': 15.2,
            'volatility': 18.3,
            'sharpe_ratio': 1.45,
            'max_drawdown': 8.2,
            'calmar_ratio': 1.85,
            'sortino_ratio': 1.62,
            'beta': 1.15,
            'alpha': 2.3,
            'information_ratio': 0.85,
            'tracking_error': 4.2
        }
        
        mock_benchmark_data = {
            'total_return': 10.0,
            'annualized_return': 12.0,
            'volatility': 16.0,
            'sharpe_ratio': 1.2,
            'max_drawdown': 12.0
        }
        
        portfolio_tools.portfolio_analyzer.calculate_performance_metrics = AsyncMock(
            return_value=mock_performance_data
        )
        portfolio_tools.portfolio_analyzer.get_benchmark_performance = AsyncMock(
            return_value=mock_benchmark_data
        )
        
        result = await portfolio_tools.get_portfolio_performance(
            period="1y",
            benchmark="SPY"
        )
        
        assert result['period'] == "1y"
        assert result['benchmark'] == "SPY"
        assert result['portfolio_performance']['total_return'] == 12.5
        assert result['benchmark_performance']['total_return'] == 10.0
        assert result['relative_performance']['excess_return'] == 2.5
    
    @pytest.mark.asyncio
    async def test_analyze_portfolio_risk_success(self, portfolio_tools):
        """Test successful portfolio risk analysis."""
        mock_positions = [
            {'symbol': 'AAPL', 'market_value': '50000'},
            {'symbol': 'GOOGL', 'market_value': '30000'},
            {'symbol': 'MSFT', 'market_value': '20000'}
        ]
        
        mock_risk_metrics = {
            'var': 5000.0,
            'expected_shortfall': 7500.0,
            'volatility': 18.5,
            'beta': 1.2,
            'max_drawdown': 15.3,
            'downside_deviation': 12.8
        }
        
        mock_concentration = {
            'max_position_weight': 50.0,
            'top_5_weight': 100.0,
            'top_10_weight': 100.0,
            'herfindahl_index': 0.38,
            'effective_positions': 2.6,
            'sector_breakdown': {
                'Technology': 80.0,
                'Healthcare': 20.0
            }
        }
        
        mock_correlation = {
            'avg_correlation': 0.65,
            'max_correlation': 0.85,
            'clusters': [['AAPL', 'GOOGL'], ['MSFT']]
        }
        
        portfolio_tools.alpaca_client.get_positions = AsyncMock(return_value=mock_positions)
        portfolio_tools.risk_manager.calculate_portfolio_risk = AsyncMock(return_value=mock_risk_metrics)
        portfolio_tools.risk_manager.analyze_concentration = AsyncMock(return_value=mock_concentration)
        portfolio_tools.risk_manager.analyze_correlations = AsyncMock(return_value=mock_correlation)
        
        result = await portfolio_tools.analyze_portfolio_risk(
            confidence_level=0.95,
            time_horizon=1
        )
        
        assert result['confidence_level'] == 0.95
        assert result['time_horizon_days'] == 1
        assert result['risk_metrics']['value_at_risk'] == 5000.0
        assert result['concentration_risk']['largest_position_weight'] == 50.0
        assert result['correlation_risk']['average_correlation'] == 0.65
        assert len(result['risk_warnings']) > 0  # Should have warnings for high concentration
    
    @pytest.mark.asyncio
    async def test_get_asset_allocation_success(self, portfolio_tools):
        """Test successful asset allocation analysis."""
        mock_positions = [
            {'symbol': 'AAPL', 'market_value': '40000', 'qty': '100', 'side': 'long'},
            {'symbol': 'GOOGL', 'market_value': '30000', 'qty': '50', 'side': 'long'},
            {'symbol': 'SPY', 'market_value': '20000', 'qty': '200', 'side': 'long'},
            {'symbol': 'MSFT', 'market_value': '10000', 'qty': '25', 'side': 'long'}
        ]
        
        portfolio_tools.alpaca_client.get_positions = AsyncMock(return_value=mock_positions)
        
        result = await portfolio_tools.get_asset_allocation(breakdown_type="all")
        
        assert result['total_portfolio_value'] == 100000.0
        assert result['breakdown_type'] == "all"
        
        # Check sector allocation
        assert 'sector_allocation' in result
        assert 'Technology' in result['sector_allocation']
        
        # Check asset type allocation
        assert 'asset_type_allocation' in result
        assert 'Stocks' in result['asset_type_allocation']
        assert 'ETFs' in result['asset_type_allocation']
        
        # Check geographic allocation
        assert 'geographic_allocation' in result
        assert 'US' in result['geographic_allocation']
        
        # Check positions
        assert len(result['positions']) == 4
        assert result['positions'][0]['symbol'] == 'AAPL'
        assert result['positions'][0]['weight'] == 40.0  # 40% of portfolio
    
    @pytest.mark.asyncio
    async def test_portfolio_tools_error_handling(self, portfolio_tools):
        """Test error handling in portfolio tools."""
        # Mock alpaca client to raise exception
        portfolio_tools.alpaca_client.get_account_info = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with pytest.raises(PortfolioAutomationError) as exc_info:
            await portfolio_tools.get_portfolio_summary()
        
        assert "Failed to get portfolio summary" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)
    
    def test_calculate_start_date(self, portfolio_tools):
        """Test start date calculation."""
        end_date = datetime(2024, 1, 15)
        
        # Test different periods
        start_1d = portfolio_tools._calculate_start_date('1d', end_date)
        assert start_1d == end_date - timedelta(days=1)
        
        start_1w = portfolio_tools._calculate_start_date('1w', end_date)
        assert start_1w == end_date - timedelta(weeks=1)
        
        start_1m = portfolio_tools._calculate_start_date('1m', end_date)
        assert start_1m == end_date - timedelta(days=30)
        
        start_ytd = portfolio_tools._calculate_start_date('ytd', end_date)
        assert start_ytd == datetime(2024, 1, 1)
    
    def test_generate_risk_warnings(self, portfolio_tools):
        """Test risk warning generation."""
        # High concentration risk
        risk_metrics = {'volatility': 30, 'max_drawdown': 25}
        concentration_analysis = {'max_position_weight': 25}
        
        warnings = portfolio_tools._generate_risk_warnings(risk_metrics, concentration_analysis)
        
        assert len(warnings) == 2  # High volatility and high drawdown
        assert any("High portfolio volatility" in w for w in warnings)
        assert any("High maximum drawdown" in w for w in warnings)
        
        # Low risk scenario
        risk_metrics = {'volatility': 10, 'max_drawdown': 5}
        concentration_analysis = {'max_position_weight': 15}
        
        warnings = portfolio_tools._generate_risk_warnings(risk_metrics, concentration_analysis)
        assert len(warnings) == 0
    
    def test_health_check(self, portfolio_tools):
        """Test health check functionality."""
        health_status = portfolio_tools.health_check()
        
        assert health_status['status'] == 'healthy'
        assert 'services' in health_status
        assert 'last_check' in health_status
        
        services = health_status['services']
        assert 'analytics_service' in services
        assert 'portfolio_analyzer' in services
        assert 'risk_manager' in services
        assert 'alpaca_client' in services


if __name__ == '__main__':
    pytest.main([__file__])