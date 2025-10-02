"""
Strategy management commands for CLI.

Provides commands for listing strategies, running backtests, optimizing parameters,
executing strategies, and monitoring strategy performance.
"""

import click
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from financial_portfolio_automation.cli.utils import (
    format_output, format_currency, format_percentage, 
    handle_error, confirm_action, validate_symbol, validate_date_range
)


@click.group()
def strategy():
    """Strategy management and backtesting commands."""
    pass


@strategy.command()
@click.option('--strategy-type', type=click.Choice(['momentum', 'mean_reversion', 'pairs', 'all']), 
              default='all', help='Filter by strategy type')
@click.option('--active-only', is_flag=True, help='Show only active strategies')
@click.pass_context
def list(ctx, strategy_type: str, active_only: bool):
    """
    List available trading strategies and their configurations.
    
    Shows strategy details including parameters, performance metrics,
    and current status.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        click.echo("📋 Available Trading Strategies")
        click.echo("=" * 50)
        
        # Get strategies list
        strategies_data = strategy_tools.list_strategies(
            strategy_type=strategy_type if strategy_type != 'all' else None,
            active_only=active_only
        )
        
        if not strategies_data:
            click.echo("📭 No strategies found matching criteria")
            return
        
        # Format strategies for display
        formatted_strategies = []
        for strategy in strategies_data:
            formatted_strategy = {
                'Name': strategy.get('name', ''),
                'Type': strategy.get('type', ''),
                'Status': '🟢 Active' if strategy.get('is_active') else '🔴 Inactive',
                'Symbols': ', '.join(strategy.get('symbols', [])),
                'Last Run': strategy.get('last_run', 'Never'),
                'Performance': format_percentage(strategy.get('total_return', 0)),
                'Sharpe Ratio': f"{strategy.get('sharpe_ratio', 0):.2f}"
            }
            formatted_strategies.append(formatted_strategy)
        
        output = format_output(formatted_strategies, ctx.obj['output_format'])
        click.echo(output)
        
        # Summary
        active_count = sum(1 for s in strategies_data if s.get('is_active'))
        total_count = len(strategies_data)
        
        click.echo(f"\n📊 Summary: {total_count} strategies ({active_count} active)")
        
    except Exception as e:
        handle_error(f"Failed to list strategies: {e}", ctx.obj.get('verbose', False))


@strategy.command()
@click.argument('strategy_name', required=True)
@click.option('--start-date', type=str, help='Backtest start date (YYYY-MM-DD)')
@click.option('--end-date', type=str, help='Backtest end date (YYYY-MM-DD)')
@click.option('--initial-capital', type=float, default=100000, 
              help='Initial capital for backtest')
@click.option('--benchmark', help='Benchmark symbol for comparison')
@click.option('--save-results', is_flag=True, help='Save backtest results to file')
@click.pass_context
def backtest(ctx, strategy_name: str, start_date: Optional[str], end_date: Optional[str], 
             initial_capital: float, benchmark: Optional[str], save_results: bool):
    """
    Run strategy backtest with historical data.
    
    Simulates strategy performance over historical period and provides
    comprehensive performance analysis and risk metrics.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        # Validate date range if provided
        if start_date and end_date:
            start_dt, end_dt = validate_date_range(start_date, end_date)
        else:
            # Default to last year
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        # Validate benchmark symbol if provided
        if benchmark:
            benchmark = validate_symbol(benchmark)
        
        click.echo(f"🔄 Running Backtest for {strategy_name}")
        click.echo(f"📅 Period: {start_date} to {end_date}")
        click.echo(f"💰 Initial Capital: {format_currency(initial_capital)}")
        if benchmark:
            click.echo(f"📊 Benchmark: {benchmark}")
        click.echo("=" * 50)
        
        # Run backtest
        with click.progressbar(length=100, label='Running backtest') as bar:
            backtest_results = strategy_tools.run_backtest(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                benchmark=benchmark,
                progress_callback=lambda p: bar.update(p - bar.pos)
            )
        
        if not backtest_results:
            click.echo("❌ Backtest failed or returned no results")
            return
        
        # Display performance summary
        click.echo("\n📈 Performance Summary")
        click.echo("=" * 30)
        
        performance = backtest_results.get('performance', {})
        performance_metrics = {
            'Total Return': format_percentage(performance.get('total_return', 0)),
            'Annualized Return': format_percentage(performance.get('annualized_return', 0)),
            'Volatility': format_percentage(performance.get('volatility', 0)),
            'Sharpe Ratio': f"{performance.get('sharpe_ratio', 0):.2f}",
            'Sortino Ratio': f"{performance.get('sortino_ratio', 0):.2f}",
            'Maximum Drawdown': format_percentage(performance.get('max_drawdown', 0)),
            'Win Rate': format_percentage(performance.get('win_rate', 0)),
            'Profit Factor': f"{performance.get('profit_factor', 0):.2f}"
        }
        
        perf_output = format_output(performance_metrics, ctx.obj['output_format'])
        click.echo(perf_output)
        
        # Trading statistics
        trading_stats = backtest_results.get('trading_stats', {})
        if trading_stats:
            click.echo("\n📊 Trading Statistics")
            click.echo("=" * 30)
            
            trading_metrics = {
                'Total Trades': trading_stats.get('total_trades', 0),
                'Winning Trades': trading_stats.get('winning_trades', 0),
                'Losing Trades': trading_stats.get('losing_trades', 0),
                'Average Win': format_currency(trading_stats.get('avg_win', 0)),
                'Average Loss': format_currency(trading_stats.get('avg_loss', 0)),
                'Largest Win': format_currency(trading_stats.get('largest_win', 0)),
                'Largest Loss': format_currency(trading_stats.get('largest_loss', 0)),
                'Average Trade': format_currency(trading_stats.get('avg_trade', 0))
            }
            
            trading_output = format_output(trading_metrics, ctx.obj['output_format'])
            click.echo(trading_output)
        
        # Benchmark comparison
        if benchmark and 'benchmark_comparison' in backtest_results:
            click.echo(f"\n📊 Benchmark Comparison ({benchmark})")
            click.echo("=" * 40)
            
            comparison = backtest_results['benchmark_comparison']
            comparison_metrics = {
                'Strategy Return': format_percentage(performance.get('total_return', 0)),
                f'{benchmark} Return': format_percentage(comparison.get('benchmark_return', 0)),
                'Excess Return': format_percentage(comparison.get('excess_return', 0)),
                'Alpha': format_percentage(comparison.get('alpha', 0)),
                'Beta': f"{comparison.get('beta', 0):.2f}",
                'Information Ratio': f"{comparison.get('information_ratio', 0):.2f}",
                'Tracking Error': format_percentage(comparison.get('tracking_error', 0))
            }
            
            comp_output = format_output(comparison_metrics, ctx.obj['output_format'])
            click.echo(comp_output)
        
        # Monthly returns table
        monthly_returns = backtest_results.get('monthly_returns', [])
        if monthly_returns and ctx.obj['output_format'] == 'table':
            click.echo("\n📅 Monthly Returns")
            click.echo("=" * 30)
            
            # Format monthly returns for table display
            formatted_monthly = []
            for month_data in monthly_returns[-12:]:  # Last 12 months
                formatted_month = {
                    'Month': month_data.get('month', ''),
                    'Return': format_percentage(month_data.get('return', 0)),
                    'Benchmark': format_percentage(month_data.get('benchmark_return', 0)) if benchmark else 'N/A'
                }
                formatted_monthly.append(formatted_month)
            
            monthly_output = format_output(formatted_monthly, ctx.obj['output_format'])
            click.echo(monthly_output)
        
        # Save results if requested
        if save_results:
            from pathlib import Path
            import json
            from datetime import datetime
            
            results_dir = Path('backtest_results')
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{strategy_name}_{timestamp}.json"
            filepath = results_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(backtest_results, f, indent=2, default=str)
            
            click.echo(f"\n💾 Results saved to: {filepath}")
        
    except Exception as e:
        handle_error(f"Failed to run backtest: {e}", ctx.obj.get('verbose', False))


