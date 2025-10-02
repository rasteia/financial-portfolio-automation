"""
Analysis API routes.

Provides endpoints for risk analysis, performance analysis, technical analysis,
correlation analysis, and attribution analysis.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from financial_portfolio_automation.api.auth import AuthUser, get_current_user, require_permission
from financial_portfolio_automation.api.schemas.analysis import (
    RiskAssessment,
    PerformanceAnalysis,
    TechnicalAnalysis,
    CorrelationAnalysis,
    AttributionAnalysis
)

router = APIRouter()


@router.get("/risk", response_model=RiskAssessment)
async def assess_portfolio_risk(
    symbol: Optional[str] = Query(None, description="Analyze specific symbol risk"),
    confidence_level: float = Query(0.95, description="Confidence level for VaR calculation"),
    time_horizon: int = Query(1, description="Time horizon in days for risk metrics"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Perform comprehensive portfolio risk assessment.
    
    Analyzes portfolio risk metrics including VaR, beta, volatility,
    concentration risk, and stress testing scenarios.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        risk_data = risk_tools.assess_portfolio_risk(
            symbol=symbol,
            confidence_level=confidence_level,
            time_horizon=time_horizon
        )
        
        if not risk_data:
            raise HTTPException(status_code=404, detail="Risk assessment data not found")
        
        return RiskAssessment(**risk_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assess portfolio risk: {str(e)}")


@router.get("/performance", response_model=PerformanceAnalysis)
async def analyze_performance(
    period: str = Query("1m", description="Analysis period"),
    benchmark: Optional[str] = Query(None, description="Benchmark symbol for comparison"),
    attribution: bool = Query(False, description="Include performance attribution analysis"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Perform detailed portfolio performance analysis.
    
    Analyzes returns, risk-adjusted metrics, drawdowns, and optionally
    provides performance attribution by sector or security.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        performance_data = analysis_tools.analyze_performance(
            period=period,
            benchmark=benchmark,
            include_attribution=attribution
        )
        
        if not performance_data:
            raise HTTPException(status_code=404, detail="Performance analysis data not found")
        
        return PerformanceAnalysis(**performance_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze performance: {str(e)}")


@router.get("/technical/{symbol}", response_model=TechnicalAnalysis)
async def perform_technical_analysis(
    symbol: str,
    period: str = Query("3m", description="Analysis period"),
    indicators: Optional[List[str]] = Query(None, description="Technical indicators to calculate"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Perform technical analysis for a specific security.
    
    Calculates technical indicators, identifies chart patterns,
    and provides trading signals based on technical analysis.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        symbol = symbol.upper()
        analysis_tools = AnalysisTools()
        
        technical_data = analysis_tools.perform_technical_analysis(
            symbol=symbol,
            period=period,
            indicators=indicators
        )
        
        if not technical_data:
            raise HTTPException(status_code=404, detail=f"Technical analysis data not found for {symbol}")
        
        return TechnicalAnalysis(**technical_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform technical analysis: {str(e)}")


@router.get("/correlation", response_model=CorrelationAnalysis)
async def analyze_correlation(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols to analyze"),
    period: str = Query("3m", description="Analysis period"),
    min_correlation: float = Query(0.5, description="Minimum correlation threshold to display"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Analyze correlation and diversification metrics.
    
    Calculates correlation matrix between portfolio positions or specified symbols,
    and provides diversification analysis.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        
        # Parse symbols if provided
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        correlation_data = analysis_tools.analyze_correlation(
            symbols=symbol_list,
            period=period,
            min_correlation=min_correlation
        )
        
        if not correlation_data:
            raise HTTPException(status_code=404, detail="Correlation analysis data not found")
        
        return CorrelationAnalysis(**correlation_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze correlation: {str(e)}")


@router.get("/attribution", response_model=AttributionAnalysis)
async def analyze_attribution(
    period: str = Query("1m", description="Analysis period"),
    level: str = Query("security", description="Attribution level (security, sector, asset_class)"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Perform performance attribution analysis.
    
    Analyzes performance contribution by individual securities, sectors,
    or asset classes to understand sources of returns.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        attribution_data = analysis_tools.analyze_attribution(
            period=period,
            level=level
        )
        
        if not attribution_data:
            raise HTTPException(status_code=404, detail="Attribution analysis data not found")
        
        return AttributionAnalysis(**attribution_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze attribution: {str(e)}")


@router.post("/scenario")
async def run_scenario_analysis(
    scenarios: List[Dict[str, Any]],
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Run custom scenario analysis.
    
    Tests portfolio performance under various market scenarios
    and stress conditions.
    """
    try:
        from financial_portfolio_automation.mcp.risk_tools import RiskTools
        
        risk_tools = RiskTools()
        scenario_results = risk_tools.run_scenario_analysis(scenarios=scenarios)
        
        if not scenario_results:
            raise HTTPException(status_code=500, detail="Failed to run scenario analysis")
        
        return {
            "scenarios_tested": len(scenarios),
            "results": scenario_results,
            "summary": {
                "best_case": max(scenario_results, key=lambda x: x.get('portfolio_impact', 0)),
                "worst_case": min(scenario_results, key=lambda x: x.get('portfolio_impact', 0)),
                "average_impact": sum(r.get('portfolio_impact', 0) for r in scenario_results) / len(scenario_results)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run scenario analysis: {str(e)}")


@router.get("/market-regime")
async def analyze_market_regime(
    lookback_days: int = Query(252, description="Lookback period in days"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Analyze current market regime and conditions.
    
    Identifies market conditions (bull, bear, volatile, calm) and
    provides context for portfolio positioning.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        regime_data = analysis_tools.analyze_market_regime(lookback_days=lookback_days)
        
        if not regime_data:
            raise HTTPException(status_code=404, detail="Market regime analysis data not found")
        
        return regime_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze market regime: {str(e)}")


@router.get("/factor-exposure")
async def analyze_factor_exposure(
    factors: Optional[List[str]] = Query(None, description="Factors to analyze (value, growth, momentum, quality, etc.)"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Analyze portfolio factor exposures.
    
    Analyzes exposure to various investment factors like value, growth,
    momentum, quality, size, and volatility.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        factor_data = analysis_tools.analyze_factor_exposure(factors=factors)
        
        if not factor_data:
            raise HTTPException(status_code=404, detail="Factor exposure analysis data not found")
        
        return factor_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze factor exposure: {str(e)}")


@router.get("/sector-rotation")
async def analyze_sector_rotation(
    period: str = Query("1y", description="Analysis period"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Analyze sector rotation patterns and trends.
    
    Identifies sector performance trends and rotation patterns
    to inform sector allocation decisions.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        analysis_tools = AnalysisTools()
        rotation_data = analysis_tools.analyze_sector_rotation(period=period)
        
        if not rotation_data:
            raise HTTPException(status_code=404, detail="Sector rotation analysis data not found")
        
        return rotation_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze sector rotation: {str(e)}")


@router.get("/volatility-surface")
async def get_volatility_surface(
    symbol: str = Query(..., description="Symbol for volatility analysis"),
    current_user: AuthUser = Depends(require_permission("analysis:read"))
):
    """
    Get implied volatility surface for options analysis.
    
    Provides implied volatility data across strikes and expirations
    for options trading and risk management.
    """
    try:
        from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
        
        symbol = symbol.upper()
        analysis_tools = AnalysisTools()
        
        volatility_data = analysis_tools.get_volatility_surface(symbol=symbol)
        
        if not volatility_data:
            raise HTTPException(status_code=404, detail=f"Volatility surface data not found for {symbol}")
        
        return volatility_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get volatility surface: {str(e)}")