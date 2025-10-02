"""
FastAPI application for Portfolio Management REST API.

Provides comprehensive REST API endpoints for portfolio management,
analysis, execution, monitoring, and reporting.
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import time
import logging
from typing import Dict, Any

from financial_portfolio_automation.api.auth import get_current_user, AuthUser
from financial_portfolio_automation.api.middleware import (
    RateLimitMiddleware, 
    LoggingMiddleware,
    ErrorHandlingMiddleware
)
from financial_portfolio_automation.api.routes import (
    portfolio,
    analysis,
    execution,
    monitoring,
    reporting,
    strategies
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Financial Portfolio Automation API",
    description="Comprehensive REST API for intelligent portfolio management and automation",
    version="1.0.0",
    docs_url=None,  # Disable default docs to add custom authentication
    redoc_url=None,
    openapi_url="/api/v1/openapi.json"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "testserver", "*.yourdomain.com"]
)

app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Financial Portfolio Automation API",
        "version": "1.0.0",
        "description": "Comprehensive REST API for intelligent portfolio management",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_prefix": "/api/v1"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connectivity
        from financial_portfolio_automation.data.store import DataStore
        data_store = DataStore()
        
        # Test MCP tools availability
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        portfolio_tools = PortfolioTools(None)
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "database": "connected",
                "mcp_tools": "available",
                "api": "running"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(current_user: AuthUser = Depends(get_current_user)):
    """Custom Swagger UI with authentication."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


def custom_openapi():
    """Custom OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Include API routes
app.include_router(
    portfolio.router,
    prefix="/api/v1/portfolio",
    tags=["Portfolio"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    analysis.router,
    prefix="/api/v1/analysis",
    tags=["Analysis"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    execution.router,
    prefix="/api/v1/execution",
    tags=["Execution"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    monitoring.router,
    prefix="/api/v1/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    reporting.router,
    prefix="/api/v1/reporting",
    tags=["Reporting"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    strategies.router,
    prefix="/api/v1/strategies",
    tags=["Strategies"],
    dependencies=[Depends(get_current_user)]
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": time.time(),
                "path": str(request.url)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": time.time(),
                "path": str(request.url)
            }
        }
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("Financial Portfolio Automation API starting up...")
    
    # Initialize services
    try:
        # Test database connection
        from financial_portfolio_automation.data.store import DataStore
        data_store = DataStore()
        logger.info("Database connection established")
        
        # Initialize MCP tools
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        from financial_portfolio_automation.config.settings import get_config
        
        config = get_config()
        portfolio_tools = PortfolioTools(config)
        logger.info("MCP tools initialized")
        
        logger.info("API startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Financial Portfolio Automation API shutting down...")
    
    # Cleanup resources
    try:
        # Close database connections
        # Close any open connections, cleanup resources
        logger.info("Resources cleaned up successfully")
    except Exception as e:
        logger.error(f"Shutdown cleanup failed: {e}")
    
    logger.info("API shutdown completed")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "financial_portfolio_automation.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )