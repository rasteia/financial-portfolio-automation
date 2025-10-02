# Financial Portfolio Automation Framework

🚀 **A comprehensive, production-ready financial portfolio automation system built with Python**

This framework integrates with Alpaca Markets to provide intelligent portfolio management, automated trading strategies, real-time analysis, and comprehensive risk management for both traditional securities and cryptocurrencies.

## 🌟 Key Features

### 📈 **Multi-Asset Trading**
- **Stocks & ETFs**: Automated trading across all major sectors
- **Cryptocurrency**: 24/7 crypto trading with 60+ supported assets
- **Options**: Advanced options strategies (coming soon)
- **Fractional Shares**: Support for fractional stock and crypto purchases

### 🤖 **Intelligent Automation**
- **Strategy Engine**: Momentum, mean reversion, and custom strategies
- **Risk Management**: Automated stop losses, position sizing, and portfolio limits
- **Backtesting**: Historical strategy validation with Monte Carlo simulation
- **Rebalancing**: Automatic portfolio rebalancing to maintain target allocations

### 📊 **Advanced Analytics**
- **Technical Analysis**: 20+ indicators (RSI, MACD, Bollinger Bands, etc.)
- **Portfolio Metrics**: Sharpe ratio, beta, VaR, drawdown analysis
- **Performance Reporting**: Comprehensive P&L and tax reporting
- **Real-time Monitoring**: Live portfolio tracking with alerts

### 🔧 **Multiple Interfaces**
- **CLI**: Command-line interface for system management
- **REST API**: FastAPI-based web API for external integrations
- **MCP Integration**: AI assistant integration for natural language trading
- **Web Dashboard**: Real-time portfolio visualization (coming soon)

### 🛡️ **Enterprise-Grade Security**
- **Risk Controls**: Pre-trade validation and real-time monitoring
- **Audit Logging**: Complete transaction and system audit trails
- **Error Handling**: Comprehensive error management and recovery
- **Paper Trading**: Safe testing environment with real market data

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/your-username/financial-portfolio-automation.git
cd financial-portfolio-automation
pip install -r requirements.txt
pip install -e .
```

### 2. Configuration

Create your configuration file:
```bash
cp config/example_config.py config/secrets.py
```

Edit `config/secrets.py` with your Alpaca API credentials:
```python
ALPACA_API_KEY = "your_alpaca_api_key"
ALPACA_SECRET_KEY = "your_alpaca_secret_key"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # Paper trading
```

### 3. Start Trading

```bash
# Start with the clean example script
python start_trading_clean.py

# Or use environment variables
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
python start_trading_clean.py
```

### 4. Monitor Your Portfolio

```bash
# Check portfolio status
python -m financial_portfolio_automation.cli.main portfolio status

# View positions
python -m financial_portfolio_automation.cli.main portfolio positions

# Start monitoring
python -m financial_portfolio_automation.cli.main monitoring start
```

## 📁 Project Architecture

```
financial_portfolio_automation/
├── api/                    # External API integrations
│   ├── alpaca_client.py   # Alpaca Markets API client
│   ├── market_data_client.py  # Market data handling
│   └── websocket_handler.py   # Real-time data streaming
├── analysis/              # Portfolio analysis engine
│   ├── portfolio_analyzer.py  # Portfolio metrics
│   ├── risk_manager.py       # Risk assessment
│   └── technical_analysis.py # Technical indicators
├── cli/                   # Command-line interface
├── data/                  # Data management layer
│   ├── store.py          # Data persistence
│   ├── cache.py          # In-memory caching
│   └── validator.py      # Data validation
├── execution/             # Trade execution engine
│   ├── order_executor.py # Order management
│   ├── risk_controller.py # Pre-trade risk checks
│   └── trade_logger.py   # Transaction logging
├── mcp/                   # AI assistant integration
├── models/                # Data models and schemas
├── monitoring/            # Real-time monitoring
├── notifications/         # Alert system
├── reporting/             # Report generation
├── strategy/              # Trading strategies
│   ├── base.py           # Strategy framework
│   ├── momentum.py       # Momentum strategies
│   ├── mean_reversion.py # Mean reversion strategies
│   └── backtester.py     # Strategy backtesting
└── utils/                 # Utility functions
```

## 🎯 Usage Examples

### Basic Portfolio Management

```python
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.models.config import AlpacaConfig

