"""
Analysis commands for CLI.

Provides commands for risk analysis, performance analysis, technical analysis,
correlation analysis, and attribution analysis.
"""

import click
from typing import Optional, List
from datetime import datetime, timedelta

from financial_portfolio_automation.cli.utils import (
    format_output, format_currency, format_percentage, 
    handle_error, validate_symbol, validate_date_range
)


@click.group()
def analysis():
    """Portfolio and market analysis commands."""
    pass


@analysis.command()
@click.option('--symbol', '-s', help='Analyze specific symbol risk')
@click.option('--confidence-level', type=float, default=0.95, 
              help='Confidence level for VaR calculation')
@click.option('--time-horizon', type=int, default=1, 
              help='Time horizon in days for risk metrics')
@click.pass_context
def risk(ctx, symbol: Optional[str], confidence_level: float, time_horizon: int):
    """
    Perform comprehensive portfolio risk assessment.
    
    Analyzes portfolio risk metrics including VaR, beta, volatility,
    concentration risk, and stress testing scenarios.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        
        if symbol:
            symbol = validate_symbol(symbol)
            click.echo(f"🎯 Risk Analysis for {symbol}")
        else:
            click.echo("⚠️  Portfolio Risk Analysis")
        
        click.echo("=" * 50)
        
        # Get risk assessment
        risk_data = risk_tools.assess_portfolio_risk(
            symbol=symbol,
            confidence_level=confidence_level,
            time_horizon=time_horizon
        )
        
        if not risk_data:
            click.echo("❌ Unable to retrieve risk data")
            return
        
        # Format risk metrics
        risk_metrics = {
            'Value at Risk (VaR)': format_currency(risk_data.get('var', 0)),
            'Expected Shortfall': format_currency(risk_data.get('expected_shortfall', 0)),
            'Beta': f"{risk_data.get('beta', 0):.2f}",
            'Volatility (Annualized)': format_percentage(risk_data.get('volatility', 0)),
            'Maximum Drawdown': format_percentage(risk_data.get('max_drawdown', 0)),
            'Sharpe Ratio': f"{risk_data.get('sharpe_ratio', 0):.2f}",
            'Sortino Ratio': f"{risk_data.get('sortino_ratio', 0):.2f}"
        }
        
        output = format_output(risk_metrics, ctx.obj['output_format'])
        click.echo(output)
        
        # Concentration risk analysis
        concentration_data = risk_data.get('concentration_risk', {})
        if concentration_data:
            click.echo("\n🎯 Concentration Risk")
            click.echo("=" * 30)
            
            concentration_metrics = {
                'Largest Position %': format_percentage(concentration_data.get('largest_position_pct', 0) / 100),
                'Top 5 Positions %': format_percentage(concentration_data.get('top5_positions_pct', 0) / 100),
                'Herfindahl Index': f"{concentration_data.get('herfindahl_index', 0):.4f}",
                'Effective Positions': f"{concentration_data.get('effective_positions', 0):.1f}",
                'Concentration Score': concentration_data.get('concentration_score', 'N/A')
            }
            
            concentration_output = format_output(concentration_metrics, ctx.obj['output_format'])
            click.echo(concentration_output)
        
        # Stress test scenarios
        stress_tests = risk_data.get('stress_tests', [])
        if stress_tests:
            click.echo("\n🧪 Stress Test Scenarios")
            click.echo("=" * 30)
            
            formatted_stress_tests = []
            for test in stress_tests:
                formatted_test = {
                    'Scenario': test.get('scenario', ''),
                    'Portfolio Impact': format_currency(test.get('portfolio_impact', 0)),
                    'Impact %': format_percentage(test.get('impact_percent', 0)),
                    'Probability': format_percentage(test.get('probability', 0))
                }
                formatted_stress_tests.append(formatted_test)
            
            stress_output = format_output(formatted_stress_tests, ctx.obj['output_format'])
            click.echo(stress_output)
        
    except Exception as e:
        handle_error(f"Failed to perform risk analysis: {e}", ctx.obj.get('verbose', False))


@analysis.command()
@click.option('--period', type=click.Choice(['1d', '1w', '1m', '3m', '6m', '1y', 'ytd', 'all']), 
              default='1m', help='Analysis period')
@click.option('--benchmark', help='Benchmark symbol for comparison')
@click.option('--attribution', is_flag=True, help='Include performance attribution analysis')
@click.pass_context
def performance(ctx, period: str, benchmark: Optional[str], attribution: bool):
    """
    Perform detailed portfolio performance analysis.
    
    Analyzes returns, risk-adjusted metrics, drawdowns, and optionally
    provides performance attribution by sector or security.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        click.echo(f"📈 Performance Analysis ({period.upper()})")
        click.echo("=" * 50)
        
        # Get performance analysis
        performance_data = analysis_tools.analyze_performance(
            period=period,
            benchmark=benchmark,
            include_attribution=attribution
        )
        
        if not performance_data:
            click.echo("❌ Unable to retrieve performance data")
            return
        
        # Basic performance metrics
        basic_metrics = {
            'Total Return': format_percentage(performance_data.get('total_return', 0)),
            'Annualized Return': format_percentage(performance_data.get('annualized_return', 0)),
            'Volatility': format_percentage(performance_data.get('volatility', 0)),
            'Sharpe Ratio': f"{performance_data.get('sharpe_ratio', 0):.2f}",
            'Sortino Ratio': f"{performance_data.get('sortino_ratio', 0):.2f}",
            'Calmar Ratio': f"{performance_data.get('calmar_ratio', 0):.2f}",
            'Maximum Drawdown': format_percentage(performance_data.get('max_drawdown', 0)),
            'Win Rate': format_percentage(performance_data.get('win_rate', 0))
        }
        
        output = format_output(basic_metrics, ctx.obj['output_format'])
        click.echo(output)
        
        # Benchmark comparison
        if benchmark and 'benchmark_comparison' in performance_data:
            benchmark = validate_symbol(benchmark)
            click.echo(f"\n📊 Benchmark Comparison ({benchmark})")
            click.echo("=" * 40)
            
            comparison_data = performance_data['benchmark_comparison']
            comparison_metrics = {
                'Alpha': format_percentage(comparison_data.get('alpha', 0)),
                'Beta': f"{comparison_data.get('beta', 0):.2f}",
                'Correlation': f"{comparison_data.get('correlation', 0):.2f}",
                'Tracking Error': format_percentage(comparison_data.get('tracking_error', 0)),
                'Information Ratio': f"{comparison_data.get('information_ratio', 0):.2f}",
                'Up Capture': format_percentage(comparison_data.get('up_capture', 0)),
                'Down Capture': format_percentage(comparison_data.get('down_capture', 0))
            }
            
            comparison_output = format_output(comparison_metrics, ctx.obj['output_format'])
            click.echo(comparison_output)
        
        # Performance attribution
        if attribution and 'attribution' in performance_data:
            click.echo("\n🎯 Performance Attribution")
            click.echo("=" * 40)
            
            attribution_data = performance_data['attribution']
            
            # Sector attribution
            if 'sector_attribution' in attribution_data:
                click.echo("\n📊 Sector Attribution")
                sector_data = attribution_data['sector_attribution']
                
                formatted_sectors = []
                for sector in sector_data:
                    formatted_sector = {
                        'Sector': sector.get('sector', ''),
                        'Weight %': format_percentage(sector.get('weight', 0) / 100),
                        'Return %': format_percentage(sector.get('return', 0)),
                        'Contribution': format_percentage(sector.get('contribution', 0)),
                        'Selection Effect': format_percentage(sector.get('selection_effect', 0)),
                        'Allocation Effect': format_percentage(sector.get('allocation_effect', 0))
                    }
                    formatted_sectors.append(formatted_sector)
                
                sector_output = format_output(formatted_sectors, ctx.obj['output_format'])
                click.echo(sector_output)
            
            # Security attribution (top contributors/detractors)
            if 'security_attribution' in attribution_data:
                click.echo("\n🏆 Top Contributors/Detractors")
                security_data = attribution_data['security_attribution']
                
                # Top contributors
                contributors = security_data.get('top_contributors', [])[:5]
                if contributors:
                    click.echo("\n✅ Top Contributors")
                    formatted_contributors = []
                    for contrib in contributors:
                        formatted_contrib = {
                            'Symbol': contrib.get('symbol', ''),
                            'Weight %': format_percentage(contrib.get('weight', 0) / 100),
                            'Return %': format_percentage(contrib.get('return', 0)),
                            'Contribution': format_percentage(contrib.get('contribution', 0))
                        }
                        formatted_contributors.append(formatted_contrib)
                    
                    contrib_output = format_output(formatted_contributors, ctx.obj['output_format'])
                    click.echo(contrib_output)
                
                # Top detractors
                detractors = security_data.get('top_detractors', [])[:5]
                if detractors:
                    click.echo("\n❌ Top Detractors")
                    formatted_detractors = []
                    for detractor in detractors:
                        formatted_detractor = {
                            'Symbol': detractor.get('symbol', ''),
                            'Weight %': format_percentage(detractor.get('weight', 0) / 100),
                            'Return %': format_percentage(detractor.get('return', 0)),
                            'Contribution': format_percentage(detractor.get('contribution', 0))
                        }
                        formatted_detractors.append(formatted_detractor)
                    
                    detractor_output = format_output(formatted_detractors, ctx.obj['output_format'])
                    click.echo(detractor_output)
        
    except Exception as e:
        handle_error(f"Failed to perform performance analysis: {e}", ctx.obj.get('verbose', False))


