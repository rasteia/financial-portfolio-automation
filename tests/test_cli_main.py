"""
Tests for CLI main application.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from financial_portfolio_automation.cli.main import cli, version, health


class TestCLIMain:
    """Test cases for CLI main functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Financial Portfolio Automation System CLI' in result.output
        assert 'portfolio' in result.output
        assert 'analysis' in result.output
        assert 'strategy' in result.output
    
    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(version)
        assert result.exit_code == 0
        assert 'Financial Portfolio Automation CLI' in result.output
        assert 'v' in result.output
    
    @patch('financial_portfolio_automation.data.store.DataStore')
    @patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools')
    @patch('financial_portfolio_automation.cli.utils.load_config')
    def test_health_command_success(self, mock_load_config, mock_portfolio_tools, mock_data_store):
        """Test health command with successful checks."""
        # Mock successful health checks
        mock_portfolio_tools.return_value = MagicMock()
        mock_data_store.return_value = MagicMock()
        mock_load_config.return_value = MagicMock()
        
        result = self.runner.invoke(cli, ['health'])
        assert result.exit_code == 0
        assert 'Checking system health' in result.output
        assert 'System health check completed' in result.output
    
    @patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioTools')
    @patch('financial_portfolio_automation.cli.utils.load_config')
    def test_health_command_failure(self, mock_load_config, mock_portfolio_tools):
        """Test health command with failures."""
        # Mock failed health check
        mock_portfolio_tools.side_effect = Exception("Connection failed")
        mock_load_config.return_value = MagicMock()
        
        result = self.runner.invoke(cli, ['health'])
        assert result.exit_code == 0  # Health command doesn't exit with error
        assert 'Health check failed' in result.output
    
    def test_cli_with_config_option(self):
        """Test CLI with config file option."""
        with self.runner.isolated_filesystem():
            # Create a test config file
            with open('test_config.json', 'w') as f:
                f.write('{"test": "value"}')
            
            result = self.runner.invoke(cli, ['--config', 'test_config.json', '--help'])
            assert result.exit_code == 0
    
    def test_cli_with_verbose_option(self):
        """Test CLI with verbose option."""
        result = self.runner.invoke(cli, ['--verbose', '--help'])
        assert result.exit_code == 0
    
    def test_cli_with_format_option(self):
        """Test CLI with different output formats."""
        for format_type in ['json', 'table', 'csv']:
            result = self.runner.invoke(cli, ['--format', format_type, '--help'])
            assert result.exit_code == 0
    
    def test_cli_with_profile_option(self):
        """Test CLI with profile option."""
        result = self.runner.invoke(cli, ['--profile', 'test', '--help'])
        assert result.exit_code == 0
    
    def test_cli_keyboard_interrupt(self):
        """Test CLI handling of keyboard interrupt."""
        with patch('financial_portfolio_automation.cli.main.cli') as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()
            
            from financial_portfolio_automation.cli.main import main
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    def test_cli_unexpected_error(self):
        """Test CLI handling of unexpected errors."""
        with patch('financial_portfolio_automation.cli.main.cli') as mock_cli:
            mock_cli.side_effect = Exception("Unexpected error")
            
            from financial_portfolio_automation.cli.main import main
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1