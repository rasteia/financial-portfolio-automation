#!/usr/bin/env python3
"""
Test connection to Alpaca paper trading API.
"""

import sys
import os
from pathlib import Path
import json

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.config.settings import ConfigManager


def main():
    """Test Alpaca API connection."""
    print("🔌 Testing Alpaca Paper Trading Connection...")
    print("=" * 50)
    
    try:
        # Load and parse config file
        with open("config/config.json", 'r') as f:
            config_data = json.load(f)
        
        # Set environment variables from config file
        os.environ['ALPACA_API_KEY'] = config_data['alpaca']['api_key']
        os.environ['ALPACA_SECRET_KEY'] = config_data['alpaca']['secret_key']
        os.environ['ALPACA_BASE_URL'] = config_data['alpaca']['base_url']
        os.environ['DATABASE_URL'] = config_data['database']['url']
        
        # Load configuration
        config_manager = ConfigManager("config/config.json")
        config = config_manager.load_config()
        
        print(f"✅ Configuration loaded")
        print(f"📡 API Endpoint: {config.alpaca.base_url}")
        print(f"🔑 API Key: {config.alpaca.api_key[:8]}...")
        
        # Initialize Alpaca client
        alpaca_client = AlpacaClient(config.alpaca)
        print("✅ Alpaca client initialized")
        
        # Test account connection
        print("\n📊 Testing Account Connection...")
        account_info = alpaca_client.get_account()
        
        if account_info:
            print("🎉 SUCCESS! Connected to Alpaca Paper Trading!")
            print(f"💰 Account Value: ${float(account_info.portfolio_value):,.2f}")
            print(f"💵 Buying Power: ${float(account_info.buying_power):,.2f}")
            print(f"📈 Day P&L: ${float(account_info.unrealized_pl):,.2f}")
            print(f"🏦 Account Status: {account_info.status}")
            print(f"📅 Account Created: {account_info.created_at}")
            
            # Test market data
            print("\n📈 Testing Market Data...")
            try:
                # Get a quote for AAPL
                quote = alpaca_client.get_latest_quote("AAPL")
                if quote:
                    print(f"✅ AAPL Quote: ${quote.bid} / ${quote.ask}")
                else:
                    print("⚠️  No quote data available (market may be closed)")
            except Exception as e:
                print(f"⚠️  Market data test failed: {e}")
            
            # Test positions
            print("\n📋 Current Positions:")
            positions = alpaca_client.get_positions()
            if positions:
                for pos in positions:
                    print(f"  {pos.symbol}: {pos.qty} shares @ ${pos.market_value}")
            else:
                print("  No positions found (starting fresh!)")
            
            print(f"\n🎯 Ready to Trade!")
            print("Your system is now connected to LIVE market data!")
            print("All trades will be executed with virtual money.")
            
        else:
            print("❌ Failed to get account information")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API keys are correct")
        print("2. Ensure you're using paper trading keys (not live)")
        print("3. Verify your Alpaca account is active")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)