"""
Risk Controller for pre-trade validation and real-time risk monitoring.

This module provides comprehensive risk control capabilities including
pre-trade validation, real-time position monitoring, and automatic
risk management actions.
"""

import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
import threading
import time
from dataclasses import dataclass

from ..models.core import Order, OrderSide, OrderType, OrderStatus, Position, PortfolioSnapshot
from ..models.config import RiskLimits
from ..analysis.risk_manager import RiskManager
from ..api.alpaca_client import AlpacaClient
from ..exceptions import RiskError, PositionLimitError, DrawdownLimitError, TradingError
from .order_executor import OrderRequest, ExecutionResult


logger = logging.getLogger(__name__)


class RiskAction(Enum):
    """Risk management action types."""
    BLOCK_ORDER = "block_order"
    REDUCE_POSITION = "reduce_position"
    CLOSE_POSITION = "close_position"
    STOP_TRADING = "stop_trading"
    REBALANCE_PORTFOLIO = "rebalance_portfolio"
    ALERT_ONLY = "alert_only"


@dataclass
class RiskViolation:
    """Risk violation details."""
    violation_type: str
    severity: str  # low, medium, high, critical
    symbol: Optional[str]
    message: str
    recommended_action: RiskAction
    violation_value: float
    limit_value: float
    timestamp: datetime
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class RiskControlResult:
    """Result of risk control validation."""
    approved: bool
    violations: List[RiskViolation]
    warnings: List[str]
    recommended_actions: List[RiskAction]
    modified_order: Optional[OrderRequest] = None
    
    @property
    def has_critical_violations(self) -> bool:
        """Check if there are any critical violations."""
        return any(v.severity == "critical" for v in self.violations)
    
    @property
    def has_high_violations(self) -> bool:
        """Check if there are any high severity violations."""
        return any(v.severity in ["high", "critical"] for v in self.violations)


