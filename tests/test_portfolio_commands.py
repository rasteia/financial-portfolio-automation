"""
Tests for CLI portfolio commands.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from financial_portfolio_automation.cli.portfolio_commands import portfolio


class TestPortfolioCommands:
    """Test cases for portfolio CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_portfolio_help(self):
        """Test portfolio command help."""
        result = self.runner.invoke(portfolio, ['--help'])
        assert result.exit_code == 0
        assert 'Portfolio management commands' in result.output
        assert 'status' in result.output
        assert 'positions' in result.output
        assert 'performance' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_status_success(self, mock_portfolio_tools):
        """Test portfolio status command with successful data retrieval."""
        # Mock portfolio data
        mock_tools = MagicMock()
        mock_tools.get_portfolio_overview.return_value = {
            'total_value': 100000.0,
            'buying_power': 25000.0,
            'day_pnl': 1500.0,
            'total_pnl': 5000.0,
            'position_count': 10,
            'last_updated': '2024-01-01 10:00:00'
        }
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['status'])
        assert result.exit_code == 0
        assert 'Portfolio Status' in result.output
        assert '$100,000.00' in result.output
        assert '$25,000.00' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_status_detailed(self, mock_portfolio_tools):
        """Test portfolio status command with detailed flag."""
        # Mock portfolio data
        mock_tools = MagicMock()
        mock_tools.get_portfolio_overview.return_value = {
            'total_value': 100000.0,
            'buying_power': 25000.0,
            'day_pnl': 1500.0,
            'total_pnl': 5000.0,
            'position_count': 10,
            'last_updated': '2024-01-01 10:00:00'
        }
        mock_tools.get_detailed_metrics.return_value = {
            'beta': 1.2,
            'sharpe_ratio': 1.5,
            'volatility': 0.15,
            'max_drawdown': 0.08,
            'win_rate': 0.65
        }
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['status', '--detailed'])
        assert result.exit_code == 0
        assert 'Detailed Metrics' in result.output
        assert '1.20' in result.output  # Beta
        assert '1.50' in result.output  # Sharpe ratio
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_status_no_data(self, mock_portfolio_tools):
        """Test portfolio status command with no data."""
        mock_tools = MagicMock()
        mock_tools.get_portfolio_overview.return_value = None
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['status'])
        assert result.exit_code == 0
        assert 'Unable to retrieve portfolio data' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_positions_success(self, mock_portfolio_tools):
        """Test portfolio positions command with successful data retrieval."""
        # Mock positions data
        mock_tools = MagicMock()
        mock_tools.get_positions.return_value = [
            {
                'symbol': 'AAPL',
                'quantity': 100,
                'market_value': 15000.0,
                'cost_basis': 14000.0,
                'unrealized_pnl': 1000.0,
                'day_pnl': 150.0,
                'allocation_percent': 15.0
            },
            {
                'symbol': 'GOOGL',
                'quantity': 50,
                'market_value': 12000.0,
                'cost_basis': 11500.0,
                'unrealized_pnl': 500.0,
                'day_pnl': -75.0,
                'allocation_percent': 12.0
            }
        ]
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['positions'])
        assert result.exit_code == 0
        assert 'Portfolio Positions' in result.output
        assert 'AAPL' in result.output
        assert 'GOOGL' in result.output
        assert '$15,000.00' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_positions_filtered(self, mock_portfolio_tools):
        """Test portfolio positions command with symbol filter."""
        # Mock positions data
        mock_tools = MagicMock()
        mock_tools.get_positions.return_value = [
            {
                'symbol': 'AAPL',
                'quantity': 100,
                'market_value': 15000.0,
                'cost_basis': 14000.0,
                'unrealized_pnl': 1000.0,
                'day_pnl': 150.0,
                'allocation_percent': 15.0
            }
        ]
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['positions', '--symbol', 'AAPL'])
        assert result.exit_code == 0
        assert 'AAPL' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_positions_no_data(self, mock_portfolio_tools):
        """Test portfolio positions command with no data."""
        mock_tools = MagicMock()
        mock_tools.get_positions.return_value = []
        mock_portfolio_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['positions'])
        assert result.exit_code == 0
        assert 'No positions found' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.AnalysisTools')
    def test_portfolio_performance_success(self, mock_analysis_tools):
        """Test portfolio performance command with successful data retrieval."""
        # Mock performance data
        mock_tools = MagicMock()
        mock_tools.get_portfolio_performance.return_value = {
            'total_return': 0.15,
            'annualized_return': 0.12,
            'volatility': 0.18,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.08,
            'win_rate': 0.65,
            'best_day': 0.05,
            'worst_day': -0.03
        }
        mock_analysis_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['performance'])
        assert result.exit_code == 0
        assert 'Portfolio Performance' in result.output
        assert '15.00%' in result.output  # Total return
        assert '1.20' in result.output    # Sharpe ratio
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.AnalysisTools')
    def test_portfolio_performance_with_benchmark(self, mock_analysis_tools):
        """Test portfolio performance command with benchmark comparison."""
        # Mock performance data with benchmark
        mock_tools = MagicMock()
        mock_tools.get_portfolio_performance.return_value = {
            'total_return': 0.15,
            'annualized_return': 0.12,
            'volatility': 0.18,
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.08,
            'win_rate': 0.65,
            'best_day': 0.05,
            'worst_day': -0.03
        }
        mock_tools.compare_to_benchmark.return_value = {
            'benchmark_return': 0.10,
            'alpha': 0.05,
            'beta': 1.1,
            'correlation': 0.85,
            'tracking_error': 0.04
        }
        mock_analysis_tools.return_value = mock_tools
        
        result = self.runner.invoke(portfolio, ['performance', '--benchmark', 'SPY'])
        assert result.exit_code == 0
        assert 'Benchmark Comparison (SPY)' in result.output
        assert '5.00%' in result.output  # Alpha
    
    def test_portfolio_positions_invalid_symbol(self):
        """Test portfolio positions command with invalid symbol."""
        result = self.runner.invoke(portfolio, ['positions', '--symbol', 'INVALID@SYMBOL'])
        assert result.exit_code == 0
        assert 'Invalid symbol format' in result.output
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_command_error_handling(self, mock_portfolio_tools):
        """Test portfolio command error handling."""
        mock_portfolio_tools.side_effect = Exception("API Error")
        
        result = self.runner.invoke(portfolio, ['status'])
        assert result.exit_code == 0
        assert 'Failed to retrieve portfolio status' in result.output
    
    def test_portfolio_performance_invalid_period(self):
        """Test portfolio performance command with invalid period."""
        result = self.runner.invoke(portfolio, ['performance', '--period', 'invalid'])
        assert result.exit_code != 0  # Should fail due to invalid choice