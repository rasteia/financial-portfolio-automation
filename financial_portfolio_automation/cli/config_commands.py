"""
Configuration commands for CLI.

Provides commands for initializing, viewing, updating, and validating
system configuration including API keys, risk parameters, and preferences.
"""

import click
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from financial_portfolio_automation.cli.utils import (
    format_output, handle_error, confirm_action
)


@click.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.option('--profile', type=str, help='Configuration profile name')
@click.option('--interactive', is_flag=True, help='Interactive configuration setup')
@click.option('--format', 'config_format', 
              type=click.Choice(['yaml', 'json']), 
              default='yaml', help='Configuration file format')
@click.pass_context
def init(ctx, profile: Optional[str], interactive: bool, config_format: str):
    """
    Initialize system configuration.
    
    Creates a new configuration file with default settings and
    prompts for essential configuration values.
    """
    try:
        click.echo("🔧 Initializing Portfolio CLI Configuration")
        click.echo("=" * 50)
        
        # Determine config file path
        config_dir = Path.home() / '.portfolio-cli'
        config_dir.mkdir(exist_ok=True)
        
        if profile:
            config_file = config_dir / f'config-{profile}.{config_format}'
        else:
            config_file = config_dir / f'config.{config_format}'
        
        # Check if config already exists
        if config_file.exists():
            if not confirm_action(f"Configuration file {config_file} already exists. Overwrite?", default=False):
                click.echo("❌ Configuration initialization cancelled")
                return
        
        # Default configuration
        default_config = {
            'version': '1.0',
            'profile': profile or 'default',
            'output_format': 'table',
            'verbose': False,
            'alpaca': {
                'base_url': 'https://paper-api.alpaca.markets',
                'data_feed': 'iex',
                'api_key': '',
                'secret_key': ''
            },
            'risk_limits': {
                'max_position_size': 10000.0,
                'max_portfolio_concentration': 0.2,
                'max_daily_loss': 5000.0,
                'max_drawdown': 0.15,
                'stop_loss_percentage': 0.05
            },
            'notifications': {
                'email': {
                    'enabled': False,
                    'smtp_server': '',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_address': '',
                    'to_addresses': []
                },
                'sms': {
                    'enabled': False,
                    'provider': 'twilio',
                    'account_sid': '',
                    'auth_token': '',
                    'from_number': '',
                    'to_numbers': []
                }
            },
            'monitoring': {
                'refresh_interval': 5,
                'alert_thresholds': {
                    'portfolio_loss_percent': 0.05,
                    'position_loss_percent': 0.1,
                    'volatility_spike': 2.0
                }
            },
            'reporting': {
                'default_format': 'pdf',
                'output_directory': str(Path.home() / 'portfolio_reports'),
                'include_charts': True,
                'chart_style': 'professional'
            }
        }
        
        # Interactive configuration
        if interactive:
            click.echo("\n📝 Interactive Configuration Setup")
            click.echo("=" * 40)
            
            # Alpaca API configuration
            click.echo("\n🔑 Alpaca Markets API Configuration:")
            use_live = click.confirm("Use live trading environment? (default: paper trading)", default=False)
            
            if use_live:
                default_config['alpaca']['base_url'] = 'https://api.alpaca.markets'
                click.echo("⚠️  WARNING: Live trading environment selected!")
            
            api_key = click.prompt("Alpaca API Key", default='', show_default=False)
            if api_key:
                default_config['alpaca']['api_key'] = api_key
            
            secret_key = click.prompt("Alpaca Secret Key", default='', show_default=False, hide_input=True)
            if secret_key:
                default_config['alpaca']['secret_key'] = secret_key
            
            data_feed = click.prompt("Data feed", 
                                   type=click.Choice(['iex', 'sip']), 
                                   default='iex')
            default_config['alpaca']['data_feed'] = data_feed
            
            # Risk limits
            click.echo("\n⚠️  Risk Management Configuration:")
            max_position = click.prompt("Maximum position size ($)", 
                                      type=float, 
                                      default=10000.0)
            default_config['risk_limits']['max_position_size'] = max_position
            
            max_concentration = click.prompt("Maximum portfolio concentration (0.0-1.0)", 
                                           type=float, 
                                           default=0.2)
            default_config['risk_limits']['max_portfolio_concentration'] = max_concentration
            
            max_daily_loss = click.prompt("Maximum daily loss ($)", 
                                        type=float, 
                                        default=5000.0)
            default_config['risk_limits']['max_daily_loss'] = max_daily_loss
            
            # Notification preferences
            click.echo("\n📧 Notification Configuration:")
            enable_email = click.confirm("Enable email notifications?", default=False)
            
            if enable_email:
                default_config['notifications']['email']['enabled'] = True
                email_address = click.prompt("Email address for notifications")
                default_config['notifications']['email']['to_addresses'] = [email_address]
                
                smtp_server = click.prompt("SMTP server", default='smtp.gmail.com')
                default_config['notifications']['email']['smtp_server'] = smtp_server
                
                smtp_username = click.prompt("SMTP username")
                default_config['notifications']['email']['username'] = smtp_username
                default_config['notifications']['email']['from_address'] = smtp_username
                
                smtp_password = click.prompt("SMTP password", hide_input=True)
                default_config['notifications']['email']['password'] = smtp_password
            
            # Output preferences
            click.echo("\n📊 Output Preferences:")
            output_format = click.prompt("Default output format", 
                                       type=click.Choice(['table', 'json', 'csv']), 
                                       default='table')
            default_config['output_format'] = output_format
            
            verbose = click.confirm("Enable verbose output by default?", default=False)
            default_config['verbose'] = verbose
        
        # Save configuration
        try:
            with open(config_file, 'w') as f:
                if config_format == 'yaml':
                    yaml.dump(default_config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(default_config, f, indent=2)
            
            click.echo(f"\n✅ Configuration saved to: {config_file}")
            
            # Display configuration summary
            click.echo("\n📋 Configuration Summary:")
            summary = {
                'Profile': default_config.get('profile', 'default'),
                'Format': config_format.upper(),
                'Alpaca Environment': 'Live' if 'api.alpaca.markets' in default_config['alpaca']['base_url'] else 'Paper',
                'API Key Configured': 'Yes' if default_config['alpaca']['api_key'] else 'No',
                'Email Notifications': 'Enabled' if default_config['notifications']['email']['enabled'] else 'Disabled',
                'Max Position Size': f"${default_config['risk_limits']['max_position_size']:,.2f}",
                'Output Format': default_config['output_format'].title()
            }
            
            summary_output = format_output(summary, ctx.obj.get('output_format', 'table'))
            click.echo(summary_output)
            
            # Security reminder
            if default_config['alpaca']['api_key'] or default_config['alpaca']['secret_key']:
                click.echo("\n🔒 Security Reminder:")
                click.echo("• Keep your API keys secure and never share them")
                click.echo("• Consider using environment variables for sensitive data")
                click.echo("• Regularly rotate your API keys")
                click.echo(f"• Configuration file permissions: {oct(config_file.stat().st_mode)[-3:]}")
            
            # Next steps
            click.echo("\n🚀 Next Steps:")
            click.echo("• Run 'portfolio-cli config validate' to test your configuration")
            click.echo("• Use 'portfolio-cli health' to check system connectivity")
            click.echo("• Try 'portfolio-cli portfolio status' to view your portfolio")
            
        except Exception as e:
            handle_error(f"Failed to save configuration: {e}", ctx.obj.get('verbose', False))
        
    except Exception as e:
        handle_error(f"Failed to initialize configuration: {e}", ctx.obj.get('verbose', False))


@config.command()
@click.option('--profile', type=str, help='Configuration profile to show')
@click.option('--section', type=str, help='Show specific configuration section')
@click.option('--hide-secrets', is_flag=True, default=True, help='Hide sensitive values')
@click.pass_context
def show(ctx, profile: Optional[str], section: Optional[str], hide_secrets: bool):
    """
    Display current configuration settings.
    
    Shows the active configuration with options to filter by section
    and hide sensitive information.
    """
    try:
        click.echo("📋 Current Configuration")
        if profile:
            click.echo(f"🏷️  Profile: {profile}")
        if section:
            click.echo(f"📂 Section: {section}")
        click.echo("=" * 50)
        
        # Load configuration
        config_data = ctx.obj.get('config', {})
        
        if not config_data:
            click.echo("❌ No configuration loaded")
            click.echo("💡 Run 'portfolio-cli config init' to create a configuration")
            return
        
        # Filter by section if specified
        if section:
            if section in config_data:
                display_config = {section: config_data[section]}
            else:
                click.echo(f"❌ Section '{section}' not found in configuration")
                available_sections = list(config_data.keys())
                click.echo(f"Available sections: {', '.join(available_sections)}")
                return
        else:
            display_config = config_data.copy()
        
        # Hide sensitive information
        if hide_secrets:
            display_config = _hide_sensitive_values(display_config)
        
        # Display configuration
        if ctx.obj.get('output_format') == 'json':
            config_output = json.dumps(display_config, indent=2)
            click.echo(config_output)
        elif ctx.obj.get('output_format') == 'yaml':
            config_output = yaml.dump(display_config, default_flow_style=False, indent=2)
            click.echo(config_output)
        else:
            # Table format - flatten the configuration
            flattened_config = _flatten_config(display_config)
            config_output = format_output(flattened_config, 'table')
            click.echo(config_output)
        
        # Configuration statistics
        click.echo(f"\n📊 Configuration Statistics:")
        click.echo(f"📂 Sections: {len(config_data)}")
        click.echo(f"🔧 Total Settings: {_count_config_items(config_data)}")
        
        # Validation status
        validation_status = _quick_validate_config(config_data)
        status_icon = '✅' if validation_status['valid'] else '❌'
        click.echo(f"✓ Validation: {status_icon} {validation_status['message']}")
        
        if not validation_status['valid'] and validation_status.get('issues'):
            click.echo("⚠️  Issues found:")
            for issue in validation_status['issues']:
                click.echo(f"  • {issue}")
        
    except Exception as e:
        handle_error(f"Failed to show configuration: {e}", ctx.obj.get('verbose', False))


@config.command()
@click.argument('key', required=True)
@click.argument('value', required=True)
@click.option('--profile', type=str, help='Configuration profile to update')
@click.option('--type', 'value_type', 
              type=click.Choice(['string', 'int', 'float', 'bool', 'json']),
              default='string', help='Value type')
@click.pass_context
def set(ctx, key: str, value: str, profile: Optional[str], value_type: str):
    """
    Update a configuration setting.
    
    Sets a configuration value using dot notation for nested keys.
    
    Examples:
        config set alpaca.api_key "your_api_key"
        config set risk_limits.max_position_size 15000 --type float
        config set notifications.email.enabled true --type bool
    """
    try:
        click.echo(f"🔧 Updating Configuration: {key}")
        click.echo("=" * 50)
        
        # Load current configuration
        config_data = ctx.obj.get('config', {})
        
        if not config_data:
            click.echo("❌ No configuration found")
            click.echo("💡 Run 'portfolio-cli config init' to create a configuration")
            return
        
        # Parse value based on type
        try:
            if value_type == 'int':
                parsed_value = int(value)
            elif value_type == 'float':
                parsed_value = float(value)
            elif value_type == 'bool':
                parsed_value = value.lower() in ('true', '1', 'yes', 'on')
            elif value_type == 'json':
                parsed_value = json.loads(value)
            else:
                parsed_value = value
        except (ValueError, json.JSONDecodeError) as e:
            click.echo(f"❌ Invalid value for type {value_type}: {e}")
            return
        
        # Update configuration using dot notation
        keys = key.split('.')
        current = config_data
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Store old value for comparison
        old_value = current.get(keys[-1], '<not set>')
        
        # Set the new value
        current[keys[-1]] = parsed_value
        
        # Display the change
        change_info = {
            'Key': key,
            'Old Value': str(old_value),
            'New Value': str(parsed_value),
            'Type': value_type
        }
        
        change_output = format_output(change_info, ctx.obj['output_format'])
        click.echo(change_output)
        
        # Confirm the change
        if not confirm_action("Apply this configuration change?", default=True):
            click.echo("❌ Configuration change cancelled")
            return
        
        # Save configuration
        config_file = _find_config_file(profile)
        if not config_file:
            click.echo("❌ Configuration file not found")
            return
        
        try:
            with open(config_file, 'w') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)
            
            click.echo(f"✅ Configuration updated successfully")
            click.echo(f"📁 File: {config_file}")
            
            # Validate the updated configuration
            validation_result = _quick_validate_config(config_data)
            if not validation_result['valid']:
                click.echo("⚠️  Warning: Configuration validation failed after update")
                click.echo(f"Issue: {validation_result['message']}")
            
        except Exception as e:
            click.echo(f"❌ Failed to save configuration: {e}")
        
    except Exception as e:
        handle_error(f"Failed to update configuration: {e}", ctx.obj.get('verbose', False))


