"""
Configuration module for the Legal Document Severity Classification System.
Handles environment variables and application settings with comprehensive validation.
"""

import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv
import logging

# Configure logging for configuration module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables with comprehensive validation."""
    
    # Gemini API Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY", description="Gemini API key for AI services")
    
    # Google Cloud Configuration
    google_cloud_project_id: str = Field(..., env="GOOGLE_CLOUD_PROJECT_ID", description="Google Cloud Project ID")
    firestore_database_id: str = Field("(default)", env="FIRESTORE_DATABASE_ID", description="Firestore database ID")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS", description="Path to Google Cloud service account key")
    
    # Google Cloud Vision Configuration
    vision_api_enabled: bool = Field(True, env="VISION_API_ENABLED", description="Enable Google Cloud Vision API")
    
    # Application Configuration
    environment: str = Field("development", env="ENVIRONMENT", description="Application environment (development, staging, production)")
    log_level: str = Field("INFO", env="LOG_LEVEL", description="Logging level")
    debug: bool = Field(False, env="DEBUG", description="Enable debug mode")
    
    # Server Configuration
    host: str = Field("0.0.0.0", env="HOST", description="Server host")
    port: int = Field(8000, env="PORT", description="Server port")
    workers: int = Field(1, env="WORKERS", description="Number of worker processes")
    
    # Classification Configuration
    default_confidence_threshold_auto_accept: float = Field(0.85, env="DEFAULT_CONFIDENCE_THRESHOLD_AUTO_ACCEPT", description="Confidence threshold for auto-acceptance")
    default_confidence_threshold_human_review: float = Field(0.60, env="DEFAULT_CONFIDENCE_THRESHOLD_HUMAN_REVIEW", description="Confidence threshold for human review")
    default_top_k_buckets: int = Field(3, env="DEFAULT_TOP_K_BUCKETS", description="Number of top buckets to retrieve")
    default_top_n_context_chunks: int = Field(5, env="DEFAULT_TOP_N_CONTEXT_CHUNKS", description="Number of context chunks to retrieve")
    
    # Performance Configuration
    max_concurrent_requests: int = Field(100, env="MAX_CONCURRENT_REQUESTS", description="Maximum concurrent requests")
    request_timeout: int = Field(300, env="REQUEST_TIMEOUT", description="Request timeout in seconds")
    gemini_rate_limit: int = Field(60, env="GEMINI_RATE_LIMIT", description="Gemini API rate limit per minute")
    
    # Security Configuration
    cors_origins: str = Field("*", env="CORS_ORIGINS", description="CORS allowed origins (comma-separated)")
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER", description="API key header name")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(True, env="ENABLE_METRICS", description="Enable metrics collection")
    metrics_port: int = Field(9090, env="METRICS_PORT", description="Metrics server port")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL", description="Health check interval in seconds")
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_environments = ['development', 'staging', 'production', 'test']
        if v not in valid_environments:
            raise ValueError(f'Environment must be one of: {valid_environments}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level value."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @validator('default_confidence_threshold_auto_accept', 'default_confidence_threshold_human_review')
    def validate_confidence_thresholds(cls, v):
        """Validate confidence threshold values."""
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence thresholds must be between 0.0 and 1.0')
        return v
    
    @validator('default_top_k_buckets', 'default_top_n_context_chunks')
    def validate_positive_integers(cls, v):
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError('Value must be a positive integer')
        return v
    
    @validator('port', 'metrics_port')
    def validate_port_numbers(cls, v):
        """Validate port numbers."""
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('google_application_credentials')
    def validate_credentials_path(cls, v):
        """Validate Google Cloud credentials path if provided."""
        if v and not Path(v).exists():
            logger.warning(f"Google Cloud credentials file not found: {v}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        validate_assignment = True


# Global settings instance
settings = Settings()


def validate_configuration() -> bool:
    """
    Validate that all required configuration is present and valid.
    
    Returns:
        bool: True if configuration is valid, False otherwise
        
    Raises:
        ConfigurationError: If configuration validation fails
    """
    try:
        # Check required fields
        if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
            raise ConfigurationError("GEMINI_API_KEY is required and must be set to a valid API key")
        
        if not settings.google_cloud_project_id or settings.google_cloud_project_id == "your_project_id_here":
            raise ConfigurationError("GOOGLE_CLOUD_PROJECT_ID is required and must be set to a valid project ID")
        
        # Validate confidence threshold relationship
        if settings.default_confidence_threshold_human_review >= settings.default_confidence_threshold_auto_accept:
            raise ConfigurationError("default_confidence_threshold_human_review must be less than default_confidence_threshold_auto_accept")
        
        # Validate Google Cloud credentials if specified
        if settings.google_application_credentials:
            creds_path = Path(settings.google_application_credentials)
            if not creds_path.exists():
                raise ConfigurationError(f"Google Cloud credentials file not found: {settings.google_application_credentials}")
            if not creds_path.is_file():
                raise ConfigurationError(f"Google Cloud credentials path is not a file: {settings.google_application_credentials}")
        
        # Environment-specific validations
        if settings.environment == "production":
            if settings.debug:
                logger.warning("Debug mode is enabled in production environment")
            if settings.log_level == "DEBUG":
                logger.warning("Debug logging is enabled in production environment")
        
        # Validate CORS origins format
        if settings.cors_origins != "*":
            origins = [origin.strip() for origin in settings.cors_origins.split(",")]
            for origin in origins:
                if not origin.startswith(("http://", "https://")) and origin != "localhost":
                    logger.warning(f"CORS origin may be invalid: {origin}")
        
        logger.info("Configuration validation successful")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(f"Configuration validation failed: {e}")


def validate_required_environment_variables() -> Dict[str, Any]:
    """
    Validate that all required environment variables are present.
    
    Returns:
        Dict[str, Any]: Dictionary of missing or invalid environment variables
    """
    missing_vars = {}
    
    # Required environment variables
    required_vars = {
        "GEMINI_API_KEY": "Gemini API key for AI services",
        "GOOGLE_CLOUD_PROJECT_ID": "Google Cloud Project ID for Firestore",
    }
    
    # Test/placeholder values that should be replaced in production
    test_values = [
        "your_api_key_here", 
        "your_project_id_here", 
        "test_api_key_for_testing", 
        "test-project-id",
        "your_gemini_api_key_here"
    ]
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            missing_vars[var_name] = f"Missing: {description}"
        elif value in test_values and settings.environment == "production":
            missing_vars[var_name] = f"Production requires real value: {description}"
    
    # Check Google Cloud credentials
    if is_render_deployment():
        # On Render, we need either SERVICE_KEY_JSON or default credentials
        service_key_json = os.getenv("SERVICE_KEY_JSON")
        if not service_key_json:
            missing_vars["SERVICE_KEY_JSON"] = "Required for Render deployment: Google Cloud service account key as JSON string"
    else:
        # Local development should have credentials file
        if settings.google_application_credentials:
            if not Path(settings.google_application_credentials).exists():
                missing_vars["GOOGLE_APPLICATION_CREDENTIALS"] = f"Credentials file not found: {settings.google_application_credentials}"
    
    return missing_vars


def get_configuration_summary() -> Dict[str, Any]:
    """
    Get a summary of current configuration settings (excluding sensitive data).
    
    Returns:
        Dict[str, Any]: Configuration summary
    """
    return {
        "environment": settings.environment,
        "log_level": settings.log_level,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "workers": settings.workers,
        "vision_api_enabled": settings.vision_api_enabled,
        "confidence_thresholds": {
            "auto_accept": settings.default_confidence_threshold_auto_accept,
            "human_review": settings.default_confidence_threshold_human_review,
        },
        "classification_settings": {
            "top_k_buckets": settings.default_top_k_buckets,
            "top_n_context_chunks": settings.default_top_n_context_chunks,
        },
        "performance_settings": {
            "max_concurrent_requests": settings.max_concurrent_requests,
            "request_timeout": settings.request_timeout,
            "gemini_rate_limit": settings.gemini_rate_limit,
        },
        "monitoring": {
            "enable_metrics": settings.enable_metrics,
            "metrics_port": settings.metrics_port,
            "health_check_interval": settings.health_check_interval,
        },
        "has_gemini_api_key": bool(settings.gemini_api_key and settings.gemini_api_key != "test_api_key_for_testing"),
        "has_google_credentials": bool(settings.google_application_credentials),
    }


def is_render_deployment() -> bool:
    """
    Check if we're running on Render platform.
    
    Returns:
        bool: True if running on Render, False otherwise
    """
    return os.getenv("RENDER") == "true" or "render.com" in os.getenv("RENDER_EXTERNAL_URL", "")


def get_firestore_config() -> dict:
    """
    Get Firestore configuration dictionary.
    Handles both local development and Render deployment.
    
    Returns:
        dict: Firestore configuration parameters
    """
    config = {
        "project": settings.google_cloud_project_id,
        "database": settings.firestore_database_id,
    }
    
    # Handle credentials differently for Render vs local development
    if is_render_deployment():
        # On Render, use SERVICE_KEY_JSON environment variable
        service_key_json = os.getenv("SERVICE_KEY_JSON")
        if service_key_json:
            config["service_account_info"] = service_key_json
        # If no SERVICE_KEY_JSON, rely on default credentials (ADC)
    else:
        # Local development: use credentials file if specified
        if settings.google_application_credentials and Path(settings.google_application_credentials).exists():
            config["credentials_path"] = settings.google_application_credentials
    
    return config


def get_gemini_config() -> dict:
    """
    Get Gemini API configuration dictionary.
    
    Returns:
        dict: Gemini API configuration parameters
    """
    return {
        "api_key": settings.gemini_api_key,
    }


def get_vision_config() -> dict:
    """
    Get Google Cloud Vision API configuration dictionary.
    
    Returns:
        dict: Vision API configuration parameters
    """
    config = {
        "project": settings.google_cloud_project_id,
        "enabled": settings.vision_api_enabled,
    }
    
    # Add credentials path if specified
    if settings.google_application_credentials:
        config["credentials_path"] = settings.google_application_credentials
    
    return config