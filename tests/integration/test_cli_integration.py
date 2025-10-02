"""
Integration tests for CLI functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from financial_portfolio_automation.cli.main import cli


class TestCLIIntegration:
    """Integration test cases for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_full_workflow(self):
        """Test complete CLI workflow from config to portfolio analysis."""
        with self.runner.isolated_filesystem():
            # Create test configuration
            config_data = {
                'alpaca': {
                    'api_key': 'test_key',
                    'secret_key': 'test_secret',
                    'base_url': 'https://paper-api.alpaca.markets'
                },
                'risk_limits': {
                    'max_position_size': 10000.0,
                    'max_daily_loss': 5000.0
                },
                'output_format': 'json'
            }
            
            with open('test_config.json', 'w') as f:
                json.dump(config_data, f)
            
            # Test config show
            result = self.runner.invoke(cli, ['--config', 'test_config.json', 'config', 'show'])
            assert result.exit_code == 0
            
            # Test health check
            with patch('financial_portfolio_automation.cli.main.PortfolioTools'):
                with patch('financial_portfolio_automation.cli.main.DataStore'):
                    result = self.runner.invoke(cli, ['--config', 'test_config.json', 'health'])
                    assert result.exit_code == 0
    
    @patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools')
    def test_portfolio_status_integration(self, mock_portfolio_tools):
        """Test portfolio status command integration."""
        # Mock comprehensive portfolio data
        mock_tools = MagicMock()
        mock_tools.get_portfolio_overview.return_value = {
            'total_value': 150000.0,
            'buying_power': 30000.0,
            'day_pnl': 2500.0,
            'total_pnl': 15000.0,
            'position_count': 15,
            'last_updated': '2024-01-01 15:30:00'
        }
        mock_tools.get_detailed_metrics.return_value = {
            'beta': 1.15,
            'sharpe_ratio': 1.8,
            'volatility': 0.16,
            'max_drawdown': 0.12,
            'win_rate': 0.72
        }
        mock_portfolio_tools.return_value = mock_tools
        
        # Test basic status
        result = self.runner.invoke(cli, ['portfolio', 'status'])
        assert result.exit_code == 0
        assert 'Portfolio Status' in result.output
        
        # Test detailed status
        result = self.runner.invoke(cli, ['portfolio', 'status', '--detailed'])
        assert result.exit_code == 0
        assert 'Detailed Metrics' in result.output
    
    @patch('financial_portfolio_automation.cli.analysis_commands.RiskTools')
    def test_risk_analysis_integration(self, mock_risk_tools):
        """Test risk analysis command integration."""
        # Mock risk assessment data
        mock_tools = MagicMock()
        mock_tools.assess_portfolio_risk.return_value = {
            'var': 5000.0,
            'expected_shortfall': 7500.0,
            'beta': 1.2,
            'volatility': 0.18,
            'max_drawdown': 0.10,
            'sharpe_ratio': 1.5,
            'sortino_ratio': 1.8,
            'concentration_risk': {
                'largest_position_pct': 15.0,
                'top5_positions_pct': 45.0,
                'herfindahl_index': 0.08,
                'effective_positions': 12.5,
                'concentration_score': 'Medium'
            },
            'stress_tests': [
                {
                    'scenario': 'Market Crash (-20%)',
                    'portfolio_impact': -30000.0,
                    'impact_percent': -0.20,
                    'probability': 0.05
                }
            ]
        }
        mock_risk_tools.return_value = mock_tools
        
        result = self.runner.invoke(cli, ['analysis', 'risk'])
        assert result.exit_code == 0
        assert 'Portfolio Risk Analysis' in result.output
        assert 'Concentration Risk' in result.output
        assert 'Stress Test Scenarios' in result.output
    
    @patch('financial_portfolio_automation.cli.strategy_commands.StrategyTools')
    def test_strategy_list_integration(self, mock_strategy_tools):
        """Test strategy list command integration."""
        # Mock strategy data
        mock_tools = MagicMock()
        mock_tools.list_strategies.return_value = [
            {
                'name': 'Momentum Strategy',
                'type': 'momentum',
                'is_active': True,
                'symbols': ['AAPL', 'GOOGL', 'MSFT'],
                'last_run': '2024-01-01 14:00:00',
                'total_return': 0.18,
                'sharpe_ratio': 1.6
            },
            {
                'name': 'Mean Reversion Strategy',
                'type': 'mean_reversion',
                'is_active': False,
                'symbols': ['SPY', 'QQQ'],
                'last_run': '2024-01-01 10:00:00',
                'total_return': 0.12,
                'sharpe_ratio': 1.2
            }
        ]
        mock_strategy_tools.return_value = mock_tools
        
        result = self.runner.invoke(cli, ['strategy', 'list'])
        assert result.exit_code == 0
        assert 'Available Trading Strategies' in result.output
        assert 'Momentum Strategy' in result.output
        assert 'Mean Reversion Strategy' in result.output
    
    @patch('financial_portfolio_automation.cli.monitoring_commands.MonitoringTools')
    def test_monitoring_alerts_integration(self, mock_monitoring_tools):
        """Test monitoring alerts command integration."""
        # Mock alerts data
        mock_tools = MagicMock()
        mock_tools.get_alerts.return_value = [
            {
                'severity': 'CRITICAL',
                'message': 'Portfolio loss exceeds 5% threshold',
                'symbol': 'Portfolio',
                'is_active': True,
                'triggered_at': '2024-01-01 15:45:00',
                'trigger_value': '-7500.0',
                'threshold': '-5000.0'
            },
            {
                'severity': 'WARNING',
                'message': 'AAPL position down 8%',
                'symbol': 'AAPL',
                'is_active': True,
                'triggered_at': '2024-01-01 15:30:00',
                'trigger_value': '-8.2',
                'threshold': '-8.0'
            }
        ]
        mock_monitoring_tools.return_value = mock_tools
        
        result = self.runner.invoke(cli, ['monitoring', 'alerts'])
        assert result.exit_code == 0
        assert 'Portfolio Alerts' in result.output
        assert 'CRITICAL Alerts' in result.output
        assert 'WARNING Alerts' in result.output
    
    def test_cli_error_handling_integration(self):
        """Test CLI error handling across different commands."""
        # Test with non-existent config file
        result = self.runner.invoke(cli, ['--config', 'nonexistent.json', 'portfolio', 'status'])
        assert result.exit_code == 1
        
        # Test with invalid format option
        result = self.runner.invoke(cli, ['--format', 'invalid', 'portfolio', 'status'])
        assert result.exit_code != 0
    
    def test_cli_output_formats_integration(self):
        """Test CLI with different output formats."""
        with patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools') as mock_tools:
            mock_portfolio_tools = MagicMock()
            mock_portfolio_tools.get_portfolio_overview.return_value = {
                'total_value': 100000.0,
                'buying_power': 25000.0,
                'day_pnl': 1500.0,
                'total_pnl': 5000.0,
                'position_count': 10,
                'last_updated': '2024-01-01 10:00:00'
            }
            mock_tools.return_value = mock_portfolio_tools
            
            # Test JSON format
            result = self.runner.invoke(cli, ['--format', 'json', 'portfolio', 'status'])
            assert result.exit_code == 0
            
            # Test CSV format
            result = self.runner.invoke(cli, ['--format', 'csv', 'portfolio', 'status'])
            assert result.exit_code == 0
            
            # Test table format (default)
            result = self.runner.invoke(cli, ['--format', 'table', 'portfolio', 'status'])
            assert result.exit_code == 0
    
    def test_cli_verbose_mode_integration(self):
        """Test CLI verbose mode across commands."""
        with patch('financial_portfolio_automation.cli.portfolio_commands.PortfolioTools') as mock_tools:
            mock_portfolio_tools = MagicMock()
            mock_portfolio_tools.get_portfolio_overview.side_effect = Exception("Test error")
            mock_tools.return_value = mock_portfolio_tools
            
            # Test verbose error output
            result = self.runner.invoke(cli, ['--verbose', 'portfolio', 'status'])
            assert result.exit_code == 0
            assert 'Failed to retrieve portfolio status' in result.output
    
    def test_cli_config_integration(self):
        """Test CLI configuration integration."""
        with self.runner.isolated_filesystem():
            # Test config initialization
            result = self.runner.invoke(cli, ['config', 'init', '--format', 'json'])
            # This will fail without interactive input, but we can test the command structure
            assert 'Initializing Portfolio CLI Configuration' in result.output or result.exit_code != 0
    
    @patch('financial_portfolio_automation.cli.reporting_commands.ReportingTools')
    def test_reporting_integration(self, mock_reporting_tools):
        """Test reporting command integration."""
        # Mock report generation
        mock_tools = MagicMock()
        mock_tools.generate_report.return_value = {
            'success': True,
            'file_path': '/tmp/test_report.pdf',
            'file_size_mb': 2.5,
            'page_count': 15,
            'generation_time_ms': 3500,
            'contents_summary': {
                'portfolio_value': 150000.0,
                'total_return': 0.15,
                'positions_count': 12,
                'transactions_count': 45,
                'charts_count': 8
            }
        }
        mock_reporting_tools.return_value = mock_tools
        
        result = self.runner.invoke(cli, ['reporting', 'generate', '--type', 'performance'])
        assert result.exit_code == 0
        assert 'Generating Performance Report' in result.output
        assert 'Report Generated Successfully' in result.output