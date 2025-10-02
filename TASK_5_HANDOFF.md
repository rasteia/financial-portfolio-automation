# Task 5 Handoff Document: Technical Analysis and Portfolio Analysis Engines

## Overview

This document provides comprehensive guidance for implementing Task 5 of the Financial Portfolio Automation system: **Build technical analysis and portfolio analysis engines**. This task involves creating sophisticated analysis capabilities that will process market data and portfolio information to generate actionable insights for trading decisions.

## Task Breakdown

### 5.1 Implement technical analysis indicators
- Create TechnicalAnalysis class with moving averages (SMA, EMA)
- Add momentum indicators (RSI, MACD, Stochastic)
- Implement volatility indicators (Bollinger Bands, ATR)
- Write unit tests with known indicator values for validation
- **Requirements**: 2.3, 4.1

### 5.2 Implement portfolio analyzer for metrics calculation
- Create PortfolioAnalyzer class for portfolio value and allocation
- Add risk metrics calculation (beta, volatility, Sharpe ratio)
- Implement performance attribution and correlation analysis
- Write unit tests with sample portfolio data
- **Requirements**: 3.1, 3.2, 3.3, 3.4

### 5.3 Implement risk manager for exposure monitoring
- Create RiskManager class with position size validation
- Add portfolio concentration and drawdown monitoring
- Implement volatility-based position sizing calculations
- Write unit tests for risk limit validation scenarios
- **Requirements**: 4.4, 5.4, 6.1

## Current System Context

### Completed Foundation (Task 4)
The data management layer is now complete and provides:

1. **DataStore** (`financial_portfolio_automation/data/store.py`):
   - SQLite backend with comprehensive CRUD operations
   - Storage for quotes, trades, positions, orders, and portfolio snapshots
   - Database migration and schema versioning support

2. **DataCache** (`financial_portfolio_automation/data/cache.py`):
   - Thread-safe in-memory caching with TTL support
   - Cache warming and invalidation strategies
   - Performance optimization with hit/miss statistics

3. **DataValidator** (`financial_portfolio_automation/data/validator.py`):
   - Comprehensive validation rules for all data types
   - Price bounds checking and timestamp validation
   - Data consistency checks across related records

### Existing Components Available for Integration

1. **Core Data Models** (`financial_portfolio_automation/models/core.py`):
   - `Quote`: Market quote data with bid/ask prices
   - `Position`: Portfolio position information
   - `Order`: Trading order details
   - `PortfolioSnapshot`: Complete portfolio state at a point in time

2. **API Integration Layer** (`financial_portfolio_automation/api/`):
   - `AlpacaClient`: Authenticated API client for market data
   - `WebSocketHandler`: Real-time data streaming
   - `MarketDataClient`: Market data retrieval

3. **Configuration System** (`financial_portfolio_automation/config/`):
   - Environment-based configuration management
   - Logging configuration

### Project Structure for Task 5
```
financial_portfolio_automation/
├── analysis/                   # NEW: Analysis engines
│   ├── __init__.py
│   ├── technical.py           # TechnicalAnalysis implementation
│   ├── portfolio.py           # PortfolioAnalyzer implementation
│   ├── risk.py                # RiskManager implementation
│   └── indicators/            # Technical indicator implementations
│       ├── __init__.py
│       ├── trend.py           # Moving averages (SMA, EMA)
│       ├── momentum.py        # RSI, MACD, Stochastic
│       └── volatility.py      # Bollinger Bands, ATR
├── data/                      # Existing data layer
├── api/                       # Existing API layer
├── models/                    # Existing models
└── exceptions.py              # Existing exceptions
```

## Detailed Implementation Guide

### 5.1 Technical Analysis Implementation

#### Technical Indicator Mathematics

**Simple Moving Average (SMA)**:
```
SMA(n) = (P1 + P2 + ... + Pn) / n
```

**Exponential Moving Average (EMA)**:
```
EMA(today) = (Price(today) × α) + (EMA(yesterday) × (1 - α))
where α = 2 / (n + 1)
```

