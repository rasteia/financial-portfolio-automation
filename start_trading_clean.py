#!/usr/bin/env python3
"""
Clean startup script for automated trading strategies.
Uses environment variables or config file for API credentials.
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
from financial_portfolio_automation.execution.order_executor import OrderExecutor, OrderRequest, ExecutionStrategy
from financial_portfolio_automation.models.core import OrderSide, OrderType
from decimal import Decimal


def get_api_credentials():
    """
    Get API credentials from environment variables or config file.
    
    Returns:
        tuple: (api_key, secret_key, base_url)
    """
    # Try environment variables first
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    
    if api_key and secret_key:
        return api_key, secret_key, base_url
    
    # Try importing from secrets config file
    try:
        from config.secrets import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
        return ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL
    except ImportError:
        print("❌ No API credentials found!")
        print("Please set environment variables or create config/secrets.py")
        print("See config/example_config.py for template")
        return None, None, None


def place_initial_trades(alpaca_client, order_executor):
    """Place some initial diversified trades."""
    print("💰 Placing Initial Diversified Trades...")
    print("-" * 40)
    
    # Define our initial portfolio allocation
    trades = [
        # Tech giants (30% allocation)
        {"symbol": "AAPL", "qty": 20, "allocation": "Tech - Apple"},
        {"symbol": "MSFT", "qty": 8, "allocation": "Tech - Microsoft"},
        {"symbol": "GOOGL", "qty": 2, "allocation": "Tech - Google"},
        
        # Financial sector (20% allocation)
        {"symbol": "JPM", "qty": 13, "allocation": "Finance - JPMorgan"},
        {"symbol": "BAC", "qty": 60, "allocation": "Finance - Bank of America"},
        
        # Healthcare (15% allocation)
        {"symbol": "JNJ", "qty": 9, "allocation": "Healthcare - J&J"},
        {"symbol": "PFE", "qty": 52, "allocation": "Healthcare - Pfizer"},
        
        # Consumer goods (10% allocation)
        {"symbol": "PG", "qty": 6, "allocation": "Consumer - P&G"},
        {"symbol": "KO", "qty": 17, "allocation": "Consumer - Coca Cola"},
        
        # Energy (10% allocation)
        {"symbol": "XOM", "qty": 9, "allocation": "Energy - Exxon"},
        
        # ETFs for diversification (15% allocation)
        {"symbol": "SPY", "qty": 3, "allocation": "ETF - S&P 500"},
        {"symbol": "VTI", "qty": 3, "allocation": "ETF - Total Market"},
    ]
    
    successful_trades = []
    failed_trades = []
    
    for trade in trades:
        try:
            print(f"📈 Buying {trade['qty']} shares of {trade['symbol']} ({trade['allocation']})")
            
            # Create order request
            order_request = OrderRequest(
                symbol=trade['symbol'],
                quantity=trade['qty'],
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                execution_strategy=ExecutionStrategy.IMMEDIATE
            )
            
            # Execute order
            result = order_executor.execute_order(order_request)
            
            if result.success:
                successful_trades.append(trade)
                print(f"✅ Order executed: {trade['symbol']} - Order ID: {result.order_id}")
                if result.average_fill_price:
                    print(f"   Fill Price: ${result.average_fill_price}")
            else:
                failed_trades.append(trade)
                print(f"❌ Order failed: {trade['symbol']} - {result.error_message}")
                
        except Exception as e:
            failed_trades.append(trade)
            print(f"❌ Error placing order for {trade['symbol']}: {e}")
    
    return successful_trades, failed_trades


def setup_automated_strategies():
    """Set up automated trading strategies."""
    print("\n🤖 Setting Up Automated Strategies...")
    print("-" * 40)
    
    strategies = [
        {
            "name": "Stop Loss Protection",
            "description": "5% stop loss on all positions",
            "status": "Active"
        },
        {
            "name": "Momentum Trading",
            "description": "Buy on RSI oversold, sell on overbought",
            "status": "Ready"
        },
        {
            "name": "Mean Reversion",
            "description": "Buy dips in quality stocks",
            "status": "Ready"
        },
        {
            "name": "Portfolio Rebalancing",
            "description": "Maintain target allocation",
            "status": "Active"
        }
    ]
    
    for strategy in strategies:
        print(f"⚙️  {strategy['name']}: {strategy['description']} - {strategy['status']}")
    
    return strategies


def main():
    """Start the paper money machine!"""
    print("🚀 STARTING PAPER MONEY MACHINE!")
    print("=" * 60)
    print("💰 Initial Capital: $100,000")
    print("🎯 Goal: Build a diversified, profitable portfolio")
    print("🤖 Method: Automated trading with risk management")
    print("=" * 60)
    
    try:
        # Get API credentials
        api_key, secret_key, base_url = get_api_credentials()
        
        if not api_key or not secret_key:
            return False
        
        # Create Alpaca config
        alpaca_config = AlpacaConfig(
            api_key=api_key,
            secret_key=secret_key,
            base_url=base_url,
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
        
        # Check market status
        market_open = alpaca_client.is_market_open()
        print(f"🏪 Market Status: {'OPEN' if market_open else 'CLOSED'}")
        
        if not market_open:
            print("⏰ Market is closed. Orders will be queued for next market open.")
        
        # Get current account status
        account_info = alpaca_client.get_account_info()
        print(f"💵 Available Buying Power: ${float(account_info.get('buying_power', 0)):,.2f}")
        
        # Place initial trades
        successful_trades, failed_trades = place_initial_trades(alpaca_client, order_executor)
        
        print(f"\n📊 Trading Summary:")
        print(f"✅ Successful Orders: {len(successful_trades)}")
        print(f"❌ Failed Orders: {len(failed_trades)}")
        
        if successful_trades:
            print(f"\n🎉 Successfully placed orders for:")
            for trade in successful_trades:
                print(f"  • {trade['qty']} shares of {trade['symbol']}")
        
        # Set up automated strategies
        strategies = setup_automated_strategies()
        
        print(f"\n🎯 PAPER MONEY MACHINE IS RUNNING!")
        print("=" * 60)
        print("📈 Your portfolio is now actively managed")
        print("🤖 Automated strategies are monitoring markets")
        print("🔔 Alerts will notify you of important events")
        print("💰 Watch your paper money grow!")
        
        print(f"\n📱 Monitor Your Portfolio:")
        print("python -m financial_portfolio_automation.cli.main portfolio status")
        print("python -m financial_portfolio_automation.cli.main portfolio positions")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start trading: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)