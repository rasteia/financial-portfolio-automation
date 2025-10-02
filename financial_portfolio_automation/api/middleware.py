"""
Middleware for the REST API.

Provides rate limiting, logging, error handling, and other middleware
functionality for the portfolio management API.
"""

import time
import logging
import json
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        calls: int = 100,
        period: int = 3600,  # 1 hour
        per_user_calls: int = 1000,
        per_user_period: int = 3600
    ):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.per_user_calls = per_user_calls
        self.per_user_period = per_user_period
        
        # Global rate limiting
        self.global_requests = deque()
        
        # Per-user rate limiting
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        
        # Per-IP rate limiting
        self.ip_requests: Dict[str, deque] = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old requests
        self._clean_old_requests(current_time)
        
        # Check global rate limit
        if len(self.global_requests) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": 429,
                        "message": "Global rate limit exceeded",
                        "retry_after": self.period
                    }
                }
            )
        
        # Check IP rate limit
        if len(self.ip_requests[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": 429,
                        "message": "IP rate limit exceeded",
                        "retry_after": self.period
                    }
                }
            )
        
        # Add request to tracking
        self.global_requests.append(current_time)
        self.ip_requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.calls - len(self.ip_requests[client_ip])))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.period))
        
        return response
    
    def _clean_old_requests(self, current_time: float):
        """Clean old requests from tracking."""
        cutoff_time = current_time - self.period
        
        # Clean global requests
        while self.global_requests and self.global_requests[0] < cutoff_time:
            self.global_requests.popleft()
        
        # Clean IP requests
        for ip, requests in self.ip_requests.items():
            while requests and requests[0] < cutoff_time:
                requests.popleft()
        
        # Clean user requests
        for user, requests in self.user_requests.items():
            while requests and requests[0] < cutoff_time:
                requests.popleft()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""
    
    def __init__(self, app: ASGIApp, log_requests: bool = True, log_responses: bool = True):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next):
        """Process request with logging."""
        start_time = time.time()
        
        # Log request
        if self.log_requests:
            await self._log_request(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        if self.log_responses:
            self._log_response(request, response, process_time)
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    async def _log_request(self, request: Request):
        """Log incoming request."""
        client_ip = request.client.host
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        
        # Remove sensitive headers
        sensitive_headers = ["authorization", "x-api-key", "cookie"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "***REDACTED***"
        
        logger.info(
            f"Request: {method} {url} from {client_ip}",
            extra={
                "method": method,
                "url": url,
                "client_ip": client_ip,
                "headers": headers,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _log_response(self, request: Request, response: Response, process_time: float):
        """Log outgoing response."""
        method = request.method
        url = str(request.url)
        status_code = response.status_code
        
        log_level = logging.INFO
        if status_code >= 400:
            log_level = logging.WARNING
        if status_code >= 500:
            log_level = logging.ERROR
        
        logger.log(
            log_level,
            f"Response: {method} {url} - {status_code} ({process_time:.3f}s)",
            extra={
                "method": method,
                "url": url,
                "status_code": status_code,
                "process_time": process_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with error handling."""
        try:
            response = await call_next(request)
            return response
        
        except HTTPException as exc:
            # Re-raise HTTP exceptions to be handled by FastAPI
            raise exc
        
        except Exception as exc:
            # Log unexpected errors
            logger.error(
                f"Unhandled exception in {request.method} {request.url}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host,
                    "error": str(exc),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Return generic error response
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class CacheMiddleware(BaseHTTPMiddleware):
    """Simple in-memory caching middleware."""
    
    def __init__(self, app: ASGIApp, cache_ttl: int = 300):  # 5 minutes default
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next):
        """Process request with caching."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        current_time = time.time()
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if current_time - cache_entry["timestamp"] < self.cache_ttl:
                # Return cached response
                cached_response = cache_entry["response"]
                response = JSONResponse(
                    content=cached_response["content"],
                    status_code=cached_response["status_code"]
                )
                response.headers["X-Cache"] = "HIT"
                return response
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            try:
                content = json.loads(response_body.decode())
                
                # Store in cache
                self.cache[cache_key] = {
                    "timestamp": current_time,
                    "response": {
                        "content": content,
                        "status_code": response.status_code
                    }
                }
                
                # Clean old cache entries
                self._clean_cache(current_time)
                
                # Recreate response
                response = JSONResponse(content=content, status_code=response.status_code)
                response.headers["X-Cache"] = "MISS"
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Can't cache non-JSON responses
                response.headers["X-Cache"] = "SKIP"
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        url = str(request.url)
        # Include user info in cache key for user-specific data
        user_header = request.headers.get("authorization", "")
        return f"{url}:{hash(user_header)}"
    
    def _clean_cache(self, current_time: float):
        """Clean expired cache entries."""
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry["timestamp"] > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]


class MetricsMiddleware(BaseHTTPMiddleware):
    """Metrics collection middleware."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            "requests_total": 0,
            "requests_by_method": defaultdict(int),
            "requests_by_status": defaultdict(int),
            "response_times": deque(maxlen=1000),  # Keep last 1000 response times
            "errors_total": 0,
            "start_time": time.time()
        }
    
    async def dispatch(self, request: Request, call_next):
        """Collect metrics for request."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        process_time = time.time() - start_time
        
        # Update metrics
        self.metrics["requests_total"] += 1
        self.metrics["requests_by_method"][request.method] += 1
        self.metrics["requests_by_status"][response.status_code] += 1
        self.metrics["response_times"].append(process_time)
        
        if response.status_code >= 400:
            self.metrics["errors_total"] += 1
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        response_times = list(self.metrics["response_times"])
        
        return {
            "requests_total": self.metrics["requests_total"],
            "requests_by_method": dict(self.metrics["requests_by_method"]),
            "requests_by_status": dict(self.metrics["requests_by_status"]),
            "errors_total": self.metrics["errors_total"],
            "uptime_seconds": time.time() - self.metrics["start_time"],
            "response_time_stats": {
                "count": len(response_times),
                "avg": sum(response_times) / len(response_times) if response_times else 0,
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0
            }
        }


# Global metrics instance
metrics_middleware = None


def get_metrics() -> Dict[str, Any]:
    """Get current API metrics."""
    if metrics_middleware:
        return metrics_middleware.get_metrics()
    return {"error": "Metrics not available"}