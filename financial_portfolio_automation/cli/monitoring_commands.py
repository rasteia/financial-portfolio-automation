"""
Monitoring commands for CLI.

Provides commands for real-time portfolio monitoring, alert management,
risk monitoring, and performance tracking.
"""

import click
import time
from typing import Optional, List
from datetime import datetime, timedelta

from financial_portfolio_automation.cli.utils import (
    format_output, format_currency, format_percentage, 
    handle_error, confirm_action, validate_symbol
)


@click.group()
def monitoring():
    """Real-time monitoring and alerting commands."""
    pass


@monitoring.command()
@click.option('--duration', type=int, default=60, help='Monitoring duration in seconds')
@click.option('--refresh-interval', type=int, default=5, help='Refresh interval in seconds')
@click.option('--symbols', help='Comma-separated list of symbols to monitor')
@click.option('--alerts-only', is_flag=True, help='Show only when alerts are triggered')
@click.pass_context
def start(ctx, duration: int, refresh_interval: int, symbols: Optional[str], alerts_only: bool):
    """
    Start real-time portfolio monitoring.
    
    Continuously monitors portfolio positions, performance, and risk metrics
    with configurable refresh intervals and alert notifications.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        # Parse symbols if provided
        symbol_list = None
        if symbols:
            symbol_list = [validate_symbol(s.strip()) for s in symbols.split(',')]
        
        click.echo("🔍 Starting Real-Time Portfolio Monitoring")
        if symbol_list:
            click.echo(f"🎯 Monitoring: {', '.join(symbol_list)}")
        click.echo(f"⏱️  Duration: {duration}s, Refresh: {refresh_interval}s")
        click.echo("=" * 50)
        click.echo("Press Ctrl+C to stop monitoring")
        click.echo()
        
        start_time = time.time()
        iteration = 0
        
        try:
            while time.time() - start_time < duration:
                iteration += 1
                current_time = datetime.now().strftime('%H:%M:%S')
                
                # Get monitoring data
                monitoring_data = monitoring_tools.get_real_time_data(
                    symbols=symbol_list,
                    include_alerts=True
                )
                
                if not monitoring_data:
                    click.echo(f"[{current_time}] ❌ Failed to retrieve monitoring data")
                    time.sleep(refresh_interval)
                    continue
                
                # Check for alerts
                alerts = monitoring_data.get('alerts', [])
                has_alerts = len(alerts) > 0
                
                # Skip display if alerts_only mode and no alerts
                if alerts_only and not has_alerts:
                    time.sleep(refresh_interval)
                    continue
                
                # Clear screen for better display (optional)
                if not alerts_only and iteration > 1:
                    click.clear()
                
                click.echo(f"[{current_time}] 📊 Portfolio Monitor (Update #{iteration})")
                click.echo("=" * 60)
                
                # Portfolio summary
                portfolio_summary = monitoring_data.get('portfolio_summary', {})
                if portfolio_summary:
                    summary_data = {
                        'Total Value': format_currency(portfolio_summary.get('total_value', 0)),
                        'Day P&L': format_currency(portfolio_summary.get('day_pnl', 0)),
                        'Day P&L %': format_percentage(portfolio_summary.get('day_pnl_percent', 0)),
                        'Positions': portfolio_summary.get('position_count', 0),
                        'Buying Power': format_currency(portfolio_summary.get('buying_power', 0))
                    }
                    
                    if not alerts_only:
                        summary_output = format_output(summary_data, 'table')
                        click.echo(summary_output)
                
                # Position updates (if monitoring specific symbols)
                if symbol_list:
                    position_updates = monitoring_data.get('position_updates', [])
                    if position_updates:
                        click.echo("\n🎯 Position Updates:")
                        
                        formatted_positions = []
                        for pos in position_updates:
                            formatted_pos = {
                                'Symbol': pos.get('symbol', ''),
                                'Price': format_currency(pos.get('current_price', 0)),
                                'Change': format_currency(pos.get('price_change', 0)),
                                'Change %': format_percentage(pos.get('price_change_percent', 0)),
                                'Position P&L': format_currency(pos.get('position_pnl', 0)),
                                'Volume': f"{pos.get('volume', 0):,}"
                            }
                            formatted_positions.append(formatted_pos)
                        
                        positions_output = format_output(formatted_positions, 'table')
                        click.echo(positions_output)
                
                # Display alerts
                if has_alerts:
                    click.echo("\n🚨 ALERTS:")
                    click.echo("=" * 20)
                    
                    for alert in alerts:
                        alert_type = alert.get('type', 'INFO')
                        alert_icon = '🔴' if alert_type == 'CRITICAL' else '🟡' if alert_type == 'WARNING' else '🔵'
                        
                        click.echo(f"{alert_icon} {alert.get('message', '')}")
                        if alert.get('details'):
                            click.echo(f"   Details: {alert['details']}")
                        click.echo(f"   Time: {alert.get('timestamp', current_time)}")
                        click.echo()
                
                # Risk metrics
                risk_metrics = monitoring_data.get('risk_metrics', {})
                if risk_metrics and not alerts_only:
                    click.echo("\n⚠️  Risk Metrics:")
                    risk_data = {
                        'Portfolio Beta': f"{risk_metrics.get('beta', 0):.2f}",
                        'VaR (1-day)': format_currency(risk_metrics.get('var_1d', 0)),
                        'Volatility': format_percentage(risk_metrics.get('volatility', 0)),
                        'Concentration Risk': risk_metrics.get('concentration_risk', 'Low')
                    }
                    
                    risk_output = format_output(risk_data, 'table')
                    click.echo(risk_output)
                
                # Market indicators
                market_data = monitoring_data.get('market_indicators', {})
                if market_data and not alerts_only:
                    click.echo("\n📈 Market Indicators:")
                    market_info = {
                        'VIX': f"{market_data.get('vix', 0):.2f}",
                        'SPY': f"{market_data.get('spy_price', 0):.2f} ({market_data.get('spy_change_percent', 0):+.2f}%)",
                        'Market Status': market_data.get('market_status', 'Unknown'),
                        'Next Close': market_data.get('next_close', 'Unknown')
                    }
                    
                    market_output = format_output(market_info, 'table')
                    click.echo(market_output)
                
                if not alerts_only:
                    click.echo(f"\n⏱️  Next update in {refresh_interval}s... (Ctrl+C to stop)")
                
                time.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            click.echo("\n⚠️  Monitoring stopped by user")
        
        # Final summary
        total_time = time.time() - start_time
        click.echo(f"\n📊 Monitoring Summary:")
        click.echo(f"⏱️  Total Time: {total_time:.1f}s")
        click.echo(f"🔄 Updates: {iteration}")
        click.echo(f"📊 Average Interval: {total_time/max(iteration, 1):.1f}s")
        
    except Exception as e:
        handle_error(f"Failed to start monitoring: {e}", ctx.obj.get('verbose', False))


@monitoring.command()
@click.option('--active-only', is_flag=True, help='Show only active alerts')
@click.option('--severity', type=click.Choice(['INFO', 'WARNING', 'CRITICAL', 'ALL']),
              default='ALL', help='Filter by alert severity')
@click.option('--last-hours', type=int, default=24, help='Show alerts from last N hours')
@click.pass_context
def alerts(ctx, active_only: bool, severity: str, last_hours: int):
    """
    View and manage portfolio alerts.
    
    Shows current and historical alerts with filtering options
    by severity, status, and time period.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        click.echo("🚨 Portfolio Alerts")
        if active_only:
            click.echo("🟢 Active alerts only")
        if severity != 'ALL':
            click.echo(f"🎯 Severity: {severity}")
        click.echo(f"📅 Last {last_hours} hours")
        click.echo("=" * 50)
        
        # Get alerts
        alerts_data = monitoring_tools.get_alerts(
            active_only=active_only,
            severity=severity if severity != 'ALL' else None,
            hours_back=last_hours
        )
        
        if not alerts_data:
            click.echo("📭 No alerts found matching criteria")
            return
        
        # Group alerts by severity
        alerts_by_severity = {}
        for alert in alerts_data:
            alert_severity = alert.get('severity', 'INFO')
            if alert_severity not in alerts_by_severity:
                alerts_by_severity[alert_severity] = []
            alerts_by_severity[alert_severity].append(alert)
        
        # Display alerts by severity
        severity_order = ['CRITICAL', 'WARNING', 'INFO']
        severity_icons = {'CRITICAL': '🔴', 'WARNING': '🟡', 'INFO': '🔵'}
        
        for sev in severity_order:
            if sev in alerts_by_severity:
                alerts_list = alerts_by_severity[sev]
                icon = severity_icons.get(sev, '⚪')
                
                click.echo(f"\n{icon} {sev} Alerts ({len(alerts_list)})")
                click.echo("=" * 30)
                
                formatted_alerts = []
                for alert in alerts_list:
                    status_icon = '🟢' if alert.get('is_active') else '⚪'
                    
                    formatted_alert = {
                        'Status': f"{status_icon} {'Active' if alert.get('is_active') else 'Resolved'}",
                        'Message': alert.get('message', '')[:60] + '...' if len(alert.get('message', '')) > 60 else alert.get('message', ''),
                        'Symbol': alert.get('symbol', 'Portfolio'),
                        'Triggered': alert.get('triggered_at', ''),
                        'Value': alert.get('trigger_value', ''),
                        'Threshold': alert.get('threshold', '')
                    }
                    formatted_alerts.append(formatted_alert)
                
                alerts_output = format_output(formatted_alerts, ctx.obj['output_format'])
                click.echo(alerts_output)
        
        # Alert statistics
        total_alerts = len(alerts_data)
        active_alerts = sum(1 for alert in alerts_data if alert.get('is_active'))
        critical_alerts = len(alerts_by_severity.get('CRITICAL', []))
        
        click.echo(f"\n📊 Alert Summary:")
        click.echo(f"📋 Total Alerts: {total_alerts}")
        click.echo(f"🟢 Active: {active_alerts}")
        click.echo(f"🔴 Critical: {critical_alerts}")
        
        # Recent alert trend
        if total_alerts > 0:
            recent_alerts = [a for a in alerts_data if a.get('triggered_at')]
            if recent_alerts:
                recent_alerts.sort(key=lambda x: x.get('triggered_at', ''), reverse=True)
                latest_alert = recent_alerts[0]
                click.echo(f"🕐 Latest: {latest_alert.get('message', '')} ({latest_alert.get('triggered_at', '')})")
        
    except Exception as e:
        handle_error(f"Failed to retrieve alerts: {e}", ctx.obj.get('verbose', False))