# Initialize client
config = AlpacaConfig(
    api_key="your_key",
    secret_key="your_secret",
    base_url="https://paper-api.alpaca.markets"
)
client = AlpacaClient(config)
client.authenticate()

# Get portfolio status
positions = client.get_positions()
account_info = client.get_account_info()
```

### Strategy Backtesting

```python
from financial_portfolio_automation.strategy.backtester import Backtester
from financial_portfolio_automation.strategy.momentum import MomentumStrategy

# Create and backtest a strategy
strategy = MomentumStrategy({"rsi_period": 14, "rsi_oversold": 30})
backtester = Backtester()

results = backtester.run_backtest(
    strategy=strategy,
    start_date="2023-01-01",
    end_date="2024-01-01",
    initial_capital=100000
)
```

### Risk Management

```python
from financial_portfolio_automation.analysis.risk_manager import RiskManager

risk_manager = RiskManager()

# Validate order against risk limits
is_valid = risk_manager.validate_order_risk(order, current_positions)

# Monitor portfolio risk
risk_metrics = risk_manager.monitor_portfolio_risk(positions, market_data)
```

## 🔧 Configuration Options

### Risk Management Settings
```python
# In config/secrets.py
MAX_POSITION_SIZE = 10000      # Maximum position size in USD
MAX_DAILY_LOSS = 500          # Maximum daily loss in USD
STOP_LOSS_PERCENTAGE = 0.05   # 5% stop loss
MAX_PORTFOLIO_CONCENTRATION = 0.15  # 15% max per position
```

### Strategy Parameters
```python
# Momentum Strategy
MOMENTUM_RSI_PERIOD = 14
MOMENTUM_RSI_OVERSOLD = 30
MOMENTUM_RSI_OVERBOUGHT = 70

# Mean Reversion Strategy
MEAN_REVERSION_LOOKBACK = 20
MEAN_REVERSION_THRESHOLD = 2.0
```

## 📊 Supported Assets

### Stocks & ETFs
- All US-listed stocks and ETFs
- Major indices (SPY, QQQ, IWM, etc.)
- Sector ETFs (XLF, XLK, XLE, etc.)
- International ETFs (EFA, EEM, etc.)

### Cryptocurrencies (60+ supported)
- **Major**: BTC/USD, ETH/USD, ADA/USD, DOT/USD
- **DeFi**: AAVE/USD, UNI/USD, COMP/USD, MKR/USD
- **Layer 1**: AVAX/USD, SOL/USD, ALGO/USD, ATOM/USD
- **Stablecoins**: USDC, USDT pairs

## 🛡️ Security & Risk Management

### Pre-Trade Controls
- Position size validation
- Portfolio concentration limits
- Available buying power checks
- Market hours validation

### Real-Time Monitoring
- Stop-loss execution
- Drawdown monitoring
- Volatility alerts
- Position limit breaches

### Audit & Compliance
- Complete transaction logging
- System event tracking
- Error logging and alerting
- Performance metrics recording

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/system/

# Run with coverage
pytest --cov=financial_portfolio_automation
```

## 📈 Performance Metrics

The system tracks comprehensive performance metrics:

- **Returns**: Total return, annualized return, excess return
- **Risk**: Volatility, beta, maximum drawdown, VaR
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Attribution**: Sector allocation, security selection effects

## 🔄 Deployment

### Docker Deployment
```bash
# Build the container
docker build -t portfolio-automation .

# Run with environment variables
docker run -e ALPACA_API_KEY=your_key -e ALPACA_SECRET_KEY=your_secret portfolio-automation
```

### Production Considerations
- Use environment variables for secrets
- Enable comprehensive logging
- Set up monitoring and alerting
- Configure backup strategies
- Implement circuit breakers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**Important**: This software is for educational and research purposes only. 

- Trading financial instruments involves substantial risk of loss
- Past performance is not indicative of future results
- Always use paper trading before live trading
- Consult with qualified financial advisors before making investment decisions
- The authors are not responsible for any financial losses

## 🆘 Support

- 📖 **Documentation**: Check the `/docs` directory for detailed guides
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Join GitHub Discussions for questions
- 📧 **Contact**: Open an issue for direct support

---

**Built with ❤️ for the trading community**