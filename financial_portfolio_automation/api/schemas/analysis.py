"""
Analysis-related Pydantic schemas for API models.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConcentrationRisk(BaseModel):
    """Concentration risk model."""
    largest_position_pct: float = Field(..., description="Largest position percentage")
    top5_positions_pct: float = Field(..., description="Top 5 positions percentage")
    herfindahl_index: float = Field(..., description="Herfindahl concentration index")
    effective_positions: float = Field(..., description="Effective number of positions")
    concentration_score: str = Field(..., description="Concentration risk score")


class StressTest(BaseModel):
    """Stress test scenario model."""
    scenario: str = Field(..., description="Scenario name")
    portfolio_impact: float = Field(..., description="Portfolio impact amount")
    impact_percent: float = Field(..., description="Portfolio impact percentage")
    probability: float = Field(..., description="Scenario probability")


class RiskAssessment(BaseModel):
    """Risk assessment response model."""
    var: float = Field(..., description="Value at Risk")
    expected_shortfall: float = Field(..., description="Expected Shortfall (CVaR)")
    beta: float = Field(..., description="Portfolio beta")
    volatility: float = Field(..., description="Annualized volatility")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    concentration_risk: Optional[ConcentrationRisk] = Field(None, description="Concentration risk metrics")
    stress_tests: Optional[List[StressTest]] = Field(None, description="Stress test results")
    
    class Config:
        schema_extra = {
            "example": {
                "var": 5000.0,
                "expected_shortfall": 7500.0,
                "beta": 1.2,
                "volatility": 0.18,
                "max_drawdown": 0.10,
                "sharpe_ratio": 1.5,
                "sortino_ratio": 1.8,
                "concentration_risk": {
                    "largest_position_pct": 15.0,
                    "top5_positions_pct": 45.0,
                    "herfindahl_index": 0.08,
                    "effective_positions": 12.5,
                    "concentration_score": "Medium"
                }
            }
        }


class BenchmarkComparison(BaseModel):
    """Benchmark comparison model."""
    benchmark_return: float = Field(..., description="Benchmark return")
    alpha: float = Field(..., description="Alpha vs benchmark")
    beta: float = Field(..., description="Beta vs benchmark")
    correlation: float = Field(..., description="Correlation with benchmark")
    tracking_error: float = Field(..., description="Tracking error")
    information_ratio: float = Field(..., description="Information ratio")
    up_capture: Optional[float] = Field(None, description="Up capture ratio")
    down_capture: Optional[float] = Field(None, description="Down capture ratio")


class AttributionItem(BaseModel):
    """Attribution item model."""
    name: str = Field(..., description="Security/sector/asset class name")
    weight: float = Field(..., description="Weight in portfolio")
    return_pct: float = Field(..., description="Return percentage")
    contribution: float = Field(..., description="Contribution to portfolio return")
    selection_effect: Optional[float] = Field(None, description="Security selection effect")
    allocation_effect: Optional[float] = Field(None, description="Asset allocation effect")


class PerformanceAnalysis(BaseModel):
    """Performance analysis response model."""
    total_return: float = Field(..., description="Total return")
    annualized_return: float = Field(..., description="Annualized return")
    volatility: float = Field(..., description="Volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    sortino_ratio: float = Field(..., description="Sortino ratio")
    calmar_ratio: float = Field(..., description="Calmar ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    win_rate: float = Field(..., description="Win rate")
    benchmark_comparison: Optional[BenchmarkComparison] = Field(None, description="Benchmark comparison")
    attribution: Optional[Dict[str, List[AttributionItem]]] = Field(None, description="Performance attribution")
    
    class Config:
        schema_extra = {
            "example": {
                "total_return": 0.15,
                "annualized_return": 0.12,
                "volatility": 0.18,
                "sharpe_ratio": 1.2,
                "sortino_ratio": 1.5,
                "calmar_ratio": 1.8,
                "max_drawdown": 0.08,
                "win_rate": 0.65
            }
        }


class TechnicalIndicator(BaseModel):
    """Technical indicator model."""
    name: str = Field(..., description="Indicator name")
    value: float = Field(..., description="Current value")
    signal: Optional[str] = Field(None, description="Signal (buy/sell/hold)")
    description: Optional[str] = Field(None, description="Indicator description")


class TradingSignal(BaseModel):
    """Trading signal model."""
    indicator: str = Field(..., description="Source indicator")
    signal: str = Field(..., description="Signal type")
    strength: str = Field(..., description="Signal strength")
    description: str = Field(..., description="Signal description")


class SupportResistance(BaseModel):
    """Support and resistance levels model."""
    support_levels: List[float] = Field(..., description="Support price levels")
    resistance_levels: List[float] = Field(..., description="Resistance price levels")


class TechnicalAnalysis(BaseModel):
    """Technical analysis response model."""
    symbol: str = Field(..., description="Stock symbol")
    current_price: float = Field(..., description="Current price")
    price_change: float = Field(..., description="Price change")
    price_change_percent: float = Field(..., description="Price change percentage")
    volume: int = Field(..., description="Trading volume")
    indicators: Dict[str, Any] = Field(..., description="Technical indicators")
    signals: List[TradingSignal] = Field(..., description="Trading signals")
    support_resistance: Optional[SupportResistance] = Field(None, description="Support and resistance levels")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "current_price": 150.0,
                "price_change": 2.5,
                "price_change_percent": 0.017,
                "volume": 50000000,
                "indicators": {
                    "rsi": 65.5,
                    "macd": 0.25,
                    "sma_20": 148.0,
                    "sma_50": 145.0
                },
                "signals": [
                    {
                        "indicator": "RSI",
                        "signal": "neutral",
                        "strength": "medium",
                        "description": "RSI at 65.5, approaching overbought"
                    }
                ]
            }
        }


class CorrelationMatrix(BaseModel):
    """Correlation matrix model."""
    symbols: List[str] = Field(..., description="List of symbols")
    matrix: Dict[str, Dict[str, float]] = Field(..., description="Correlation matrix")


class HighCorrelation(BaseModel):
    """High correlation pair model."""
    symbol1: str = Field(..., description="First symbol")
    symbol2: str = Field(..., description="Second symbol")
    correlation: float = Field(..., description="Correlation coefficient")
    risk_level: str = Field(..., description="Risk level assessment")


class DiversificationMetrics(BaseModel):
    """Diversification metrics model."""
    average_correlation: float = Field(..., description="Average correlation")
    diversification_ratio: float = Field(..., description="Diversification ratio")
    effective_assets: float = Field(..., description="Effective number of assets")
    concentration_score: str = Field(..., description="Concentration score")
    diversification_score: str = Field(..., description="Diversification score")


class CorrelationAnalysis(BaseModel):
    """Correlation analysis response model."""
    correlation_matrix: CorrelationMatrix = Field(..., description="Correlation matrix")
    high_correlations: List[HighCorrelation] = Field(..., description="High correlation pairs")
    diversification_metrics: DiversificationMetrics = Field(..., description="Diversification metrics")
    sector_correlation: Optional[Dict[str, Any]] = Field(None, description="Sector correlation analysis")
    
    class Config:
        schema_extra = {
            "example": {
                "correlation_matrix": {
                    "symbols": ["AAPL", "GOOGL", "MSFT"],
                    "matrix": {
                        "AAPL": {"AAPL": 1.0, "GOOGL": 0.75, "MSFT": 0.68},
                        "GOOGL": {"AAPL": 0.75, "GOOGL": 1.0, "MSFT": 0.72},
                        "MSFT": {"AAPL": 0.68, "GOOGL": 0.72, "MSFT": 1.0}
                    }
                },
                "high_correlations": [
                    {
                        "symbol1": "AAPL",
                        "symbol2": "GOOGL",
                        "correlation": 0.75,
                        "risk_level": "Medium"
                    }
                ],
                "diversification_metrics": {
                    "average_correlation": 0.72,
                    "diversification_ratio": 0.85,
                    "effective_assets": 2.1,
                    "concentration_score": "High",
                    "diversification_score": "Low"
                }
            }
        }


class AttributionAnalysis(BaseModel):
    """Attribution analysis response model."""
    period: str = Field(..., description="Analysis period")
    level: str = Field(..., description="Attribution level")
    top_contributors: List[AttributionItem] = Field(..., description="Top contributors")
    top_detractors: List[AttributionItem] = Field(..., description="Top detractors")
    sector_attribution: Optional[List[AttributionItem]] = Field(None, description="Sector attribution")
    security_attribution: Optional[List[AttributionItem]] = Field(None, description="Security attribution")
    
    class Config:
        schema_extra = {
            "example": {
                "period": "1m",
                "level": "security",
                "top_contributors": [
                    {
                        "name": "AAPL",
                        "weight": 0.15,
                        "return_pct": 0.08,
                        "contribution": 0.012
                    }
                ],
                "top_detractors": [
                    {
                        "name": "TSLA",
                        "weight": 0.10,
                        "return_pct": -0.05,
                        "contribution": -0.005
                    }
                ]
            }
        }