#!/usr/bin/env python3
"""
Add cryptocurrency positions to the portfolio
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.execution.order_executor import OrderExecutor, OrderRequest, ExecutionStrategy
from financial_portfolio_automation.models.core import OrderSide, OrderType
from decimal import Decimal

def place_crypto_trades(alpaca_client, order_executor):
    """Place some crypto trades for diversification."""
    print("🪙 Adding Crypto to Portfolio...")
    print("-" * 40)
    
    # Define crypto allocation (5% of portfolio = $5K)
    crypto_trades = [
        # Major cryptocurrencies
        {"symbol": "BTC/USD", "notional": 2000, "allocation": "Bitcoin - Digital Gold"},
        {"symbol": "ETH/USD", "notional": 1500, "allocation": "Ethereum - Smart Contracts"},
        {"symbol": "AVAX/USD", "notional": 800, "allocation": "Avalanche - DeFi Platform"},
        {"symbol": "AAVE/USD", "notional": 700, "allocation": "Aave - DeFi Lending"},
    ]
    
    successful_trades = []
    failed_trades = []
    
    for trade in crypto_trades:
        try:
            print(f"🚀 Buying ${trade['notional']} of {trade['symbol']} ({trade['allocation']})")
            
            # For crypto, we use notional (dollar amount) instead of quantity
            # This allows fractional crypto purchases
            order = alpaca_client._api.submit_order(
                symbol=trade['symbol'],
                notional=trade['notional'],
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            
            if order:
                successful_trades.append(trade)
                print(f"✅ Crypto order placed: {trade['symbol']} - Order ID: {order.id}")
                print(f"   Notional Amount: ${trade['notional']}")
            else:
                failed_trades.append(trade)
                print(f"❌ Order failed: {trade['symbol']}")
                
        except Exception as e:
            failed_trades.append(trade)
            print(f"❌ Error placing crypto order for {trade['symbol']}: {e}")
    
    return successful_trades, failed_trades

def main():
    """Add crypto to the portfolio!"""
    print("🚀 ADDING CRYPTO TO PORTFOLIO!")
    print("=" * 50)
    print("💰 Crypto Allocation: $5,000 (5% of portfolio)")
    print("🎯 Goal: Diversify into digital assets")
    print("🪙 Strategy: Major cryptocurrencies with utility")
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
        
        # Initialize client and order executor
        alpaca_client = AlpacaClient(alpaca_config)
        order_executor = OrderExecutor(alpaca_client)
        
        # Authenticate
        if not alpaca_client.authenticate():
            print("❌ Failed to authenticate with Alpaca")
            return False
        
        print("✅ Connected to Alpaca Paper Trading")
        
        # Check account status
        account_info = alpaca_client.get_account_info()
        print(f"💵 Available Buying Power: ${float(account_info.get('buying_power', 0)):,.2f}")
        
        # Place crypto trades
        successful_trades, failed_trades = place_crypto_trades(alpaca_client, order_executor)
        
        print(f"\n📊 Crypto Trading Summary:")
        print(f"✅ Successful Orders: {len(successful_trades)}")
        print(f"❌ Failed Orders: {len(failed_trades)}")
        
        if successful_trades:
            print(f"\n🎉 Successfully placed crypto orders:")
            total_invested = 0
            for trade in successful_trades:
                print(f"  • ${trade['notional']} in {trade['symbol']}")
                total_invested += trade['notional']
            print(f"\n💰 Total Crypto Investment: ${total_invested:,}")
        
        if failed_trades:
            print(f"\n⚠️  Failed crypto orders:")
            for trade in failed_trades:
                print(f"  • ${trade['notional']} in {trade['symbol']}")
        
        print(f"\n🎯 CRYPTO ADDED TO PORTFOLIO!")
        print("=" * 50)
        print("🪙 Your portfolio now includes digital assets")
        print("📈 Crypto positions will execute 24/7")
        print("🔔 Monitor crypto volatility closely")
        print("💎 HODL and diversify!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add crypto: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)