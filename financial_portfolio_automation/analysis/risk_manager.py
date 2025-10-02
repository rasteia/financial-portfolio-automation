"""
Risk Manager module for portfolio risk monitoring and position size validation.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import math

from ..models.core import Position, PortfolioSnapshot, Order, OrderSide
from ..models.config import RiskLimits

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk manager class for monitoring portfolio risk exposure, validating position sizes,
    and implementing risk controls.
    """
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        """
        Initialize the RiskManager class.
        
        Args:
            risk_limits: Risk limits configuration
        """
        self.logger = logger
        self.risk_limits = risk_limits or self._get_default_risk_limits()
    
    def _get_default_risk_limits(self) -> RiskLimits:
        """Get default risk limits if none provided."""
        return RiskLimits(
            max_position_size=Decimal('50000.00'),  # $50k max per position
            max_portfolio_concentration=0.20,  # 20% max allocation per position
            max_daily_loss=Decimal('5000.00'),  # $5k max daily loss
            max_drawdown=0.15,  # 15% max drawdown
            stop_loss_percentage=0.05  # 5% stop loss
        )
    
    def set_risk_limits(self, risk_limits: RiskLimits) -> None:
        """
        Set new risk limits.
        
        Args:
            risk_limits: New risk limits configuration
        """
        self.risk_limits = risk_limits
        self.logger.info("Risk limits updated")
    
    def validate_position_size(self, symbol: str, quantity: int, price: Decimal, 
                             current_portfolio: PortfolioSnapshot) -> Dict[str, any]:
        """
        Validate if a position size is within risk limits.
        
        Args:
            symbol: Symbol to validate
            quantity: Proposed quantity
            price: Current price
            current_portfolio: Current portfolio snapshot
            
        Returns:
            Dictionary with validation results
        """
        try:
            position_value = abs(quantity * price)
            portfolio_value = float(current_portfolio.total_value)
            
            # Check maximum position size limit
            max_position_exceeded = position_value > self.risk_limits.max_position_size
            
            # Check portfolio concentration limit
            concentration = float(position_value / current_portfolio.total_value) if portfolio_value > 0 else 0
            concentration_exceeded = concentration > self.risk_limits.max_portfolio_concentration
            
            # Check if position already exists and calculate new total
            existing_position = current_portfolio.get_position(symbol)
            if existing_position:
                new_quantity = existing_position.quantity + quantity
                new_position_value = abs(new_quantity * price)
                new_concentration = float(new_position_value / current_portfolio.total_value) if portfolio_value > 0 else 0
            else:
                new_quantity = quantity
                new_position_value = position_value
                new_concentration = concentration
            
            # Final validation checks
            final_position_exceeded = new_position_value > self.risk_limits.max_position_size
            final_concentration_exceeded = new_concentration > self.risk_limits.max_portfolio_concentration
            
            is_valid = not (final_position_exceeded or final_concentration_exceeded)
            
            validation_result = {
                'is_valid': is_valid,
                'symbol': symbol,
                'proposed_quantity': quantity,
                'proposed_value': float(position_value),
                'current_quantity': existing_position.quantity if existing_position else 0,
                'new_total_quantity': new_quantity,
                'new_position_value': float(new_position_value),
                'concentration_percent': new_concentration * 100,
                'violations': [],
                'warnings': []
            }
            
            # Add specific violations
            if final_position_exceeded:
                validation_result['violations'].append({
                    'type': 'max_position_size',
                    'message': f"Position value ${new_position_value:,.2f} exceeds maximum ${self.risk_limits.max_position_size:,.2f}",
                    'limit': float(self.risk_limits.max_position_size),
                    'actual': float(new_position_value)
                })
            
            if final_concentration_exceeded:
                validation_result['violations'].append({
                    'type': 'max_concentration',
                    'message': f"Position concentration {new_concentration:.1%} exceeds maximum {self.risk_limits.max_portfolio_concentration:.1%}",
                    'limit': self.risk_limits.max_portfolio_concentration,
                    'actual': new_concentration
                })
            
            # Add warnings for positions approaching limits
            if new_concentration > self.risk_limits.max_portfolio_concentration * 0.8:
                validation_result['warnings'].append({
                    'type': 'approaching_concentration_limit',
                    'message': f"Position concentration {new_concentration:.1%} is approaching limit {self.risk_limits.max_portfolio_concentration:.1%}"
                })
            
            if new_position_value > float(self.risk_limits.max_position_size) * 0.8:
                validation_result['warnings'].append({
                    'type': 'approaching_position_limit',
                    'message': f"Position value ${new_position_value:,.2f} is approaching limit ${self.risk_limits.max_position_size:,.2f}"
                })
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error validating position size: {e}")
            raise
    
    def monitor_portfolio_concentration(self, portfolio: PortfolioSnapshot) -> Dict[str, any]:
        """
        Monitor portfolio concentration and identify concentration risks.
        
        Args:
            portfolio: Portfolio snapshot to analyze
            
        Returns:
            Dictionary with concentration analysis
        """
        try:
            if not portfolio.positions or portfolio.total_value <= 0:
                return {
                    'total_positions': 0,
                    'concentration_violations': [],
                    'concentration_warnings': [],
                    'herfindahl_index': 0,
                    'effective_positions': 0,
                    'is_diversified': True
                }
            
            portfolio_value = float(portfolio.total_value)
            concentrations = []
            violations = []
            warnings = []
            
            for position in portfolio.positions:
                allocation = float(abs(position.market_value) / portfolio.total_value)
                concentrations.append(allocation)
                
                # Check for concentration violations
                if allocation > self.risk_limits.max_portfolio_concentration:
                    violations.append({
                        'symbol': position.symbol,
                        'allocation_percent': allocation * 100,
                        'limit_percent': self.risk_limits.max_portfolio_concentration * 100,
                        'excess_percent': (allocation - self.risk_limits.max_portfolio_concentration) * 100,
                        'market_value': float(position.market_value)
                    })
                
                # Check for concentration warnings (80% of limit)
                elif allocation > self.risk_limits.max_portfolio_concentration * 0.8:
                    warnings.append({
                        'symbol': position.symbol,
                        'allocation_percent': allocation * 100,
                        'limit_percent': self.risk_limits.max_portfolio_concentration * 100,
                        'market_value': float(position.market_value)
                    })
            
            # Calculate Herfindahl-Hirschman Index (HHI)
            hhi = sum(conc ** 2 for conc in concentrations)
            
            # Calculate effective number of positions
            effective_positions = 1 / hhi if hhi > 0 else 0
            
            # Determine if portfolio is well diversified
            is_diversified = (
                len(violations) == 0 and 
                hhi < 0.25 and  # HHI less than 0.25 indicates good diversification
                len(portfolio.positions) >= 5  # At least 5 positions
            )
            
            return {
                'total_positions': len(portfolio.positions),
                'concentration_violations': violations,
                'concentration_warnings': warnings,
                'herfindahl_index': hhi,
                'effective_positions': effective_positions,
                'is_diversified': is_diversified,
                'max_allocation_percent': max(concentrations) * 100 if concentrations else 0,
                'diversification_score': min(100, effective_positions * 10)  # Score out of 100
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring portfolio concentration: {e}")
            raise
    
    def monitor_drawdown(self, portfolio_snapshots: List[PortfolioSnapshot]) -> Dict[str, any]:
        """
        Monitor portfolio drawdown and identify drawdown violations.
        
        Args:
            portfolio_snapshots: List of portfolio snapshots over time
            
        Returns:
            Dictionary with drawdown analysis
        """
        try:
            if len(portfolio_snapshots) < 2:
                return {
                    'current_drawdown': 0,
                    'max_drawdown': 0,
                    'drawdown_violation': False,
                    'days_in_drawdown': 0,
                    'peak_value': 0,
                    'current_value': 0
                }
            
            # Extract portfolio values
            values = [float(snapshot.total_value) for snapshot in portfolio_snapshots]
            timestamps = [snapshot.timestamp for snapshot in portfolio_snapshots]
            
            # Calculate running maximum (peak)
            peak_value = values[0]
            current_drawdown = 0
            max_drawdown = 0
            days_in_drawdown = 0
            drawdown_start = None
            
            for i, value in enumerate(values):
                if value > peak_value:
                    peak_value = value
                    if drawdown_start is not None:
                        # Drawdown period ended
                        drawdown_start = None
                else:
                    # Calculate current drawdown
                    current_drawdown = (peak_value - value) / peak_value if peak_value > 0 else 0
                    max_drawdown = max(max_drawdown, current_drawdown)
                    
                    if drawdown_start is None and current_drawdown > 0:
                        drawdown_start = timestamps[i]
            
            # Calculate days in current drawdown
            if drawdown_start is not None:
                days_in_drawdown = (timestamps[-1] - drawdown_start).days
            
            # Check for drawdown violation
            drawdown_violation = current_drawdown > self.risk_limits.max_drawdown
            
            return {
                'current_drawdown': current_drawdown,
                'current_drawdown_percent': current_drawdown * 100,
                'max_drawdown': max_drawdown,
                'max_drawdown_percent': max_drawdown * 100,
                'drawdown_violation': drawdown_violation,
                'drawdown_limit_percent': self.risk_limits.max_drawdown * 100,
                'days_in_drawdown': days_in_drawdown,
                'peak_value': peak_value,
                'current_value': values[-1],
                'is_in_drawdown': current_drawdown > 0.01  # More than 1% drawdown
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring drawdown: {e}")
            raise
    
    def calculate_volatility_based_position_size(self, symbol: str, price: Decimal, 
                                                volatility: float, portfolio_value: Decimal,
                                                risk_per_trade: float = 0.02) -> Dict[str, any]:
        """
        Calculate position size based on volatility and risk tolerance.
        
        Args:
            symbol: Symbol to calculate position size for
            price: Current price
            volatility: Historical volatility (annualized)
            portfolio_value: Current portfolio value
            risk_per_trade: Risk per trade as percentage of portfolio (default: 2%)
            
        Returns:
            Dictionary with position sizing recommendations
        """
        try:
            if volatility <= 0 or price <= 0 or portfolio_value <= 0:
                return {
                    'recommended_quantity': 0,
                    'recommended_value': 0,
                    'risk_per_trade_percent': 0,
                    'stop_loss_price': 0,
                    'max_loss_amount': 0,
                    'position_size_method': 'volatility_based'
                }
            
            # Calculate daily volatility from annual
            daily_volatility = volatility / math.sqrt(252)
            
            # Calculate stop loss distance (2 standard deviations)
            stop_loss_distance = float(price) * daily_volatility * 2
            
            # Calculate maximum loss amount
            max_loss_amount = float(portfolio_value) * risk_per_trade
            
            # Calculate position size based on risk
            if stop_loss_distance > 0:
                recommended_value = max_loss_amount / stop_loss_distance
                recommended_quantity = int(recommended_value / float(price))
            else:
                recommended_quantity = 0
                recommended_value = 0
            
            # Apply position size limits
            max_position_value = float(self.risk_limits.max_position_size)
            if recommended_value > max_position_value:
                recommended_value = max_position_value
                recommended_quantity = int(recommended_value / float(price))
            
            # Apply concentration limits
            max_concentration_value = float(portfolio_value) * self.risk_limits.max_portfolio_concentration
            if recommended_value > max_concentration_value:
                recommended_value = max_concentration_value
                recommended_quantity = int(recommended_value / float(price))
            
            # Calculate stop loss price
            stop_loss_price = float(price) - stop_loss_distance
            
            # Recalculate actual risk based on final position size
            actual_position_value = recommended_quantity * float(price)
            actual_max_loss = actual_position_value * (stop_loss_distance / float(price))
            actual_risk_percent = actual_max_loss / float(portfolio_value) * 100 if portfolio_value > 0 else 0
            
            return {
                'symbol': symbol,
                'current_price': float(price),
                'volatility_annual': volatility,
                'volatility_daily': daily_volatility,
                'recommended_quantity': recommended_quantity,
                'recommended_value': actual_position_value,
                'risk_per_trade_percent': actual_risk_percent,
                'target_risk_percent': risk_per_trade * 100,
                'stop_loss_price': max(0, stop_loss_price),
                'stop_loss_distance': stop_loss_distance,
                'max_loss_amount': actual_max_loss,
                'position_size_method': 'volatility_based',
                'size_limited_by': self._get_limiting_factor(
                    recommended_value, max_position_value, max_concentration_value
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility-based position size: {e}")
            raise
    
    def _get_limiting_factor(self, recommended_value: float, max_position_value: float, 
                           max_concentration_value: float) -> str:
        """Determine what factor limited the position size."""
        if recommended_value <= max_position_value and recommended_value <= max_concentration_value:
            return 'volatility_risk'
        elif max_position_value < max_concentration_value:
            return 'max_position_size'
        else:
            return 'max_concentration'
    
    def validate_order_risk(self, order: Order, current_portfolio: PortfolioSnapshot,
                           current_price: Optional[Decimal] = None) -> Dict[str, any]:
        """
        Validate an order against risk limits before execution.
        
        Args:
            order: Order to validate
            current_portfolio: Current portfolio snapshot
            current_price: Current market price (optional)
            
        Returns:
            Dictionary with order validation results
        """
        try:
            # Use limit price if available, otherwise use current price
            price = current_price or order.limit_price
            if price is None:
                return {
                    'is_valid': False,
                    'violations': [{'type': 'missing_price', 'message': 'No price available for risk validation'}],
                    'warnings': []
                }
            
            # Determine effective quantity based on order side
            effective_quantity = order.quantity if order.side == OrderSide.BUY else -order.quantity
            
            # Validate position size
            position_validation = self.validate_position_size(
                order.symbol, effective_quantity, price, current_portfolio
            )
            
            # Check daily loss limits
            daily_pnl = float(current_portfolio.day_pnl)
            order_value = float(order.quantity * price)
            
            # Estimate potential loss (simplified - assumes 5% adverse move)
            potential_loss = order_value * 0.05 if order.side == OrderSide.BUY else -order_value * 0.05
            projected_daily_loss = daily_pnl - potential_loss  # Subtract potential loss from current PnL
            
            daily_loss_violation = (
                projected_daily_loss < -float(self.risk_limits.max_daily_loss)
            )
            
            # Combine all validations
            is_valid = position_validation['is_valid'] and not daily_loss_violation
            
            violations = position_validation['violations'].copy()
            warnings = position_validation['warnings'].copy()
            
            if daily_loss_violation:
                violations.append({
                    'type': 'max_daily_loss',
                    'message': f"Order could push daily loss to ${abs(projected_daily_loss):,.2f}, exceeding limit ${self.risk_limits.max_daily_loss:,.2f}",
                    'limit': float(self.risk_limits.max_daily_loss),
                    'projected_loss': abs(projected_daily_loss)
                })
            
            return {
                'is_valid': is_valid,
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': float(price),
                'order_value': order_value,
                'current_daily_pnl': daily_pnl,
                'projected_daily_pnl': projected_daily_loss,
                'violations': violations,
                'warnings': warnings,
                'position_validation': position_validation
            }
            
        except Exception as e:
            self.logger.error(f"Error validating order risk: {e}")
            raise
    
    def generate_risk_report(self, portfolio: PortfolioSnapshot, 
                           portfolio_history: Optional[List[PortfolioSnapshot]] = None) -> Dict[str, any]:
        """
        Generate comprehensive risk report for the portfolio.
        
        Args:
            portfolio: Current portfolio snapshot
            portfolio_history: Historical portfolio snapshots for trend analysis
            
        Returns:
            Dictionary with comprehensive risk analysis
        """
        try:
            # Basic portfolio metrics
            concentration_analysis = self.monitor_portfolio_concentration(portfolio)
            
            # Drawdown analysis if history available
            drawdown_analysis = {}
            if portfolio_history and len(portfolio_history) > 1:
                drawdown_analysis = self.monitor_drawdown(portfolio_history)
            
            # Risk limit compliance
            risk_compliance = {
                'concentration_compliant': len(concentration_analysis['concentration_violations']) == 0,
                'drawdown_compliant': not drawdown_analysis.get('drawdown_violation', False),
                'daily_loss_compliant': float(portfolio.day_pnl) > -float(self.risk_limits.max_daily_loss)
            }
            
            # Overall risk score (0-100, higher is riskier)
            risk_score = self._calculate_risk_score(
                concentration_analysis, drawdown_analysis, portfolio
            )
            
            # Risk recommendations
            recommendations = self._generate_risk_recommendations(
                concentration_analysis, drawdown_analysis, portfolio
            )
            
            return {
                'report_timestamp': datetime.now(),
                'portfolio_value': float(portfolio.total_value),
                'day_pnl': float(portfolio.day_pnl),
                'risk_score': risk_score,
                'risk_level': self._categorize_risk_level(risk_score),
                'concentration_analysis': concentration_analysis,
                'drawdown_analysis': drawdown_analysis,
                'risk_compliance': risk_compliance,
                'risk_limits': {
                    'max_position_size': float(self.risk_limits.max_position_size),
                    'max_concentration_percent': self.risk_limits.max_portfolio_concentration * 100,
                    'max_daily_loss': float(self.risk_limits.max_daily_loss),
                    'max_drawdown_percent': self.risk_limits.max_drawdown * 100,
                    'stop_loss_percent': self.risk_limits.stop_loss_percentage * 100
                },
                'recommendations': recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Error generating risk report: {e}")
            raise
    
    def _calculate_risk_score(self, concentration_analysis: Dict, drawdown_analysis: Dict, 
                            portfolio: PortfolioSnapshot) -> float:
        """Calculate overall risk score (0-100)."""
        score = 0
        
        # Concentration risk (0-40 points)
        hhi = concentration_analysis.get('herfindahl_index', 0)
        concentration_score = min(40, hhi * 100)
        score += concentration_score
        
        # Drawdown risk (0-30 points)
        current_drawdown = drawdown_analysis.get('current_drawdown', 0)
        drawdown_score = min(30, current_drawdown * 100)
        score += drawdown_score
        
        # Daily loss risk (0-20 points)
        daily_pnl = float(portfolio.day_pnl)
        if daily_pnl < 0:
            daily_loss_ratio = abs(daily_pnl) / float(self.risk_limits.max_daily_loss)
            daily_loss_score = min(20, daily_loss_ratio * 20)
            score += daily_loss_score
        
        # Position count risk (0-10 points)
        position_count = len(portfolio.positions)
        if position_count < 5:
            position_score = (5 - position_count) * 2
            score += position_score
        
        return min(100, score)
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk level based on risk score."""
        if risk_score < 20:
            return "Low"
        elif risk_score < 40:
            return "Moderate"
        elif risk_score < 60:
            return "High"
        elif risk_score < 80:
            return "Very High"
        else:
            return "Extreme"
    
    def _generate_risk_recommendations(self, concentration_analysis: Dict, 
                                     drawdown_analysis: Dict, 
                                     portfolio: PortfolioSnapshot) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        # Concentration recommendations
        if concentration_analysis['concentration_violations']:
            recommendations.append(
                f"Reduce concentration in {len(concentration_analysis['concentration_violations'])} "
                f"positions exceeding {self.risk_limits.max_portfolio_concentration:.1%} limit"
            )
        
        if concentration_analysis['herfindahl_index'] > 0.25:
            recommendations.append("Consider diversifying portfolio across more positions")
        
        # Drawdown recommendations
        if drawdown_analysis.get('drawdown_violation', False):
            recommendations.append(
                f"Portfolio drawdown of {drawdown_analysis['current_drawdown_percent']:.1f}% "
                f"exceeds {self.risk_limits.max_drawdown:.1%} limit - consider reducing risk"
            )
        
        if drawdown_analysis.get('days_in_drawdown', 0) > 30:
            recommendations.append("Portfolio has been in drawdown for over 30 days - review strategy")
        
        # Daily loss recommendations
        daily_pnl = float(portfolio.day_pnl)
        if daily_pnl < -float(self.risk_limits.max_daily_loss) * 0.8:
            recommendations.append("Daily losses approaching limit - consider reducing position sizes")
        
        # Diversification recommendations
        if len(portfolio.positions) < 5:
            recommendations.append("Consider adding more positions to improve diversification")
        
        if not recommendations:
            recommendations.append("Portfolio risk levels are within acceptable limits")
        
        return recommendations