"""
Retry and Fallback Mechanisms for Legal Document Severity Classification System.

This module provides exponential backoff retry logic, circuit breaker patterns,
and fallback strategies for external service failures.
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps

from core.exceptions import (
    GeminiAPIException, GeminiRateLimitException, GeminiServiceUnavailableException,
    FirestoreException, FirestoreConnectionException, ServiceUnavailableException
)
from audit.error_logger import error_logger

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.strategy = strategy
        self.retryable_exceptions = retryable_exceptions or [
            GeminiAPIException,
            FirestoreConnectionException,
            ServiceUnavailableException,
            ConnectionError,
            TimeoutError
        ]


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_calls = half_open_max_calls


class RetryMechanism:
    """
    Retry mechanism with exponential backoff and jitter.
    
    Provides configurable retry logic for handling transient failures.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        else:  # IMMEDIATE
            delay = 0
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter and delay > 0:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def is_retryable(self, exception: Exception) -> bool:
        """
        Check if an exception is retryable.
        
        Args:
            exception: Exception to check
            
        Returns:
            True if retryable, False otherwise
        """
        # Check for rate limiting with retry-after
        if isinstance(exception, GeminiRateLimitException):
            return True
        
        # Check against configured retryable exceptions
        return any(isinstance(exception, exc_type) for exc_type in self.config.retryable_exceptions)
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            context: Additional context for logging
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        context = context or {}
        
        for attempt in range(self.config.max_attempts):
            try:
                # Log retry attempt
                if attempt > 0:
                    error_logger.log_error(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} for {func.__name__}",
                        "RETRY_ATTEMPT",
                        context={
                            **context,
                            "attempt": attempt + 1,
                            "max_attempts": self.config.max_attempts,
                            "function": func.__name__
                        }
                    )
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - log if this was a retry
                if attempt > 0:
                    error_logger.log_error(
                        f"Retry successful for {func.__name__} after {attempt + 1} attempts",
                        "RETRY_SUCCESS",
                        level=error_logger.LogLevel.INFO,
                        context={
                            **context,
                            "successful_attempt": attempt + 1,
                            "function": func.__name__
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                if not self.is_retryable(e):
                    error_logger.log_error(
                        f"Non-retryable exception in {func.__name__}: {str(e)}",
                        "NON_RETRYABLE_ERROR",
                        context={
                            **context,
                            "exception_type": type(e).__name__,
                            "function": func.__name__
                        }
                    )
                    raise e
                
                # Check if we have more attempts
                if attempt >= self.config.max_attempts - 1:
                    error_logger.log_error(
                        f"All retry attempts exhausted for {func.__name__}: {str(e)}",
                        "RETRY_EXHAUSTED",
                        context={
                            **context,
                            "total_attempts": self.config.max_attempts,
                            "exception_type": type(e).__name__,
                            "function": func.__name__
                        }
                    )
                    break
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                
                # Handle rate limiting with specific retry-after
                if isinstance(e, GeminiRateLimitException) and "retry_after" in e.context:
                    delay = max(delay, e.context["retry_after"])
                
                error_logger.log_error(
                    f"Retryable exception in {func.__name__}, waiting {delay:.2f}s: {str(e)}",
                    "RETRYABLE_ERROR",
                    context={
                        **context,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "exception_type": type(e).__name__,
                        "function": func.__name__
                    }
                )
                
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # All retries failed
        raise last_exception


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by temporarily stopping calls to failing services.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.success_count = 0
    
    def can_execute(self) -> bool:
        """
        Check if execution is allowed based on circuit breaker state.
        
        Returns:
            True if execution is allowed, False otherwise
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
                error_logger.log_error(
                    f"Circuit breaker {self.name} transitioning to HALF_OPEN",
                    "CIRCUIT_BREAKER_HALF_OPEN",
                    level=error_logger.LogLevel.INFO,
                    context={"circuit_breaker": self.name}
                )
                return True
            return False
        else:  # HALF_OPEN
            return self.half_open_calls < self.config.half_open_max_calls
    
    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.half_open_max_calls:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                error_logger.log_error(
                    f"Circuit breaker {self.name} recovered, transitioning to CLOSED",
                    "CIRCUIT_BREAKER_RECOVERED",
                    level=error_logger.LogLevel.INFO,
                    context={"circuit_breaker": self.name}
                )
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self, exception: Exception) -> None:
        """
        Record a failed execution.
        
        Args:
            exception: The exception that occurred
        """
        if not isinstance(exception, self.config.expected_exception):
            return
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            error_logger.log_error(
                f"Circuit breaker {self.name} failed during HALF_OPEN, returning to OPEN",
                "CIRCUIT_BREAKER_FAILED_HALF_OPEN",
                context={
                    "circuit_breaker": self.name,
                    "exception_type": type(exception).__name__
                }
            )
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
            error_logger.log_error(
                f"Circuit breaker {self.name} opened due to {self.failure_count} failures",
                "CIRCUIT_BREAKER_OPENED",
                context={
                    "circuit_breaker": self.name,
                    "failure_count": self.failure_count,
                    "threshold": self.config.failure_threshold
                }
            )
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.half_open_calls += 1
    
    async def execute(
        self,
        func: Callable,
        *args,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            context: Additional context for logging
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            ServiceUnavailableException: If circuit breaker is open
            Original exception: If function fails
        """
        if not self.can_execute():
            error_logger.log_error(
                f"Circuit breaker {self.name} is OPEN, rejecting call to {func.__name__}",
                "CIRCUIT_BREAKER_REJECTED",
                context={
                    "circuit_breaker": self.name,
                    "function": func.__name__,
                    "state": self.state.value
                }
            )
            raise ServiceUnavailableException(
                f"Service {self.name} is currently unavailable (circuit breaker open)"
            )
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self.record_success()
            return result
            
        except Exception as e:
            self.record_failure(e)
            raise


class FallbackStrategy:
    """
    Fallback strategy for when primary services fail.
    
    Provides alternative approaches when AI services are unavailable.
    """
    
    def __init__(self):
        self.fallback_handlers = {}
    
    def register_fallback(self, service_name: str, handler: Callable) -> None:
        """
        Register a fallback handler for a service.
        
        Args:
            service_name: Name of the service
            handler: Fallback handler function
        """
        self.fallback_handlers[service_name] = handler
        logger.info(f"Registered fallback handler for {service_name}")
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with fallback if primary fails.
        
        Args:
            service_name: Name of the service
            primary_func: Primary function to execute
            *args: Function arguments
            context: Additional context
            **kwargs: Function keyword arguments
            
        Returns:
            Result from primary or fallback function
        """
        context = context or {}
        
        try:
            # Try primary function
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(*args, **kwargs)
            else:
                return primary_func(*args, **kwargs)
                
        except Exception as e:
            error_logger.log_error(
                f"Primary service {service_name} failed, attempting fallback: {str(e)}",
                "FALLBACK_TRIGGERED",
                context={
                    **context,
                    "service_name": service_name,
                    "primary_function": primary_func.__name__,
                    "exception_type": type(e).__name__
                }
            )
            
            # Try fallback if available
            if service_name in self.fallback_handlers:
                try:
                    fallback_handler = self.fallback_handlers[service_name]
                    
                    if asyncio.iscoroutinefunction(fallback_handler):
                        result = await fallback_handler(*args, **kwargs)
                    else:
                        result = fallback_handler(*args, **kwargs)
                    
                    error_logger.log_error(
                        f"Fallback successful for {service_name}",
                        "FALLBACK_SUCCESS",
                        level=error_logger.LogLevel.INFO,
                        context={
                            **context,
                            "service_name": service_name
                        }
                    )
                    
                    return result
                    
                except Exception as fallback_error:
                    error_logger.log_error(
                        f"Fallback failed for {service_name}: {str(fallback_error)}",
                        "FALLBACK_FAILED",
                        context={
                            **context,
                            "service_name": service_name,
                            "fallback_exception_type": type(fallback_error).__name__
                        }
                    )
                    # Re-raise original exception
                    raise e
            else:
                error_logger.log_error(
                    f"No fallback handler registered for {service_name}",
                    "NO_FALLBACK_HANDLER",
                    context={
                        **context,
                        "service_name": service_name
                    }
                )
                raise e


# Decorators for easy use
def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to functions.
    
    Args:
        config: Retry configuration
    """
    if config is None:
        config = RetryConfig()
    
    retry_mechanism = RetryMechanism(config)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_mechanism.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
    """
    if config is None:
        config = CircuitBreakerConfig()
    
    circuit_breaker = CircuitBreaker(name, config)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.execute(func, *args, **kwargs)
        return wrapper
    return decorator


# Global instances
default_retry_config = RetryConfig()
gemini_retry_config = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    retryable_exceptions=[
        GeminiAPIException,
        GeminiRateLimitException,
        GeminiServiceUnavailableException,
        ConnectionError,
        TimeoutError
    ]
)

firestore_retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=[
        FirestoreConnectionException,
        ConnectionError,
        TimeoutError
    ]
)

# Circuit breakers
gemini_circuit_breaker = CircuitBreaker(
    "gemini_api",
    CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception=GeminiAPIException
    )
)

firestore_circuit_breaker = CircuitBreaker(
    "firestore",
    CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        expected_exception=FirestoreException
    )
)

# Fallback strategy
fallback_strategy = FallbackStrategy()

# Export all classes and instances
__all__ = [
    'RetryStrategy',
    'CircuitBreakerState',
    'RetryConfig',
    'CircuitBreakerConfig',
    'RetryMechanism',
    'CircuitBreaker',
    'FallbackStrategy',
    'with_retry',
    'with_circuit_breaker',
    'default_retry_config',
    'gemini_retry_config',
    'firestore_retry_config',
    'gemini_circuit_breaker',
    'firestore_circuit_breaker',
    'fallback_strategy'
]