@monitoring.command()
@click.option('--symbol', help='Symbol to monitor (leave empty for portfolio)')
@click.option('--metric', type=click.Choice(['price', 'pnl', 'volume', 'volatility']),
              required=True, help='Metric to monitor')
@click.option('--condition', type=click.Choice(['above', 'below', 'change_above', 'change_below']),
              required=True, help='Alert condition')
@click.option('--threshold', type=float, required=True, help='Alert threshold value')
@click.option('--email', help='Email address for notifications')
@click.option('--sms', help='SMS number for notifications')
@click.pass_context
def create_alert(ctx, symbol: Optional[str], metric: str, condition: str, 
                threshold: float, email: Optional[str], sms: Optional[str]):
    """
    Create a new portfolio or position alert.
    
    Sets up monitoring alerts for price movements, P&L changes,
    volume spikes, or volatility changes.
    
    Examples:
        monitoring create-alert --metric price --condition above --threshold 150 --symbol AAPL
        monitoring create-alert --metric pnl --condition below --threshold -1000
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        # Validate symbol if provided
        if symbol:
            symbol = validate_symbol(symbol)
        
        click.echo("🚨 Creating New Alert")
        click.echo("=" * 30)
        
        # Display alert configuration
        alert_config = {
            'Target': symbol if symbol else 'Portfolio',
            'Metric': metric.title(),
            'Condition': condition.replace('_', ' ').title(),
            'Threshold': f"{threshold:,.2f}",
            'Email': email if email else 'None',
            'SMS': sms if sms else 'None'
        }
        
        config_output = format_output(alert_config, ctx.obj['output_format'])
        click.echo(config_output)
        
        # Confirm alert creation
        if not confirm_action("Create this alert?", default=True):
            click.echo("❌ Alert creation cancelled")
            return
        
        # Create alert
        alert_result = monitoring_tools.create_alert(
            symbol=symbol,
            metric=metric,
            condition=condition,
            threshold=threshold,
            email=email,
            sms=sms
        )
        
        if not alert_result or not alert_result.get('success'):
            error_msg = alert_result.get('error', 'Unknown error') if alert_result else 'Alert creation failed'
            click.echo(f"❌ {error_msg}")
            return
        
        # Display success message
        click.echo("✅ Alert Created Successfully")
        click.echo("=" * 40)
        
        alert_info = {
            'Alert ID': alert_result.get('alert_id', ''),
            'Status': 'Active',
            'Created': alert_result.get('created_at', ''),
            'Next Check': alert_result.get('next_check', ''),
            'Notification Methods': len([n for n in [email, sms] if n])
        }
        
        info_output = format_output(alert_info, ctx.obj['output_format'])
        click.echo(info_output)
        
        # Show current value vs threshold
        current_value = alert_result.get('current_value')
        if current_value is not None:
            click.echo(f"\n📊 Current Status:")
            click.echo(f"Current Value: {current_value:,.2f}")
            click.echo(f"Threshold: {threshold:,.2f}")
            
            if condition == 'above':
                distance = threshold - current_value
                click.echo(f"Distance to Alert: {distance:+.2f}")
            elif condition == 'below':
                distance = current_value - threshold
                click.echo(f"Distance to Alert: {distance:+.2f}")
        
    except Exception as e:
        handle_error(f"Failed to create alert: {e}", ctx.obj.get('verbose', False))


@monitoring.command()
@click.option('--symbol', help='Filter by specific symbol')
@click.option('--time-window', type=click.Choice(['1h', '4h', '1d', '1w']),
              default='1d', help='Risk monitoring time window')
@click.pass_context
def risk(ctx, symbol: Optional[str], time_window: str):
    """
    Monitor real-time portfolio risk metrics.
    
    Displays current risk exposure, VaR, volatility, and concentration
    metrics with real-time updates.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        
        # Validate symbol if provided
        if symbol:
            symbol = validate_symbol(symbol)
            click.echo(f"⚠️  Risk Monitoring for {symbol}")
        else:
            click.echo("⚠️  Portfolio Risk Monitoring")
        
        click.echo(f"📅 Time Window: {time_window}")
        click.echo("=" * 50)
        
        # Get risk metrics
        risk_data = risk_tools.get_real_time_risk_metrics(
            symbol=symbol,
            time_window=time_window
        )
        
        if not risk_data:
            click.echo("❌ Unable to retrieve risk data")
            return
        
        # Core risk metrics
        core_metrics = risk_data.get('core_metrics', {})
        if core_metrics:
            click.echo("📊 Core Risk Metrics")
            click.echo("=" * 30)
            
            risk_metrics = {
                'Value at Risk (95%)': format_currency(core_metrics.get('var_95', 0)),
                'Expected Shortfall': format_currency(core_metrics.get('expected_shortfall', 0)),
                'Beta': f"{core_metrics.get('beta', 0):.2f}",
                'Volatility (Annualized)': format_percentage(core_metrics.get('volatility', 0)),
                'Sharpe Ratio': f"{core_metrics.get('sharpe_ratio', 0):.2f}",
                'Maximum Drawdown': format_percentage(core_metrics.get('max_drawdown', 0))
            }
            
            metrics_output = format_output(risk_metrics, ctx.obj['output_format'])
            click.echo(metrics_output)
        
        # Risk breakdown by position
        if not symbol:  # Portfolio-level analysis
            position_risk = risk_data.get('position_risk', [])
            if position_risk:
                click.echo("\n🎯 Risk by Position (Top 10)")
                click.echo("=" * 40)
                
                # Sort by risk contribution
                position_risk.sort(key=lambda x: x.get('risk_contribution', 0), reverse=True)
                
                formatted_positions = []
                for pos in position_risk[:10]:
                    formatted_pos = {
                        'Symbol': pos.get('symbol', ''),
                        'Weight %': format_percentage(pos.get('weight', 0) / 100),
                        'Beta': f"{pos.get('beta', 0):.2f}",
                        'Volatility': format_percentage(pos.get('volatility', 0)),
                        'VaR': format_currency(pos.get('var', 0)),
                        'Risk Contribution': format_percentage(pos.get('risk_contribution', 0))
                    }
                    formatted_positions.append(formatted_pos)
                
                positions_output = format_output(formatted_positions, ctx.obj['output_format'])
                click.echo(positions_output)
        
        # Concentration risk
        concentration = risk_data.get('concentration_risk', {})
        if concentration:
            click.echo("\n🎯 Concentration Risk")
            click.echo("=" * 30)
            
            concentration_metrics = {
                'Largest Position %': format_percentage(concentration.get('largest_position_pct', 0) / 100),
                'Top 5 Positions %': format_percentage(concentration.get('top5_positions_pct', 0) / 100),
                'Herfindahl Index': f"{concentration.get('herfindahl_index', 0):.4f}",
                'Effective Positions': f"{concentration.get('effective_positions', 0):.1f}",
                'Concentration Score': concentration.get('concentration_score', 'N/A')
            }
            
            conc_output = format_output(concentration_metrics, ctx.obj['output_format'])
            click.echo(conc_output)
        
        # Risk alerts and warnings
        risk_alerts = risk_data.get('risk_alerts', [])
        if risk_alerts:
            click.echo("\n🚨 Risk Alerts")
            click.echo("=" * 30)
            
            for alert in risk_alerts:
                severity = alert.get('severity', 'INFO')
                icon = '🔴' if severity == 'CRITICAL' else '🟡' if severity == 'WARNING' else '🔵'
                
                click.echo(f"{icon} {alert.get('message', '')}")
                if alert.get('recommendation'):
                    click.echo(f"   💡 Recommendation: {alert['recommendation']}")
                click.echo()
        
        # Market risk factors
        market_risk = risk_data.get('market_risk_factors', {})
        if market_risk:
            click.echo("\n📈 Market Risk Factors")
            click.echo("=" * 30)
            
            market_metrics = {
                'Market Beta': f"{market_risk.get('market_beta', 0):.2f}",
                'Sector Concentration': format_percentage(market_risk.get('sector_concentration', 0)),
                'Currency Exposure': market_risk.get('currency_exposure', 'USD'),
                'Interest Rate Sensitivity': f"{market_risk.get('interest_rate_sensitivity', 0):.2f}",
                'Correlation to Market': f"{market_risk.get('market_correlation', 0):.2f}"
            }
            
            market_output = format_output(market_metrics, ctx.obj['output_format'])
            click.echo(market_output)
        
        # Risk trend
        risk_trend = risk_data.get('risk_trend', {})
        if risk_trend:
            click.echo(f"\n📊 Risk Trend ({time_window})")
            click.echo("=" * 30)
            
            trend_direction = risk_trend.get('direction', 'stable')
            trend_icon = '📈' if trend_direction == 'increasing' else '📉' if trend_direction == 'decreasing' else '➡️'
            
            click.echo(f"{trend_icon} Risk Trend: {trend_direction.title()}")
            click.echo(f"📊 Change: {risk_trend.get('change_percent', 0):+.2f}%")
            
            if risk_trend.get('drivers'):
                click.echo("🔍 Key Drivers:")
                for driver in risk_trend['drivers']:
                    click.echo(f"  • {driver}")
        
    except Exception as e:
        handle_error(f"Failed to monitor risk: {e}", ctx.obj.get('verbose', False))