@analysis.command()
@click.argument('symbol', required=True)
@click.option('--period', type=click.Choice(['1d', '5d', '1m', '3m', '6m', '1y']), 
              default='3m', help='Analysis period')
@click.option('--indicators', multiple=True, 
              type=click.Choice(['sma', 'ema', 'rsi', 'macd', 'bollinger', 'stochastic', 'atr']),
              help='Technical indicators to calculate')
@click.pass_context
def technical(ctx, symbol: str, period: str, indicators: tuple):
    """
    Perform technical analysis for a specific security.
    
    Calculates technical indicators, identifies chart patterns,
    and provides trading signals based on technical analysis.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        symbol = validate_symbol(symbol)
        analysis_tools = AnalysisTools()
        
        click.echo(f"📊 Technical Analysis for {symbol} ({period.upper()})")
        click.echo("=" * 50)
        
        # Get technical analysis
        technical_data = analysis_tools.perform_technical_analysis(
            symbol=symbol,
            period=period,
            indicators=list(indicators) if indicators else None
        )
        
        if not technical_data:
            click.echo("❌ Unable to retrieve technical analysis data")
            return
        
        # Current price and basic info
        current_data = technical_data.get('current_data', {})
        if current_data:
            price_info = {
                'Current Price': format_currency(current_data.get('price', 0)),
                'Change': format_currency(current_data.get('change', 0)),
                'Change %': format_percentage(current_data.get('change_percent', 0)),
                'Volume': f"{current_data.get('volume', 0):,}",
                '52-Week High': format_currency(current_data.get('high_52w', 0)),
                '52-Week Low': format_currency(current_data.get('low_52w', 0))
            }
            
            price_output = format_output(price_info, ctx.obj['output_format'])
            click.echo(price_output)
        
        # Technical indicators
        indicators_data = technical_data.get('indicators', {})
        if indicators_data:
            click.echo("\n📈 Technical Indicators")
            click.echo("=" * 30)
            
            formatted_indicators = {}
            
            # Moving averages
            if 'moving_averages' in indicators_data:
                ma_data = indicators_data['moving_averages']
                formatted_indicators.update({
                    'SMA 20': format_currency(ma_data.get('sma_20', 0)),
                    'SMA 50': format_currency(ma_data.get('sma_50', 0)),
                    'SMA 200': format_currency(ma_data.get('sma_200', 0)),
                    'EMA 12': format_currency(ma_data.get('ema_12', 0)),
                    'EMA 26': format_currency(ma_data.get('ema_26', 0))
                })
            
            # Momentum indicators
            if 'momentum' in indicators_data:
                momentum_data = indicators_data['momentum']
                formatted_indicators.update({
                    'RSI': f"{momentum_data.get('rsi', 0):.2f}",
                    'MACD': f"{momentum_data.get('macd', 0):.4f}",
                    'MACD Signal': f"{momentum_data.get('macd_signal', 0):.4f}",
                    'Stochastic %K': f"{momentum_data.get('stoch_k', 0):.2f}",
                    'Stochastic %D': f"{momentum_data.get('stoch_d', 0):.2f}"
                })
            
            # Volatility indicators
            if 'volatility' in indicators_data:
                vol_data = indicators_data['volatility']
                formatted_indicators.update({
                    'Bollinger Upper': format_currency(vol_data.get('bb_upper', 0)),
                    'Bollinger Middle': format_currency(vol_data.get('bb_middle', 0)),
                    'Bollinger Lower': format_currency(vol_data.get('bb_lower', 0)),
                    'ATR': format_currency(vol_data.get('atr', 0))
                })
            
            if formatted_indicators:
                indicators_output = format_output(formatted_indicators, ctx.obj['output_format'])
                click.echo(indicators_output)
        
        # Trading signals
        signals = technical_data.get('signals', [])
        if signals:
            click.echo("\n🚦 Trading Signals")
            click.echo("=" * 30)
            
            formatted_signals = []
            for signal in signals:
                formatted_signal = {
                    'Indicator': signal.get('indicator', ''),
                    'Signal': signal.get('signal', ''),
                    'Strength': signal.get('strength', ''),
                    'Description': signal.get('description', '')
                }
                formatted_signals.append(formatted_signal)
            
            signals_output = format_output(formatted_signals, ctx.obj['output_format'])
            click.echo(signals_output)
        
        # Support and resistance levels
        levels = technical_data.get('support_resistance', {})
        if levels:
            click.echo("\n🎯 Support & Resistance Levels")
            click.echo("=" * 40)
            
            levels_info = {}
            if 'resistance_levels' in levels:
                for i, level in enumerate(levels['resistance_levels'][:3], 1):
                    levels_info[f'Resistance {i}'] = format_currency(level)
            
            if 'support_levels' in levels:
                for i, level in enumerate(levels['support_levels'][:3], 1):
                    levels_info[f'Support {i}'] = format_currency(level)
            
            if levels_info:
                levels_output = format_output(levels_info, ctx.obj['output_format'])
                click.echo(levels_output)
        
    except Exception as e:
        handle_error(f"Failed to perform technical analysis: {e}", ctx.obj.get('verbose', False))


@analysis.command()
@click.option('--symbols', help='Comma-separated list of symbols to analyze')
@click.option('--period', type=click.Choice(['1m', '3m', '6m', '1y']), 
              default='3m', help='Analysis period')
@click.option('--min-correlation', type=float, default=0.5, 
              help='Minimum correlation threshold to display')
@click.pass_context
def correlation(ctx, symbols: Optional[str], period: str, min_correlation: float):
    """
    Analyze correlation and diversification metrics.
    
    Calculates correlation matrix between portfolio positions or specified symbols,
    and provides diversification analysis.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        # Parse symbols if provided
        symbol_list = None
        if symbols:
            symbol_list = [validate_symbol(s.strip()) for s in symbols.split(',')]
            click.echo(f"🔗 Correlation Analysis for {', '.join(symbol_list)} ({period.upper()})")
        else:
            click.echo(f"🔗 Portfolio Correlation Analysis ({period.upper()})")
        
        click.echo("=" * 50)
        
        # Get correlation analysis
        correlation_data = analysis_tools.analyze_correlation(
            symbols=symbol_list,
            period=period,
            min_correlation=min_correlation
        )
        
        if not correlation_data:
            click.echo("❌ Unable to retrieve correlation data")
            return
        
        # Correlation matrix
        correlation_matrix = correlation_data.get('correlation_matrix', {})
        if correlation_matrix:
            click.echo("📊 Correlation Matrix")
            click.echo("=" * 30)
            
            # Format correlation matrix for display
            symbols_in_matrix = list(correlation_matrix.keys())
            
            if ctx.obj['output_format'] == 'table':
                # Create table format for correlation matrix
                matrix_data = []
                for symbol1 in symbols_in_matrix:
                    row = {'Symbol': symbol1}
                    for symbol2 in symbols_in_matrix:
                        correlation = correlation_matrix.get(symbol1, {}).get(symbol2, 0)
                        row[symbol2] = f"{correlation:.2f}"
                    matrix_data.append(row)
                
                matrix_output = format_output(matrix_data, ctx.obj['output_format'])
                click.echo(matrix_output)
            else:
                # JSON/CSV format
                matrix_output = format_output(correlation_matrix, ctx.obj['output_format'])
                click.echo(matrix_output)
        
        # High correlations (potential concentration risk)
        high_correlations = correlation_data.get('high_correlations', [])
        if high_correlations:
            click.echo(f"\n⚠️  High Correlations (>{min_correlation:.1f})")
            click.echo("=" * 40)
            
            formatted_correlations = []
            for corr in high_correlations:
                formatted_corr = {
                    'Symbol 1': corr.get('symbol1', ''),
                    'Symbol 2': corr.get('symbol2', ''),
                    'Correlation': f"{corr.get('correlation', 0):.3f}",
                    'Risk Level': corr.get('risk_level', '')
                }
                formatted_correlations.append(formatted_corr)
            
            corr_output = format_output(formatted_correlations, ctx.obj['output_format'])
            click.echo(corr_output)
        
        # Diversification metrics
        diversification = correlation_data.get('diversification_metrics', {})
        if diversification:
            click.echo("\n🎯 Diversification Metrics")
            click.echo("=" * 40)
            
            div_metrics = {
                'Average Correlation': f"{diversification.get('average_correlation', 0):.3f}",
                'Diversification Ratio': f"{diversification.get('diversification_ratio', 0):.3f}",
                'Effective Number of Assets': f"{diversification.get('effective_assets', 0):.1f}",
                'Concentration Score': diversification.get('concentration_score', 'N/A'),
                'Diversification Score': diversification.get('diversification_score', 'N/A')
            }
            
            div_output = format_output(div_metrics, ctx.obj['output_format'])
            click.echo(div_output)
        
        # Sector correlation analysis
        sector_correlation = correlation_data.get('sector_correlation', {})
        if sector_correlation:
            click.echo("\n🏢 Sector Correlation Analysis")
            click.echo("=" * 40)
            
            sector_metrics = {
                'Most Correlated Sectors': ', '.join(sector_correlation.get('high_correlation_sectors', [])),
                'Least Correlated Sectors': ', '.join(sector_correlation.get('low_correlation_sectors', [])),
                'Sector Concentration Risk': sector_correlation.get('concentration_risk', 'N/A')
            }
            
            sector_output = format_output(sector_metrics, ctx.obj['output_format'])
            click.echo(sector_output)
        
    except Exception as e:
        handle_error(f"Failed to perform correlation analysis: {e}", ctx.obj.get('verbose', False))