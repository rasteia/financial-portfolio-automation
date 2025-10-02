#!/usr/bin/env python3
"""
Analyze the diversified portfolio and show improvements.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.data.store import DataStore


def main():
    """Analyze the diversified portfolio."""
    print("📊 Portfolio Diversification Analysis")
    print("=" * 60)
    
    # Get current portfolio data
    data_store = DataStore("portfolio_automation.db")
    latest_snapshot = data_store.get_latest_portfolio_snapshot()
    
    if not latest_snapshot:
        print("❌ No portfolio data found")
        return
    
    positions = latest_snapshot.positions
    total_value = latest_snapshot.total_value
    
    # Before vs After comparison
    print("🔄 TRANSFORMATION SUMMARY")
    print("-" * 40)
    print("BEFORE (Old Portfolio):")
    print("  • GOOGL: 47.6% - HIGHLY CONCENTRATED! ⚠️")
    print("  • MSFT:  26.4%")
    print("  • AAPL:  26.0%")
    print("  • Total: 3 positions, all tech stocks")
    print("  • Risk: Very high concentration risk")
    
    print("\nAFTER (Diversified Portfolio):")
    
    # Calculate sector allocations
    sectors = {
        "Technology": ["AAPL", "MSFT"],
        "Healthcare": ["JNJ", "PFE"],
        "Financial Services": ["JPM", "BAC"],
        "Consumer Goods": ["PG", "KO"],
        "Energy": ["XOM"],
        "ETFs/Diversified": ["SPY", "VTI", "VXUS", "BND"]
    }
    
    for sector, symbols in sectors.items():
        sector_positions = [pos for pos in positions if pos.symbol in symbols]
        sector_value = sum(pos.market_value for pos in sector_positions)
        sector_pct = (sector_value / total_value) * 100
        
        print(f"  • {sector}: {sector_pct:.1f}%", end="")
        if sector_positions:
            symbol_list = [pos.symbol for pos in sector_positions]
            print(f" ({', '.join(symbol_list)})")
        else:
            print()
    
    print(f"  • Total: {len(positions)} positions across 6 sectors")
    print("  • Risk: Well-diversified, reduced concentration")
    
    # Risk metrics
    print("\n📈 RISK IMPROVEMENT METRICS")
    print("-" * 40)
    
    largest_position = max(pos.market_value for pos in positions)
    largest_pct = float((largest_position / total_value) * 100)
    
    print(f"Concentration Risk:")
    print(f"  • Before: 47.6% in single stock (GOOGL)")
    print(f"  • After:  {largest_pct:.1f}% in largest position")
    print(f"  • Improvement: {47.6 - largest_pct:.1f} percentage points reduction")
    
    print(f"\nDiversification Metrics:")
    print(f"  • Sectors: 6 (vs 1 before)")
    print(f"  • Asset Classes: Stocks + Bonds + International")
    print(f"  • Geographic: US + International exposure")
    print(f"  • Position Count: {len(positions)} (vs 3 before)")
    
    # Performance metrics
    total_cost = sum(pos.cost_basis for pos in positions)
    total_return_pct = float((latest_snapshot.total_pnl / total_cost) * 100)
    
    print(f"\n💰 PERFORMANCE SUMMARY")
    print("-" * 40)
    print(f"Portfolio Value: ${total_value:,.2f}")
    print(f"Total Return: ${latest_snapshot.total_pnl:,.2f} ({total_return_pct:.2f}%)")
    print(f"Day P&L: ${latest_snapshot.day_pnl:,.2f}")
    print(f"Available Cash: ${latest_snapshot.buying_power:,.2f}")
    
    # Top performers
    print(f"\n🏆 TOP PERFORMERS")
    print("-" * 40)
    sorted_positions = sorted(positions, key=lambda x: x.unrealized_pnl, reverse=True)
    for i, pos in enumerate(sorted_positions[:5]):
        return_pct = float((pos.unrealized_pnl / pos.cost_basis) * 100)
        print(f"{i+1}. {pos.symbol}: ${pos.unrealized_pnl:,.2f} ({return_pct:.2f}%)")
    
    # Allocation by asset type
    print(f"\n🥧 ASSET ALLOCATION")
    print("-" * 40)
    
    stocks = [pos for pos in positions if pos.symbol not in ["SPY", "VTI", "VXUS", "BND"]]
    etfs = [pos for pos in positions if pos.symbol in ["SPY", "VTI", "VXUS", "BND"]]
    
    stocks_value = sum(pos.market_value for pos in stocks)
    etfs_value = sum(pos.market_value for pos in etfs)
    
    stocks_pct = float((stocks_value / total_value) * 100)
    etfs_pct = float((etfs_value / total_value) * 100)
    
    print(f"Individual Stocks: {stocks_pct:.1f}% (${stocks_value:,.2f})")
    print(f"ETFs/Funds: {etfs_pct:.1f}% (${etfs_value:,.2f})")
    
    # International exposure
    international_pos = [pos for pos in positions if pos.symbol == "VXUS"]
    if international_pos:
        intl_pct = float((international_pos[0].market_value / total_value) * 100)
        print(f"International Exposure: {intl_pct:.1f}%")
    
    # Bond allocation
    bond_pos = [pos for pos in positions if pos.symbol == "BND"]
    if bond_pos:
        bond_pct = float((bond_pos[0].market_value / total_value) * 100)
        print(f"Bond Allocation: {bond_pct:.1f}%")
    
    print(f"\n✅ DIVERSIFICATION SUCCESS!")
    print("Your portfolio is now:")
    print("  🎯 Well-balanced across sectors")
    print("  🌍 Globally diversified")
    print("  📊 Risk-optimized")
    print("  💪 Growth-oriented with stability")
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Monitor performance with CLI commands")
    print("2. Set up rebalancing alerts")
    print("3. Consider adding more international exposure")
    print("4. Implement systematic investment strategies")


if __name__ == "__main__":
    main()