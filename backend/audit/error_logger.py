"""
Error Logging System for Legal Document Severity Classification System.

This module provides comprehensive error logging, monitoring integration,
and alerting capabilities for system errors.
"""

import logging
import json
import traceback
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from core.exceptions import BaseCustomException, ErrorSeverity


class LogLevel(str, Enum):
    """Log levels for error logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorLogger:
    """
    Comprehensive error logging system.
    
    Provides structured logging, error aggregation, and monitoring integration.
    """
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.error_patterns = {}
    
    def log_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an exception with comprehensive context.
        
        Args:
            exception: The exception to log
            context: Additional context information
            request_id: Request ID for tracing
            user_id: User ID if available
            additional_data: Any additional data to include
        """
        # Prepare log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
            "request_id": request_id,
            "user_id": user_id,
            "context": context or {},
            "additional_data": additional_data or {}
        }
        
        # Handle custom exceptions
        if isinstance(exception, BaseCustomException):
            log_data.update({
                "error_code": exception.error_code,
                "severity": exception.severity.value,
                "custom_context": exception.context,
                "cause": str(exception.cause) if exception.cause else None
            })
            
            # Log based on severity
            if exception.severity == ErrorSeverity.CRITICAL:
                self.logger.critical(
                    f"Critical error: {exception.message}",
                    extra=log_data,
                    exc_info=exception
                )
            elif exception.severity == ErrorSeverity.HIGH:
                self.logger.error(
                    f"High severity error: {exception.message}",
                    extra=log_data,
                    exc_info=exception
                )
            elif exception.severity == ErrorSeverity.MEDIUM:
                self.logger.warning(
                    f"Medium severity error: {exception.message}",
                    extra=log_data
                )
            else:
                self.logger.info(
                    f"Low severity error: {exception.message}",
                    extra=log_data
                )
        else:
            # Handle standard exceptions
            self.logger.error(
                f"Unhandled exception: {str(exception)}",
                extra=log_data,
                exc_info=exception
            )
        
        # Track error patterns
        self._track_error_pattern(exception, context)
    
    def log_error(
        self,
        message: str,
        error_code: str,
        level: LogLevel = LogLevel.ERROR,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log a structured error message.
        
        Args:
            message: Error message
            error_code: Standardized error code
            level: Log level
            context: Additional context
            request_id: Request ID for tracing
            user_id: User ID if available
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_code": error_code,
            "message": message,
            "request_id": request_id,
            "user_id": user_id,
            "context": context or {}
        }
        
        # Log at appropriate level
        if level == LogLevel.CRITICAL:
            self.logger.critical(message, extra=log_data)
        elif level == LogLevel.ERROR:
            self.logger.error(message, extra=log_data)
        elif level == LogLevel.WARNING:
            self.logger.warning(message, extra=log_data)
        elif level == LogLevel.INFO:
            self.logger.info(message, extra=log_data)
        else:
            self.logger.debug(message, extra=log_data)
    
    def log_api_error(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        error_message: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> None:
        """
        Log API-specific errors.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            error_message: Error message
            request_data: Request data (sanitized)
            response_data: Response data
            request_id: Request ID
            processing_time: Request processing time
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "error_message": error_message,
            "request_id": request_id,
            "processing_time": processing_time,
            "request_data": self._sanitize_data(request_data) if request_data else None,
            "response_data": response_data
        }
        
        if status_code >= 500:
            self.logger.error(f"API server error: {method} {endpoint}", extra=log_data)
        elif status_code >= 400:
            self.logger.warning(f"API client error: {method} {endpoint}", extra=log_data)
        else:
            self.logger.info(f"API response: {method} {endpoint}", extra=log_data)
    
    def log_external_service_error(
        self,
        service_name: str,
        operation: str,
        error_message: str,
        error_code: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None
    ) -> None:
        """
        Log errors from external services (Gemini API, Firestore, etc.).
        
        Args:
            service_name: Name of the external service
            operation: Operation being performed
            error_message: Error message
            error_code: Service-specific error code
            request_data: Request data (sanitized)
            response_data: Response data
            retry_count: Number of retries attempted
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_name": service_name,
            "operation": operation,
            "error_message": error_message,
            "error_code": error_code,
            "retry_count": retry_count,
            "request_data": self._sanitize_data(request_data) if request_data else None,
            "response_data": response_data
        }
        
        self.logger.error(f"External service error: {service_name} - {operation}", extra=log_data)
    
    def log_performance_issue(
        self,
        operation: str,
        duration: float,
        threshold: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log performance issues.
        
        Args:
            operation: Operation that was slow
            duration: Actual duration
            threshold: Expected threshold
            context: Additional context
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "duration": duration,
            "threshold": threshold,
            "performance_ratio": duration / threshold,
            "context": context or {}
        }
        
        self.logger.warning(f"Performance issue: {operation} took {duration:.2f}s", extra=log_data)
    
    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            description: Event description
            user_id: User ID if available
            ip_address: Client IP address
            user_agent: Client user agent
            additional_data: Additional event data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "additional_data": additional_data or {}
        }
        
        if severity.upper() in ["CRITICAL", "HIGH"]:
            self.logger.critical(f"Security event: {event_type}", extra=log_data)
        else:
            self.logger.warning(f"Security event: {event_type}", extra=log_data)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Error summary statistics
        """
        # This would typically query a logging backend
        # For now, return current in-memory counts
        return {
            "error_counts": dict(self.error_counts),
            "error_patterns": dict(self.error_patterns),
            "time_period_hours": hours,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _track_error_pattern(self, exception: Exception, context: Optional[Dict[str, Any]]) -> None:
        """Track error patterns for analysis."""
        error_type = type(exception).__name__
        
        # Count errors by type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Track patterns
        if isinstance(exception, BaseCustomException):
            pattern_key = f"{error_type}:{exception.error_code}"
        else:
            pattern_key = error_type
        
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = {
                "count": 0,
                "first_seen": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat(),
                "contexts": []
            }
        
        self.error_patterns[pattern_key]["count"] += 1
        self.error_patterns[pattern_key]["last_seen"] = datetime.utcnow().isoformat()
        
        # Store context (limit to last 5)
        if context:
            self.error_patterns[pattern_key]["contexts"].append(context)
            if len(self.error_patterns[pattern_key]["contexts"]) > 5:
                self.error_patterns[pattern_key]["contexts"] = self.error_patterns[pattern_key]["contexts"][-5:]
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data from logs.
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        if not data:
            return {}
        
        sensitive_keys = {
            'password', 'token', 'api_key', 'secret', 'authorization',
            'credit_card', 'ssn', 'social_security', 'passport'
        }
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, str) and len(value) > 1000:
                # Truncate very long strings
                sanitized[key] = value[:1000] + "...[TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized


class MonitoringIntegration:
    """
    Integration with monitoring systems.
    
    Provides hooks for external monitoring and alerting systems.
    """
    
    def __init__(self):
        self.alert_handlers = []
        self.metric_handlers = []
    
    def add_alert_handler(self, handler: callable) -> None:
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def add_metric_handler(self, handler: callable) -> None:
        """Add a metric handler function."""
        self.metric_handlers.append(handler)
    
    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send alert to configured handlers.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            context: Additional context
        """
        alert_data = {
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for handler in self.alert_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                # Don't let alert handler failures break the system
                logging.getLogger(__name__).error(f"Alert handler failed: {e}")
    
    def record_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        metric_data = {
            "metric_name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for handler in self.metric_handlers:
            try:
                handler(metric_data)
            except Exception as e:
                # Don't let metric handler failures break the system
                logging.getLogger(__name__).error(f"Metric handler failed: {e}")


# Global instances
error_logger = ErrorLogger("legal_classification_system")
monitoring = MonitoringIntegration()

# Export classes and instances
__all__ = [
    'LogLevel',
    'ErrorLogger',
    'MonitoringIntegration',
    'error_logger',
    'monitoring'
]