**Relative Strength Index (RSI)**:
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))
```

**MACD (Moving Average Convergence Divergence)**:
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

**Bollinger Bands**:
```
Middle Band = SMA(20)
Upper Band = SMA(20) + (2 × Standard Deviation)
Lower Band = SMA(20) - (2 × Standard Deviation)
```

**Average True Range (ATR)**:
```
True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
ATR = SMA(True Range, 14)
```

#### TechnicalAnalysis Class Structure

Create `financial_portfolio_automation/analysis/technical.py`:

```python
"""
Technical analysis engine for calculating trading indicators.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import numpy as np
import pandas as pd

from ..models.core import Quote
from ..data.store import DataStore
from ..data.cache import DataCache
from ..exceptions import DataError, ValidationError


class TechnicalAnalysis:
    """Technical analysis engine for calculating trading indicators."""
    
    def __init__(self, data_store: DataStore, data_cache: Optional[DataCache] = None):
        self.data_store = data_store
        self.data_cache = data_cache
        self.logger = logging.getLogger(__name__)
    
    # Moving Averages
    def calculate_sma(self, symbol: str, period: int, limit: int = 100) -> List[Tuple[datetime, Decimal]]:
        """Calculate Simple Moving Average."""
        # Implementation details...
    
    def calculate_ema(self, symbol: str, period: int, limit: int = 100) -> List[Tuple[datetime, Decimal]]:
        """Calculate Exponential Moving Average."""
        # Implementation details...
    
    # Momentum Indicators
    def calculate_rsi(self, symbol: str, period: int = 14, limit: int = 100) -> List[Tuple[datetime, Decimal]]:
        """Calculate Relative Strength Index."""
        # Implementation details...
    
    def calculate_macd(self, symbol: str, fast: int = 12, slow: int = 26, signal: int = 9, 
                      limit: int = 100) -> Dict[str, List[Tuple[datetime, Decimal]]]:
        """Calculate MACD indicator."""
        # Implementation details...
    
    # Volatility Indicators
    def calculate_bollinger_bands(self, symbol: str, period: int = 20, std_dev: float = 2.0,
                                 limit: int = 100) -> Dict[str, List[Tuple[datetime, Decimal]]]:
        """Calculate Bollinger Bands."""
        # Implementation details...
    
    def calculate_atr(self, symbol: str, period: int = 14, limit: int = 100) -> List[Tuple[datetime, Decimal]]:
        """Calculate Average True Range."""
        # Implementation details...
```

### 5.2 Portfolio Analyzer Implementation

#### Portfolio Metrics Formulas

**Portfolio Value**:
```
Total Value = Σ(Position Quantity × Current Price)
```

**Asset Allocation**:
```
Allocation % = (Position Value / Total Portfolio Value) × 100
```

**Portfolio Beta**:
```
β = Covariance(Portfolio Returns, Market Returns) / Variance(Market Returns)
```

**Sharpe Ratio**:
```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Standard Deviation
```

**Maximum Drawdown**:
```
Drawdown = (Peak Value - Trough Value) / Peak Value
Max Drawdown = Maximum of all drawdown periods
```

#### PortfolioAnalyzer Class Structure

Create `financial_portfolio_automation/analysis/portfolio.py`:

```python
"""
Portfolio analysis engine for calculating portfolio metrics and performance.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from ..models.core import PortfolioSnapshot, Position
from ..data.store import DataStore
from ..data.cache import DataCache
from ..exceptions import DataError, ValidationError


class PortfolioAnalyzer:
    """Portfolio analysis engine for calculating metrics and performance."""
    
    def __init__(self, data_store: DataStore, data_cache: Optional[DataCache] = None):
        self.data_store = data_store
        self.data_cache = data_cache
        self.logger = logging.getLogger(__name__)
    
    # Portfolio Value and Allocation
    def calculate_portfolio_value(self, snapshot: PortfolioSnapshot) -> Decimal:
        """Calculate total portfolio value."""
        # Implementation details...
    
    def calculate_asset_allocation(self, snapshot: PortfolioSnapshot) -> Dict[str, Decimal]:
        """Calculate asset allocation percentages."""
        # Implementation details...
    
    # Risk Metrics
    def calculate_portfolio_beta(self, symbol: str, market_symbol: str = "SPY", 
                               days: int = 252) -> Decimal:
        """Calculate portfolio beta relative to market."""
        # Implementation details...
    
    def calculate_volatility(self, symbol: str, days: int = 252) -> Decimal:
        """Calculate annualized volatility."""
        # Implementation details...
    
    def calculate_sharpe_ratio(self, symbol: str, risk_free_rate: Decimal = Decimal("0.02"),
                              days: int = 252) -> Decimal:
        """Calculate Sharpe ratio."""
        # Implementation details...
    
    # Performance Analysis
    def calculate_returns(self, symbol: str, start_date: datetime, 
                         end_date: datetime) -> List[Tuple[datetime, Decimal]]:
        """Calculate daily returns for a symbol."""
        # Implementation details...
    
    def calculate_max_drawdown(self, symbol: str, days: int = 252) -> Dict[str, any]:
        """Calculate maximum drawdown."""
        # Implementation details...
