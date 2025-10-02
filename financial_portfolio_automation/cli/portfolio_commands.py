"""
Portfolio management commands for CLI.

Provides commands for viewing portfolio status, positions, performance,
allocation, and rebalancing operations.
"""

import click
from typing import Optional, List
from datetime import datetime, timedelta

from financial_portfolio_automation.cli.utils import (
    format_output, format_currency, format_percentage, 
    handle_error, confirm_action, validate_symbol
)


@click.group()
def portfolio():
    """Portfolio management commands."""
    pass


@portfolio.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed portfolio information')
@click.pass_context
def status(ctx, detailed: bool):
    """
    Display current portfolio status and overview.
    
    Shows portfolio value, buying power, day P&L, and position count.
    Use --detailed for comprehensive portfolio metrics.
    """
    try:
        from financial_portfolio_automation.data.store import DataStore
        
        # Get portfolio overview
        click.echo("📊 Portfolio Status")
        click.echo("=" * 50)
        
        # Get basic portfolio data from database
        data_store = DataStore("portfolio_automation.db")
        latest_snapshot = data_store.get_latest_portfolio_snapshot()
        
        if not latest_snapshot:
            click.echo("❌ No portfolio data found")
            return
        
        # Format basic information
        basic_info = {
            'Total Value': format_currency(latest_snapshot.total_value),
            'Buying Power': format_currency(latest_snapshot.buying_power),
            'Day P&L': format_currency(latest_snapshot.day_pnl),
            'Total P&L': format_currency(latest_snapshot.total_pnl),
            'Position Count': len(latest_snapshot.positions),
            'Last Updated': latest_snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        output = format_output(basic_info, ctx.obj['output_format'])
        click.echo(output)
        
        if detailed:
            click.echo("\n📈 Detailed Metrics")
            click.echo("=" * 50)
            
            # Calculate some basic metrics from positions
            positions = latest_snapshot.positions
            if positions:
                total_cost = sum(pos.cost_basis for pos in positions)
                total_return_pct = (latest_snapshot.total_pnl / total_cost * 100) if total_cost > 0 else 0
                
                metrics = {
                    'Total Return %': f"{total_return_pct:.2f}%",
                    'Average Position Size': format_currency(latest_snapshot.total_value / len(positions)),
                    'Largest Position': format_currency(max(pos.market_value for pos in positions)),
                    'Smallest Position': format_currency(min(pos.market_value for pos in positions)),
                    'Cash Available': format_currency(latest_snapshot.buying_power)
                }
                
                detailed_output = format_output(metrics, ctx.obj['output_format'])
                click.echo(detailed_output)
        
    except Exception as e:
        handle_error(f"Failed to retrieve portfolio status: {e}", ctx.obj.get('verbose', False))


@portfolio.command()
@click.option('--symbol', '-s', help='Filter by specific symbol')
@click.option('--min-value', type=float, help='Minimum position value filter')
@click.option('--sort-by', type=click.Choice(['symbol', 'value', 'pnl', 'allocation']), 
              default='value', help='Sort positions by field')
@click.pass_context
def positions(ctx, symbol: Optional[str], min_value: Optional[float], sort_by: str):
    """
    Display current portfolio positions.
    
    Shows detailed information about each position including quantity,
    market value, unrealized P&L, and allocation percentage.
    """
    try:
        from financial_portfolio_automation.data.store import DataStore
        
        click.echo("📋 Portfolio Positions")
        click.echo("=" * 50)
        
        # Get positions data directly from database
        data_store = DataStore("portfolio_automation.db")
        positions_data = data_store.get_current_positions()
        
        if not positions_data:
            click.echo("📭 No positions found")
            return
        
        # Calculate total portfolio value for allocation percentages
        total_portfolio_value = sum(pos.market_value for pos in positions_data)
        
        # Filter by symbol if specified
        if symbol:
            symbol = validate_symbol(symbol)
            positions_data = [pos for pos in positions_data if pos.symbol == symbol]
            
            if not positions_data:
                click.echo(f"📭 No position found for symbol: {symbol}")
                return
        
        # Filter by minimum value if specified
        if min_value:
            positions_data = [pos for pos in positions_data 
                            if pos.market_value >= min_value]
        
        # Sort positions
        reverse_sort = sort_by in ['value', 'pnl']
        if sort_by == 'symbol':
            positions_data.sort(key=lambda x: x.symbol)
        elif sort_by == 'value':
            positions_data.sort(key=lambda x: x.market_value, reverse=reverse_sort)
        elif sort_by == 'pnl':
            positions_data.sort(key=lambda x: x.unrealized_pnl, reverse=reverse_sort)
        elif sort_by == 'allocation':
            positions_data.sort(key=lambda x: x.market_value, reverse=reverse_sort)
        
        # Format positions for display
        formatted_positions = []
        for pos in positions_data:
            allocation_percent = (pos.market_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
            formatted_pos = {
                'Symbol': pos.symbol,
                'Quantity': f"{pos.quantity:,}",
                'Market Value': format_currency(pos.market_value),
                'Cost Basis': format_currency(pos.cost_basis),
                'Unrealized P&L': format_currency(pos.unrealized_pnl),
                'Day P&L': format_currency(pos.day_pnl),
                'Allocation %': format_percentage(allocation_percent / 100)
            }
            formatted_positions.append(formatted_pos)
        
        if formatted_positions:
            output = format_output(formatted_positions, ctx.obj['output_format'])
            click.echo(output)
            
            # Summary
            total_value = sum(pos.market_value for pos in positions_data)
            total_pnl = sum(pos.unrealized_pnl for pos in positions_data)
            
            click.echo(f"\n📊 Summary: {len(formatted_positions)} positions, "
                      f"Total Value: {format_currency(total_value)}, "
                      f"Total P&L: {format_currency(total_pnl)}")
        else:
            click.echo("📭 No positions match the specified criteria")
        
    except Exception as e:
        handle_error(f"Failed to retrieve positions: {e}", ctx.obj.get('verbose', False))


@portfolio.command()
@click.option('--period', type=click.Choice(['1d', '1w', '1m', '3m', '6m', '1y', 'ytd']), 
              default='1m', help='Performance period')
@click.option('--benchmark', help='Benchmark symbol for comparison (e.g., SPY)')
@click.pass_context
def performance(ctx, period: str, benchmark: Optional[str]):
    """
    Display portfolio performance metrics.
    
    Shows returns, risk metrics, and performance attribution for the specified period.
    Optionally compare against a benchmark.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        click.echo(f"📈 Portfolio Performance ({period.upper()})")
        click.echo("=" * 50)
        
        # Get performance data
        performance_data = analysis_tools.get_portfolio_performance(period=period)
        
        if not performance_data:
            click.echo("❌ Unable to retrieve performance data")
            return
        
        # Format performance metrics
        metrics = {
            'Total Return': format_percentage(performance_data.get('total_return', 0)),
            'Annualized Return': format_percentage(performance_data.get('annualized_return', 0)),
            'Volatility': format_percentage(performance_data.get('volatility', 0)),
            'Sharpe Ratio': f"{performance_data.get('sharpe_ratio', 0):.2f}",
            'Max Drawdown': format_percentage(performance_data.get('max_drawdown', 0)),
            'Win Rate': format_percentage(performance_data.get('win_rate', 0)),
            'Best Day': format_percentage(performance_data.get('best_day', 0)),
            'Worst Day': format_percentage(performance_data.get('worst_day', 0))
        }
        
        output = format_output(metrics, ctx.obj['output_format'])
        click.echo(output)
        
        # Benchmark comparison if requested
        if benchmark:
            benchmark = validate_symbol(benchmark)
            click.echo(f"\n📊 Benchmark Comparison ({benchmark})")
            click.echo("=" * 50)
            
            benchmark_data = analysis_tools.compare_to_benchmark(
                benchmark_symbol=benchmark, 
                period=period
            )
            
            if benchmark_data:
                comparison = {
                    'Portfolio Return': format_percentage(performance_data.get('total_return', 0)),
                    f'{benchmark} Return': format_percentage(benchmark_data.get('benchmark_return', 0)),
                    'Alpha': format_percentage(benchmark_data.get('alpha', 0)),
                    'Beta': f"{benchmark_data.get('beta', 0):.2f}",
                    'Correlation': f"{benchmark_data.get('correlation', 0):.2f}",
                    'Tracking Error': format_percentage(benchmark_data.get('tracking_error', 0))
                }
                
                comparison_output = format_output(comparison, ctx.obj['output_format'])
                click.echo(comparison_output)
        
    except Exception as e:
        handle_error(f"Failed to retrieve performance data: {e}", ctx.obj.get('verbose', False))


@portfolio.command()
@click.option('--by-sector', is_flag=True, help='Show allocation by sector')
@click.option('--by-asset-class', is_flag=True, help='Show allocation by asset class')
@click.option('--min-allocation', type=float, default=0.01, 
              help='Minimum allocation percentage to display')
@click.pass_context
def allocation(ctx, by_sector: bool, by_asset_class: bool, min_allocation: float):
    """
    Display portfolio allocation breakdown.
    
    Shows allocation by individual positions, sectors, or asset classes.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        click.echo("🥧 Portfolio Allocation")
        click.echo("=" * 50)
        
        if by_sector:
            # Get sector allocation
            allocation_data = analysis_tools.get_sector_allocation()
            title = "Sector Allocation"
        elif by_asset_class:
            # Get asset class allocation
            allocation_data = analysis_tools.get_asset_class_allocation()
            title = "Asset Class Allocation"
        else:
            # Get position allocation
            allocation_data = analysis_tools.get_position_allocation()
            title = "Position Allocation"
        
        if not allocation_data:
            click.echo("❌ Unable to retrieve allocation data")
            return
        
        # Filter by minimum allocation
        filtered_data = [
            item for item in allocation_data 
            if item.get('allocation_percent', 0) >= min_allocation * 100
        ]
        
        # Sort by allocation percentage (descending)
        filtered_data.sort(key=lambda x: x.get('allocation_percent', 0), reverse=True)
        
        # Format allocation data
        formatted_allocation = []
        for item in filtered_data:
            formatted_item = {
                'Name': item.get('name', ''),
                'Value': format_currency(item.get('value', 0)),
                'Allocation %': format_percentage(item.get('allocation_percent', 0) / 100),
                'Count': item.get('position_count', 1) if by_sector or by_asset_class else ''
            }
            if not (by_sector or by_asset_class):
                formatted_item.pop('Count')  # Remove count for individual positions
            
            formatted_allocation.append(formatted_item)
        
        if formatted_allocation:
            click.echo(f"📊 {title}")
            output = format_output(formatted_allocation, ctx.obj['output_format'])
            click.echo(output)
            
            # Summary
            total_shown = sum(item.get('allocation_percent', 0) for item in filtered_data)
            click.echo(f"\n📈 Showing {len(formatted_allocation)} items "
                      f"({format_percentage(total_shown / 100)} of portfolio)")
        else:
            click.echo("📭 No allocations meet the minimum threshold")
        
    except Exception as e:
        handle_error(f"Failed to retrieve allocation data: {e}", ctx.obj.get('verbose', False))


@portfolio.command()
@click.option('--target-allocation', help='Path to target allocation file (JSON/YAML)')
@click.option('--rebalance-threshold', type=float, default=0.05, 
              help='Minimum deviation threshold for rebalancing')
@click.option('--dry-run', is_flag=True, help='Show rebalancing plan without executing')
@click.pass_context
def rebalance(ctx, target_allocation: Optional[str], rebalance_threshold: float, dry_run: bool):
    """
    Generate and optionally execute portfolio rebalancing recommendations.
    
    Analyzes current allocation against target allocation and suggests trades
    to bring the portfolio back into balance.
    """
    try:
        from financial_portfolio_automation.mcp.optimization_tools import OptimizationTools
        
        optimization_tools = OptimizationTools()
        
        click.echo("⚖️  Portfolio Rebalancing")
        click.echo("=" * 50)
        
        # Load target allocation if provided
        target_weights = None
        if target_allocation:
            import json
            import yaml
            from pathlib import Path
            
            target_file = Path(target_allocation)
            if not target_file.exists():
                click.echo(f"❌ Target allocation file not found: {target_allocation}")
                return
            
            with open(target_file, 'r') as f:
                if target_file.suffix.lower() in ['.yaml', '.yml']:
                    target_weights = yaml.safe_load(f)
                else:
                    target_weights = json.load(f)
        
        # Get rebalancing recommendations
        rebalance_data = optimization_tools.generate_rebalancing_plan(
            target_weights=target_weights,
            threshold=rebalance_threshold
        )
        
        if not rebalance_data:
            click.echo("❌ Unable to generate rebalancing plan")
            return
        
        # Check if rebalancing is needed
        if not rebalance_data.get('trades_needed', []):
            click.echo("✅ Portfolio is already well-balanced. No rebalancing needed.")
            return
        
        # Display current vs target allocation
        current_allocation = rebalance_data.get('current_allocation', {})
        target_allocation_data = rebalance_data.get('target_allocation', {})
        
        if current_allocation and target_allocation_data:
            click.echo("📊 Current vs Target Allocation")
            allocation_comparison = []
            
            all_symbols = set(current_allocation.keys()) | set(target_allocation_data.keys())
            
            for symbol in sorted(all_symbols):
                current_pct = current_allocation.get(symbol, 0)
                target_pct = target_allocation_data.get(symbol, 0)
                deviation = current_pct - target_pct
                
                allocation_comparison.append({
                    'Symbol': symbol,
                    'Current %': format_percentage(current_pct / 100),
                    'Target %': format_percentage(target_pct / 100),
                    'Deviation': format_percentage(deviation / 100),
                    'Action': 'Buy' if deviation < -rebalance_threshold * 100 else 
                             'Sell' if deviation > rebalance_threshold * 100 else 'Hold'
                })
            
            output = format_output(allocation_comparison, ctx.obj['output_format'])
            click.echo(output)
        
        # Display recommended trades
        trades = rebalance_data.get('trades_needed', [])
        if trades:
            click.echo(f"\n🔄 Recommended Trades ({len(trades)} trades)")
            
            formatted_trades = []
            for trade in trades:
                formatted_trade = {
                    'Symbol': trade.get('symbol', ''),
                    'Action': trade.get('side', ''),
                    'Quantity': f"{trade.get('quantity', 0):,}",
                    'Estimated Value': format_currency(trade.get('estimated_value', 0)),
                    'Reason': trade.get('reason', '')
                }
                formatted_trades.append(formatted_trade)
            
            trades_output = format_output(formatted_trades, ctx.obj['output_format'])
            click.echo(trades_output)
            
            # Summary
            total_trade_value = sum(abs(trade.get('estimated_value', 0)) for trade in trades)
            click.echo(f"\n💰 Total Trade Value: {format_currency(total_trade_value)}")
        
        # Execute trades if not dry run
        if not dry_run and trades:
            if confirm_action("Execute rebalancing trades?", default=False):
                click.echo("\n🚀 Executing rebalancing trades...")
                
                from financial_portfolio_automation.mcp.execution_tools import ExecutionTools
                execution_tools = ExecutionTools()
                
                executed_trades = []
                failed_trades = []
                
                for trade in trades:
                    try:
                        result = execution_tools.place_order(
                            symbol=trade['symbol'],
                            quantity=trade['quantity'],
                            side=trade['side'],
                            order_type='market'
                        )
                        
                        if result.get('success'):
                            executed_trades.append(trade)
                            click.echo(f"✅ {trade['side']} {trade['quantity']} {trade['symbol']}")
                        else:
                            failed_trades.append(trade)
                            click.echo(f"❌ Failed to {trade['side']} {trade['symbol']}: {result.get('error')}")
                    
                    except Exception as e:
                        failed_trades.append(trade)
                        click.echo(f"❌ Error executing {trade['symbol']}: {e}")
                
                # Summary
                click.echo(f"\n📊 Execution Summary:")
                click.echo(f"✅ Successful: {len(executed_trades)} trades")
                click.echo(f"❌ Failed: {len(failed_trades)} trades")
                
                if failed_trades:
                    click.echo("\n⚠️  Failed trades can be retried manually")
        
    except Exception as e:
        handle_error(f"Failed to generate rebalancing plan: {e}", ctx.obj.get('verbose', False))