@config.command()
@click.option('--profile', type=str, help='Configuration profile to validate')
@click.option('--check-connectivity', is_flag=True, help='Test API connectivity')
@click.pass_context
def validate(ctx, profile: Optional[str], check_connectivity: bool):
    """
    Validate configuration settings and connectivity.
    
    Checks configuration completeness, validates API credentials,
    and tests connectivity to external services.
    """
    try:
        click.echo("🔍 Validating Configuration")
        if profile:
            click.echo(f"🏷️  Profile: {profile}")
        click.echo("=" * 50)
        
        # Load configuration
        config_data = ctx.obj.get('config', {})
        
        if not config_data:
            click.echo("❌ No configuration found")
            return
        
        validation_results = []
        
        # Basic configuration validation
        click.echo("📋 Basic Configuration Validation")
        click.echo("=" * 40)
        
        # Check required sections
        required_sections = ['alpaca', 'risk_limits', 'notifications', 'monitoring']
        for section in required_sections:
            if section in config_data:
                validation_results.append({
                    'Check': f'{section.title()} Section',
                    'Status': '✅ Present',
                    'Details': f"{len(config_data[section])} settings"
                })
            else:
                validation_results.append({
                    'Check': f'{section.title()} Section',
                    'Status': '❌ Missing',
                    'Details': 'Required section not found'
                })
        
        # Alpaca API validation
        alpaca_config = config_data.get('alpaca', {})
        api_key = alpaca_config.get('api_key', '')
        secret_key = alpaca_config.get('secret_key', '')
        
        if api_key and secret_key:
            validation_results.append({
                'Check': 'Alpaca API Keys',
                'Status': '✅ Configured',
                'Details': f"Key length: {len(api_key)}, Secret length: {len(secret_key)}"
            })
        else:
            validation_results.append({
                'Check': 'Alpaca API Keys',
                'Status': '⚠️  Missing',
                'Details': 'API keys not configured'
            })
        
        # Risk limits validation
        risk_limits = config_data.get('risk_limits', {})
        required_limits = ['max_position_size', 'max_portfolio_concentration', 'max_daily_loss']
        
        risk_valid = all(limit in risk_limits and isinstance(risk_limits[limit], (int, float)) 
                        for limit in required_limits)
        
        validation_results.append({
            'Check': 'Risk Limits',
            'Status': '✅ Valid' if risk_valid else '❌ Invalid',
            'Details': f"{len([l for l in required_limits if l in risk_limits])}/{len(required_limits)} limits set"
        })
        
        # Notification validation
        notifications = config_data.get('notifications', {})
        email_config = notifications.get('email', {})
        sms_config = notifications.get('sms', {})
        
        notification_methods = 0
        if email_config.get('enabled') and email_config.get('smtp_server'):
            notification_methods += 1
        if sms_config.get('enabled') and sms_config.get('account_sid'):
            notification_methods += 1
        
        validation_results.append({
            'Check': 'Notifications',
            'Status': '✅ Configured' if notification_methods > 0 else '⚠️  None',
            'Details': f"{notification_methods} method(s) configured"
        })
        
        # Display validation results
        validation_output = format_output(validation_results, ctx.obj['output_format'])
        click.echo(validation_output)
        
        # Connectivity tests
        if check_connectivity:
            click.echo("\n🌐 Connectivity Tests")
            click.echo("=" * 30)
            
            connectivity_results = []
            
            # Test Alpaca API connectivity
            if api_key and secret_key:
                try:
                    from financial_portfolio_automation.api.alpaca_client import AlpacaClient
                    
                    alpaca_client = AlpacaClient()
                    account_info = alpaca_client.get_account()
                    
                    if account_info:
                        connectivity_results.append({
                            'Service': 'Alpaca API',
                            'Status': '✅ Connected',
                            'Details': f"Account: {account_info.get('account_number', 'N/A')}"
                        })
                    else:
                        connectivity_results.append({
                            'Service': 'Alpaca API',
                            'Status': '❌ Failed',
                            'Details': 'Unable to retrieve account info'
                        })
                
                except Exception as e:
                    connectivity_results.append({
                        'Service': 'Alpaca API',
                        'Status': '❌ Error',
                        'Details': str(e)[:50] + '...' if len(str(e)) > 50 else str(e)
                    })
            else:
                connectivity_results.append({
                    'Service': 'Alpaca API',
                    'Status': '⚠️  Skipped',
                    'Details': 'API keys not configured'
                })
            
            # Test email connectivity
            if email_config.get('enabled') and email_config.get('smtp_server'):
                try:
                    import smtplib
                    from email.mime.text import MIMEText
                    
                    server = smtplib.SMTP(email_config['smtp_server'], email_config.get('smtp_port', 587))
                    server.starttls()
                    
                    if email_config.get('username') and email_config.get('password'):
                        server.login(email_config['username'], email_config['password'])
                    
                    server.quit()
                    
                    connectivity_results.append({
                        'Service': 'Email SMTP',
                        'Status': '✅ Connected',
                        'Details': f"Server: {email_config['smtp_server']}"
                    })
                
                except Exception as e:
                    connectivity_results.append({
                        'Service': 'Email SMTP',
                        'Status': '❌ Failed',
                        'Details': str(e)[:50] + '...' if len(str(e)) > 50 else str(e)
                    })
            else:
                connectivity_results.append({
                    'Service': 'Email SMTP',
                    'Status': '⚠️  Skipped',
                    'Details': 'Email not configured'
                })
            
            # Display connectivity results
            connectivity_output = format_output(connectivity_results, ctx.obj['output_format'])
            click.echo(connectivity_output)
        
        # Overall validation summary
        total_checks = len(validation_results)
        passed_checks = len([r for r in validation_results if '✅' in r['Status']])
        
        click.echo(f"\n📊 Validation Summary:")
        click.echo(f"✅ Passed: {passed_checks}/{total_checks}")
        click.echo(f"❌ Failed: {total_checks - passed_checks}/{total_checks}")
        
        if passed_checks == total_checks:
            click.echo("🎉 Configuration is valid and ready to use!")
        else:
            click.echo("⚠️  Some configuration issues found. Please review and fix.")
        
    except Exception as e:
        handle_error(f"Failed to validate configuration: {e}", ctx.obj.get('verbose', False))


