#!/usr/bin/env python3
"""
Investment Research and Watchlist Manager

This script helps identify good investment opportunities and manages a watchlist
using the financial portfolio automation system's capabilities.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project to path
sys.path.append(str(Path(__file__).parent))

class InvestmentResearcher:
    """Investment research and watchlist management."""
    
    def __init__(self):
        self.watchlist_file = "watchlist.json"
        self.research_file = "investment_research.json"
        
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
    
    def get_sector_leaders(self):
        """Get current sector leaders based on fundamental analysis."""
        # These are some fundamentally strong companies across different sectors
        # In a real implementation, this would pull from financial APIs
        sector_leaders = {
            "Technology": {
                "AAPL": {
                    "name": "Apple Inc.",
                    "reason": "Strong ecosystem, consistent revenue growth, excellent margins",
                    "sector": "Technology",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.5%",
                    "pe_ratio": "28.5",
                    "growth_potential": "High"
                },
                "MSFT": {
                    "name": "Microsoft Corporation",
                    "reason": "Cloud dominance, AI leadership, recurring revenue model",
                    "sector": "Technology",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.7%",
                    "pe_ratio": "32.1",
                    "growth_potential": "High"
                },
                "NVDA": {
                    "name": "NVIDIA Corporation",
                    "reason": "AI chip leader, data center growth, gaming strength",
                    "sector": "Technology",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.1%",
                    "pe_ratio": "65.2",
                    "growth_potential": "Very High"
                }
            },
            "Healthcare": {
                "JNJ": {
                    "name": "Johnson & Johnson",
                    "reason": "Diversified healthcare, strong pipeline, dividend aristocrat",
                    "sector": "Healthcare",
                    "market_cap": "Large Cap",
                    "dividend_yield": "3.1%",
                    "pe_ratio": "15.8",
                    "growth_potential": "Moderate"
                },
                "UNH": {
                    "name": "UnitedHealth Group",
                    "reason": "Healthcare services leader, consistent growth, strong margins",
                    "sector": "Healthcare",
                    "market_cap": "Large Cap",
                    "dividend_yield": "1.3%",
                    "pe_ratio": "25.4",
                    "growth_potential": "High"
                }
            },
            "Financial": {
                "JPM": {
                    "name": "JPMorgan Chase & Co.",
                    "reason": "Leading investment bank, strong balance sheet, rising rates benefit",
                    "sector": "Financial",
                    "market_cap": "Large Cap",
                    "dividend_yield": "2.4%",
                    "pe_ratio": "12.3",
                    "growth_potential": "Moderate"
                },
                "BRK.B": {
                    "name": "Berkshire Hathaway Inc.",
                    "reason": "Warren Buffett leadership, diversified holdings, strong cash position",
                    "sector": "Financial",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.0%",
                    "pe_ratio": "22.1",
                    "growth_potential": "Moderate"
                }
            },
            "Consumer": {
                "AMZN": {
                    "name": "Amazon.com Inc.",
                    "reason": "E-commerce dominance, AWS growth, logistics network",
                    "sector": "Consumer Discretionary",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.0%",
                    "pe_ratio": "45.2",
                    "growth_potential": "High"
                },
                "TSLA": {
                    "name": "Tesla Inc.",
                    "reason": "EV market leader, energy storage, autonomous driving potential",
                    "sector": "Consumer Discretionary",
                    "market_cap": "Large Cap",
                    "dividend_yield": "0.0%",
                    "pe_ratio": "78.5",
                    "growth_potential": "Very High"
                }
            },
            "ETFs": {
                "SPY": {
                    "name": "SPDR S&P 500 ETF Trust",
                    "reason": "Broad market exposure, low fees, high liquidity",
                    "sector": "Diversified ETF",
                    "market_cap": "ETF",
                    "dividend_yield": "1.3%",
                    "expense_ratio": "0.09%",
                    "growth_potential": "Market"
                },
                "QQQ": {
                    "name": "Invesco QQQ Trust",
                    "reason": "Tech-heavy Nasdaq exposure, growth focus",
                    "sector": "Technology ETF",
                    "market_cap": "ETF",
                    "dividend_yield": "0.6%",
                    "expense_ratio": "0.20%",
                    "growth_potential": "High"
                },
                "VTI": {
                    "name": "Vanguard Total Stock Market ETF",
                    "reason": "Total US market exposure, ultra-low fees",
                    "sector": "Diversified ETF",
                    "market_cap": "ETF",
                    "dividend_yield": "1.3%",
                    "expense_ratio": "0.03%",
                    "growth_potential": "Market"
                }
            }
        }
        return sector_leaders
    
    def analyze_investment_opportunities(self):
        """Analyze current investment opportunities."""
        print("🔍 Analyzing Investment Opportunities...")
        print("=" * 60)
        
        sector_leaders = self.get_sector_leaders()
        opportunities = []
        
        for sector, stocks in sector_leaders.items():
            print(f"\n📊 {sector} Sector Leaders:")
            print("-" * 40)
            
            for symbol, data in stocks.items():
                print(f"\n🏢 {symbol} - {data['name']}")
                print(f"   💡 Investment Thesis: {data['reason']}")
                print(f"   📈 Growth Potential: {data['growth_potential']}")
                
                if 'dividend_yield' in data:
                    print(f"   💰 Dividend Yield: {data['dividend_yield']}")
                if 'pe_ratio' in data:
                    print(f"   📊 P/E Ratio: {data['pe_ratio']}")
                if 'expense_ratio' in data:
                    print(f"   💸 Expense Ratio: {data['expense_ratio']}")
                
                opportunities.append({
                    "symbol": symbol,
                    "name": data['name'],
                    "sector": sector,
                    "reason": data['reason'],
                    "growth_potential": data['growth_potential'],
                    "analysis_date": datetime.now().isoformat()
                })
        
        return opportunities
    
    def get_diversified_portfolio_suggestions(self):
        """Suggest a diversified portfolio allocation."""
        suggestions = {
            "Conservative Portfolio (Low Risk)": {
                "allocation": {
                    "Large Cap Growth": ["AAPL", "MSFT"],
                    "Dividend Stocks": ["JNJ", "JPM"],
                    "Broad Market ETF": ["SPY", "VTI"],
                    "Healthcare": ["UNH"]
                },
                "risk_level": "Low",
                "expected_return": "6-8%",
                "description": "Focus on stable, dividend-paying companies and broad market exposure"
            },
            "Moderate Portfolio (Balanced)": {
                "allocation": {
                    "Technology Growth": ["AAPL", "MSFT", "NVDA"],
                    "Healthcare": ["JNJ", "UNH"],
                    "Financial": ["JPM", "BRK.B"],
                    "Consumer": ["AMZN"],
                    "ETFs": ["QQQ", "SPY"]
                },
                "risk_level": "Moderate",
                "expected_return": "8-12%",
                "description": "Balanced mix of growth and value across sectors"
            },
            "Aggressive Portfolio (High Growth)": {
                "allocation": {
                    "High Growth Tech": ["NVDA", "TSLA", "AMZN"],
                    "Tech Leaders": ["AAPL", "MSFT"],
                    "Growth ETF": ["QQQ"],
                    "Emerging Opportunities": ["Individual growth stocks"]
                },
                "risk_level": "High",
                "expected_return": "12-18%",
                "description": "Focus on high-growth companies with higher volatility"
            }
        }
        return suggestions
    
    def create_watchlist_from_analysis(self, opportunities):
        """Create a watchlist from investment analysis."""
        watchlist = self.load_watchlist()
        
        print("\n🎯 Creating Investment Watchlist...")
        print("=" * 50)
        
        # Get top picks from each category
        top_picks = []
        
        # Technology leaders
        tech_picks = ["AAPL", "MSFT", "NVDA"]
        top_picks.extend(tech_picks)
        
        # Diversification picks
        diversification_picks = ["JNJ", "JPM", "UNH", "AMZN"]
        top_picks.extend(diversification_picks)
        
        # ETF picks for broad exposure
        etf_picks = ["SPY", "QQQ", "VTI"]
        top_picks.extend(etf_picks)
        
        # Add to watchlist
        for symbol in top_picks:
            if symbol not in [item['symbol'] for item in watchlist['symbols']]:
                # Find the opportunity data
                opp_data = next((opp for opp in opportunities if opp['symbol'] == symbol), None)
                if opp_data:
                    watchlist['symbols'].append({
                        'symbol': symbol,
                        'name': opp_data['name'],
                        'sector': opp_data['sector'],
                        'reason': opp_data['reason'],
                        'added_date': datetime.now().isoformat(),
                        'growth_potential': opp_data['growth_potential']
                    })
        
        self.save_watchlist(watchlist)
        return watchlist
    
    def display_watchlist(self, watchlist):
        """Display the current watchlist."""
        print("\n📋 Current Investment Watchlist:")
        print("=" * 60)
        
        if not watchlist['symbols']:
            print("No symbols in watchlist yet.")
            return
        
        for i, item in enumerate(watchlist['symbols'], 1):
            print(f"\n{i}. {item['symbol']} - {item['name']}")
            print(f"   🏢 Sector: {item['sector']}")
            print(f"   💡 Reason: {item['reason']}")
            print(f"   📈 Growth Potential: {item['growth_potential']}")
            print(f"   📅 Added: {item['added_date'][:10]}")
        
        print(f"\n📊 Total symbols in watchlist: {len(watchlist['symbols'])}")
        if watchlist['last_updated']:
            print(f"🕒 Last updated: {watchlist['last_updated'][:19]}")
    
    def display_portfolio_suggestions(self):
        """Display portfolio allocation suggestions."""
        suggestions = self.get_diversified_portfolio_suggestions()
        
        print("\n💼 Portfolio Allocation Suggestions:")
        print("=" * 60)
        
        for portfolio_name, details in suggestions.items():
            print(f"\n🎯 {portfolio_name}")
            print(f"   Risk Level: {details['risk_level']}")
            print(f"   Expected Return: {details['expected_return']}")
            print(f"   Description: {details['description']}")
            print("   Suggested Allocation:")
            
            for category, symbols in details['allocation'].items():
                print(f"     • {category}: {', '.join(symbols)}")
    
    def run_investment_research(self):
        """Run the complete investment research process."""
        print("🚀 Financial Portfolio Investment Research")
        print("=" * 60)
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Analyze opportunities
        opportunities = self.analyze_investment_opportunities()
        
        # Create watchlist
        watchlist = self.create_watchlist_from_analysis(opportunities)
        
        # Display results
        self.display_watchlist(watchlist)
        self.display_portfolio_suggestions()
        
        # Save research data
        research_data = {
            "analysis_date": datetime.now().isoformat(),
            "opportunities": opportunities,
            "watchlist_count": len(watchlist['symbols']),
            "market_outlook": "Positive with focus on technology and healthcare sectors"
        }
        
        with open(self.research_file, 'w') as f:
            json.dump(research_data, f, indent=2)
        
        print(f"\n✅ Research completed and saved to {self.research_file}")
        print(f"✅ Watchlist saved to {self.watchlist_file}")
        
        return watchlist, opportunities

def main():
    """Main function to run investment research."""
    researcher = InvestmentResearcher()
    watchlist, opportunities = researcher.run_investment_research()
    
    print("\n🎉 Investment research completed!")
    print("You now have a curated watchlist of investment opportunities.")
    print("\nNext steps:")
    print("1. Review the watchlist and research each symbol further")
    print("2. Consider your risk tolerance and investment timeline")
    print("3. Start with small positions and diversify across sectors")
    print("4. Monitor the watchlist regularly for entry opportunities")

if __name__ == "__main__":
    main()