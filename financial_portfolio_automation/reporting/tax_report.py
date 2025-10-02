"""
Tax Report Generator.

This module generates comprehensive tax reports including realized gains/losses,
wash sale detection, and tax-loss harvesting opportunities.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.core import Order, Position
from ..data.store import DataStore
from ..execution.trade_logger import TradeLogger


class TaxLotMethod(Enum):
    """Tax lot accounting methods."""
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    SPECIFIC_ID = "specific_id"  # Specific identification
    AVERAGE_COST = "average_cost"  # Average cost basis


class GainLossType(Enum):
    """Capital gain/loss classification."""
    SHORT_TERM = "short_term"  # Held <= 1 year
    LONG_TERM = "long_term"    # Held > 1 year


@dataclass
class TaxLot:
    """Individual tax lot for tracking cost basis."""
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    acquisition_date: date
    lot_id: str


@dataclass
class RealizedGainLoss:
    """Realized capital gain or loss transaction."""
    symbol: str
    quantity: Decimal
    sale_date: date
    sale_price: Decimal
    cost_basis: Decimal
    gain_loss: Decimal
    gain_loss_type: GainLossType
    wash_sale_adjustment: Decimal = Decimal('0')
    is_wash_sale: bool = False
    acquisition_date: Optional[date] = None
    holding_period_days: Optional[int] = None


@dataclass
class WashSaleTransaction:
    """Wash sale rule violation."""
    symbol: str
    sale_date: date
    sale_quantity: Decimal
    disallowed_loss: Decimal
    repurchase_date: date
    repurchase_quantity: Decimal
    adjusted_basis: Decimal


@dataclass
class TaxSummary:
    """Tax year summary."""
    tax_year: int
    total_short_term_gain_loss: Decimal
    total_long_term_gain_loss: Decimal
    total_gain_loss: Decimal
    wash_sale_adjustments: Decimal
    tax_loss_carryforward: Decimal


class TaxReport:
    """
    Tax report generator for capital gains/losses and compliance.
    
    Handles tax lot tracking, wash sale detection, and generates
    reports for tax filing purposes.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        trade_logger: TradeLogger,
        tax_lot_method: TaxLotMethod = TaxLotMethod.FIFO
    ):
        """
        Initialize tax report generator.
        
        Args:
            data_store: Data storage interface
            trade_logger: Trade logging system
            tax_lot_method: Method for tax lot accounting
        """
        self.data_store = data_store
        self.trade_logger = trade_logger
        self.tax_lot_method = tax_lot_method
        self.logger = logging.getLogger(__name__)
        
        # Tax lot tracking
        self._tax_lots: Dict[str, List[TaxLot]] = {}
        self._realized_gains_losses: List[RealizedGainLoss] = []
        self._wash_sales: List[WashSaleTransaction] = []
    
    def generate_data(
        self,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate tax report data for the specified period.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            symbols: Optional symbol filter
            
        Returns:
            Dictionary containing all tax report data
        """
        self.logger.info(
            f"Generating tax report data: {start_date} to {end_date}"
        )
        
        # Initialize tax lot tracking
        self._initialize_tax_lots(start_date, symbols)
        
        # Process all transactions in the period
        transactions = self._get_transactions(start_date, end_date, symbols)
        
        for transaction in transactions:
            self._process_transaction(transaction)
        
        # Detect wash sales
        self._detect_wash_sales(start_date, end_date)
        
        # Generate tax summary
        tax_summary = self._generate_tax_summary(start_date.year)
        
        # Prepare detailed reports
        detailed_transactions = self._prepare_detailed_transactions()
        form_8949_data = self._prepare_form_8949_data()
        tax_loss_opportunities = self._identify_tax_loss_opportunities()
        
        return {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': start_date,
                'end_date': end_date,
                'tax_year': start_date.year,
                'tax_lot_method': self.tax_lot_method.value,
                'symbols_filter': symbols
            },
            'tax_summary': tax_summary,
            'realized_gains_losses': self._realized_gains_losses,
            'wash_sales': self._wash_sales,
            'detailed_transactions': detailed_transactions,
            'form_8949_data': form_8949_data,
            'tax_loss_opportunities': tax_loss_opportunities,
            'current_tax_lots': self._get_current_tax_lots_summary()
        }
    
    def _initialize_tax_lots(
        self, 
        start_date: date, 
        symbols: Optional[List[str]] = None
    ) -> None:
        """Initialize tax lots from historical positions."""
        # Get positions at start of period
        positions = self.data_store.get_positions_at_date(start_date)
        
        if symbols:
            positions = [p for p in positions if p.symbol in symbols]
        
        for position in positions:
            if position.quantity > 0:
                # Create initial tax lot (simplified - would need historical data)
                lot = TaxLot(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    cost_basis=position.cost_basis,
                    acquisition_date=start_date,  # Approximation
                    lot_id=f"{position.symbol}_{start_date.isoformat()}_initial"
                )
                
                if position.symbol not in self._tax_lots:
                    self._tax_lots[position.symbol] = []
                
                self._tax_lots[position.symbol].append(lot)
    
    def _get_transactions(
        self,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None
    ) -> List[Order]:
        """Get all transactions for the specified period."""
        orders = self.data_store.get_orders(
            start_date=start_date,
            end_date=end_date,
            status='FILLED'
        )
        
        if symbols:
            orders = [o for o in orders if o.symbol in symbols]
        
        return sorted(orders, key=lambda o: o.filled_at or o.created_at)
    
    def _process_transaction(self, order: Order) -> None:
        """Process a single transaction for tax purposes."""
        if order.side == 'BUY':
            self._process_buy_transaction(order)
        elif order.side == 'SELL':
            self._process_sell_transaction(order)
    
    def _process_buy_transaction(self, order: Order) -> None:
        """Process a buy transaction - create new tax lot."""
        lot = TaxLot(
            symbol=order.symbol,
            quantity=order.filled_quantity,
            cost_basis=order.filled_quantity * order.average_fill_price,
            acquisition_date=(order.filled_at or order.created_at).date(),
            lot_id=f"{order.symbol}_{order.order_id}"
        )
        
        if order.symbol not in self._tax_lots:
            self._tax_lots[order.symbol] = []
        
        self._tax_lots[order.symbol].append(lot)
        
        self.logger.debug(f"Created tax lot: {lot.lot_id}")
    
    def _process_sell_transaction(self, order: Order) -> None:
        """Process a sell transaction - realize gains/losses."""
        symbol = order.symbol
        sell_quantity = order.filled_quantity
        sell_price = order.average_fill_price
        sell_date = (order.filled_at or order.created_at).date()
        
        if symbol not in self._tax_lots:
            self.logger.warning(f"No tax lots found for sale: {symbol}")
            return
        
        remaining_quantity = sell_quantity
        
        while remaining_quantity > 0 and self._tax_lots[symbol]:
            # Select tax lot based on method
            lot = self._select_tax_lot(symbol)
            
            if not lot:
                break
            
            # Determine quantity to sell from this lot
            lot_sell_quantity = min(remaining_quantity, lot.quantity)
            
            # Calculate gain/loss
            cost_basis_per_share = lot.cost_basis / lot.quantity
            total_cost_basis = lot_sell_quantity * cost_basis_per_share
            total_proceeds = lot_sell_quantity * sell_price
            gain_loss = total_proceeds - total_cost_basis
            
            # Determine holding period
            holding_days = (sell_date - lot.acquisition_date).days
            gain_loss_type = (
                GainLossType.LONG_TERM if holding_days > 365 
                else GainLossType.SHORT_TERM
            )
            
            # Create realized gain/loss record
            realized_gl = RealizedGainLoss(
                symbol=symbol,
                quantity=lot_sell_quantity,
                sale_date=sell_date,
                sale_price=sell_price,
                cost_basis=total_cost_basis,
                gain_loss=gain_loss,
                gain_loss_type=gain_loss_type,
                acquisition_date=lot.acquisition_date,
                holding_period_days=holding_days
            )
            
            self._realized_gains_losses.append(realized_gl)
            
            # Update tax lot
            lot.quantity -= lot_sell_quantity
            lot.cost_basis -= total_cost_basis
            
            # Remove lot if fully sold
            if lot.quantity <= 0:
                self._tax_lots[symbol].remove(lot)
            
            remaining_quantity -= lot_sell_quantity
            
            self.logger.debug(
                f"Realized {gain_loss_type.value} gain/loss: "
                f"{symbol} ${gain_loss:.2f}"
            )
    
    def _select_tax_lot(self, symbol: str) -> Optional[TaxLot]:
        """Select tax lot based on accounting method."""
        lots = self._tax_lots.get(symbol, [])
        
        if not lots:
            return None
        
        if self.tax_lot_method == TaxLotMethod.FIFO:
            return min(lots, key=lambda l: l.acquisition_date)
        elif self.tax_lot_method == TaxLotMethod.LIFO:
            return max(lots, key=lambda l: l.acquisition_date)
        else:
            # Default to FIFO
            return min(lots, key=lambda l: l.acquisition_date)
    
    def _detect_wash_sales(self, start_date: date, end_date: date) -> None:
        """Detect wash sale rule violations."""
        # Group losses by symbol
        losses_by_symbol = {}
        
        for gl in self._realized_gains_losses:
            if gl.gain_loss < 0:  # Only losses can be wash sales
                if gl.symbol not in losses_by_symbol:
                    losses_by_symbol[gl.symbol] = []
                losses_by_symbol[gl.symbol].append(gl)
        
        # Check for repurchases within 30 days
        for symbol, losses in losses_by_symbol.items():
            for loss in losses:
                wash_sale = self._check_wash_sale_violation(
                    loss, start_date, end_date
                )
                if wash_sale:
                    self._wash_sales.append(wash_sale)
                    
                    # Adjust the loss
                    loss.is_wash_sale = True
                    loss.wash_sale_adjustment = abs(loss.gain_loss)
                    loss.gain_loss = Decimal('0')  # Disallow the loss
    
    def _check_wash_sale_violation(
        self,
        loss_transaction: RealizedGainLoss,
        start_date: date,
        end_date: date
    ) -> Optional[WashSaleTransaction]:
        """Check if a loss transaction violates wash sale rules."""
        symbol = loss_transaction.symbol
        sale_date = loss_transaction.sale_date
        
        # Check 30 days before and after sale
        wash_start = sale_date - timedelta(days=30)
        wash_end = sale_date + timedelta(days=30)
        
        # Get all buy transactions in wash sale period
        buy_orders = self.data_store.get_orders(
            start_date=max(wash_start, start_date),
            end_date=min(wash_end, end_date),
            symbol=symbol,
            side='BUY',
            status='FILLED'
        )
        
        # Exclude the sale date itself
        buy_orders = [
            o for o in buy_orders 
            if (o.filled_at or o.created_at).date() != sale_date
        ]
        
        if buy_orders:
            # Find the first repurchase (simplified)
            repurchase = min(
                buy_orders, 
                key=lambda o: abs(
                    (o.filled_at or o.created_at).date() - sale_date
                ).days
            )
            
            return WashSaleTransaction(
                symbol=symbol,
                sale_date=sale_date,
                sale_quantity=loss_transaction.quantity,
                disallowed_loss=abs(loss_transaction.gain_loss),
                repurchase_date=(repurchase.filled_at or repurchase.created_at).date(),
                repurchase_quantity=repurchase.filled_quantity,
                adjusted_basis=repurchase.filled_quantity * repurchase.average_fill_price + abs(loss_transaction.gain_loss)
            )
        
        return None
    
    def _generate_tax_summary(self, tax_year: int) -> TaxSummary:
        """Generate tax year summary."""
        short_term_total = sum(
            gl.gain_loss for gl in self._realized_gains_losses
            if gl.gain_loss_type == GainLossType.SHORT_TERM
        )
        
        long_term_total = sum(
            gl.gain_loss for gl in self._realized_gains_losses
            if gl.gain_loss_type == GainLossType.LONG_TERM
        )
        
        wash_sale_adjustments = sum(
            gl.wash_sale_adjustment for gl in self._realized_gains_losses
        )
        
        total_gain_loss = short_term_total + long_term_total
        
        # Calculate tax loss carryforward (simplified)
        tax_loss_carryforward = min(total_gain_loss, Decimal('0'))
        
        return TaxSummary(
            tax_year=tax_year,
            total_short_term_gain_loss=short_term_total,
            total_long_term_gain_loss=long_term_total,
            total_gain_loss=total_gain_loss,
            wash_sale_adjustments=wash_sale_adjustments,
            tax_loss_carryforward=tax_loss_carryforward
        )
    
    def _prepare_detailed_transactions(self) -> List[Dict[str, Any]]:
        """Prepare detailed transaction list for reporting."""
        transactions = []
        
        for gl in self._realized_gains_losses:
            transactions.append({
                'symbol': gl.symbol,
                'quantity': float(gl.quantity),
                'acquisition_date': gl.acquisition_date.isoformat() if gl.acquisition_date else None,
                'sale_date': gl.sale_date.isoformat(),
                'sale_price': float(gl.sale_price),
                'cost_basis': float(gl.cost_basis),
                'proceeds': float(gl.quantity * gl.sale_price),
                'gain_loss': float(gl.gain_loss),
                'gain_loss_type': gl.gain_loss_type.value,
                'holding_period_days': gl.holding_period_days,
                'is_wash_sale': gl.is_wash_sale,
                'wash_sale_adjustment': float(gl.wash_sale_adjustment)
            })
        
        return sorted(transactions, key=lambda t: t['sale_date'])
    
    def _prepare_form_8949_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Prepare data for IRS Form 8949."""
        short_term = []
        long_term = []
        
        for gl in self._realized_gains_losses:
            form_entry = {
                'description': f"{gl.quantity} shares {gl.symbol}",
                'acquisition_date': gl.acquisition_date.strftime('%m/%d/%Y') if gl.acquisition_date else '',
                'sale_date': gl.sale_date.strftime('%m/%d/%Y'),
                'proceeds': float(gl.quantity * gl.sale_price),
                'cost_basis': float(gl.cost_basis),
                'adjustment_code': 'W' if gl.is_wash_sale else '',
                'adjustment_amount': float(gl.wash_sale_adjustment) if gl.is_wash_sale else 0,
                'gain_loss': float(gl.gain_loss)
            }
            
            if gl.gain_loss_type == GainLossType.SHORT_TERM:
                short_term.append(form_entry)
            else:
                long_term.append(form_entry)
        
        return {
            'short_term': short_term,
            'long_term': long_term
        }
    
    def _identify_tax_loss_opportunities(self) -> List[Dict[str, Any]]:
        """Identify potential tax-loss harvesting opportunities."""
        opportunities = []
        
        # Get current positions with unrealized losses
        current_positions = self.data_store.get_current_positions()
        
        for position in current_positions:
            if position.unrealized_pnl < 0:  # Unrealized loss
                # Check if not subject to wash sale rules
                recent_sales = [
                    gl for gl in self._realized_gains_losses
                    if gl.symbol == position.symbol and
                    (date.today() - gl.sale_date).days <= 30
                ]
                
                if not recent_sales:
                    opportunities.append({
                        'symbol': position.symbol,
                        'quantity': float(position.quantity),
                        'current_value': float(position.market_value),
                        'cost_basis': float(position.cost_basis),
                        'unrealized_loss': float(position.unrealized_pnl),
                        'potential_tax_benefit': float(abs(position.unrealized_pnl) * Decimal('0.22'))  # Assume 22% tax rate
                    })
        
        return sorted(
            opportunities, 
            key=lambda o: o['unrealized_loss']
        )
    
    def _get_current_tax_lots_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get summary of current tax lots by symbol."""
        summary = {}
        
        for symbol, lots in self._tax_lots.items():
            if lots:
                summary[symbol] = [
                    {
                        'lot_id': lot.lot_id,
                        'quantity': float(lot.quantity),
                        'cost_basis': float(lot.cost_basis),
                        'cost_per_share': float(lot.cost_basis / lot.quantity) if lot.quantity > 0 else 0,
                        'acquisition_date': lot.acquisition_date.isoformat(),
                        'holding_period_days': (date.today() - lot.acquisition_date).days
                    }
                    for lot in lots
                ]
        
        return summary