@strategy.command()
@click.argument('strategy_name', required=True)
@click.option('--parameter', '-p', multiple=True, 
              help='Parameter to optimize (format: param_name:min:max:step)')
@click.option('--objective', type=click.Choice(['sharpe', 'return', 'sortino', 'calmar']), 
              default='sharpe', help='Optimization objective')
@click.option('--start-date', type=str, help='Optimization start date (YYYY-MM-DD)')
@click.option('--end-date', type=str, help='Optimization end date (YYYY-MM-DD)')
@click.option('--max-iterations', type=int, default=100, help='Maximum optimization iterations')
@click.pass_context
def optimize(ctx, strategy_name: str, parameter: tuple, objective: str, 
             start_date: Optional[str], end_date: Optional[str], max_iterations: int):
    """
    Optimize strategy parameters using historical data.
    
    Uses various optimization algorithms to find optimal parameter combinations
    that maximize the specified objective function.
    
    Example:
        strategy optimize momentum -p lookback:10:50:5 -p threshold:0.01:0.1:0.01
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        # Parse parameter ranges
        param_ranges = {}
        for param_spec in parameter:
            try:
                parts = param_spec.split(':')
                if len(parts) != 4:
                    raise ValueError(f"Invalid parameter format: {param_spec}")
                
                param_name, min_val, max_val, step = parts
                param_ranges[param_name] = {
                    'min': float(min_val),
                    'max': float(max_val),
                    'step': float(step)
                }
            except ValueError as e:
                click.echo(f"❌ Error parsing parameter '{param_spec}': {e}")
                return
        
        if not param_ranges:
            click.echo("❌ No parameters specified for optimization")
            click.echo("Use -p param_name:min:max:step format")
            return
        
        # Validate date range if provided
        if start_date and end_date:
            start_dt, end_dt = validate_date_range(start_date, end_date)
        else:
            # Default to last year
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            start_date = start_dt.strftime('%Y-%m-%d')
            end_date = end_dt.strftime('%Y-%m-%d')
        
        click.echo(f"🔧 Optimizing Strategy: {strategy_name}")
        click.echo(f"🎯 Objective: {objective.title()}")
        click.echo(f"📅 Period: {start_date} to {end_date}")
        click.echo(f"🔢 Parameters: {', '.join(param_ranges.keys())}")
        click.echo("=" * 50)
        
        # Run optimization
        with click.progressbar(length=max_iterations, label='Optimizing parameters') as bar:
            optimization_results = strategy_tools.optimize_strategy(
                strategy_name=strategy_name,
                parameter_ranges=param_ranges,
                objective=objective,
                start_date=start_date,
                end_date=end_date,
                max_iterations=max_iterations,
                progress_callback=lambda p: bar.update(1)
            )
        
        if not optimization_results:
            click.echo("❌ Optimization failed or returned no results")
            return
        
        # Display optimization results
        click.echo("\n🏆 Optimization Results")
        click.echo("=" * 30)
        
        best_params = optimization_results.get('best_parameters', {})
        best_performance = optimization_results.get('best_performance', {})
        
        # Best parameters
        click.echo("🎯 Optimal Parameters:")
        param_output = format_output(best_params, ctx.obj['output_format'])
        click.echo(param_output)
        
        # Best performance
        click.echo("\n📈 Optimal Performance:")
        performance_metrics = {
            'Objective Value': f"{best_performance.get(objective, 0):.4f}",
            'Total Return': format_percentage(best_performance.get('total_return', 0)),
            'Sharpe Ratio': f"{best_performance.get('sharpe_ratio', 0):.2f}",
            'Maximum Drawdown': format_percentage(best_performance.get('max_drawdown', 0)),
            'Win Rate': format_percentage(best_performance.get('win_rate', 0))
        }
        
        perf_output = format_output(performance_metrics, ctx.obj['output_format'])
        click.echo(perf_output)
        
        # Optimization statistics
        opt_stats = optimization_results.get('optimization_stats', {})
        if opt_stats:
            click.echo("\n📊 Optimization Statistics:")
            stats_metrics = {
                'Total Iterations': opt_stats.get('total_iterations', 0),
                'Successful Runs': opt_stats.get('successful_runs', 0),
                'Best Iteration': opt_stats.get('best_iteration', 0),
                'Improvement %': format_percentage(opt_stats.get('improvement_percent', 0)),
                'Convergence': 'Yes' if opt_stats.get('converged', False) else 'No'
            }
            
            stats_output = format_output(stats_metrics, ctx.obj['output_format'])
            click.echo(stats_output)
        
        # Parameter sensitivity analysis
        sensitivity = optimization_results.get('parameter_sensitivity', {})
        if sensitivity:
            click.echo("\n🎛️  Parameter Sensitivity:")
            
            formatted_sensitivity = []
            for param, sens_data in sensitivity.items():
                formatted_sens = {
                    'Parameter': param,
                    'Sensitivity': f"{sens_data.get('sensitivity', 0):.4f}",
                    'Optimal Value': f"{sens_data.get('optimal_value', 0):.4f}",
                    'Range Impact': format_percentage(sens_data.get('range_impact', 0))
                }
                formatted_sensitivity.append(formatted_sens)
            
            sens_output = format_output(formatted_sensitivity, ctx.obj['output_format'])
            click.echo(sens_output)
        
        # Ask if user wants to update strategy with optimal parameters
        if confirm_action("Update strategy with optimal parameters?", default=False):
            try:
                update_result = strategy_tools.update_strategy_parameters(
                    strategy_name=strategy_name,
                    parameters=best_params
                )
                
                if update_result.get('success'):
                    click.echo("✅ Strategy parameters updated successfully")
                else:
                    click.echo(f"❌ Failed to update parameters: {update_result.get('error')}")
            
            except Exception as e:
                click.echo(f"❌ Error updating strategy parameters: {e}")
        
    except Exception as e:
        handle_error(f"Failed to optimize strategy: {e}", ctx.obj.get('verbose', False))


@strategy.command()
@click.argument('strategy_name', required=True)
@click.option('--dry-run', is_flag=True, help='Simulate execution without placing real orders')
@click.option('--max-positions', type=int, help='Maximum number of positions to hold')
@click.option('--capital-allocation', type=float, help='Capital allocation for this strategy')
@click.pass_context
def execute(ctx, strategy_name: str, dry_run: bool, max_positions: Optional[int], 
            capital_allocation: Optional[float]):
    """
    Execute trading strategy with current market conditions.
    
    Runs the strategy against live market data and generates trading signals.
    Use --dry-run to simulate without placing actual orders.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        click.echo(f"🚀 Executing Strategy: {strategy_name}")
        if dry_run:
            click.echo("🧪 DRY RUN MODE - No actual trades will be placed")
        click.echo("=" * 50)
        
        # Execute strategy
        execution_results = strategy_tools.execute_strategy(
            strategy_name=strategy_name,
            dry_run=dry_run,
            max_positions=max_positions,
            capital_allocation=capital_allocation
        )
        
        if not execution_results:
            click.echo("❌ Strategy execution failed")
            return
        
        # Display execution summary
        click.echo("📊 Execution Summary")
        click.echo("=" * 30)
        
        summary = execution_results.get('summary', {})
        summary_metrics = {
            'Strategy Status': summary.get('status', 'Unknown'),
            'Signals Generated': summary.get('signals_generated', 0),
            'Orders Placed': summary.get('orders_placed', 0),
            'Positions Modified': summary.get('positions_modified', 0),
            'Execution Time': f"{summary.get('execution_time_ms', 0):.0f}ms",
            'Capital Allocated': format_currency(summary.get('capital_allocated', 0))
        }
        
        summary_output = format_output(summary_metrics, ctx.obj['output_format'])
        click.echo(summary_output)
        
        # Display generated signals
        signals = execution_results.get('signals', [])
        if signals:
            click.echo("\n🚦 Generated Signals")
            click.echo("=" * 30)
            
            formatted_signals = []
            for signal in signals:
                formatted_signal = {
                    'Symbol': signal.get('symbol', ''),
                    'Action': signal.get('action', ''),
                    'Strength': signal.get('strength', ''),
                    'Price': format_currency(signal.get('price', 0)),
                    'Quantity': f"{signal.get('quantity', 0):,}",
                    'Confidence': format_percentage(signal.get('confidence', 0)),
                    'Reason': signal.get('reason', '')
                }
                formatted_signals.append(formatted_signal)
            
            signals_output = format_output(formatted_signals, ctx.obj['output_format'])
            click.echo(signals_output)
        
        # Display order results (if not dry run)
        if not dry_run:
            orders = execution_results.get('orders', [])
            if orders:
                click.echo("\n📋 Order Results")
                click.echo("=" * 30)
                
                formatted_orders = []
                for order in orders:
                    formatted_order = {
                        'Order ID': order.get('order_id', ''),
                        'Symbol': order.get('symbol', ''),
                        'Side': order.get('side', ''),
                        'Quantity': f"{order.get('quantity', 0):,}",
                        'Status': order.get('status', ''),
                        'Fill Price': format_currency(order.get('fill_price', 0)) if order.get('fill_price') else 'Pending'
                    }
                    formatted_orders.append(formatted_order)
                
                orders_output = format_output(formatted_orders, ctx.obj['output_format'])
                click.echo(orders_output)
        
        # Risk assessment
        risk_assessment = execution_results.get('risk_assessment', {})
        if risk_assessment:
            click.echo("\n⚠️  Risk Assessment")
            click.echo("=" * 30)
            
            risk_metrics = {
                'Portfolio Risk Level': risk_assessment.get('risk_level', 'Unknown'),
                'Position Concentration': format_percentage(risk_assessment.get('concentration', 0)),
                'Estimated VaR Impact': format_currency(risk_assessment.get('var_impact', 0)),
                'Risk Score': f"{risk_assessment.get('risk_score', 0):.2f}/10",
                'Risk Warnings': len(risk_assessment.get('warnings', []))
            }
            
            risk_output = format_output(risk_metrics, ctx.obj['output_format'])
            click.echo(risk_output)
            
            # Display risk warnings
            warnings = risk_assessment.get('warnings', [])
            if warnings:
                click.echo("\n⚠️  Risk Warnings:")
                for warning in warnings:
                    click.echo(f"  • {warning}")
        
        # Performance impact estimate
        impact = execution_results.get('performance_impact', {})
        if impact:
            click.echo("\n📈 Estimated Performance Impact")
            click.echo("=" * 40)
            
            impact_metrics = {
                'Expected Return': format_percentage(impact.get('expected_return', 0)),
                'Risk Contribution': format_percentage(impact.get('risk_contribution', 0)),
                'Sharpe Impact': f"{impact.get('sharpe_impact', 0):+.3f}",
                'Diversification Effect': impact.get('diversification_effect', 'Neutral')
            }
            
            impact_output = format_output(impact_metrics, ctx.obj['output_format'])
            click.echo(impact_output)
        
    except Exception as e:
        handle_error(f"Failed to execute strategy: {e}", ctx.obj.get('verbose', False))