@monitoring.command()
@click.option('--period', type=click.Choice(['1h', '4h', '1d', '1w']),
              default='1d', help='Performance monitoring period')
@click.option('--benchmark', help='Benchmark symbol for comparison')
@click.pass_context
def performance(ctx, period: str, benchmark: Optional[str]):
    """
    Monitor real-time portfolio performance.
    
    Tracks portfolio returns, attribution, and performance metrics
    with continuous updates.
    """
    try:
        from financial_portfolio_automation.mcp.monitoring_tools import MonitoringTools
        
        monitoring_tools = MonitoringTools()
        
        # Validate benchmark if provided
        if benchmark:
            benchmark = validate_symbol(benchmark)
        
        click.echo(f"📈 Performance Monitoring ({period.upper()})")
        if benchmark:
            click.echo(f"📊 Benchmark: {benchmark}")
        click.echo("=" * 50)
        
        # Get performance data
        performance_data = monitoring_tools.get_real_time_performance(
            period=period,
            benchmark=benchmark
        )
        
        if not performance_data:
            click.echo("❌ Unable to retrieve performance data")
            return
        
        # Current performance metrics
        current_performance = performance_data.get('current_performance', {})
        if current_performance:
            click.echo("📊 Current Performance")
            click.echo("=" * 30)
            
            perf_metrics = {
                'Portfolio Value': format_currency(current_performance.get('portfolio_value', 0)),
                'Day P&L': format_currency(current_performance.get('day_pnl', 0)),
                'Day Return %': format_percentage(current_performance.get('day_return_pct', 0)),
                'Period Return %': format_percentage(current_performance.get('period_return_pct', 0)),
                'Volatility': format_percentage(current_performance.get('volatility', 0)),
                'Sharpe Ratio': f"{current_performance.get('sharpe_ratio', 0):.2f}"
            }
            
            perf_output = format_output(perf_metrics, ctx.obj['output_format'])
            click.echo(perf_output)
        
        # Benchmark comparison
        if benchmark and 'benchmark_comparison' in performance_data:
            click.echo(f"\n📊 vs {benchmark}")
            click.echo("=" * 30)
            
            comparison = performance_data['benchmark_comparison']
            comp_metrics = {
                'Portfolio Return': format_percentage(current_performance.get('period_return_pct', 0)),
                f'{benchmark} Return': format_percentage(comparison.get('benchmark_return_pct', 0)),
                'Excess Return': format_percentage(comparison.get('excess_return_pct', 0)),
                'Beta': f"{comparison.get('beta', 0):.2f}",
                'Correlation': f"{comparison.get('correlation', 0):.2f}",
                'Tracking Error': format_percentage(comparison.get('tracking_error', 0))
            }
            
            comp_output = format_output(comp_metrics, ctx.obj['output_format'])
            click.echo(comp_output)
        
        # Top performers and laggards
        attribution = performance_data.get('attribution', {})
        if attribution:
            # Top contributors
            top_contributors = attribution.get('top_contributors', [])[:5]
            if top_contributors:
                click.echo("\n🏆 Top Contributors")
                click.echo("=" * 30)
                
                formatted_contributors = []
                for contrib in top_contributors:
                    formatted_contrib = {
                        'Symbol': contrib.get('symbol', ''),
                        'Weight %': format_percentage(contrib.get('weight', 0) / 100),
                        'Return %': format_percentage(contrib.get('return_pct', 0)),
                        'Contribution': format_percentage(contrib.get('contribution_pct', 0))
                    }
                    formatted_contributors.append(formatted_contrib)
                
                contrib_output = format_output(formatted_contributors, ctx.obj['output_format'])
                click.echo(contrib_output)
            
            # Top detractors
            top_detractors = attribution.get('top_detractors', [])[:5]
            if top_detractors:
                click.echo("\n📉 Top Detractors")
                click.echo("=" * 30)
                
                formatted_detractors = []
                for detractor in top_detractors:
                    formatted_detractor = {
                        'Symbol': detractor.get('symbol', ''),
                        'Weight %': format_percentage(detractor.get('weight', 0) / 100),
                        'Return %': format_percentage(detractor.get('return_pct', 0)),
                        'Contribution': format_percentage(detractor.get('contribution_pct', 0))
                    }
                    formatted_detractors.append(formatted_detractor)
                
                detractor_output = format_output(formatted_detractors, ctx.obj['output_format'])
                click.echo(detractor_output)
        
        # Performance alerts
        perf_alerts = performance_data.get('performance_alerts', [])
        if perf_alerts:
            click.echo("\n🚨 Performance Alerts")
            click.echo("=" * 30)
            
            for alert in perf_alerts:
                severity = alert.get('severity', 'INFO')
                icon = '🔴' if severity == 'CRITICAL' else '🟡' if severity == 'WARNING' else '🔵'
                
                click.echo(f"{icon} {alert.get('message', '')}")
                if alert.get('impact'):
                    click.echo(f"   📊 Impact: {alert['impact']}")
                click.echo()
        
        # Intraday performance chart (text-based)
        intraday_data = performance_data.get('intraday_performance', [])
        if intraday_data and len(intraday_data) > 1:
            click.echo(f"\n📈 Intraday Performance ({period})")
            click.echo("=" * 40)
            
            # Simple text-based chart
            returns = [point.get('return_pct', 0) for point in intraday_data]
            min_return = min(returns)
            max_return = max(returns)
            
            if max_return != min_return:
                click.echo(f"Range: {min_return:+.2f}% to {max_return:+.2f}%")
                
                # Show last few data points
                recent_points = intraday_data[-10:]  # Last 10 points
                for point in recent_points:
                    time_str = point.get('time', '')
                    return_pct = point.get('return_pct', 0)
                    bar_length = int(20 * (return_pct - min_return) / (max_return - min_return)) if max_return != min_return else 10
                    bar = '█' * bar_length + '░' * (20 - bar_length)
                    click.echo(f"{time_str}: {bar} {return_pct:+.2f}%")
        
    except Exception as e:
        handle_error(f"Failed to monitor performance: {e}", ctx.obj.get('verbose', False))