def _hide_sensitive_values(config: Dict[str, Any]) -> Dict[str, Any]:
    """Hide sensitive configuration values."""
    sensitive_keys = ['api_key', 'secret_key', 'password', 'auth_token', 'account_sid']
    
    def hide_recursive(obj):
        if isinstance(obj, dict):
            return {
                key: '***HIDDEN***' if any(sensitive in key.lower() for sensitive in sensitive_keys) 
                else hide_recursive(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [hide_recursive(item) for item in obj]
        else:
            return obj
    
    return hide_recursive(config)


def _flatten_config(config: Dict[str, Any], prefix: str = '') -> Dict[str, str]:
    """Flatten nested configuration for table display."""
    flattened = {}
    
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            flattened.update(_flatten_config(value, full_key))
        elif isinstance(value, list):
            flattened[full_key] = ', '.join(str(item) for item in value)
        else:
            flattened[full_key] = str(value)
    
    return [{'Setting': k, 'Value': v} for k, v in flattened.items()]


def _count_config_items(config: Dict[str, Any]) -> int:
    """Count total configuration items recursively."""
    count = 0
    for value in config.values():
        if isinstance(value, dict):
            count += _count_config_items(value)
        else:
            count += 1
    return count


def _quick_validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Perform quick configuration validation."""
    issues = []
    
    # Check for required sections
    required_sections = ['alpaca', 'risk_limits']
    for section in required_sections:
        if section not in config:
            issues.append(f"Missing required section: {section}")
    
    # Check Alpaca configuration
    alpaca_config = config.get('alpaca', {})
    if not alpaca_config.get('base_url'):
        issues.append("Alpaca base_url not configured")
    
    # Check risk limits
    risk_limits = config.get('risk_limits', {})
    required_limits = ['max_position_size', 'max_daily_loss']
    for limit in required_limits:
        if limit not in risk_limits:
            issues.append(f"Missing risk limit: {limit}")
    
    return {
        'valid': len(issues) == 0,
        'message': 'Configuration is valid' if len(issues) == 0 else f'{len(issues)} issues found',
        'issues': issues
    }


def _find_config_file(profile: Optional[str] = None) -> Optional[Path]:
    """Find the configuration file for the given profile."""
    config_dir = Path.home() / '.portfolio-cli'
    
    if profile:
        # Try profile-specific files
        for ext in ['yaml', 'yml', 'json']:
            config_file = config_dir / f'config-{profile}.{ext}'
            if config_file.exists():
                return config_file
    else:
        # Try default files
        for ext in ['yaml', 'yml', 'json']:
            config_file = config_dir / f'config.{ext}'
            if config_file.exists():
                return config_file
    
    return None