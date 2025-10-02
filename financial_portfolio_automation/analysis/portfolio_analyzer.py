"""
Portfolio Analyzer module for calculating portfolio metrics and performance analysis.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import math

from ..models.core import Position, PortfolioSnapshot

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    """
    Portfolio analyzer class for calculating portfolio metrics, risk measures,
    and performance attribution analysis.
    """
    
    def __init__(self):
        """Initialize the PortfolioAnalyzer class."""
        self.logger = logger
        self.risk_free_rate = 0.02  # Default 2% annual risk-free rate
    
    def set_risk_free_rate(self, rate: float) -> None:
        """
        Set the risk-free rate for calculations.
        
        Args:
            rate: Annual risk-free rate as a decimal (e.g., 0.02 for 2%)
        """
        if rate < 0:
            raise ValueError("Risk-free rate cannot be negative")
        self.risk_free_rate = rate
    
    def calculate_portfolio_value_and_allocation(self, portfolio: PortfolioSnapshot) -> Dict[str, any]:
        """
        Calculate portfolio value and allocation metrics.
        
        Args:
            portfolio: Portfolio snapshot
            
        Returns:
            Dictionary containing portfolio value and allocation metrics
        """
        try:
            total_value = float(portfolio.total_value)
            total_long_value = sum(float(pos.market_value) for pos in portfolio.long_positions)
            total_short_value = sum(float(pos.market_value) for pos in portfolio.short_positions)
            
            # Calculate allocations
            allocations = {}
            for position in portfolio.positions:
                symbol = position.symbol
                # For short positions, market value contributes negatively to total
                effective_market_value = float(position.market_value) if position.is_long() else -float(position.market_value)
                allocation_pct = float(abs(position.market_value) / portfolio.total_value * 100) if portfolio.total_value > 0 else 0
                allocations[symbol] = {
                    'market_value': effective_market_value,
                    'allocation_percent': allocation_pct,
                    'quantity': position.quantity,
                    'unrealized_pnl': float(position.unrealized_pnl),
                    'day_pnl': float(position.day_pnl),
                    'position_type': 'long' if position.is_long() else 'short'
                }
            
            # Calculate concentration metrics
            allocation_values = [abs(alloc['allocation_percent']) for alloc in allocations.values()]
            max_allocation = max(allocation_values) if allocation_values else 0
            
            # Calculate Herfindahl-Hirschman Index (HHI) for concentration
            hhi = sum((alloc / 100) ** 2 for alloc in allocation_values) if allocation_values else 0
            
            return {
                'total_value': total_value,
                'total_long_value': total_long_value,
                'total_short_value': total_short_value,
                'net_value': total_long_value - total_short_value,
                'buying_power': float(portfolio.buying_power),
                'day_pnl': float(portfolio.day_pnl),
                'total_pnl': float(portfolio.total_pnl),
                'position_count': portfolio.position_count,
                'long_position_count': len(portfolio.long_positions),
                'short_position_count': len(portfolio.short_positions),
                'allocations': allocations,
                'max_allocation_percent': max_allocation,
                'concentration_hhi': hhi,
                'diversification_ratio': 1 / math.sqrt(hhi) if hhi > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio value and allocation: {e}")
            raise
    
    def calculate_risk_metrics(self, portfolio_snapshots: List[PortfolioSnapshot], 
                             market_returns: Optional[List[float]] = None) -> Dict[str, float]:
        """
        Calculate portfolio risk metrics including beta, volatility, and Sharpe ratio.
        
        Args:
            portfolio_snapshots: List of portfolio snapshots over time
            market_returns: Optional list of market returns for beta calculation
            
        Returns:
            Dictionary containing risk metrics
        """
        try:
            if len(portfolio_snapshots) < 2:
                raise ValueError("Need at least 2 portfolio snapshots for risk calculations")
            
            # Calculate portfolio returns
            portfolio_values = [float(snapshot.total_value) for snapshot in portfolio_snapshots]
            portfolio_returns = []
            
            for i in range(1, len(portfolio_values)):
                if portfolio_values[i - 1] > 0:
                    return_pct = (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
                    portfolio_returns.append(return_pct)
                else:
                    portfolio_returns.append(0.0)
            
            if not portfolio_returns:
                raise ValueError("Unable to calculate portfolio returns")
            
            # Calculate basic statistics
            mean_return = np.mean(portfolio_returns)
            volatility = np.std(portfolio_returns, ddof=1) if len(portfolio_returns) > 1 else 0
            
            # Annualize metrics (assuming daily returns)
            annual_return = mean_return * 252  # 252 trading days per year
            annual_volatility = volatility * np.sqrt(252)
            
            # Calculate Sharpe ratio
            excess_return = annual_return - self.risk_free_rate
            sharpe_ratio = excess_return / annual_volatility if annual_volatility > 0 else 0
            
            # Calculate beta if market returns provided
            beta = None
            correlation = None
            if market_returns and len(market_returns) == len(portfolio_returns):
                if len(portfolio_returns) > 1:
                    correlation = np.corrcoef(portfolio_returns, market_returns)[0, 1]
                    market_volatility = np.std(market_returns, ddof=1)
                    if market_volatility > 0:
                        beta = correlation * (volatility / market_volatility)
                    else:
                        beta = 0
            
            # Calculate Value at Risk (VaR) - 95% confidence level
            var_95 = np.percentile(portfolio_returns, 5) if len(portfolio_returns) > 0 else 0
            
            # Calculate maximum drawdown
            max_drawdown = self._calculate_max_drawdown(portfolio_values)
            
            # Calculate downside deviation
            negative_returns = [r for r in portfolio_returns if r < 0]
            downside_deviation = np.std(negative_returns, ddof=1) if len(negative_returns) > 1 else 0
            annual_downside_deviation = downside_deviation * np.sqrt(252)
            
            # Calculate Sortino ratio
            sortino_ratio = excess_return / annual_downside_deviation if annual_downside_deviation > 0 else 0
            
            return {
                'mean_daily_return': mean_return,
                'daily_volatility': volatility,
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'beta': beta,
                'correlation_with_market': correlation,
                'var_95_daily': var_95,
                'max_drawdown': max_drawdown,
                'downside_deviation': annual_downside_deviation,
                'calmar_ratio': annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            raise
    
    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """
        Calculate maximum drawdown from a series of portfolio values.
        
        Args:
            values: List of portfolio values
            
        Returns:
            Maximum drawdown as a percentage
        """
        if len(values) < 2:
            return 0.0
        
        peak = values[0]
        max_drawdown = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def calculate_performance_attribution(self, portfolio_snapshots: List[PortfolioSnapshot]) -> Dict[str, any]:
        """
        Calculate performance attribution by position.
        
        Args:
            portfolio_snapshots: List of portfolio snapshots over time
            
        Returns:
            Dictionary containing performance attribution analysis
        """
        try:
            if len(portfolio_snapshots) < 2:
                raise ValueError("Need at least 2 portfolio snapshots for performance attribution")
            
            first_snapshot = portfolio_snapshots[0]
            last_snapshot = portfolio_snapshots[-1]
            
            # Calculate total portfolio return
            initial_value = float(first_snapshot.total_value)
            final_value = float(last_snapshot.total_value)
            total_return = (final_value - initial_value) / initial_value if initial_value > 0 else 0
            
            # Calculate contribution by position
            position_contributions = {}
            
            # Get all unique symbols across snapshots
            all_symbols = set()
            for snapshot in portfolio_snapshots:
                all_symbols.update(pos.symbol for pos in snapshot.positions)
            
            for symbol in all_symbols:
                # Find position in first and last snapshots
                initial_pos = first_snapshot.get_position(symbol)
                final_pos = last_snapshot.get_position(symbol)
                
                initial_value = float(initial_pos.market_value) if initial_pos else 0
                final_value = float(final_pos.market_value) if final_pos else 0
                
                # Calculate position return
                position_return = (final_value - initial_value) / abs(initial_value) if initial_value != 0 else 0
                
                # Calculate contribution to total return
                initial_weight = abs(initial_value) / float(first_snapshot.total_value) if first_snapshot.total_value > 0 else 0
                contribution = initial_weight * position_return
                
                position_contributions[symbol] = {
                    'initial_value': initial_value,
                    'final_value': final_value,
                    'absolute_change': final_value - initial_value,
                    'position_return': position_return,
                    'initial_weight': initial_weight,
                    'contribution_to_return': contribution,
                    'contribution_percent': contribution / total_return * 100 if total_return != 0 else 0
                }
            
            # Calculate sector/category attribution if available
            # This is a simplified version - in practice, you'd need sector mappings
            
            return {
                'total_return': total_return,
                'total_return_percent': total_return * 100,
                'initial_portfolio_value': initial_value,
                'final_portfolio_value': final_value,
                'absolute_change': final_value - initial_value,
                'position_contributions': position_contributions,
                'top_contributors': sorted(
                    position_contributions.items(),
                    key=lambda x: x[1]['contribution_to_return'],
                    reverse=True
                )[:5],
                'worst_contributors': sorted(
                    position_contributions.items(),
                    key=lambda x: x[1]['contribution_to_return']
                )[:5]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance attribution: {e}")
            raise
    
    def calculate_correlation_analysis(self, position_returns: Dict[str, List[float]]) -> Dict[str, any]:
        """
        Calculate correlation analysis between positions.
        
        Args:
            position_returns: Dictionary mapping symbols to their return series
            
        Returns:
            Dictionary containing correlation analysis
        """
        try:
            if len(position_returns) < 2:
                return {'correlation_matrix': {}, 'average_correlation': 0, 'max_correlation': 0}
            
            symbols = list(position_returns.keys())
            correlation_matrix = {}
            correlations = []
            
            # Calculate pairwise correlations
            for i, symbol1 in enumerate(symbols):
                correlation_matrix[symbol1] = {}
                for j, symbol2 in enumerate(symbols):
                    if i == j:
                        correlation = 1.0
                    else:
                        returns1 = position_returns[symbol1]
                        returns2 = position_returns[symbol2]
                        
                        # Ensure same length
                        min_length = min(len(returns1), len(returns2))
                        returns1 = returns1[:min_length]
                        returns2 = returns2[:min_length]
                        
                        if len(returns1) > 1:
                            correlation = np.corrcoef(returns1, returns2)[0, 1]
                            if not np.isnan(correlation):
                                correlations.append(abs(correlation))
                            else:
                                correlation = 0.0
                        else:
                            correlation = 0.0
                    
                    correlation_matrix[symbol1][symbol2] = correlation
            
            # Calculate summary statistics
            avg_correlation = np.mean(correlations) if correlations else 0
            max_correlation = max(correlations) if correlations else 0
            min_correlation = min(correlations) if correlations else 0
            
            # Find most and least correlated pairs
            most_correlated = None
            least_correlated = None
            max_corr_value = -1
            min_corr_value = 2
            
            for symbol1 in symbols:
                for symbol2 in symbols:
                    if symbol1 != symbol2:
                        corr_value = abs(correlation_matrix[symbol1][symbol2])
                        if corr_value > max_corr_value:
                            max_corr_value = corr_value
                            most_correlated = (symbol1, symbol2, correlation_matrix[symbol1][symbol2])
                        if corr_value < min_corr_value:
                            min_corr_value = corr_value
                            least_correlated = (symbol1, symbol2, correlation_matrix[symbol1][symbol2])
            
            return {
                'correlation_matrix': correlation_matrix,
                'average_correlation': avg_correlation,
                'max_correlation': max_correlation,
                'min_correlation': min_correlation,
                'most_correlated_pair': most_correlated,
                'least_correlated_pair': least_correlated,
                'diversification_benefit': 1 - avg_correlation  # Simple diversification measure
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation analysis: {e}")
            raise
    
    def generate_comprehensive_analysis(self, portfolio_snapshots: List[PortfolioSnapshot],
                                      market_returns: Optional[List[float]] = None,
                                      position_returns: Optional[Dict[str, List[float]]] = None) -> Dict[str, any]:
        """
        Generate comprehensive portfolio analysis combining all metrics.
        
        Args:
            portfolio_snapshots: List of portfolio snapshots over time
            market_returns: Optional market returns for beta calculation
            position_returns: Optional position returns for correlation analysis
            
        Returns:
            Dictionary containing comprehensive analysis
        """
        try:
            if not portfolio_snapshots:
                raise ValueError("Portfolio snapshots list cannot be empty")
            
            current_portfolio = portfolio_snapshots[-1]
            
            # Calculate all metrics
            value_allocation = self.calculate_portfolio_value_and_allocation(current_portfolio)
            
            risk_metrics = {}
            performance_attribution = {}
            correlation_analysis = {}
            
            if len(portfolio_snapshots) > 1:
                risk_metrics = self.calculate_risk_metrics(portfolio_snapshots, market_returns)
                performance_attribution = self.calculate_performance_attribution(portfolio_snapshots)
            
            if position_returns:
                correlation_analysis = self.calculate_correlation_analysis(position_returns)
            
            # Calculate additional summary metrics
            analysis_period_days = (portfolio_snapshots[-1].timestamp - portfolio_snapshots[0].timestamp).days
            
            return {
                'analysis_timestamp': datetime.now(),
                'analysis_period_days': analysis_period_days,
                'portfolio_snapshot_count': len(portfolio_snapshots),
                'current_portfolio': {
                    'timestamp': current_portfolio.timestamp,
                    'total_value': float(current_portfolio.total_value),
                    'position_count': current_portfolio.position_count
                },
                'value_and_allocation': value_allocation,
                'risk_metrics': risk_metrics,
                'performance_attribution': performance_attribution,
                'correlation_analysis': correlation_analysis,
                'summary': {
                    'is_diversified': value_allocation.get('max_allocation_percent', 0) < 20,
                    'risk_level': self._categorize_risk_level(risk_metrics.get('annual_volatility', 0)),
                    'performance_rating': self._rate_performance(risk_metrics.get('sharpe_ratio', 0)),
                    'concentration_warning': value_allocation.get('max_allocation_percent', 0) > 30
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive analysis: {e}")
            raise
    
    def _categorize_risk_level(self, annual_volatility: float) -> str:
        """Categorize risk level based on annual volatility."""
        if annual_volatility < 0.10:
            return "Low"
        elif annual_volatility < 0.20:
            return "Moderate"
        elif annual_volatility < 0.30:
            return "High"
        else:
            return "Very High"
    
    def _rate_performance(self, sharpe_ratio: float) -> str:
        """Rate performance based on Sharpe ratio."""
        if sharpe_ratio > 2.0:
            return "Excellent"
        elif sharpe_ratio > 1.0:
            return "Good"
        elif sharpe_ratio > 0.5:
            return "Fair"
        elif sharpe_ratio > 0:
            return "Poor"
        else:
            return "Very Poor"