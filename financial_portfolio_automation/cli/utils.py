"""
Utility functions for CLI operations.

Provides common functionality for configuration management, logging setup,
error handling, and output formatting.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
import click
from tabulate import tabulate
import yaml
from decimal import Decimal


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration for CLI operations.
    
    Args:
        verbose: Enable verbose logging output
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    if not verbose:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)


def load_config(config_path: Optional[str] = None, profile: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file or environment.
    
    Args:
        config_path: Path to configuration file
        profile: Configuration profile to use
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If configuration file not found
        ValueError: If configuration is invalid
    """
    # Default configuration paths
    default_paths = [
        Path.home() / '.portfolio-cli' / 'config.yaml',
        Path.home() / '.portfolio-cli' / 'config.json',
        Path.cwd() / 'config.yaml',
        Path.cwd() / 'config.json',
    ]
    
    config_file = None
    
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    else:
        # Find first existing default config file
        for path in default_paths:
            if path.exists():
                config_file = path
                break
    
    if not config_file:
        # Return minimal default configuration
        return {
            'output_format': 'table',
            'verbose': False,
            'alpaca': {
                'base_url': 'https://paper-api.alpaca.markets',
                'data_feed': 'iex'
            }
        }
    
    # Load configuration file
    try:
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        
        # Select profile if specified
        if profile and 'profiles' in config:
            if profile not in config['profiles']:
                raise ValueError(f"Profile '{profile}' not found in configuration")
            
            # Merge base config with profile config
            base_config = {k: v for k, v in config.items() if k != 'profiles'}
            profile_config = config['profiles'][profile]
            config = {**base_config, **profile_config}
        
        return config
        
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid configuration file format: {e}")


def handle_error(message: str, verbose: bool = False) -> None:
    """
    Handle and display error messages consistently.
    
    Args:
        message: Error message to display
        verbose: Show detailed error information
    """
    if verbose:
        click.echo(f"❌ ERROR: {message}", err=True)
        import traceback
        traceback.print_exc()
    else:
        click.echo(f"❌ {message}", err=True)


def format_output(data: Any, format_type: str = 'table', headers: Optional[List[str]] = None) -> str:
    """
    Format data for output in specified format.
    
    Args:
        data: Data to format
        format_type: Output format ('table', 'json', 'csv')
        headers: Column headers for table format
        
    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)
    
    elif format_type == 'csv':
        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # Convert list of dicts to CSV
                import csv
                import io
                
                output = io.StringIO()
                if headers:
                    fieldnames = headers
                else:
                    fieldnames = list(data[0].keys())
                
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            else:
                # Simple list to CSV
                return '\n'.join(str(item) for item in data)
        else:
            return str(data)
    
    else:  # table format
        if isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # Convert list of dicts to table
                if headers:
                    table_data = [[row.get(h, '') for h in headers] for row in data]
                else:
                    headers = list(data[0].keys())
                    table_data = [[row.get(h, '') for h in headers] for row in data]
                
                return tabulate(table_data, headers=headers, tablefmt='grid')
            else:
                # Simple list to table
                return tabulate([[item] for item in data], tablefmt='grid')
        elif isinstance(data, dict):
            # Convert dict to key-value table
            table_data = [[k, v] for k, v in data.items()]
            return tabulate(table_data, headers=['Key', 'Value'], tablefmt='grid')
        else:
            return str(data)


def format_currency(amount: float, currency: str = 'USD') -> str:
    """
    Format currency amounts for display.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == 'USD':
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_percentage(value: float, precision: int = 2) -> str:
    """
    Format percentage values for display.
    
    Args:
        value: Percentage value (as decimal)
        precision: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{precision}f}%"


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Prompt user for confirmation.
    
    Args:
        message: Confirmation message
        default: Default response if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = click.prompt(f"{message}{suffix}", default='y' if default else 'n', show_default=False)
    return response.lower() in ['y', 'yes', 'true', '1']


def progress_bar(iterable, label: str = "Processing"):
    """
    Create a progress bar for long-running operations.
    
    Args:
        iterable: Iterable to process
        label: Label for the progress bar
        
    Returns:
        Progress bar iterator
    """
    return click.progressbar(iterable, label=label)


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize stock symbol.
    
    Args:
        symbol: Stock symbol to validate
        
    Returns:
        Normalized symbol
        
    Raises:
        ValueError: If symbol is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")
    
    symbol = symbol.upper().strip()
    
    # Basic validation - alphanumeric characters and dots
    if not symbol.replace('.', '').isalnum():
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    if len(symbol) > 10:
        raise ValueError(f"Symbol too long: {symbol}")
    
    return symbol


def validate_date_range(start_date: str, end_date: str) -> tuple:
    """
    Validate and parse date range.
    
    Args:
        start_date: Start date string
        end_date: End date string
        
    Returns:
        Tuple of parsed datetime objects
        
    Raises:
        ValueError: If dates are invalid
    """
    from datetime import datetime
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")
    
    if start >= end:
        raise ValueError("Start date must be before end date")
    
    return start, end


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)