@strategy.command()
@click.option('--strategy-name', help='Filter by specific strategy name')
@click.option('--active-only', is_flag=True, help='Show only active strategy executions')
@click.option('--last-hours', type=int, default=24, help='Show executions from last N hours')
@click.pass_context
def status(ctx, strategy_name: Optional[str], active_only: bool, last_hours: int):
    """
    Monitor strategy execution status and performance.
    
    Shows current status of running strategies, recent executions,
    and real-time performance metrics.
    """
    try:
        from financial_portfolio_automation.mcp.strategy_tools import StrategyTools
        
        strategy_tools = StrategyTools()
        
        click.echo("📊 Strategy Execution Status")
        click.echo("=" * 50)
        
        # Get strategy status
        status_data = strategy_tools.get_strategy_status(
            strategy_name=strategy_name,
            active_only=active_only,
            hours_back=last_hours
        )
        
        if not status_data:
            click.echo("📭 No strategy executions found")
            return
        
        # Active strategies
        active_strategies = status_data.get('active_strategies', [])
        if active_strategies:
            click.echo("🟢 Active Strategies")
            click.echo("=" * 30)
            
            formatted_active = []
            for strategy in active_strategies:
                formatted_strategy = {
                    'Name': strategy.get('name', ''),
                    'Status': strategy.get('status', ''),
                    'Runtime': strategy.get('runtime', ''),
                    'Signals': strategy.get('signals_count', 0),
                    'Orders': strategy.get('orders_count', 0),
                    'P&L': format_currency(strategy.get('unrealized_pnl', 0)),
                    'Last Update': strategy.get('last_update', '')
                }
                formatted_active.append(formatted_strategy)
            
            active_output = format_output(formatted_active, ctx.obj['output_format'])
            click.echo(active_output)
        
        # Recent executions
        recent_executions = status_data.get('recent_executions', [])
        if recent_executions:
            click.echo(f"\n📅 Recent Executions (Last {last_hours}h)")
            click.echo("=" * 40)
            
            formatted_executions = []
            for execution in recent_executions:
                formatted_execution = {
                    'Strategy': execution.get('strategy_name', ''),
                    'Start Time': execution.get('start_time', ''),
                    'Duration': execution.get('duration', ''),
                    'Status': execution.get('status', ''),
                    'Signals': execution.get('signals_generated', 0),
                    'Orders': execution.get('orders_placed', 0),
                    'Result': execution.get('result', '')
                }
                formatted_executions.append(formatted_execution)
            
            executions_output = format_output(formatted_executions, ctx.obj['output_format'])
            click.echo(executions_output)
        
        # Performance summary
        performance_summary = status_data.get('performance_summary', {})
        if performance_summary:
            click.echo("\n📈 Performance Summary")
            click.echo("=" * 30)
            
            perf_metrics = {
                'Total Strategies': performance_summary.get('total_strategies', 0),
                'Active Strategies': performance_summary.get('active_strategies', 0),
                'Total P&L': format_currency(performance_summary.get('total_pnl', 0)),
                'Best Performer': performance_summary.get('best_performer', 'N/A'),
                'Worst Performer': performance_summary.get('worst_performer', 'N/A'),
                'Average Return': format_percentage(performance_summary.get('average_return', 0)),
                'Success Rate': format_percentage(performance_summary.get('success_rate', 0))
            }
            
            perf_output = format_output(perf_metrics, ctx.obj['output_format'])
            click.echo(perf_output)
        
        # System health
        system_health = status_data.get('system_health', {})
        if system_health:
            click.echo("\n🏥 System Health")
            click.echo("=" * 30)
            
            health_metrics = {
                'Market Data': '🟢 Connected' if system_health.get('market_data_connected') else '🔴 Disconnected',
                'Order Execution': '🟢 Available' if system_health.get('execution_available') else '🔴 Unavailable',
                'Risk Controls': '🟢 Active' if system_health.get('risk_controls_active') else '🔴 Inactive',
                'Data Latency': f"{system_health.get('data_latency_ms', 0):.0f}ms",
                'CPU Usage': format_percentage(system_health.get('cpu_usage', 0)),
                'Memory Usage': format_percentage(system_health.get('memory_usage', 0))
            }
            
            health_output = format_output(health_metrics, ctx.obj['output_format'])
            click.echo(health_output)
        
    except Exception as e:
        handle_error(f"Failed to get strategy status: {e}", ctx.obj.get('verbose', False))