```

### 5.3 Risk Manager Implementation

#### Risk Management Formulas

**Position Size Calculation**:
```
Position Size = (Risk Amount / Stop Loss Distance) / Share Price
```

**Portfolio Concentration**:
```
Concentration = Largest Position Value / Total Portfolio Value
```

**Value at Risk (VaR)**:
```
VaR = Portfolio Value × Z-Score × Portfolio Volatility
```

**Kelly Criterion**:
```
f* = (bp - q) / b
where f* = fraction of capital to wager
      b = odds received on the wager
      p = probability of winning
      q = probability of losing (1 - p)
```

#### RiskManager Class Structure

Create `financial_portfolio_automation/analysis/risk.py`:

```python
"""
Risk management engine for monitoring portfolio exposure and calculating position sizes.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import numpy as np

from ..models.core import PortfolioSnapshot, Position, Order
from ..data.store import DataStore
from ..data.cache import DataCache
from ..exceptions import DataError, ValidationError


class RiskManager:
    """Risk management engine for portfolio exposure monitoring."""
    
    def __init__(self, data_store: DataStore, data_cache: Optional[DataCache] = None,
                 max_position_size: Decimal = Decimal("0.10"),  # 10% max position
                 max_portfolio_risk: Decimal = Decimal("0.02")):  # 2% max daily risk
        self.data_store = data_store
        self.data_cache = data_cache
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.logger = logging.getLogger(__name__)
    
    # Position Size Validation
    def validate_position_size(self, symbol: str, quantity: int, 
                              portfolio_value: Decimal) -> bool:
        """Validate if position size is within risk limits."""
        # Implementation details...
    
    def calculate_optimal_position_size(self, symbol: str, stop_loss_price: Decimal,
                                       portfolio_value: Decimal, risk_amount: Decimal) -> int:
        """Calculate optimal position size based on risk parameters."""
        # Implementation details...
    
    # Portfolio Risk Monitoring
    def calculate_portfolio_concentration(self, snapshot: PortfolioSnapshot) -> Dict[str, Decimal]:
        """Calculate concentration risk by position."""
        # Implementation details...
    
    def calculate_portfolio_var(self, snapshot: PortfolioSnapshot, 
                               confidence_level: Decimal = Decimal("0.95")) -> Decimal:
        """Calculate Value at Risk for portfolio."""
        # Implementation details...
    
    def monitor_drawdown(self, days: int = 30) -> Dict[str, any]:
        """Monitor portfolio drawdown over specified period."""
        # Implementation details...
```

## Testing Strategy

### Unit Test Structure

Create comprehensive unit tests for each component:

```
tests/
├── test_technical_analysis.py     # TechnicalAnalysis tests
├── test_portfolio_analyzer.py     # PortfolioAnalyzer tests
├── test_risk_manager.py           # RiskManager tests
├── test_indicators/               # Individual indicator tests
│   ├── test_trend_indicators.py   # SMA, EMA tests
│   ├── test_momentum_indicators.py # RSI, MACD tests
│   └── test_volatility_indicators.py # Bollinger Bands, ATR tests
└── integration/
    └── test_analysis_integration.py # Integration tests
```

### Key Test Scenarios

1. **Technical Analysis Tests**:
   - Known indicator values with historical data
   - Edge cases (insufficient data, invalid parameters)
   - Performance with large datasets
   - Cache integration and optimization

2. **Portfolio Analysis Tests**:
   - Portfolio metrics calculation accuracy
   - Risk metrics validation with known datasets
   - Performance attribution analysis
   - Correlation analysis between assets

3. **Risk Management Tests**:
   - Position size validation scenarios
   - Portfolio concentration limits
   - Drawdown monitoring accuracy
   - VaR calculation validation

### Sample Test Implementation

```python
# tests/test_technical_analysis.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from financial_portfolio_automation.analysis.technical import TechnicalAnalysis
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.models.core import Quote


class TestTechnicalAnalysis:
    
    @pytest.fixture
    def technical_analysis(self, data_store):
        """Create TechnicalAnalysis instance."""
        return TechnicalAnalysis(data_store)
    
    def test_sma_calculation(self, technical_analysis, sample_quotes):
        """Test SMA calculation with known values."""
        # Create test data with known SMA values
        # Verify calculations match expected results
        
    def test_rsi_calculation(self, technical_analysis, sample_quotes):
        """Test RSI calculation with known values."""
        # Test with known RSI dataset
        # Verify overbought/oversold levels
```

## Integration Points

### With Existing Components

1. **Data Layer Integration**:
   - Use `DataStore` for historical price data retrieval
   - Leverage `DataCache` for frequently accessed calculations
   - Apply `DataValidator` for input validation

2. **API Integration**:
   - Real-time data from `WebSocketHandler` for live calculations
   - Historical data from `MarketDataClient` for backtesting
   - Market data from `AlpacaClient` for current prices

3. **Configuration Integration**:
   - Analysis parameters from configuration system
   - Risk limits and thresholds from settings
   - Logging configuration for analysis operations

### Future Components Integration

The analysis engines will be used by:
- **Strategy Engine (Task 6)**: Technical indicators for trading signals
- **Execution Layer (Task 7)**: Risk management for order validation
- **Backtesting System**: Historical analysis and strategy validation

## Performance Considerations

1. **Calculation Optimization**:
   - Use vectorized operations with NumPy/Pandas
   - Implement incremental calculations for real-time updates
   - Cache expensive calculations with appropriate TTL

2. **Memory Management**:
   - Limit historical data retrieval to necessary periods
   - Use sliding windows for continuous calculations
   - Implement data cleanup for old calculations

3. **Database Optimization**:
   - Efficient queries for time-series data
   - Proper indexing for date-range queries
   - Batch processing for bulk calculations

## Dependencies

### Required Python Packages

Add to `requirements.txt`:
```
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
scikit-learn>=1.3.0  # For advanced statistical calculations
```

### Mathematical Libraries

The implementation will use:
- **NumPy**: Vectorized mathematical operations
- **Pandas**: Time series data manipulation
- **SciPy**: Statistical functions and distributions
- **Scikit-learn**: Correlation and regression analysis

## Security Considerations

1. **Input Validation**:
   - Validate all calculation parameters
   - Sanitize symbol inputs
   - Check data ranges and periods

2. **Risk Limits**:
   - Enforce maximum position sizes
   - Validate risk parameters
   - Monitor for unusual calculations

3. **Data Integrity**:
   - Verify calculation inputs
   - Log all risk management decisions
   - Audit trail for position sizing

## Configuration Parameters

### Technical Analysis Settings
```python
TECHNICAL_ANALYSIS = {
    'default_periods': {
        'sma': [10, 20, 50, 200],
        'ema': [12, 26],
        'rsi': 14,
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},
        'bollinger': {'period': 20, 'std_dev': 2.0},
        'atr': 14
    },
    'cache_ttl': 300,  # 5 minutes
    'max_data_points': 1000
}
```

### Risk Management Settings
```python
RISK_MANAGEMENT = {
    'max_position_size': 0.10,  # 10% of portfolio
    'max_portfolio_risk': 0.02,  # 2% daily risk
    'max_concentration': 0.25,  # 25% in single position
    'var_confidence': 0.95,     # 95% confidence level
    'drawdown_threshold': 0.05  # 5% drawdown alert
}
```

## Success Criteria

Task 5 will be considered complete when:

1. ✅ All technical indicators calculate correctly with known test data
2. ✅ Portfolio metrics match expected values for sample portfolios
3. ✅ Risk management validates position sizes and portfolio limits
4. ✅ All unit tests pass with >90% code coverage
5. ✅ Integration tests demonstrate proper interaction with data layer
6. ✅ Performance benchmarks meet requirements (sub-second calculations)
7. ✅ Documentation is complete and accurate

## Next Steps After Task 5

Once Task 5 is complete, the system will be ready for:
- **Task 6**: Strategy Engine development (will use technical indicators)
- **Task 7**: Execution Layer (will use risk management)
- **Task 8**: Backtesting System (will use all analysis engines)

The analysis engines are critical for generating trading signals and managing risk, so thorough testing and robust implementation are essential for the overall system success.

## Implementation Notes

1. **Start with Task 5.1**: Technical indicators are foundational for other components
2. **Use Test-Driven Development**: Write tests with known values first
3. **Implement Incrementally**: Start with basic indicators, add complexity gradually
4. **Focus on Accuracy**: Financial calculations must be precise and reliable
5. **Consider Real-time Updates**: Design for both batch and streaming calculations

The analysis engines will transform raw market data into actionable insights, making them one of the most critical components of the entire system.