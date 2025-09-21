"""
Middleware for Legal Document Severity Classification System.

This module provides middleware for request tracking, error monitoring,
and performance metrics collection.
"""

import logging
import time
import uuid
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking requests and adding request IDs.
    
    Adds unique request IDs to all requests for tracing and debugging.
    Logs request details and response times.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracking and timing."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            return response
            
        except Exception as exc:
            # Calculate processing time for failed requests
            processing_time = time.time() - start_time
            
            # Log failed request
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "exception": str(exc),
                    "exception_type": type(exc).__name__,
                    "timestamp": datetime.utcnow().isoformat()
                },
                exc_info=True
            )
            
            # Re-raise the exception to be handled by exception handlers
            raise


class ErrorMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring and alerting on errors.
    
    Tracks error rates and patterns for system monitoring.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_counts = {}
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error monitoring."""
        endpoint = f"{request.method} {request.url.path}"
        
        # Increment request count
        self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1
        
        try:
            response = await call_next(request)
            
            # Monitor error responses
            if response.status_code >= 400:
                self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
                
                # Log error rate if it's high
                error_rate = self.error_counts[endpoint] / self.request_counts[endpoint]
                if error_rate > 0.1 and self.request_counts[endpoint] > 10:  # >10% error rate with >10 requests
                    logger.warning(
                        f"High error rate detected for {endpoint}: {error_rate:.2%}",
                        extra={
                            "endpoint": endpoint,
                            "error_rate": error_rate,
                            "error_count": self.error_counts[endpoint],
                            "total_requests": self.request_counts[endpoint]
                        }
                    )
            
            return response
            
        except Exception as exc:
            # Increment error count for exceptions
            self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1
            
            # Log exception with monitoring context
            logger.error(
                f"Exception in {endpoint}",
                extra={
                    "endpoint": endpoint,
                    "exception_type": type(exc).__name__,
                    "error_count": self.error_counts[endpoint],
                    "total_requests": self.request_counts[endpoint]
                }
            )
            
            raise


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring performance metrics.
    
    Tracks response times and identifies slow endpoints.
    """
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 5.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold  # seconds
        self.response_times = {}
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance monitoring."""
        endpoint = f"{request.method} {request.url.path}"
        start_time = time.time()
        
        try:
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Track response times
            if endpoint not in self.response_times:
                self.response_times[endpoint] = []
            self.response_times[endpoint].append(processing_time)
            
            # Keep only last 100 response times per endpoint
            if len(self.response_times[endpoint]) > 100:
                self.response_times[endpoint] = self.response_times[endpoint][-100:]
            
            self.request_counts[endpoint] = self.request_counts.get(endpoint, 0) + 1
            
            # Log slow requests
            if processing_time > self.slow_request_threshold:
                avg_time = sum(self.response_times[endpoint]) / len(self.response_times[endpoint])
                logger.warning(
                    f"Slow request detected: {endpoint} took {processing_time:.2f}s",
                    extra={
                        "endpoint": endpoint,
                        "processing_time": processing_time,
                        "average_time": avg_time,
                        "request_count": self.request_counts[endpoint],
                        "request_id": getattr(request.state, 'request_id', None)
                    }
                )
            
            # Log performance summary every 100 requests per endpoint
            if self.request_counts[endpoint] % 100 == 0:
                avg_time = sum(self.response_times[endpoint]) / len(self.response_times[endpoint])
                max_time = max(self.response_times[endpoint])
                min_time = min(self.response_times[endpoint])
                
                logger.info(
                    f"Performance summary for {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "request_count": self.request_counts[endpoint],
                        "average_time": avg_time,
                        "max_time": max_time,
                        "min_time": min_time
                    }
                )
            
            return response
            
        except Exception as exc:
            processing_time = time.time() - start_time
            
            # Log exception with timing
            logger.error(
                f"Exception in {endpoint} after {processing_time:.2f}s",
                extra={
                    "endpoint": endpoint,
                    "processing_time": processing_time,
                    "exception_type": type(exc).__name__,
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
            
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    
    Adds standard security headers to all responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


# Export all middleware classes
__all__ = [
    'RequestTrackingMiddleware',
    'ErrorMonitoringMiddleware',
    'PerformanceMonitoringMiddleware',
    'SecurityHeadersMiddleware'
]