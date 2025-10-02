"""
Metrics Calculator for real-time portfolio metrics.

This module calculates various portfolio metrics including performance,
risk, and allocation metrics for dashboard display.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import math
import logging

from ..models.core import PortfolioSnapshot, Position
from ..data.store import DataStore
from ..analysis.portfolio_analyzer import PortfolioAnalyzer


class MetricsCalculator:
    """
    Calculator for real-time portfolio metrics.
    
    Provides methods to calculate various portfolio metrics including
    performance, risk, and allocation metrics for dashboard consumption.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        portfolio_analyzer: PortfolioAnalyzer
    ):
        """
        Initialize metrics calculator.
        
        Args:
            data_store: Data storage interface
            portfolio_analyzer: Portfolio analysis engine
        """
        self.data_store = data_store
        self.portfolio_analyzer = portfolio_analyzer
        self.logger = logging.getLogger(__name__)
    
    def calculate_real_time_metrics(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Dict[str, Any]:
        """
        Calculate real-time portfolio metrics.
        
        Args:
            snapshot: Current portfolio snapshot
            
        Returns:
            Dictionary of real-time metrics
        """
        metrics = {
            'timestamp': snapshot.timestamp,
            'portfolio_value': float(snapshot.total_value),
            'buying_power': float(snapshot.buying_power),
            'day_pnl': float(snapshot.day_pnl),
            'total_pnl': float(snapshot.total_pnl),
            'positions_count': len(snapshot.positions),
            'cash_percentage': self._calculate_cash_percentage(snapshot),
            'largest_position': self._get_largest_position(snapshot),
            'concentration_risk': self._calculate_concentration_risk(snapshot)
        }
        
        # Add percentage calculations
        if snapshot.total_value > 0:
            metrics['day_pnl_pct'] = float(snapshot.day_pnl / snapshot.total_value * 100)
        else:
            metrics['day_pnl_pct'] = 0.0
        
        # Calculate total return percentage
        initial_value = snapshot.total_value - snapshot.total_pnl
        if initial_value > 0:
            metrics['total_return_pct'] = float(snapshot.total_pnl / initial_value * 100)
        else:
            metrics['total_return_pct'] = 0.0
        
        return metrics
    
    def calculate_period_performance(
        self,
        start_snapshot: PortfolioSnapshot,
        end_snapshot: PortfolioSnapshot,
        period_days: int
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics for a specific period.
        
        Args:
            start_snapshot: Starting portfolio snapshot
            end_snapshot: Ending portfolio snapshot
            period_days: Number of days in the period
            
        Returns:
            Period performance metrics
        """
        start_value = start_snapshot.total_value
        end_value = end_snapshot.total_value
        
        # Calculate return
        if start_value > 0:
            total_return = end_value - start_value
            return_pct = total_return / start_value * 100
        else:
            total_return = Decimal('0')
            return_pct = Decimal('0')
        
        # Annualize if period is less than a year
        if period_days > 0 and period_days < 365:
            annualized_return = (1 + float(return_pct) / 100) ** (365 / period_days) - 1
            annualized_return_pct = annualized_return * 100
        else:
            annualized_return_pct = float(return_pct)
        
        return {
            'period_days': period_days,
            'start_value': float(start_value),
            'end_value': float(end_value),
            'total_return': float(total_return),
            'return_pct': float(return_pct),
            'annualized_return_pct': annualized_return_pct,
            'start_date': start_snapshot.timestamp.date().isoformat(),
            'end_date': end_snapshot.timestamp.date().isoformat()
        }
    
    def calculate_risk_metrics(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Dict[str, Decimal]:
        """
        Calculate current risk metrics.
        
        Args:
            snapshot: Current portfolio snapshot
            
        Returns:
            Dictionary of risk metrics
        """
        risk_metrics = {}
        
        # Position concentration
        risk_metrics['concentration_risk'] = self._calculate_concentration_risk(snapshot)
        
        # Sector concentration
        risk_metrics['sector_concentration'] = self._calculate_sector_concentration(snapshot)
        
        # Cash allocation
        risk_metrics['cash_percentage'] = self._calculate_cash_percentage(snapshot)
        
        # Largest position percentage
        largest_position = self._get_largest_position(snapshot)
        risk_metrics['largest_position_pct'] = largest_position.get('weight_pct', Decimal('0'))
        
        return risk_metrics
    
    def calculate_comprehensive_risk_metrics(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics using historical data.
        
        Args:
            snapshots: List of portfolio snapshots
            
        Returns:
            Comprehensive risk analysis
        """
        if len(snapshots) < 2:
            return {}
        
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
        
        # Calculate volatility
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        daily_volatility = math.sqrt(variance)
        annualized_volatility = daily_volatility * math.sqrt(252)  # 252 trading days
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown(snapshots)
        
        # Calculate Value at Risk (simplified)
        var_95 = self._calculate_var(daily_returns, 0.95)
        var_99 = self._calculate_var(daily_returns, 0.99)
        
        # Calculate Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = (mean_return * 252) / annualized_volatility if annualized_volatility > 0 else 0
        
        return {
            'volatility_daily': daily_volatility,
            'volatility_annualized': annualized_volatility,
            'max_drawdown_pct': float(max_drawdown),
            'var_95_pct': var_95 * 100,
            'var_99_pct': var_99 * 100,
            'sharpe_ratio': sharpe_ratio,
            'mean_daily_return': mean_return,
            'return_periods_analyzed': len(daily_returns)
        }
    
    def calculate_allocation_metrics(
        self, 
        snapshot: PortfolioSnapshot
    ) -> Dict[str, Any]:
        """
        Calculate portfolio allocation metrics.
        
        Args:
            snapshot: Portfolio snapshot
            
        Returns:
            Allocation metrics
        """
        total_value = snapshot.total_value
        
        if total_value <= 0:
            return {}
        
        # Position allocations
        position_allocations = []
        for position in snapshot.positions:
            weight_pct = position.market_value / total_value * 100
            position_allocations.append({
                'symbol': position.symbol,
                'value': float(position.market_value),
                'weight_pct': float(weight_pct),
                'day_pnl': float(position.day_pnl),
                'unrealized_pnl': float(position.unrealized_pnl)
            })
        
        # Sort by weight
        position_allocations.sort(key=lambda x: x['weight_pct'], reverse=True)
        
        # Sector allocations
        sector_allocations = self._calculate_sector_allocations(snapshot)
        
        # Concentration metrics
        concentration_metrics = {
            'top_5_concentration': sum(
                pos['weight_pct'] for pos in position_allocations[:5]
            ),
            'top_10_concentration': sum(
                pos['weight_pct'] for pos in position_allocations[:10]
            ),
            'herfindahl_index': self._calculate_herfindahl_index(position_allocations)
        }
        
        return {
            'position_allocations': position_allocations,
            'sector_allocations': sector_allocations,
            'concentration_metrics': concentration_metrics,
            'total_positions': len(position_allocations)
        }
    
    def _calculate_cash_percentage(self, snapshot: PortfolioSnapshot) -> Decimal:
        """Calculate cash percentage of portfolio."""
        if snapshot.total_value <= 0:
            return Decimal('100')
        
        # Cash is buying power as percentage of total value
        return snapshot.buying_power / snapshot.total_value * 100
    
    def _get_largest_position(self, snapshot: PortfolioSnapshot) -> Dict[str, Any]:
        """Get the largest position by market value."""
        if not snapshot.positions:
            return {'symbol': None, 'value': 0, 'weight_pct': Decimal('0')}
        
        largest_pos = max(snapshot.positions, key=lambda p: p.market_value)
        
        weight_pct = (
            largest_pos.market_value / snapshot.total_value * 100
            if snapshot.total_value > 0 else Decimal('0')
        )
        
        return {
            'symbol': largest_pos.symbol,
            'value': float(largest_pos.market_value),
            'weight_pct': weight_pct
        }
    
    def _calculate_concentration_risk(self, snapshot: PortfolioSnapshot) -> Decimal:
        """Calculate portfolio concentration risk using Herfindahl index."""
        if not snapshot.positions or snapshot.total_value <= 0:
            return Decimal('0')
        
        # Calculate weights
        weights = [
            (pos.market_value / snapshot.total_value) ** 2
            for pos in snapshot.positions
        ]
        
        # Herfindahl index (sum of squared weights)
        herfindahl_index = sum(weights)
        
        # Convert to concentration risk score (0-100)
        # Higher values indicate more concentration
        return Decimal(str(herfindahl_index * 100))
    
    def _calculate_sector_concentration(self, snapshot: PortfolioSnapshot) -> Decimal:
        """Calculate sector concentration risk."""
        if not snapshot.positions or snapshot.total_value <= 0:
            return Decimal('0')
        
        # Group by sector
        sector_values = {}
        for position in snapshot.positions:
            sector = self._get_position_sector(position.symbol)
            
            if sector not in sector_values:
                sector_values[sector] = Decimal('0')
            
            sector_values[sector] += position.market_value
        
        # Calculate sector weights and concentration
        sector_weights = [
            (value / snapshot.total_value) ** 2
            for value in sector_values.values()
        ]
        
        herfindahl_index = sum(sector_weights)
        return Decimal(str(herfindahl_index * 100))
    
    def _calculate_sector_allocations(
        self, 
        snapshot: PortfolioSnapshot
    ) -> List[Dict[str, Any]]:
        """Calculate sector allocation breakdown."""
        if not snapshot.positions or snapshot.total_value <= 0:
            return []
        
        sector_data = {}
        
        for position in snapshot.positions:
            sector = self._get_position_sector(position.symbol)
            
            if sector not in sector_data:
                sector_data[sector] = {
                    'sector': sector,
                    'value': Decimal('0'),
                    'positions': 0,
                    'day_pnl': Decimal('0')
                }
            
            sector_data[sector]['value'] += position.market_value
            sector_data[sector]['positions'] += 1
            sector_data[sector]['day_pnl'] += position.day_pnl
        
        # Convert to list with percentages
        sector_allocations = []
        for sector_info in sector_data.values():
            weight_pct = sector_info['value'] / snapshot.total_value * 100
            
            sector_allocations.append({
                'sector': sector_info['sector'],
                'value': float(sector_info['value']),
                'weight_pct': float(weight_pct),
                'positions': sector_info['positions'],
                'day_pnl': float(sector_info['day_pnl'])
            })
        
        # Sort by weight
        sector_allocations.sort(key=lambda x: x['weight_pct'], reverse=True)
        
        return sector_allocations
    
    def _calculate_max_drawdown(
        self, 
        snapshots: List[PortfolioSnapshot]
    ) -> Decimal:
        """Calculate maximum drawdown from snapshots."""
        if len(snapshots) < 2:
            return Decimal('0')
        
        values = [float(s.total_value) for s in snapshots]
        
        max_drawdown = 0
        peak = values[0]
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return Decimal(str(max_drawdown * 100))
    
    def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk at given confidence level."""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        
        if index >= len(sorted_returns):
            return sorted_returns[-1]
        
        return sorted_returns[index]
    
    def _calculate_herfindahl_index(
        self, 
        allocations: List[Dict[str, Any]]
    ) -> float:
        """Calculate Herfindahl concentration index."""
        if not allocations:
            return 0.0
        
        # Sum of squared weights (as decimals, not percentages)
        squared_weights = sum(
            (alloc['weight_pct'] / 100) ** 2 
            for alloc in allocations
        )
        
        return squared_weights
    
    def _get_position_sector(self, symbol: str) -> str:
        """Get sector for a position symbol."""
        # Simplified sector mapping
        sector_mapping = {
            'AAPL': 'Technology',
            'GOOGL': 'Technology',
            'MSFT': 'Technology',
            'TSLA': 'Consumer Discretionary',
            'NVDA': 'Technology',
            'JPM': 'Financial Services',
            'BAC': 'Financial Services',
            'WFC': 'Financial Services',
            'GS': 'Financial Services',
            'JNJ': 'Healthcare',
            'PFE': 'Healthcare',
            'XOM': 'Energy',
            'CVX': 'Energy'
        }
        
        return sector_mapping.get(symbol, 'Other')