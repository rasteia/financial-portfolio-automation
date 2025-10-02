"""
Example configuration file for Financial Portfolio Automation.

Copy this file to config/secrets.py and fill in your actual API credentials.
Never commit secrets.py to version control!
"""

# Alpaca Markets API Configuration
ALPACA_API_KEY = "YOUR_ALPACA_API_KEY_HERE"
ALPACA_SECRET_KEY = "YOUR_ALPACA_SECRET_KEY_HERE"

# Environment Settings
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # Paper trading
# ALPACA_BASE_URL = "https://api.alpaca.markets"  # Live trading (use with caution!)

# Data Feed Settings
ALPACA_DATA_FEED = "IEX"  # Options: IEX, SIP

# Risk Management Settings
MAX_POSITION_SIZE = 10000  # Maximum position size in USD
MAX_DAILY_LOSS = 500      # Maximum daily loss in USD
STOP_LOSS_PERCENTAGE = 0.05  # 5% stop loss

# Notification Settings (optional)
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_USERNAME = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

# Database Settings
DATABASE_URL = "sqlite:///portfolio_automation.db"

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "logs/portfolio_automation.log"