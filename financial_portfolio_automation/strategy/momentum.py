"""
Momentum strategy implementation for trend following.

This module implements momentum-based trading strategies that follow
market trends and generate signals based on price momentum indicators.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
import logging

from .base import Strategy, StrategySignal, SignalType
from ..models.core import Quote, PortfolioSnapshot
from ..models.config import StrategyConfig
from ..analysis.technical_analysis import TechnicalAnalysis


logger = logging.getLogger(__name__)


class MomentumStrategy(Strategy):
    """
    Momentum strategy that follows price trends using technical indicators.
    
    This strategy generates buy signals when momentum indicators suggest
    upward price movement and sell signals when momentum weakens.
    """
    
    def __init__(self, config: StrategyConfig):
        """
        Initialize momentum strategy.
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        self.technical_analysis = TechnicalAnalysis()
        
        # Strategy parameters with defaults
        self.lookback_period = config.parameters.get('lookback_period', 20)
        self.rsi_oversold = config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 70)
        self.macd_signal_threshold = config.parameters.get('macd_signal_threshold', 0.0)
        self.price_change_threshold = config.parameters.get('price_change_threshold', 0.02)  # 2%
        self.volume_threshold = config.parameters.get('volume_threshold', 1.5)  # 1.5x average
        
        # Minimum signal strength for momentum signals
        self.min_momentum_strength = config.parameters.get('min_momentum_strength', 0.6)
        
        self.logger.info(f"Initialized momentum strategy with lookback period {self.lookback_period}")
    
    def generate_signals(
        self,
        market_data: Dict[str, Quote],
        portfolio: PortfolioSnapshot,
        historical_data: Optional[Dict[str, List[Quote]]] = None
    ) -> List[StrategySignal]:
        """
        Generate momentum-based trading signals.
        
        Args:
            market_data: Current market quotes
            portfolio: Current portfolio snapshot
            historical_data: Historical market data for analysis
            
        Returns:
            List of momentum trading signals
        """
        signals = []
        
        if not historical_data:
            self.logger.warning("No historical data provided for momentum analysis")
            return signals
        
        for symbol in self.symbols:
            if symbol not in market_data:
                self.logger.debug(f"No current market data for {symbol}")
                continue
            
            if symbol not in historical_data or len(historical_data[symbol]) < self.lookback_period:
                self.logger.debug(f"Insufficient historical data for {symbol}")
                continue
            
            try:
                signal = self._analyze_momentum(symbol, market_data[symbol], historical_data[symbol])
                if signal:
                    signals.append(signal)
            except Exception as e:
                self.logger.error(f"Error analyzing momentum for {symbol}: {e}")
        
        return signals
    
    def _analyze_momentum(
        self,
        symbol: str,
        current_quote: Quote,
        historical_quotes: List[Quote]
    ) -> Optional[StrategySignal]:
        """
        Analyze momentum for a specific symbol.
        
        Args:
            symbol: Symbol to analyze
            current_quote: Current market quote
            historical_quotes: Historical quotes for analysis
            
        Returns:
            Momentum signal if conditions are met, None otherwise
        """
        # Extract price data
        prices = [float(quote.close) for quote in historical_quotes[-self.lookback_period:]]
        volumes = [quote.volume for quote in historical_quotes[-self.lookback_period:]]
        
        if len(prices) < self.lookback_period:
            return None
        
        # Calculate technical indicators
        rsi = self.technical_analysis.calculate_rsi(prices, period=14)
        macd_line, macd_signal, _ = self.technical_analysis.calculate_macd(prices)
        sma_short = self.technical_analysis.calculate_sma(prices, period=10)
        sma_long = self.technical_analysis.calculate_sma(prices, period=20)
        
        current_price = float(current_quote.close)
        
        # Calculate price momentum
        price_change = (current_price - prices[-2]) / prices[-2] if len(prices) > 1 else 0
        
        # Calculate volume momentum
        avg_volume = sum(volumes[-10:]) / min(10, len(volumes)) if volumes else 0
        volume_ratio = current_quote.volume / avg_volume if avg_volume > 0 else 1
        
        # Determine signal type and strength
        signal_type = SignalType.HOLD
        signal_strength = 0.0
        metadata = {
            'rsi': rsi[-1] if rsi else None,
            'macd_line': macd_line[-1] if macd_line else None,
            'macd_signal': macd_signal[-1] if macd_signal else None,
            'price_change': price_change,
            'volume_ratio': volume_ratio,
            'sma_short': sma_short[-1] if sma_short else None,
            'sma_long': sma_long[-1] if sma_long else None
        }
        
        # Bullish momentum conditions
        bullish_conditions = []
        
        # RSI not overbought and showing momentum
        if rsi and rsi[-1] < self.rsi_overbought and rsi[-1] > 50:
            bullish_conditions.append(0.2)
        
        # MACD bullish crossover
        if (macd_line and macd_signal and len(macd_line) > 1 and len(macd_signal) > 1):
            if macd_line[-1] > macd_signal[-1] and macd_line[-2] <= macd_signal[-2]:
                bullish_conditions.append(0.3)
            elif macd_line[-1] > macd_signal[-1]:
                bullish_conditions.append(0.1)
        
        # Price momentum
        if price_change > self.price_change_threshold:
            bullish_conditions.append(0.25)
        elif price_change > 0:
            bullish_conditions.append(0.1)
        
        # Volume confirmation
        if volume_ratio > self.volume_threshold:
            bullish_conditions.append(0.15)
        
        # Moving average trend
        if sma_short and sma_long and sma_short[-1] > sma_long[-1]:
            bullish_conditions.append(0.1)
        
        # Bearish momentum conditions
        bearish_conditions = []
        
        # RSI overbought or showing weakness
        if rsi and rsi[-1] > self.rsi_overbought:
            bearish_conditions.append(0.2)
        elif rsi and rsi[-1] < 50:
            bearish_conditions.append(0.1)
        
        # MACD bearish crossover
        if (macd_line and macd_signal and len(macd_line) > 1 and len(macd_signal) > 1):
            if macd_line[-1] < macd_signal[-1] and macd_line[-2] >= macd_signal[-2]:
                bearish_conditions.append(0.3)
            elif macd_line[-1] < macd_signal[-1]:
                bearish_conditions.append(0.1)
        
        # Negative price momentum
        if price_change < -self.price_change_threshold:
            bearish_conditions.append(0.25)
        elif price_change < 0:
            bearish_conditions.append(0.1)
        
        # Moving average trend
        if sma_short and sma_long and sma_short[-1] < sma_long[-1]:
            bearish_conditions.append(0.1)
        
        # Determine signal
        bullish_strength = sum(bullish_conditions)
        bearish_strength = sum(bearish_conditions)
        
        if bullish_strength > bearish_strength and bullish_strength >= self.min_momentum_strength:
            signal_type = SignalType.BUY
            signal_strength = min(bullish_strength, 1.0)
        elif bearish_strength > bullish_strength and bearish_strength >= self.min_momentum_strength:
            # Check if we have a position to sell
            current_position = self.state.positions.get(symbol)
            if current_position and current_position.quantity > 0:
                signal_type = SignalType.SELL
                signal_strength = min(bearish_strength, 1.0)
        
        # Only generate signal if strength meets minimum threshold
        if signal_type != SignalType.HOLD and signal_strength >= self.min_momentum_strength:
            return StrategySignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=signal_strength,
                price=current_quote.close,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata
            )
        
        return None
    
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
            'portfolio_value': float(portfolio.total_value)
        })