class RiskController:
    """
    Risk controller for pre-trade validation and real-time risk monitoring.
    
    Provides comprehensive risk control including pre-trade checks,
    real-time monitoring, and automatic risk management actions.
    """
    
    def __init__(self, alpaca_client: AlpacaClient, risk_limits: Optional[RiskLimits] = None):
        """
        Initialize the risk controller.
        
        Args:
            alpaca_client: Authenticated Alpaca API client
            risk_limits: Risk limits configuration
        """
        self.alpaca_client = alpaca_client
        self.risk_manager = RiskManager(risk_limits)
        self.risk_limits = risk_limits or self.risk_manager.risk_limits
        
        # Risk monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._risk_callbacks: List[Callable[[RiskViolation], None]] = []
        self._trading_halted = False
        self._last_portfolio_snapshot: Optional[PortfolioSnapshot] = None
        
        # Risk statistics
        self._risk_stats = {
            'total_orders_checked': 0,
            'orders_blocked': 0,
            'orders_modified': 0,
            'risk_violations_detected': 0,
            'automatic_actions_taken': 0
        }
        
        logger.info("RiskController initialized")
    
    def validate_pre_trade_risk(self, order_request: OrderRequest) -> RiskControlResult:
        """
        Validate order against risk limits before execution.
        
        Args:
            order_request: Order request to validate
            
        Returns:
            RiskControlResult with validation details
        """
        try:
            logger.info(f"Validating pre-trade risk for {order_request.symbol} order")
            
            self._risk_stats['total_orders_checked'] += 1
            
            # Check if trading is halted
            if self._trading_halted:
                violation = RiskViolation(
                    violation_type="trading_halted",
                    severity="critical",
                    symbol=order_request.symbol,
                    message="Trading is currently halted due to risk violations",
                    recommended_action=RiskAction.BLOCK_ORDER,
                    violation_value=1,
                    limit_value=0,
                    timestamp=datetime.now(timezone.utc)
                )
                
                return RiskControlResult(
                    approved=False,
                    violations=[violation],
                    warnings=[],
                    recommended_actions=[RiskAction.BLOCK_ORDER]
                )
            
            # Get current portfolio snapshot
            portfolio = self.alpaca_client.get_portfolio_snapshot()
            
            # Create temporary order for validation
            temp_order = Order(
                order_id="temp_validation",
                symbol=order_request.symbol,
                quantity=order_request.quantity,
                side=order_request.side,
                order_type=order_request.order_type,
                status=OrderStatus.NEW,
                limit_price=order_request.limit_price,
                stop_price=order_request.stop_price
            )
            
            # Validate order risk
            validation_result = self.risk_manager.validate_order_risk(
                temp_order, portfolio, order_request.limit_price
            )
            
            violations = []
            warnings = []
            recommended_actions = []
            
            # Process validation violations
            for violation_data in validation_result.get('violations', []):
                severity = self._determine_violation_severity(violation_data['type'])
                action = self._determine_recommended_action(violation_data['type'], severity)
                
                violation = RiskViolation(
                    violation_type=violation_data['type'],
                    severity=severity,
                    symbol=order_request.symbol,
                    message=violation_data['message'],
                    recommended_action=action,
                    violation_value=violation_data.get('actual', 0),
                    limit_value=violation_data.get('limit', 0),
                    timestamp=datetime.now(timezone.utc)
                )
                
                violations.append(violation)
                recommended_actions.append(action)
            
            # Process warnings
            for warning_data in validation_result.get('warnings', []):
                warnings.append(warning_data['message'])
            
            # Additional risk checks
            additional_violations = self._perform_additional_risk_checks(
                order_request, portfolio
            )
            violations.extend(additional_violations)
            
            # Determine if order should be approved
            # Block orders with high or critical violations
            has_blocking_violations = any(
                v.severity in ["high", "critical"] for v in violations
            )
            approved = not has_blocking_violations
            
            # Check for order modification opportunities
            modified_order = None
            if not approved and any(v.violation_type == "max_position_size" and v.severity == "medium" for v in violations):
                modified_order = self._suggest_order_modification(order_request, portfolio)
                if modified_order:
                    approved = True
                    warnings.append("Order quantity reduced to comply with position size limits")
                    self._risk_stats['orders_modified'] += 1
            
            if not approved:
                self._risk_stats['orders_blocked'] += 1
            
            if violations:
                self._risk_stats['risk_violations_detected'] += len(violations)
            
            result = RiskControlResult(
                approved=approved,
                violations=violations,
                warnings=warnings,
                recommended_actions=list(set(recommended_actions)),
                modified_order=modified_order
            )
            
            # Trigger risk callbacks for violations
            for violation in violations:
                self._trigger_risk_callbacks(violation)
            
            logger.info(
                f"Pre-trade risk validation completed. Approved: {approved}, "
                f"Violations: {len(violations)}, Warnings: {len(warnings)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in pre-trade risk validation: {str(e)}")
            # In case of error, be conservative and block the order
            violation = RiskViolation(
                violation_type="validation_error",
                severity="critical",
                symbol=order_request.symbol,
                message=f"Risk validation failed: {str(e)}",
                recommended_action=RiskAction.BLOCK_ORDER,
                violation_value=0,
                limit_value=0,
                timestamp=datetime.now(timezone.utc)
            )
            
            return RiskControlResult(
                approved=False,
                violations=[violation],
                warnings=[],
                recommended_actions=[RiskAction.BLOCK_ORDER]
            )
    
    def monitor_position_risk(self, symbol: str, current_price: Decimal) -> List[RiskViolation]:
        """
        Monitor risk for a specific position in real-time.
        
        Args:
            symbol: Symbol to monitor
            current_price: Current market price
            
        Returns:
            List of risk violations detected
        """
        try:
            violations = []
            
            # Get current portfolio
            portfolio = self.alpaca_client.get_portfolio_snapshot()
            position = portfolio.get_position(symbol)
            
            if not position:
                return violations  # No position to monitor
            
            # Check stop-loss conditions
            if position.is_long():
                # Long position - check for downward price movement
                avg_cost = position.average_cost
                stop_loss_price = avg_cost * (Decimal('1') - Decimal(str(self.risk_limits.stop_loss_percentage)))
                
                if current_price <= stop_loss_price:
                    violation = RiskViolation(
                        violation_type="stop_loss_triggered",
                        severity="high",
                        symbol=symbol,
                        message=f"Stop-loss triggered for {symbol}: price ${current_price} <= stop ${stop_loss_price:.2f}",
                        recommended_action=RiskAction.CLOSE_POSITION,
                        violation_value=float(current_price),
                        limit_value=float(stop_loss_price),
                        timestamp=datetime.now(timezone.utc)
                    )
                    violations.append(violation)
            
            elif position.is_short():
                # Short position - check for upward price movement
                avg_cost = position.average_cost
                stop_loss_price = avg_cost * (Decimal('1') + Decimal(str(self.risk_limits.stop_loss_percentage)))
                
                if current_price >= stop_loss_price:
                    violation = RiskViolation(
                        violation_type="stop_loss_triggered",
                        severity="high",
                        symbol=symbol,
                        message=f"Stop-loss triggered for {symbol}: price ${current_price} >= stop ${stop_loss_price:.2f}",
                        recommended_action=RiskAction.CLOSE_POSITION,
                        violation_value=float(current_price),
                        limit_value=float(stop_loss_price),
                        timestamp=datetime.now(timezone.utc)
                    )
                    violations.append(violation)
            
            # Check position size limits
            position_value = abs(position.quantity * current_price)
            if position_value > self.risk_limits.max_position_size:
                violation = RiskViolation(
                    violation_type="position_size_exceeded",
                    severity="medium",
                    symbol=symbol,
                    message=f"Position size ${position_value:,.2f} exceeds limit ${self.risk_limits.max_position_size:,.2f}",
                    recommended_action=RiskAction.REDUCE_POSITION,
                    violation_value=float(position_value),
                    limit_value=float(self.risk_limits.max_position_size),
                    timestamp=datetime.now(timezone.utc)
                )
                violations.append(violation)
            
            # Check concentration limits
            if portfolio.total_value > 0:
                concentration = float(position_value / portfolio.total_value)
                if concentration > self.risk_limits.max_portfolio_concentration:
                    violation = RiskViolation(
                        violation_type="concentration_exceeded",
                        severity="medium",
                        symbol=symbol,
                        message=f"Position concentration {concentration:.1%} exceeds limit {self.risk_limits.max_portfolio_concentration:.1%}",
                        recommended_action=RiskAction.REDUCE_POSITION,
                        violation_value=concentration,
                        limit_value=self.risk_limits.max_portfolio_concentration,
                        timestamp=datetime.now(timezone.utc)
                    )
                    violations.append(violation)
            
            return violations
            
        except Exception as e:
            logger.error(f"Error monitoring position risk for {symbol}: {str(e)}")
            return []
    
    def execute_automatic_risk_action(self, violation: RiskViolation) -> bool:
        """
        Execute automatic risk management action.
        
        Args:
            violation: Risk violation that triggered the action
            
        Returns:
            True if action was executed successfully, False otherwise
        """
        try:
            logger.info(f"Executing automatic risk action: {violation.recommended_action.value}")
            
            if violation.recommended_action == RiskAction.BLOCK_ORDER:
                # Order blocking is handled in validation, no action needed here
                return True
            
            elif violation.recommended_action == RiskAction.CLOSE_POSITION:
                return self._close_position(violation.symbol)
            
            elif violation.recommended_action == RiskAction.REDUCE_POSITION:
                return self._reduce_position(violation.symbol, 0.5)  # Reduce by 50%
            
            elif violation.recommended_action == RiskAction.STOP_TRADING:
                return self._halt_trading()
            
            elif violation.recommended_action == RiskAction.REBALANCE_PORTFOLIO:
                return self._trigger_portfolio_rebalance()
            
            elif violation.recommended_action == RiskAction.ALERT_ONLY:
                # Just log the alert, no action needed
                logger.warning(f"Risk alert: {violation.message}")
                return True
            
            else:
                logger.warning(f"Unknown risk action: {violation.recommended_action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing risk action {violation.recommended_action}: {str(e)}")
            return False
    
    def start_real_time_monitoring(self) -> None:
        """Start real-time risk monitoring."""
        if self._monitoring_active:
            logger.warning("Risk monitoring is already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Real-time risk monitoring started")
    
    def stop_real_time_monitoring(self) -> None:
        """Stop real-time risk monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=10)
        logger.info("Real-time risk monitoring stopped")
    
    def register_risk_callback(self, callback: Callable[[RiskViolation], None]) -> None:
        """
        Register a callback for risk violations.
        
        Args:
            callback: Function to call when risk violations are detected
        """
        self._risk_callbacks.append(callback)
        logger.debug("Risk callback registered")
    
    def halt_trading(self) -> None:
        """Halt all trading due to risk violations."""
        self._trading_halted = True
        logger.critical("Trading halted due to risk violations")
    
    def resume_trading(self) -> None:
        """Resume trading after risk issues are resolved."""
        self._trading_halted = False
        logger.info("Trading resumed")
    
    def is_trading_halted(self) -> bool:
        """Check if trading is currently halted."""
        return self._trading_halted
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """
        Get risk control statistics.
        
        Returns:
            Dictionary with risk control metrics
        """
        stats = self._risk_stats.copy()
        
        # Calculate derived metrics
        if stats['total_orders_checked'] > 0:
            stats['block_rate'] = stats['orders_blocked'] / stats['total_orders_checked']
            stats['modification_rate'] = stats['orders_modified'] / stats['total_orders_checked']
        else:
            stats['block_rate'] = 0.0
            stats['modification_rate'] = 0.0
        
        stats['trading_halted'] = self._trading_halted
        stats['monitoring_active'] = self._monitoring_active
        
        return stats
    
    def _perform_additional_risk_checks(self, order_request: OrderRequest, 
                                      portfolio: PortfolioSnapshot) -> List[RiskViolation]:
        """Perform additional risk checks beyond basic validation."""
        violations = []
        
        try:
            # Check daily loss limits
            daily_pnl = float(portfolio.day_pnl)
            if daily_pnl < -float(self.risk_limits.max_daily_loss):
                violation = RiskViolation(
                    violation_type="daily_loss_exceeded",
                    severity="high",
                    symbol=order_request.symbol,
                    message=f"Daily loss ${abs(daily_pnl):,.2f} exceeds limit ${self.risk_limits.max_daily_loss:,.2f}",
                    recommended_action=RiskAction.STOP_TRADING,
                    violation_value=abs(daily_pnl),
                    limit_value=float(self.risk_limits.max_daily_loss),
                    timestamp=datetime.now(timezone.utc)
                )
                violations.append(violation)
            
            # Check market hours (if applicable)
            if not self.alpaca_client.is_market_open():
                # This is a warning, not a violation for most order types
                pass
            
            # Check account status
            try:
                account_info = self.alpaca_client.get_account_info()
                if account_info.get('trading_blocked', False):
                    violation = RiskViolation(
                        violation_type="account_trading_blocked",
                        severity="critical",
                        symbol=order_request.symbol,
                        message="Account trading is blocked",
                        recommended_action=RiskAction.BLOCK_ORDER,
                        violation_value=1,
                        limit_value=0,
                        timestamp=datetime.now(timezone.utc)
                    )
                    violations.append(violation)
            except Exception as e:
                logger.warning(f"Could not check account status: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in additional risk checks: {str(e)}")
        
        return violations
    
    def _determine_violation_severity(self, violation_type: str) -> str:
        """Determine severity level for a violation type."""
        severity_mapping = {
            'max_position_size': 'medium',
            'max_concentration': 'medium',
            'max_daily_loss': 'high',
            'stop_loss_triggered': 'high',
            'daily_loss_exceeded': 'high',
            'account_trading_blocked': 'critical',
            'trading_halted': 'critical',
            'validation_error': 'critical'
        }
        
        return severity_mapping.get(violation_type, 'medium')
    
    def _determine_recommended_action(self, violation_type: str, severity: str) -> RiskAction:
        """Determine recommended action for a violation."""
        if severity == 'critical':
            return RiskAction.BLOCK_ORDER
        
        action_mapping = {
            'max_position_size': RiskAction.REDUCE_POSITION,
            'max_concentration': RiskAction.REDUCE_POSITION,
            'max_daily_loss': RiskAction.STOP_TRADING,
            'stop_loss_triggered': RiskAction.CLOSE_POSITION,
            'daily_loss_exceeded': RiskAction.STOP_TRADING,
            'position_size_exceeded': RiskAction.REDUCE_POSITION,
            'concentration_exceeded': RiskAction.REDUCE_POSITION
        }
        
        return action_mapping.get(violation_type, RiskAction.ALERT_ONLY)
    
    def _suggest_order_modification(self, order_request: OrderRequest, 
                                  portfolio: PortfolioSnapshot) -> Optional[OrderRequest]:
        """Suggest order modification to comply with risk limits."""
        try:
            if order_request.limit_price is None:
                return None  # Can't modify market orders safely
            
            # Calculate maximum allowed position value
            max_position_value = float(self.risk_limits.max_position_size)
            max_concentration_value = float(portfolio.total_value) * self.risk_limits.max_portfolio_concentration
            
            # Use the more restrictive limit
            max_allowed_value = min(max_position_value, max_concentration_value)
            
            # Calculate maximum quantity
            max_quantity = int(max_allowed_value / float(order_request.limit_price))
            
            if max_quantity > 0 and max_quantity < order_request.quantity:
                # Create modified order request
                modified_request = OrderRequest(
                    symbol=order_request.symbol,
                    quantity=max_quantity,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    limit_price=order_request.limit_price,
                    stop_price=order_request.stop_price,
                    time_in_force=order_request.time_in_force,
                    execution_strategy=order_request.execution_strategy,
                    max_participation_rate=order_request.max_participation_rate,
                    urgency=order_request.urgency,
                    client_order_id=order_request.client_order_id
                )
                
                return modified_request
            
            return None
            
        except Exception as e:
            logger.error(f"Error suggesting order modification: {str(e)}")
            return None
    
    def _close_position(self, symbol: str) -> bool:
        """Close a position completely."""
        try:
            portfolio = self.alpaca_client.get_portfolio_snapshot()
            position = portfolio.get_position(symbol)
            
            if not position:
                logger.warning(f"No position found for {symbol} to close")
                return True  # No position to close
            
            # Create market order to close position
            side = OrderSide.SELL if position.is_long() else OrderSide.BUY
            quantity = abs(position.quantity)
            
            # Submit order via Alpaca API
            self.alpaca_client._api.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side.value,
                type="market",
                time_in_force="day"
            )
            
            self._risk_stats['automatic_actions_taken'] += 1
            logger.info(f"Position closed for {symbol}: {side.value} {quantity} shares")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return False
    
    def _reduce_position(self, symbol: str, reduction_factor: float) -> bool:
        """Reduce a position by a specified factor."""
        try:
            portfolio = self.alpaca_client.get_portfolio_snapshot()
            position = portfolio.get_position(symbol)
            
            if not position:
                logger.warning(f"No position found for {symbol} to reduce")
                return True
            
            # Calculate quantity to sell/buy back
            reduction_quantity = int(abs(position.quantity) * reduction_factor)
            if reduction_quantity == 0:
                return True  # Nothing to reduce
            
            # Create market order to reduce position
            side = OrderSide.SELL if position.is_long() else OrderSide.BUY
            
            # Submit order via Alpaca API
            self.alpaca_client._api.submit_order(
                symbol=symbol,
                qty=reduction_quantity,
                side=side.value,
                type="market",
                time_in_force="day"
            )
            
            self._risk_stats['automatic_actions_taken'] += 1
            logger.info(f"Position reduced for {symbol}: {side.value} {reduction_quantity} shares")
            return True
            
        except Exception as e:
            logger.error(f"Error reducing position for {symbol}: {str(e)}")
            return False
    
    def _halt_trading(self) -> bool:
        """Halt all trading."""
        self._trading_halted = True
        self._risk_stats['automatic_actions_taken'] += 1
        logger.critical("Trading automatically halted due to risk violation")
        return True
    
    def _trigger_portfolio_rebalance(self) -> bool:
        """Trigger portfolio rebalancing."""
        # This would integrate with a portfolio rebalancing system
        # For now, just log the action
        logger.info("Portfolio rebalancing triggered due to risk violation")
        self._risk_stats['automatic_actions_taken'] += 1
        return True
    
    def _trigger_risk_callbacks(self, violation: RiskViolation) -> None:
        """Trigger registered risk callbacks."""
        for callback in self._risk_callbacks:
            try:
                callback(violation)
            except Exception as e:
                logger.error(f"Error in risk callback: {str(e)}")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop for real-time risk monitoring."""
        logger.info("Risk monitoring loop started")
        
        while self._monitoring_active:
            try:
                # Get current portfolio
                portfolio = self.alpaca_client.get_portfolio_snapshot()
                
                # Monitor each position
                for position in portfolio.positions:
                    # Get current price (simplified - would use market data client)
                    current_price = position.current_price
                    
                    # Monitor position risk
                    violations = self.monitor_position_risk(position.symbol, current_price)
                    
                    # Execute automatic actions for high-severity violations
                    for violation in violations:
                        if violation.severity in ["high", "critical"]:
                            self.execute_automatic_risk_action(violation)
                        
                        # Trigger callbacks
                        self._trigger_risk_callbacks(violation)
                
                # Monitor portfolio-level risks
                self._monitor_portfolio_level_risks(portfolio)
                
                # Store snapshot for trend analysis
                self._last_portfolio_snapshot = portfolio
                
                # Sleep between monitoring cycles
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {str(e)}")
                time.sleep(60)  # Longer sleep on error
        
        logger.info("Risk monitoring loop stopped")
    
    def _monitor_portfolio_level_risks(self, portfolio: PortfolioSnapshot) -> None:
        """Monitor portfolio-level risk violations."""
        try:
            # Check daily loss limits
            daily_pnl = float(portfolio.day_pnl)
            if daily_pnl < -float(self.risk_limits.max_daily_loss):
                violation = RiskViolation(
                    violation_type="daily_loss_exceeded",
                    severity="high",
                    symbol=None,
                    message=f"Daily loss ${abs(daily_pnl):,.2f} exceeds limit ${self.risk_limits.max_daily_loss:,.2f}",
                    recommended_action=RiskAction.STOP_TRADING,
                    violation_value=abs(daily_pnl),
                    limit_value=float(self.risk_limits.max_daily_loss),
                    timestamp=datetime.now(timezone.utc)
                )
                
                self.execute_automatic_risk_action(violation)
                self._trigger_risk_callbacks(violation)
            
        except Exception as e:
            logger.error(f"Error monitoring portfolio-level risks: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_real_time_monitoring()