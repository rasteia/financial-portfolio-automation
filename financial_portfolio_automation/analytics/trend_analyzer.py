"""
Trend Analyzer for historical performance analysis.

This module analyzes historical portfolio data to identify trends,
patterns, and performance characteristics over time.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import math
import logging
from statistics import mean, stdev

from ..models.core import PortfolioSnapshot


class TrendAnalyzer:
    """
    Analyzer for historical portfolio trends and patterns.
    
    Provides methods to analyze historical data and identify trends,
    seasonal patterns, and performance characteristics.
    """
    
    def __init__(self, data_store):
        """
        Initialize trend analyzer.
        
        Args:
            data_store: Data storage interface
        """
        self.data_store = data_store
        self.logger = logging.getLogger(__name__)
    
    def analyze_trends(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """
        Analyze comprehensive trends from portfolio snapshots.
        
        Args:
            snapshots: List of portfolio snapshots
            
        Returns:
            Dictionary containing trend analysis results
        """
        if len(snapshots) < 2:
            return {}
        
        try:
            # Basic trend metrics
            basic_trends = self._analyze_basic_trends(snapshots)
            
            # Performance trends
            performance_trends = self._analyze_performance_trends(snapshots)
            
            # Volatility trends
            volatility_trends = self._analyze_volatility_trends(snapshots)
            
            # Growth trends
            growth_trends = self._analyze_growth_trends(snapshots)
            
            # Seasonal patterns
            seasonal_patterns = self._analyze_seasonal_patterns(snapshots)
            
            return {
                'analysis_period': {
                    'start_date': snapshots[0].timestamp.date().isoformat(),
                    'end_date': snapshots[-1].timestamp.date().isoformat(),
                    'total_days': (snapshots[-1].timestamp.date() - snapshots[0].timestamp.date()).days,
                    'data_points': len(snapshots)
                },
                'basic_trends': basic_trends,
                'performance_trends': performance_trends,
                'volatility_trends': volatility_trends,
                'growth_trends': growth_trends,
                'seasonal_patterns': seasonal_patterns
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            return {}
    
    def _analyze_basic_trends(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Analyze basic portfolio trends."""
        values = [float(s.total_value) for s in snapshots]
        dates = [s.timestamp.date() for s in snapshots]
        
        # Calculate trend direction
        start_value = values[0]
        end_value = values[-1]
        total_change = end_value - start_value
        total_change_pct = (total_change / start_value * 100) if start_value > 0 else 0
        
        # Calculate trend slope (linear regression)
        trend_slope = self._calculate_trend_slope(values)
        
        # Determine trend direction
        if trend_slope > 0.01:
            trend_direction = "Upward"
        elif trend_slope < -0.01:
            trend_direction = "Downward"
        else:
            trend_direction = "Sideways"
        
        # Calculate trend strength (R-squared)
        trend_strength = self._calculate_trend_strength(values)
        
        return {
            'start_value': start_value,
            'end_value': end_value,
            'total_change': total_change,
            'total_change_pct': total_change_pct,
            'trend_direction': trend_direction,
            'trend_slope': trend_slope,
            'trend_strength': trend_strength,
            'highest_value': max(values),
            'lowest_value': min(values),
            'average_value': mean(values)
        }
    
    def _analyze_performance_trends(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(snapshots)):
            prev_value = float(snapshots[i-1].total_value)
            curr_value = float(snapshots[i].total_value)
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                daily_returns.append(daily_return)
        
        if not daily_returns:
            return {}
        
        # Calculate performance metrics
        avg_daily_return = mean(daily_returns)
        return_volatility = stdev(daily_returns) if len(daily_returns) > 1 else 0
        
        # Annualize metrics
        avg_annual_return = avg_daily_return * 252
        annual_volatility = return_volatility * math.sqrt(252)
        
        # Calculate win rate
        positive_days = sum(1 for r in daily_returns if r > 0)
        win_rate = positive_days / len(daily_returns) * 100
        
        # Calculate best and worst days
        best_day = max(daily_returns) * 100
        worst_day = min(daily_returns) * 100
        
        # Calculate consecutive performance streaks
        win_streak, loss_streak = self._calculate_performance_streaks(daily_returns)
        
        return {
            'avg_daily_return_pct': avg_daily_return * 100,
            'avg_annual_return_pct': avg_annual_return * 100,
            'daily_volatility_pct': return_volatility * 100,
            'annual_volatility_pct': annual_volatility * 100,
            'win_rate_pct': win_rate,
            'best_day_pct': best_day,
            'worst_day_pct': worst_day,
            'max_win_streak': win_streak,
            'max_loss_streak': loss_streak,
            'sharpe_ratio': (avg_annual_return / annual_volatility) if annual_volatility > 0 else 0
        }
    
    def _analyze_volatility_trends(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Analyze volatility trends over time."""
        if len(snapshots) < 10:  # Need minimum data for volatility analysis
            return {}
        
        # Calculate rolling volatility (10-day windows)
        window_size = min(10, len(snapshots) // 3)
        rolling_volatilities = []
        
        for i in range(window_size, len(snapshots)):
            window_snapshots = snapshots[i-window_size:i]
            window_returns = []
            
            for j in range(1, len(window_snapshots)):
                prev_val = float(window_snapshots[j-1].total_value)
                curr_val = float(window_snapshots[j].total_value)
                
                if prev_val > 0:
                    ret = (curr_val - prev_val) / prev_val
                    window_returns.append(ret)
            
            if len(window_returns) > 1:
                window_vol = stdev(window_returns) * math.sqrt(252) * 100
                rolling_volatilities.append(window_vol)
        
        if not rolling_volatilities:
            return {}
        
        # Analyze volatility trends
        avg_volatility = mean(rolling_volatilities)
        min_volatility = min(rolling_volatilities)
        max_volatility = max(rolling_volatilities)
        
        # Calculate volatility trend
        vol_trend_slope = self._calculate_trend_slope(rolling_volatilities)
        
        if vol_trend_slope > 0.1:
            vol_trend = "Increasing"
        elif vol_trend_slope < -0.1:
            vol_trend = "Decreasing"
        else:
            vol_trend = "Stable"
        
        return {
            'average_volatility_pct': avg_volatility,
            'min_volatility_pct': min_volatility,
            'max_volatility_pct': max_volatility,
            'volatility_trend': vol_trend,
            'volatility_trend_slope': vol_trend_slope,
            'current_volatility_pct': rolling_volatilities[-1] if rolling_volatilities else 0
        }
    
    def _analyze_growth_trends(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Analyze portfolio growth trends."""
        values = [float(s.total_value) for s in snapshots]
        
        if len(values) < 3:
            return {}
        
        # Calculate growth phases
        growth_phases = self._identify_growth_phases(values)
        
        # Calculate compound annual growth rate (CAGR)
        days_total = (snapshots[-1].timestamp.date() - snapshots[0].timestamp.date()).days
        if days_total > 0:
            years = days_total / 365.25
            cagr = (values[-1] / values[0]) ** (1 / years) - 1 if years > 0 and values[0] > 0 else 0
        else:
            cagr = 0
        
        # Calculate maximum drawdown periods
        drawdown_periods = self._calculate_drawdown_periods(values)
        
        # Calculate recovery times
        recovery_analysis = self._analyze_recovery_times(values)
        
        return {
            'cagr_pct': cagr * 100,
            'growth_phases': growth_phases,
            'drawdown_periods': drawdown_periods,
            'recovery_analysis': recovery_analysis,
            'growth_consistency': self._calculate_growth_consistency(values)
        }
    
    def _analyze_seasonal_patterns(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns in performance."""
        if len(snapshots) < 30:  # Need sufficient data
            return {}
        
        # Group by month
        monthly_returns = {}
        for i in range(1, len(snapshots)):
            prev_snapshot = snapshots[i-1]
            curr_snapshot = snapshots[i]
            
            month = curr_snapshot.timestamp.month
            
            prev_val = float(prev_snapshot.total_value)
            curr_val = float(curr_snapshot.total_value)
            
            if prev_val > 0:
                daily_return = (curr_val - prev_val) / prev_val
                
                if month not in monthly_returns:
                    monthly_returns[month] = []
                
                monthly_returns[month].append(daily_return)
        
        # Calculate monthly performance
        monthly_performance = {}
        month_names = [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ]
        
        for month, returns in monthly_returns.items():
            if returns:
                avg_return = mean(returns) * 100
                monthly_performance[month_names[month-1]] = {
                    'avg_daily_return_pct': avg_return,
                    'total_days': len(returns),
                    'win_rate_pct': sum(1 for r in returns if r > 0) / len(returns) * 100
                }
        
        # Group by day of week
        weekday_returns = {}
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for i in range(1, len(snapshots)):
            prev_snapshot = snapshots[i-1]
            curr_snapshot = snapshots[i]
            
            weekday = curr_snapshot.timestamp.weekday()
            
            prev_val = float(prev_snapshot.total_value)
            curr_val = float(curr_snapshot.total_value)
            
            if prev_val > 0:
                daily_return = (curr_val - prev_val) / prev_val
                
                if weekday not in weekday_returns:
                    weekday_returns[weekday] = []
                
                weekday_returns[weekday].append(daily_return)
        
        # Calculate weekday performance
        weekday_performance = {}
        for weekday, returns in weekday_returns.items():
            if returns:
                avg_return = mean(returns) * 100
                weekday_performance[weekday_names[weekday]] = {
                    'avg_daily_return_pct': avg_return,
                    'total_days': len(returns),
                    'win_rate_pct': sum(1 for r in returns if r > 0) / len(returns) * 100
                }
        
        return {
            'monthly_performance': monthly_performance,
            'weekday_performance': weekday_performance,
            'best_month': max(monthly_performance.items(), key=lambda x: x[1]['avg_daily_return_pct'])[0] if monthly_performance else None,
            'worst_month': min(monthly_performance.items(), key=lambda x: x[1]['avg_daily_return_pct'])[0] if monthly_performance else None,
            'best_weekday': max(weekday_performance.items(), key=lambda x: x[1]['avg_daily_return_pct'])[0] if weekday_performance else None,
            'worst_weekday': min(weekday_performance.items(), key=lambda x: x[1]['avg_daily_return_pct'])[0] if weekday_performance else None
        }
    
    def _calculate_trend_slope(self, values: List[float]) -> float:
        """Calculate linear trend slope using least squares."""
        n = len(values)
        if n < 2:
            return 0
        
        x_values = list(range(n))
        
        # Calculate means
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        # Calculate slope
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0
    
    def _calculate_trend_strength(self, values: List[float]) -> float:
        """Calculate trend strength using R-squared."""
        n = len(values)
        if n < 2:
            return 0
        
        # Calculate linear regression
        x_values = list(range(n))
        slope = self._calculate_trend_slope(values)
        
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        # Calculate intercept
        intercept = y_mean - slope * x_mean
        
        # Calculate R-squared
        ss_res = sum((values[i] - (slope * x_values[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        
        return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    def _calculate_performance_streaks(
        self, 
        daily_returns: List[float]
    ) -> Tuple[int, int]:
        """Calculate maximum winning and losing streaks."""
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for return_val in daily_returns:
            if return_val > 0:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif return_val < 0:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
            else:
                current_win_streak = 0
                current_loss_streak = 0
        
        return max_win_streak, max_loss_streak
    
    def _identify_growth_phases(self, values: List[float]) -> List[Dict[str, Any]]:
        """Identify distinct growth phases in the portfolio."""
        if len(values) < 5:
            return []
        
        phases = []
        phase_start = 0
        
        # Simple phase detection based on trend changes
        window_size = max(3, len(values) // 10)
        
        for i in range(window_size, len(values) - window_size):
            # Calculate trend before and after current point
            before_trend = self._calculate_trend_slope(values[i-window_size:i])
            after_trend = self._calculate_trend_slope(values[i:i+window_size])
            
            # Detect significant trend change
            if abs(before_trend - after_trend) > 0.5:  # Threshold for trend change
                # End current phase
                if i - phase_start >= window_size:
                    phase_values = values[phase_start:i]
                    phase_return = (phase_values[-1] - phase_values[0]) / phase_values[0] * 100 if phase_values[0] > 0 else 0
                    
                    phases.append({
                        'start_index': phase_start,
                        'end_index': i,
                        'duration_days': i - phase_start,
                        'return_pct': phase_return,
                        'trend': 'Growth' if phase_return > 0 else 'Decline'
                    })
                
                phase_start = i
        
        # Add final phase
        if len(values) - phase_start >= window_size:
            phase_values = values[phase_start:]
            phase_return = (phase_values[-1] - phase_values[0]) / phase_values[0] * 100 if phase_values[0] > 0 else 0
            
            phases.append({
                'start_index': phase_start,
                'end_index': len(values) - 1,
                'duration_days': len(values) - 1 - phase_start,
                'return_pct': phase_return,
                'trend': 'Growth' if phase_return > 0 else 'Decline'
            })
        
        return phases
    
    def _calculate_drawdown_periods(self, values: List[float]) -> List[Dict[str, Any]]:
        """Calculate drawdown periods and their characteristics."""
        drawdowns = []
        peak = values[0]
        peak_index = 0
        in_drawdown = False
        drawdown_start = 0
        
        for i, value in enumerate(values):
            if value > peak:
                # New peak - end any current drawdown
                if in_drawdown:
                    max_dd_pct = (peak - min(values[drawdown_start:i])) / peak * 100
                    recovery_days = i - drawdown_start
                    
                    drawdowns.append({
                        'start_index': drawdown_start,
                        'end_index': i,
                        'duration_days': recovery_days,
                        'max_drawdown_pct': max_dd_pct,
                        'peak_value': peak,
                        'trough_value': min(values[drawdown_start:i])
                    })
                    
                    in_drawdown = False
                
                peak = value
                peak_index = i
            
            elif value < peak * 0.99:  # 1% threshold for drawdown
                if not in_drawdown:
                    in_drawdown = True
                    drawdown_start = peak_index
        
        # Handle ongoing drawdown
        if in_drawdown:
            max_dd_pct = (peak - min(values[drawdown_start:])) / peak * 100
            
            drawdowns.append({
                'start_index': drawdown_start,
                'end_index': len(values) - 1,
                'duration_days': len(values) - 1 - drawdown_start,
                'max_drawdown_pct': max_dd_pct,
                'peak_value': peak,
                'trough_value': min(values[drawdown_start:]),
                'ongoing': True
            })
        
        return drawdowns
    
    def _analyze_recovery_times(self, values: List[float]) -> Dict[str, Any]:
        """Analyze recovery times from drawdowns."""
        drawdown_periods = self._calculate_drawdown_periods(values)
        
        if not drawdown_periods:
            return {}
        
        completed_recoveries = [
            dd for dd in drawdown_periods 
            if not dd.get('ongoing', False)
        ]
        
        if not completed_recoveries:
            return {'no_completed_recoveries': True}
        
        recovery_times = [dd['duration_days'] for dd in completed_recoveries]
        max_drawdowns = [dd['max_drawdown_pct'] for dd in completed_recoveries]
        
        return {
            'average_recovery_days': mean(recovery_times),
            'max_recovery_days': max(recovery_times),
            'min_recovery_days': min(recovery_times),
            'average_max_drawdown_pct': mean(max_drawdowns),
            'worst_drawdown_pct': max(max_drawdowns),
            'total_drawdown_periods': len(completed_recoveries)
        }
    
    def _calculate_growth_consistency(self, values: List[float]) -> float:
        """Calculate growth consistency score (0-100)."""
        if len(values) < 2:
            return 0
        
        # Calculate monthly returns (approximate)
        monthly_points = max(1, len(values) // 30)
        monthly_values = values[::monthly_points]
        
        if len(monthly_values) < 2:
            return 0
        
        monthly_returns = []
        for i in range(1, len(monthly_values)):
            if monthly_values[i-1] > 0:
                ret = (monthly_values[i] - monthly_values[i-1]) / monthly_values[i-1]
                monthly_returns.append(ret)
        
        if not monthly_returns:
            return 0
        
        # Consistency is inverse of coefficient of variation
        avg_return = mean(monthly_returns)
        return_std = stdev(monthly_returns) if len(monthly_returns) > 1 else 0
        
        if return_std == 0:
            return 100 if avg_return >= 0 else 0
        
        cv = abs(return_std / avg_return) if avg_return != 0 else float('inf')
        consistency_score = max(0, 100 - cv * 100)
        
        return min(100, consistency_score)