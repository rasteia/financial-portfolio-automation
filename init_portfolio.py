#!/usr/bin/env python3
"""
Initialize the portfolio automation system.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
from financial_portfolio_automation.config.settings import ConfigManager, SystemConfig, AlpacaConfig, RiskLimits, DatabaseConfig
from financial_portfolio_automation.data.store import DataStore


def main():
    """Initialize the portfolio system."""
    print("🚀 Initializing Portfolio Automation System...")
    
    # Set config file path
    config_file = project_root / "config" / "config.json"
    
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        print("Please create config/config.json based on config/config.example.json")
        return False
    
    try:
        # Load and parse config file
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Set environment variables from config file
        os.environ['ALPACA_API_KEY'] = config_data['alpaca']['api_key']
        os.environ['ALPACA_SECRET_KEY'] = config_data['alpaca']['secret_key']
        os.environ['ALPACA_BASE_URL'] = config_data['alpaca']['base_url']
        os.environ['DATABASE_URL'] = config_data['database']['url']
        
        # Load configuration
        config_manager = ConfigManager(str(config_file))
        config = config_manager.load_config()
        print("✅ Configuration loaded successfully")
        
        # Initialize database
        print("📊 Initializing database...")
        # Extract the actual database path from SQLite URL
        db_url = config.database.url
        if db_url.startswith('sqlite:///'):
            db_path = db_url[10:]  # Remove 'sqlite:///' prefix
        else:
            db_path = "portfolio_automation.db"  # Default fallback
        
        data_store = DataStore(db_path)
        print("✅ Database initialized successfully")
        
        # Create logs directory
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        print("✅ Logs directory created")
        
        print("\n🎉 Portfolio Automation System initialized successfully!")
        print("\nNext steps:")
        print("1. Set up your Alpaca API credentials in config/config.json")
        print("2. Run: python -m financial_portfolio_automation.cli.main portfolio status")
        print("3. Start building your portfolio!")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)