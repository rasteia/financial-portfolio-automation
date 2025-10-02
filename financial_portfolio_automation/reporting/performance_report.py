"""
Performance Report Generator.

This module generates comprehensive portfolio performance reports including
risk-adjusted metrics, benchmark comparisons, and asset allocation analysis.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import math

from ..models.core import PortfolioSnapshot, Position
from ..data.store import DataStore
from ..analysis.portfolio_analyzer import PortfolioAnalyzer


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal
    sortino_ratio: Decimal
    beta: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    information_ratio: Optional[Decimal] = None
    tracking_error: Optional[Decimal] = None


@dataclass
class PeriodPerformance:
    """Performance metrics for a specific period."""
    period_name: str
    start_date: date
    end_date: date
    return_pct: Decimal
    benchmark_return_pct: Optional[Decimal] = None
    excess_return_pct: Optional[Decimal] = None


@dataclass
class AssetAllocation:
    """Asset allocation breakdown."""
    symbol: str
    weight: Decimal
    value: Decimal
    return_contribution: Decimal
    sector: Optional[str] = None
    asset_class: Optional[str] = None


class PerformanceReport:
    """
    Portfolio performance report generator.
    
    Generates comprehensive performance analysis including risk-adjusted
    metrics, benchmark comparisons, and detailed attribution analysis.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        portfolio_analyzer: PortfolioAnalyzer
    ):
        """
        Initialize performance report generator.
        
        Args:
            data_store: Data storage interface
            portfolio_analyzer: Portfolio analysis engine
        """
        self.data_store = data_store
        self.portfolio_analyzer = portfolio_analyzer
        self.logger = logging.getLogger(__name__)
    
    def generate_data(
        self,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
        benchmark_symbol: Optional[str] = None,
        include_charts: bool = True
    ) -> Dict[str, Any]:
        """
        Generate performance report data.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            symbols: Optional symbol filter
            benchmark_symbol: Benchmark for comparison
            include_charts: Whether to include chart data
            
        Returns:
            Dictionary containing all report data
        """
        self.logger.info(
            f"Generating performance report data: {start_date} to {end_date}"
        )
        
        # Get portfolio snapshots
        snapshots = self._get_portfolio_snapshots(start_date, end_date)
        
        if not snapshots:
            raise ValueError("No portfolio data found for specified period")
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(
            snapshots, benchmark_symbol
        )
        
        # Get period performance breakdown
        period_performance = self._calculate_period_performance(
            snapshots, benchmark_symbol
        )
        
        # Get asset allocation analysis
        allocation = self._calculate_asset_allocation(
            snapshots[-1], symbols
        )
        
        # Get drawdown analysis
        drawdown_data = self._calculate_drawdown_analysis(snapshots)
        
        # Prepare chart data if requested
        chart_data = {}
        if include_charts:
            chart_data = self._prepare_chart_data(
                snapshots, benchmark_symbol
            )
        
        return {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': start_date,
                'end_date': end_date,
                'benchmark_symbol': benchmark_symbol,
                'symbols_filter': symbols
            },
            'portfolio_summary': {
                'start_value': snapshots[0].total_value,
                'end_value': snapshots[-1].total_value,
                'total_return': metrics.total_return,
                'total_return_pct': (
                    metrics.total_return / snapshots[0].total_value * 100
                )
            },
            'performance_metrics': metrics,
            'period_performance': period_performance,
            'asset_allocation': allocation,
            'drawdown_analysis': drawdown_data,
            'chart_data': chart_data
        }
    
    def _get_portfolio_snapshots(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[PortfolioSnapshot]:
        """Get portfolio snapshots for the specified period."""
        return self.data_store.get_portfolio_snapshots(
            start_date=start_date,
            end_date=end_date
        )
    
    def _calculate_performance_metrics(
        self,
        snapshots: List[PortfolioSnapshot],
        benchmark_symbol: Optional[str] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if len(snapshots) < 2:
            raise ValueError("Insufficient data for performance calculation")
        
        # Calculate returns
        returns = self._calculate_returns(snapshots)
        
        # Basic metrics
        total_return = snapshots[-1].total_value - snapshots[0].total_value
        days = (snapshots[-1].timestamp.date() - snapshots[0].timestamp.date()).days
        annualized_return = self._annualize_return(total_return, snapshots[0].total_value, days)
        
        # Risk metrics
        volatility = self._calculate_volatility(returns)
        max_drawdown = self._calculate_max_drawdown(snapshots)
        
        # Risk-adjusted metrics
        sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
        calmar_ratio = self._calculate_calmar_ratio(annualized_return, max_drawdown)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        
        # Benchmark-relative metrics
        beta = None
        alpha = None
        information_ratio = None
        tracking_error = None
        
        if benchmark_symbol:
            benchmark_data = self._get_benchmark_data(
                benchmark_symbol, snapshots[0].timestamp.date(), 
                snapshots[-1].timestamp.date()
            )
            if benchmark_data:
                beta = self._calculate_beta(returns, benchmark_data)
                alpha = self._calculate_alpha(
                    annualized_return, benchmark_data, beta
                )
                tracking_error = self._calculate_tracking_error(
                    returns, benchmark_data
                )
                information_ratio = self._calculate_information_ratio(
                    returns, benchmark_data, tracking_error
                )
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            tracking_error=tracking_error
        )
    
    def _calculate_period_performance(
        self,
        snapshots: List[PortfolioSnapshot],
        benchmark_symbol: Optional[str] = None
    ) -> List[PeriodPerformance]:
        """Calculate performance for different time periods."""
        periods = []
        end_date = snapshots[-1].timestamp.date()
        
        # Define standard periods
        period_configs = [
            ("1 Month", 30),
            ("3 Months", 90),
            ("6 Months", 180),
            ("1 Year", 365),
            ("YTD", None)  # Year to date
        ]
        
        for period_name, days_back in period_configs:
            if period_name == "YTD":
                start_date = date(end_date.year, 1, 1)
            else:
                start_date = end_date - timedelta(days=days_back)
            
            # Find snapshots for this period
            period_snapshots = [
                s for s in snapshots 
                if s.timestamp.date() >= start_date
            ]
            
            if len(period_snapshots) >= 2:
                start_value = period_snapshots[0].total_value
                end_value = period_snapshots[-1].total_value
                return_pct = (end_value - start_value) / start_value * 100
                
                # Get benchmark return if available
                benchmark_return_pct = None
                excess_return_pct = None
                
                if benchmark_symbol:
                    benchmark_data = self._get_benchmark_data(
                        benchmark_symbol, start_date, end_date
                    )
                    if benchmark_data:
                        benchmark_return_pct = (
                            benchmark_data[-1] - benchmark_data[0]
                        ) / benchmark_data[0] * 100
                        excess_return_pct = return_pct - benchmark_return_pct
                
                periods.append(PeriodPerformance(
                    period_name=period_name,
                    start_date=start_date,
                    end_date=end_date,
                    return_pct=Decimal(str(return_pct)),
                    benchmark_return_pct=Decimal(str(benchmark_return_pct)) if benchmark_return_pct else None,
                    excess_return_pct=Decimal(str(excess_return_pct)) if excess_return_pct else None
                ))
        
        return periods
    
    def _calculate_asset_allocation(
        self,
        latest_snapshot: PortfolioSnapshot,
        symbols_filter: Optional[List[str]] = None
    ) -> List[AssetAllocation]:
        """Calculate current asset allocation breakdown."""
        allocations = []
        total_value = latest_snapshot.total_value
        
        positions = latest_snapshot.positions
        if symbols_filter:
            positions = [p for p in positions if p.symbol in symbols_filter]
        
        for position in positions:
            weight = position.market_value / total_value * 100
            
            # Calculate return contribution (simplified)
            return_contribution = position.day_pnl / total_value * 100
            
            allocations.append(AssetAllocation(
                symbol=position.symbol,
                weight=Decimal(str(weight)),
                value=position.market_value,
                return_contribution=Decimal(str(return_contribution)),
                sector=self._get_symbol_sector(position.symbol),
                asset_class=self._get_asset_class(position.symbol)
            ))
        
        return sorted(allocations, key=lambda a: a.weight, reverse=True)
    
    def _calculate_drawdown_analysis(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Calculate detailed drawdown analysis."""
        values = [float(s.total_value) for s in snapshots]
        dates = [s.timestamp.date() for s in snapshots]
        
        # Calculate running maximum
        running_max = []
        current_max = values[0]
        
        for value in values:
            current_max = max(current_max, value)
            running_max.append(current_max)
        
        # Calculate drawdowns
        drawdowns = [
            (value - peak) / peak * 100 
            for value, peak in zip(values, running_max)
        ]
        
        # Find maximum drawdown
        max_dd_idx = drawdowns.index(min(drawdowns))
        max_drawdown = abs(drawdowns[max_dd_idx])
        
        # Find drawdown periods
        drawdown_periods = []
        in_drawdown = False
        start_idx = 0
        
        for i, dd in enumerate(drawdowns):
            if dd < -0.01 and not in_drawdown:  # Start of drawdown (>1%)
                in_drawdown = True
                start_idx = i
            elif dd >= -0.01 and in_drawdown:  # End of drawdown
                in_drawdown = False
                drawdown_periods.append({
                    'start_date': dates[start_idx],
                    'end_date': dates[i-1],
                    'duration_days': (dates[i-1] - dates[start_idx]).days,
                    'max_drawdown_pct': abs(min(drawdowns[start_idx:i]))
                })
        
        return {
            'max_drawdown_pct': max_drawdown,
            'max_drawdown_date': dates[max_dd_idx],
            'current_drawdown_pct': abs(drawdowns[-1]) if drawdowns[-1] < 0 else 0,
            'drawdown_periods': drawdown_periods,
            'avg_drawdown_duration': (
                sum(p['duration_days'] for p in drawdown_periods) / 
                len(drawdown_periods) if drawdown_periods else 0
            )
        }
    
    def _prepare_chart_data(
        self,
        snapshots: List[PortfolioSnapshot],
        benchmark_symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare data for charts and visualizations."""
        dates = [s.timestamp.date().isoformat() for s in snapshots]
        values = [float(s.total_value) for s in snapshots]
        
        # Normalize to base 100 for comparison
        base_value = values[0]
        normalized_values = [v / base_value * 100 for v in values]
        
        chart_data = {
            'portfolio_value': {
                'dates': dates,
                'values': values,
                'normalized_values': normalized_values
            },
            'daily_returns': {
                'dates': dates[1:],
                'returns': [
                    (values[i] - values[i-1]) / values[i-1] * 100
                    for i in range(1, len(values))
                ]
            }
        }
        
        # Add benchmark data if available
        if benchmark_symbol:
            benchmark_data = self._get_benchmark_data(
                benchmark_symbol, 
                snapshots[0].timestamp.date(),
                snapshots[-1].timestamp.date()
            )
            if benchmark_data:
                benchmark_normalized = [
                    v / benchmark_data[0] * 100 for v in benchmark_data
                ]
                chart_data['benchmark'] = {
                    'dates': dates,
                    'normalized_values': benchmark_normalized
                }
        
        return chart_data
    
    def _calculate_returns(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> List[float]:
        """Calculate daily returns from portfolio snapshots."""
        returns = []
        for i in range(1, len(snapshots)):
            prev_value = float(snapshots[i-1].total_value)
            curr_value = float(snapshots[i].total_value)
            daily_return = (curr_value - prev_value) / prev_value
            returns.append(daily_return)
        return returns
    
    def _annualize_return(
        self, 
        total_return: Decimal, 
        initial_value: Decimal, 
        days: int
    ) -> Decimal:
        """Annualize return based on time period."""
        if days == 0:
            return Decimal('0')
        
        total_return_pct = float(total_return) / float(initial_value)
        annualized = (1 + total_return_pct) ** (365.25 / days) - 1
        return Decimal(str(annualized * 100))
    
    def _calculate_volatility(self, returns: List[float]) -> Decimal:
        """Calculate annualized volatility."""
        if len(returns) < 2:
            return Decimal('0')
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        daily_vol = math.sqrt(variance)
        annualized_vol = daily_vol * math.sqrt(252)  # 252 trading days
        return Decimal(str(annualized_vol * 100))
    
    def _calculate_max_drawdown(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Decimal:
        """Calculate maximum drawdown."""
        values = [float(s.total_value) for s in snapshots]
        
        max_dd = 0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        
        return Decimal(str(max_dd * 100))
    
    def _calculate_sharpe_ratio(
        self, 
        returns: List[float], 
        volatility: Decimal
    ) -> Decimal:
        """Calculate Sharpe ratio (assuming 0% risk-free rate)."""
        if float(volatility) == 0:
            return Decimal('0')
        
        mean_return = sum(returns) / len(returns) if returns else 0
        annualized_return = mean_return * 252  # 252 trading days
        
        sharpe = annualized_return / (float(volatility) / 100)
        return Decimal(str(sharpe))
    
    def _calculate_calmar_ratio(
        self, 
        annualized_return: Decimal, 
        max_drawdown: Decimal
    ) -> Decimal:
        """Calculate Calmar ratio."""
        if float(max_drawdown) == 0:
            return Decimal('0')
        
        calmar = float(annualized_return) / float(max_drawdown)
        return Decimal(str(calmar))
    
    def _calculate_sortino_ratio(self, returns: List[float]) -> Decimal:
        """Calculate Sortino ratio (downside deviation)."""
        if not returns:
            return Decimal('0')
        
        mean_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return Decimal('0')
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_deviation = math.sqrt(downside_variance) * math.sqrt(252)
        
        if downside_deviation == 0:
            return Decimal('0')
        
        sortino = (mean_return * 252) / downside_deviation
        return Decimal(str(sortino))
    
    def _get_benchmark_data(
        self, 
        symbol: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[List[float]]:
        """Get benchmark price data for comparison."""
        # This would fetch benchmark data from the data store
        # For now, return None to indicate no benchmark data available
        return None
    
    def _calculate_beta(
        self, 
        portfolio_returns: List[float], 
        benchmark_returns: List[float]
    ) -> Optional[Decimal]:
        """Calculate portfolio beta relative to benchmark."""
        # Implementation would calculate covariance and variance
        # For now, return None
        return None
    
    def _calculate_alpha(
        self, 
        portfolio_return: Decimal, 
        benchmark_returns: List[float], 
        beta: Optional[Decimal]
    ) -> Optional[Decimal]:
        """Calculate portfolio alpha."""
        # Implementation would use CAPM formula
        # For now, return None
        return None
    
    def _calculate_tracking_error(
        self, 
        portfolio_returns: List[float], 
        benchmark_returns: List[float]
    ) -> Optional[Decimal]:
        """Calculate tracking error."""
        # Implementation would calculate standard deviation of excess returns
        # For now, return None
        return None
    
    def _calculate_information_ratio(
        self, 
        portfolio_returns: List[float], 
        benchmark_returns: List[float], 
        tracking_error: Optional[Decimal]
    ) -> Optional[Decimal]:
        """Calculate information ratio."""
        # Implementation would calculate excess return / tracking error
        # For now, return None
        return None
    
    def _get_symbol_sector(self, symbol: str) -> Optional[str]:
        """Get sector classification for symbol."""
        # This would lookup sector information
        # For now, return None
        return None
    
    def _get_asset_class(self, symbol: str) -> Optional[str]:
        """Get asset class for symbol."""
        # This would classify the asset (equity, bond, etc.)
        # For now, return "Equity" as default
        return "Equity"