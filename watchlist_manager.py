#!/usr/bin/env python3
"""
Advanced Watchlist Manager

Integrates with the financial portfolio automation system to provide
advanced watchlist management, real-time monitoring, and investment alerts.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add the project to path
sys.path.append(str(Path(__file__).parent))

class WatchlistManager:
    """Advanced watchlist management with portfolio integration."""
    
    def __init__(self):
        self.watchlist_file = "watchlist.json"
        self.alerts_file = "watchlist_alerts.json"
        self.analysis_file = "watchlist_analysis.json"
        
    def load_watchlist(self):
        """Load existing watchlist."""
        try:
            if Path(self.watchlist_file).exists():
                with open(self.watchlist_file, 'r') as f:
                    return json.load(f)
            return {"symbols": [], "last_updated": None}
        except Exception as e:
            print(f"Error loading watchlist: {e}")
            return {"symbols": [], "last_updated": None}
    
    def save_watchlist(self, watchlist):
        """Save watchlist to file."""
        try:
            watchlist["last_updated"] = datetime.now().isoformat()
            with open(self.watchlist_file, 'w') as f:
                json.dump(watchlist, f, indent=2)
            print(f"✅ Watchlist saved to {self.watchlist_file}")
        except Exception as e:
            print(f"Error saving watchlist: {e}")
    
    def add_symbol(self, symbol: str, reason: str = "", sector: str = "", 
                   target_price: float = None, stop_loss: float = None):
        """Add a symbol to the watchlist."""
        watchlist = self.load_watchlist()
        
        # Check if symbol already exists
        existing_symbols = [item['symbol'] for item in watchlist['symbols']]
        if symbol.upper() in existing_symbols:
            print(f"⚠️  {symbol.upper()} is already in the watchlist")
            return
        
        new_entry = {
            'symbol': symbol.upper(),
            'reason': reason,
            'sector': sector,
            'added_date': datetime.now().isoformat(),
            'target_price': target_price,
            'stop_loss': stop_loss,
            'alerts_enabled': True,
            'notes': []
        }
        
        watchlist['symbols'].append(new_entry)
        self.save_watchlist(watchlist)
        print(f"✅ Added {symbol.upper()} to watchlist")
    
    def remove_symbol(self, symbol: str):
        """Remove a symbol from the watchlist."""
        watchlist = self.load_watchlist()
        
        original_count = len(watchlist['symbols'])
        watchlist['symbols'] = [item for item in watchlist['symbols'] 
                               if item['symbol'] != symbol.upper()]
        
        if len(watchlist['symbols']) < original_count:
            self.save_watchlist(watchlist)
            print(f"✅ Removed {symbol.upper()} from watchlist")
        else:
            print(f"⚠️  {symbol.upper()} not found in watchlist")
    
    def update_symbol_notes(self, symbol: str, note: str):
        """Add a note to a symbol in the watchlist."""
        watchlist = self.load_watchlist()
        
        for item in watchlist['symbols']:
            if item['symbol'] == symbol.upper():
                if 'notes' not in item:
                    item['notes'] = []
                item['notes'].append({
                    'note': note,
                    'date': datetime.now().isoformat()
                })
                self.save_watchlist(watchlist)
                print(f"✅ Added note to {symbol.upper()}")
                return
        
        print(f"⚠️  {symbol.upper()} not found in watchlist")
    
    def set_price_alerts(self, symbol: str, target_price: float = None, 
                        stop_loss: float = None):
        """Set price alerts for a symbol."""
        watchlist = self.load_watchlist()
        
        for item in watchlist['symbols']:
            if item['symbol'] == symbol.upper():
                if target_price:
                    item['target_price'] = target_price
                if stop_loss:
                    item['stop_loss'] = stop_loss
                item['alerts_enabled'] = True
                self.save_watchlist(watchlist)
                print(f"✅ Updated price alerts for {symbol.upper()}")
                return
        
        print(f"⚠️  {symbol.upper()} not found in watchlist")
    
    def get_market_movers(self):
        """Get current market movers and trending stocks."""
        # Simulated market movers - in production this would use real market data
        market_movers = {
            "top_gainers": [
                {"symbol": "NVDA", "change": "+5.2%", "price": "$875.30", "volume": "45.2M"},
                {"symbol": "TSLA", "change": "+4.8%", "price": "$248.50", "volume": "89.1M"},
                {"symbol": "AMD", "change": "+3.9%", "price": "$165.20", "volume": "52.3M"},
                {"symbol": "AAPL", "change": "+2.1%", "price": "$175.80", "volume": "67.8M"},
                {"symbol": "MSFT", "change": "+1.8%", "price": "$415.60", "volume": "28.9M"}
            ],
            "top_losers": [
                {"symbol": "META", "change": "-2.8%", "price": "$485.20", "volume": "18.7M"},
                {"symbol": "NFLX", "change": "-2.1%", "price": "$445.30", "volume": "12.4M"},
                {"symbol": "GOOGL", "change": "-1.9%", "price": "$165.80", "volume": "25.6M"}
            ],
            "high_volume": [
                {"symbol": "SPY", "volume": "125.6M", "change": "+0.8%"},
                {"symbol": "QQQ", "volume": "98.4M", "change": "+1.2%"},
                {"symbol": "TSLA", "volume": "89.1M", "change": "+4.8%"}
            ]
        }
        return market_movers
    
    def analyze_watchlist_performance(self):
        """Analyze the performance of watchlist symbols."""
        watchlist = self.load_watchlist()
        
        if not watchlist['symbols']:
            print("No symbols in watchlist to analyze")
            return
        
        print("📊 Watchlist Performance Analysis")
        print("=" * 50)
        
        # Simulated performance data - in production this would use real market data
        performance_data = {
            "AAPL": {"current_price": 175.80, "change_1d": 2.1, "change_1w": -1.2, "change_1m": 5.8},
            "MSFT": {"current_price": 415.60, "change_1d": 1.8, "change_1w": 3.2, "change_1m": 8.1},
            "NVDA": {"current_price": 875.30, "change_1d": 5.2, "change_1w": 12.8, "change_1m": 25.6},
            "JNJ": {"current_price": 162.45, "change_1d": 0.3, "change_1w": -0.8, "change_1m": 2.1},
            "JPM": {"current_price": 198.75, "change_1d": 1.1, "change_1w": 2.8, "change_1m": 6.4},
            "UNH": {"current_price": 542.30, "change_1d": 0.9, "change_1w": 1.5, "change_1m": 4.2},
            "AMZN": {"current_price": 145.20, "change_1d": 1.4, "change_1w": 4.1, "change_1m": 9.8},
            "SPY": {"current_price": 458.90, "change_1d": 0.8, "change_1w": 1.2, "change_1m": 3.5},
            "QQQ": {"current_price": 385.40, "change_1d": 1.2, "change_1w": 2.8, "change_1m": 7.2},
            "VTI": {"current_price": 265.80, "change_1d": 0.7, "change_1w": 1.1, "change_1m": 3.2}
        }
        
        analysis_results = []
        
        for item in watchlist['symbols']:
            symbol = item['symbol']
            if symbol in performance_data:
                perf = performance_data[symbol]
                
                # Calculate alerts
                alerts = []
                if item.get('target_price') and perf['current_price'] >= item['target_price']:
                    alerts.append("🎯 Target price reached!")
                if item.get('stop_loss') and perf['current_price'] <= item['stop_loss']:
                    alerts.append("🛑 Stop loss triggered!")
                
                analysis_results.append({
                    'symbol': symbol,
                    'current_price': perf['current_price'],
                    'change_1d': perf['change_1d'],
                    'change_1w': perf['change_1w'],
                    'change_1m': perf['change_1m'],
                    'alerts': alerts,
                    'sector': item.get('sector', 'Unknown'),
                    'reason': item.get('reason', '')
                })
        
        # Display results
        for result in analysis_results:
            print(f"\n📈 {result['symbol']} - ${result['current_price']:.2f}")
            print(f"   📊 1D: {result['change_1d']:+.1f}% | 1W: {result['change_1w']:+.1f}% | 1M: {result['change_1m']:+.1f}%")
            print(f"   🏢 Sector: {result['sector']}")
            
            if result['alerts']:
                for alert in result['alerts']:
                    print(f"   {alert}")
        
        # Save analysis
        analysis_data = {
            'analysis_date': datetime.now().isoformat(),
            'symbols_analyzed': len(analysis_results),
            'results': analysis_results,
            'summary': {
                'avg_1d_change': sum(r['change_1d'] for r in analysis_results) / len(analysis_results),
                'avg_1w_change': sum(r['change_1w'] for r in analysis_results) / len(analysis_results),
                'avg_1m_change': sum(r['change_1m'] for r in analysis_results) / len(analysis_results),
                'alerts_triggered': sum(len(r['alerts']) for r in analysis_results)
            }
        }
        
        with open(self.analysis_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"\n📊 Analysis Summary:")
        print(f"   Average 1D Change: {analysis_data['summary']['avg_1d_change']:+.1f}%")
        print(f"   Average 1W Change: {analysis_data['summary']['avg_1w_change']:+.1f}%")
        print(f"   Average 1M Change: {analysis_data['summary']['avg_1m_change']:+.1f}%")
        print(f"   Alerts Triggered: {analysis_data['summary']['alerts_triggered']}")
        
        return analysis_results
    
    def display_market_overview(self):
        """Display current market overview."""
        market_movers = self.get_market_movers()
        
        print("\n🌟 Market Overview")
        print("=" * 50)
        
        print("\n📈 Top Gainers:")
        for stock in market_movers['top_gainers']:
            print(f"   {stock['symbol']}: {stock['price']} ({stock['change']}) Vol: {stock['volume']}")
        
        print("\n📉 Top Losers:")
        for stock in market_movers['top_losers']:
            print(f"   {stock['symbol']}: {stock['price']} ({stock['change']}) Vol: {stock['volume']}")
        
        print("\n📊 High Volume:")
        for stock in market_movers['high_volume']:
            print(f"   {stock['symbol']}: Vol {stock['volume']} ({stock['change']})")
    
    def suggest_new_opportunities(self):
        """Suggest new investment opportunities based on market trends."""
        suggestions = {
            "AI & Technology": {
                "symbols": ["NVDA", "AMD", "PLTR", "C3.AI"],
                "reason": "AI revolution driving growth in semiconductor and software companies"
            },
            "Clean Energy": {
                "symbols": ["TSLA", "ENPH", "FSLR", "NEE"],
                "reason": "Transition to renewable energy and EV adoption"
            },
            "Healthcare Innovation": {
                "symbols": ["UNH", "JNJ", "PFE", "MRNA"],
                "reason": "Aging population and medical technology advances"
            },
            "Cloud Computing": {
                "symbols": ["MSFT", "AMZN", "GOOGL", "CRM"],
                "reason": "Digital transformation and cloud migration trends"
            },
            "Dividend Growth": {
                "symbols": ["AAPL", "MSFT", "JNJ", "PG"],
                "reason": "Stable companies with growing dividend payments"
            }
        }
        
        print("\n💡 New Investment Opportunities")
        print("=" * 50)
        
        for category, data in suggestions.items():
            print(f"\n🎯 {category}")
            print(f"   Symbols: {', '.join(data['symbols'])}")
            print(f"   Thesis: {data['reason']}")
    
    def run_watchlist_dashboard(self):
        """Run the complete watchlist dashboard."""
        print("🎯 Investment Watchlist Dashboard")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load and display current watchlist
        watchlist = self.load_watchlist()
        
        if watchlist['symbols']:
            print(f"\n📋 Current Watchlist ({len(watchlist['symbols'])} symbols)")
            print("-" * 40)
            
            for i, item in enumerate(watchlist['symbols'], 1):
                print(f"{i}. {item['symbol']} - {item.get('reason', 'No reason provided')[:50]}...")
        else:
            print("\n📋 Watchlist is empty")
        
        # Analyze performance
        self.analyze_watchlist_performance()
        
        # Display market overview
        self.display_market_overview()
        
        # Suggest new opportunities
        self.suggest_new_opportunities()
        
        print(f"\n✅ Dashboard updated - Analysis saved to {self.analysis_file}")

def main():
    """Main function with interactive menu."""
    manager = WatchlistManager()
    
    while True:
        print("\n🎯 Watchlist Manager")
        print("=" * 30)
        print("1. View Dashboard")
        print("2. Add Symbol")
        print("3. Remove Symbol")
        print("4. Set Price Alert")
        print("5. Add Note")
        print("6. Analyze Performance")
        print("7. Market Overview")
        print("8. Exit")
        
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == '1':
            manager.run_watchlist_dashboard()
        elif choice == '2':
            symbol = input("Enter symbol: ").strip()
            reason = input("Enter reason (optional): ").strip()
            sector = input("Enter sector (optional): ").strip()
            manager.add_symbol(symbol, reason, sector)
        elif choice == '3':
            symbol = input("Enter symbol to remove: ").strip()
            manager.remove_symbol(symbol)
        elif choice == '4':
            symbol = input("Enter symbol: ").strip()
            try:
                target = float(input("Enter target price (optional, press enter to skip): ") or 0)
                stop = float(input("Enter stop loss (optional, press enter to skip): ") or 0)
                manager.set_price_alerts(symbol, target if target > 0 else None, stop if stop > 0 else None)
            except ValueError:
                print("Invalid price format")
        elif choice == '5':
            symbol = input("Enter symbol: ").strip()
            note = input("Enter note: ").strip()
            manager.update_symbol_notes(symbol, note)
        elif choice == '6':
            manager.analyze_watchlist_performance()
        elif choice == '7':
            manager.display_market_overview()
        elif choice == '8':
            print("👋 Goodbye!")
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    # Run dashboard once automatically
    manager = WatchlistManager()
    manager.run_watchlist_dashboard()
    
    # Then show interactive menu
    print("\n" + "="*60)
    main()