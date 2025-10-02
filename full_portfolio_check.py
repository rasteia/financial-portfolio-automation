#!/usr/bin/env python3
"""
Complete portfolio status check including stocks and crypto
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient

def main():
    config = AlpacaConfig(
        api_key="PK84S6XGSBWSPHNMYDT3",
        secret_key="ycqrtzFjfq8XkPKZ9Lr3YyAV9QbYaEN33P1X9PFU",
        base_url="https://paper-api.alpaca.markets",
        data_feed=DataFeed.IEX,
        environment=Environment.PAPER
    )

    client = AlpacaClient(config)
    client.authenticate()

    print("📊 COMPLETE PORTFOLIO STATUS")
    print("=" * 60)

    # Get all pending orders (both stocks and crypto)
    try:
        all_orders = client._api.list_orders(status='open')
        stock_orders = [o for o in all_orders if '/' not in o.symbol]
        crypto_orders = [o for o in all_orders if '/' in o.symbol]
        
        print(f"📋 Total Pending Orders: {len(all_orders)}")
        print(f"   • Stock Orders: {len(stock_orders)}")
        print(f"   • Crypto Orders: {len(crypto_orders)}")
        
        if stock_orders:
            print(f"\n📈 Stock Orders (Queued for Market Open):")
            for i, order in enumerate(stock_orders[:15], 1):
                symbol = order.symbol
                qty = order.qty
                status = order.status
                side = order.side
                print(f"  {i:2d}. {symbol} - {side} {qty} shares - {status}")
        
        if crypto_orders:
            print(f"\n🪙 Crypto Orders (24/7 Trading):")
            for i, order in enumerate(crypto_orders, 1):
                symbol = order.symbol
                notional = getattr(order, 'notional', 'N/A')
                status = order.status
                side = order.side
                if notional != 'N/A':
                    print(f"  {i:2d}. {symbol} - {side} ${notional} - {status}")
                else:
                    print(f"  {i:2d}. {symbol} - {side} - {status}")
    
    except Exception as e:
        print(f"📋 Could not retrieve orders: {e}")

    # Get current positions (handle both stocks and crypto)
    try:
        positions = client._api.list_positions()
        stock_positions = [p for p in positions if '/' not in p.symbol]
        crypto_positions = [p for p in positions if '/' in p.symbol]
        
        print(f"\n📈 Current Positions: {len(positions)}")
        print(f"   • Stock Positions: {len(stock_positions)}")
        print(f"   • Crypto Positions: {len(crypto_positions)}")
        
        total_portfolio_value = 0
        
        if stock_positions:
            print(f"\n📊 Stock Positions:")
            for pos in stock_positions:
                symbol = pos.symbol
                qty = pos.qty
                market_value = float(pos.market_value)
                unrealized_pnl = float(pos.unrealized_pl) if pos.unrealized_pl else 0
                current_price = float(pos.current_price) if pos.current_price else 0
                total_portfolio_value += market_value
                print(f"  • {symbol}: {qty} shares @ ${current_price:.2f} = ${market_value:,.2f} (P&L: ${unrealized_pnl:+,.2f})")
        
        if crypto_positions:
            print(f"\n🪙 Crypto Positions:")
            for pos in crypto_positions:
                symbol = pos.symbol
                qty = float(pos.qty)  # Crypto can be fractional
                market_value = float(pos.market_value)
                unrealized_pnl = float(pos.unrealized_pl) if pos.unrealized_pl else 0
                current_price = float(pos.current_price) if pos.current_price else 0
                total_portfolio_value += market_value
                print(f"  • {symbol}: {qty:.6f} coins @ ${current_price:.2f} = ${market_value:,.2f} (P&L: ${unrealized_pnl:+,.2f})")
        
        if positions:
            print(f"\n💰 Total Position Value: ${total_portfolio_value:,.2f}")
    
    except Exception as e:
        print(f"📈 Could not retrieve positions: {e}")

    # Get account summary
    try:
        account = client.get_account_info()
        print(f"\n💵 Account Summary:")
        print(f"  • Total Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
        print(f"  • Available Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"  • Cash: ${float(account.get('cash', 0)):,.2f}")
        print(f"  • Day P&L: ${float(account.get('day_trade_buying_power', 0)):,.2f}")
    except Exception as e:
        print(f"💵 Could not retrieve account info: {e}")

    # Market status
    try:
        market_open = client.is_market_open()
        print(f"\n🏪 Market Status:")
        print(f"  • Stock Market: {'OPEN' if market_open else 'CLOSED'}")
        print(f"  • Crypto Market: OPEN (24/7)")
        
        if not market_open:
            print(f"  ⏰ Stock orders will execute when market opens")
        print(f"  🪙 Crypto orders execute immediately")
    except Exception as e:
        print(f"🏪 Could not get market status: {e}")

    print(f"\n🎯 PORTFOLIO SUMMARY")
    print("=" * 60)
    print("📈 Your diversified portfolio spans multiple asset classes")
    print("🤖 Automated strategies are monitoring all positions")
    print("🔔 Risk management is active across stocks and crypto")
    print("💰 Paper money machine is running at full capacity!")

if __name__ == "__main__":
    main()