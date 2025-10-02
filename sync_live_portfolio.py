#!/usr/bin/env python3
"""
Sync live Alpaca portfolio data to local database.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.data.store import DataStore


def main():
    """Sync live Alpaca data to local database."""
    print("🔄 Syncing Live Alpaca Portfolio Data...")
    print("=" * 50)
    
    try:
        # Create Alpaca config
        alpaca_config = AlpacaConfig(
            api_key="PK84S6XGSBWSPHNMYDT3",
            secret_key="ycqrtzFjfq8XkPKZ9Lr3YyAV9QbYaEN33P1X9PFU",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX,
            environment=Environment.PAPER
        )
        
        # Initialize clients
        alpaca_client = AlpacaClient(alpaca_config)
        data_store = DataStore("portfolio_automation.db")
        
        # Authenticate
        if not alpaca_client.authenticate():
            print("❌ Failed to authenticate with Alpaca")
            return False
        
        print("✅ Connected to Alpaca Paper Trading")
        
        # Get live portfolio snapshot
        print("📊 Fetching live portfolio data...")
        portfolio_snapshot = alpaca_client.get_portfolio_snapshot()
        
        # Clear existing demo data
        print("🧹 Clearing demo data...")
        if os.path.exists("portfolio_automation.db"):
            os.remove("portfolio_automation.db")
        
        # Reinitialize database
        data_store = DataStore("portfolio_automation.db")
        
        # Save live portfolio data
        print("💾 Saving live portfolio data...")
        snapshot_id = data_store.save_portfolio_snapshot(portfolio_snapshot)
        
        print(f"✅ Saved portfolio snapshot with ID: {snapshot_id}")
        print(f"💰 Portfolio Value: ${portfolio_snapshot.total_value}")
        print(f"💵 Buying Power: ${portfolio_snapshot.buying_power}")
        print(f"📋 Positions: {len(portfolio_snapshot.positions)}")
        
        if portfolio_snapshot.positions:
            print("\n📋 Live Positions:")
            for pos in portfolio_snapshot.positions:
                print(f"  {pos.symbol}: {pos.quantity} shares @ ${pos.current_price}")
        else:
            print("\n📭 No positions found - fresh $100K account ready to trade!")
        
        print(f"\n🎉 Live data sync complete!")
        print("Your CLI will now show real Alpaca account data.")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)