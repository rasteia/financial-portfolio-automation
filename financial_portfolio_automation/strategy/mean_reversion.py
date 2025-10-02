"""
Mean reversion strategy implementation.

This module implements mean reversion trading strategies that identify
when prices deviate significantly from their historical average and
generate signals expecting a return to the mean.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
import logging
import statistics

from .base import Strategy, StrategySignal, SignalType
from ..models.core import Quote, PortfolioSnapshot
from ..models.config import StrategyConfig
from ..analysis.technical_analysis import TechnicalAnalysis


logger = logging.getLogger(__name__)


class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy that identifies overbought/oversold conditions.
    
    This strategy generates buy signals when prices are significantly below
    their historical mean and sell signals when prices are above the mean.
    """
    
    def __init__(self, config: StrategyConfig):
        """
        Initialize mean reversion strategy.
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        self.technical_analysis = TechnicalAnalysis()
        
        # Strategy parameters with defaults
        self.lookback_period = config.parameters.get('lookback_period', 20)
        self.std_dev_threshold = config.parameters.get('std_dev_threshold', 2.0)
        self.rsi_oversold = config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 70)
        self.bollinger_period = config.parameters.get('bollinger_period', 20)
        self.bollinger_std = config.parameters.get('bollinger_std', 2.0)
        self.min_reversion_strength = config.parameters.get('min_reversion_strength', 0.5)
        
        # Mean reversion specific parameters
        self.mean_reversion_threshold = config.parameters.get('mean_reversion_threshold', 0.05)  # 5%
        self.volume_confirmation = config.parameters.get('volume_confirmation', True)
        self.trend_filter = config.parameters.get('trend_filter', True)
        
        self.logger.info(f"Initialized mean reversion strategy with {self.lookback_period} period lookback")
    
    def generate_signals(
        self,
        market_data: Dict[str, Quote],
        portfolio: PortfolioSnapshot,
        historical_data: Optional[Dict[str, List[Quote]]] = None
    ) -> List[StrategySignal]:
        """
        Generate mean reversion trading signals.
        
        Args:
            market_data: Current market quotes
            portfolio: Current portfolio snapshot
            historical_data: Historical market data for analysis
            
        Returns:
            List of mean reversion trading signals
        """
        signals = []
        
        if not historical_data:
            self.logger.warning("No historical data provided for mean reversion analysis")
            return signals
        
        for symbol in self.symbols:
            if symbol not in market_data:
                self.logger.debug(f"No current market data for {symbol}")
                continue
            
            if symbol not in historical_data or len(historical_data[symbol]) < self.lookback_period:
                self.logger.debug(f"Insufficient historical data for {symbol}")
                continue
            
            try:
                signal = self._analyze_mean_reversion(symbol, market_data[symbol], historical_data[symbol])
                if signal:
                    signals.append(signal)
            except Exception as e:
                self.logger.error(f"Error analyzing mean reversion for {symbol}: {e}")
        
        return signals
    
    def _analyze_mean_reversion(
        self,
        symbol: str,
        current_quote: Quote,
        historical_quotes: List[Quote]
    ) -> Optional[StrategySignal]:
        """
        Analyze mean reversion opportunity for a specific symbol.
        
        Args:
            symbol: Symbol to analyze
            current_quote: Current market quote
            historical_quotes: Historical quotes for analysis
            
        Returns:
            Mean reversion signal if conditions are met, None otherwise
        """
        # Extract price and volume data
        prices = [float(quote.close) for quote in historical_quotes[-self.lookback_period:]]
        volumes = [quote.volume for quote in historical_quotes[-self.lookback_period:]]
        
        if len(prices) < self.lookback_period:
            return None
        
        current_price = float(current_quote.close)
        
        # Calculate statistical measures
        mean_price = statistics.mean(prices)
        std_dev = statistics.stdev(prices) if len(prices) > 1 else 0
        
        # Calculate technical indicators
        rsi = self.technical_analysis.calculate_rsi(prices, period=14)
        bollinger_upper, bollinger_middle, bollinger_lower = self.technical_analysis.calculate_bollinger_bands(
            prices, period=self.bollinger_period, std_dev=self.bollinger_std
        )
        
        # Calculate price deviation from mean
        price_deviation = (current_price - mean_price) / mean_price if mean_price > 0 else 0
        z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0
        
        # Volume analysis
        avg_volume = statistics.mean(volumes[-10:]) if len(volumes) >= 10 else statistics.mean(volumes)
        volume_ratio = current_quote.volume / avg_volume if avg_volume > 0 else 1
        
        # Trend filter (optional)
        trend_direction = None
        if self.trend_filter:
            sma_short = self.technical_analysis.calculate_sma(prices, period=10)
            sma_long = self.technical_analysis.calculate_sma(prices, period=20)
            if sma_short and sma_long:
                trend_direction = 'up' if sma_short[-1] > sma_long[-1] else 'down'
        
        metadata = {
            'mean_price': mean_price,
            'std_dev': std_dev,
            'price_deviation': price_deviation,
            'z_score': z_score,
            'rsi': rsi[-1] if rsi else None,
            'bollinger_upper': bollinger_upper[-1] if bollinger_upper else None,
            'bollinger_lower': bollinger_lower[-1] if bollinger_lower else None,
            'volume_ratio': volume_ratio,
            'trend_direction': trend_direction
        }
        
        # Determine signal type and strength
        signal_type = SignalType.HOLD
        signal_strength = 0.0
        
        # Oversold conditions (potential buy signal)
        oversold_conditions = []
        
        # Price significantly below mean
        if price_deviation < -self.mean_reversion_threshold:
            oversold_conditions.append(abs(price_deviation) * 2)  # Weight by deviation magnitude
        
        # Z-score indicates oversold
        if z_score < -self.std_dev_threshold:
            oversold_conditions.append(min(abs(z_score) / self.std_dev_threshold * 0.3, 0.3))
        
        # RSI oversold
        if rsi and rsi[-1] < self.rsi_oversold:
            oversold_conditions.append(0.25)
        
        # Below Bollinger lower band
        if bollinger_lower and current_price < bollinger_lower[-1]:
            band_deviation = (bollinger_lower[-1] - current_price) / bollinger_lower[-1]
            oversold_conditions.append(min(band_deviation * 2, 0.2))
        
        # Volume confirmation (higher volume on oversold condition)
        if self.volume_confirmation and volume_ratio > 1.2:
            oversold_conditions.append(0.1)
        
        # Overbought conditions (potential sell signal)
        overbought_conditions = []
        
        # Price significantly above mean
        if price_deviation > self.mean_reversion_threshold:
            overbought_conditions.append(price_deviation * 2)
        
        # Z-score indicates overbought
        if z_score > self.std_dev_threshold:
            overbought_conditions.append(min(z_score / self.std_dev_threshold * 0.3, 0.3))
        
        # RSI overbought
        if rsi and rsi[-1] > self.rsi_overbought:
            overbought_conditions.append(0.25)
        
        # Above Bollinger upper band
        if bollinger_upper and current_price > bollinger_upper[-1]:
            band_deviation = (current_price - bollinger_upper[-1]) / bollinger_upper[-1]
            overbought_conditions.append(min(band_deviation * 2, 0.2))
        
        # Volume confirmation (higher volume on overbought condition)
        if self.volume_confirmation and volume_ratio > 1.2:
            overbought_conditions.append(0.1)
        
        # Calculate signal strength
        oversold_strength = sum(oversold_conditions)
        overbought_strength = sum(overbought_conditions)
        
        # Apply trend filter
        if self.trend_filter and trend_direction:
            if trend_direction == 'down' and oversold_strength > 0:
                oversold_strength *= 0.7  # Reduce strength against trend
            elif trend_direction == 'up' and overbought_strength > 0:
                overbought_strength *= 0.7  # Reduce strength against trend
        
        # Determine signal
        if oversold_strength > overbought_strength and oversold_strength >= self.min_reversion_strength:
            signal_type = SignalType.BUY
            signal_strength = min(oversold_strength, 1.0)
        elif overbought_strength > oversold_strength and overbought_strength >= self.min_reversion_strength:
            # Check if we have a position to sell
            current_position = self.state.positions.get(symbol)
            if current_position and current_position.quantity > 0:
                signal_type = SignalType.SELL
                signal_strength = min(overbought_strength, 1.0)
        
        # Only generate signal if strength meets minimum threshold
        if signal_type != SignalType.HOLD and signal_strength >= self.min_reversion_strength:
            return StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=signal_strength,
                price=current_quote.close,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata
            )
        
        return None
    
    def _calculate_mean_reversion_score(
        self,
        current_price: float,
        historical_prices: List[float],
        rsi_value: Optional[float] = None
    ) -> float:
        """
        Calculate a composite mean reversion score.
        
        Args:
            current_price: Current price
            historical_prices: Historical price data
            rsi_value: Current RSI value
            
        Returns:
            Mean reversion score (positive for oversold, negative for overbought)
        """
        if len(historical_prices) < 2:
            return 0.0
        
        mean_price = statistics.mean(historical_prices)
        std_dev = statistics.stdev(historical_prices)
        
        # Price deviation score
        price_score = (mean_price - current_price) / std_dev if std_dev > 0 else 0
        
        # RSI score
        rsi_score = 0
        if rsi_value is not None:
            if rsi_value < 30:
                rsi_score = (30 - rsi_value) / 30  # Positive for oversold
            elif rsi_value > 70:
                rsi_score = (rsi_value - 70) / 30 * -1  # Negative for overbought
        
        # Combine scores
        composite_score = price_score * 0.7 + rsi_score * 0.3
        
        return composite_score
    
    def update_state(
        self,
        market_data: Dict[str, Quote],
        portfolio: PortfolioSnapshot
    ) -> None:
        """
        Update strategy state based on current market conditions.
        
        Args:
            market_data: Current market quotes
            portfolio: Current portfolio snapshot
        """
        # Update positions from portfolio
        for position in portfolio.positions:
            if position.symbol in self.symbols:
                self.state.update_position(position)
        
        # Remove positions no longer in portfolio
        portfolio_symbols = {pos.symbol for pos in portfolio.positions}
        for symbol in list(self.state.positions.keys()):
            if symbol not in portfolio_symbols:
                self.state.remove_position(symbol)
        
        # Update metadata with current market conditions
        self.state.metadata.update({
            'last_market_update': datetime.now(timezone.utc).isoformat(),
            'market_symbols_available': list(market_data.keys()),
            'portfolio_value': float(portfolio.total_value),
            'strategy_type': 'mean_reversion'
        })