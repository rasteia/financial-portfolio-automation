"""
Main CLI application entry point.

Provides the primary command-line interface for the Financial Portfolio Automation System
using Click framework for command structure and user interaction.
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.cli.portfolio_commands import portfolio
from financial_portfolio_automation.cli.analysis_commands import analysis
from financial_portfolio_automation.cli.strategy_commands import strategy
from financial_portfolio_automation.cli.reporting_commands import reporting
from financial_portfolio_automation.cli.monitoring_commands import monitoring
from financial_portfolio_automation.cli.config_commands import config
from financial_portfolio_automation.cli.utils import setup_logging, load_config, handle_error


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose output')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'table', 'csv']), 
              default='table', help='Output format')
@click.option('--profile', type=str, 
              help='Configuration profile to use')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool, output_format: str, profile: Optional[str]):
    """
    Financial Portfolio Automation System CLI.
    
    A comprehensive command-line interface for managing portfolios, executing strategies,
    analyzing performance, and generating reports.
    
    Examples:
        portfolio-cli portfolio status
        portfolio-cli analyze risk --symbol AAPL
        portfolio-cli strategy backtest --strategy momentum
        portfolio-cli report generate --type performance
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(verbose)
    
    # Load configuration
    try:
        ctx.obj['config'] = load_config(config, profile)
        ctx.obj['verbose'] = verbose
        ctx.obj['output_format'] = output_format
        ctx.obj['profile'] = profile
    except Exception as e:
        handle_error(f"Failed to load configuration: {e}", verbose)
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx):
    """Display version information."""
    from financial_portfolio_automation.cli import __version__
    click.echo(f"Financial Portfolio Automation CLI v{__version__}")


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health and connectivity."""
    try:
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        
        # Initialize portfolio tools to test connectivity
        portfolio_tools = PortfolioTools()
        
        # Test basic connectivity
        click.echo("🔍 Checking system health...")
        
        # Test configuration
        config = ctx.obj.get('config')
        if config:
            click.echo("✅ Configuration loaded successfully")
        else:
            click.echo("❌ Configuration not found")
            return
        
        # Test API connectivity (if configured)
        if hasattr(config, 'alpaca') and config.alpaca:
            click.echo("✅ Alpaca API configuration found")
        else:
            click.echo("⚠️  Alpaca API not configured")
        
        # Test database connectivity
        try:
            from financial_portfolio_automation.data.store import DataStore
            data_store = DataStore()
            click.echo("✅ Database connectivity verified")
        except Exception as e:
            click.echo(f"❌ Database connection failed: {e}")
        
        click.echo("🎉 System health check completed")
        
    except Exception as e:
        handle_error(f"Health check failed: {e}", ctx.obj.get('verbose', False))


# Add command groups
cli.add_command(portfolio)
cli.add_command(analysis)
cli.add_command(strategy)
cli.add_command(reporting)
cli.add_command(monitoring)
cli.add_command(config)


def main():
    """Entry point for the CLI application."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()