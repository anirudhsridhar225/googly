"""
Configuration module for the Legal Document Severity Classification System.
Handles environment variables and application settings with comprehensive validation.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import json
import tempfile
import certifi
import ssl
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Configure logging for configuration module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Immediately sanitize GOOGLE_APPLICATION_CREDENTIALS loaded from .env
# This prevents libraries that read the env var during import from seeing
# a path wrapped in quotes or a ~ that won't expand, which can cause early
# failures (including SSL/TLS initialization errors) when the credentials
# file can't be read.
gac_raw = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if gac_raw:
    gac = gac_raw.strip()
    if (gac.startswith('"') and gac.endswith('"')) or (
        gac.startswith("'") and gac.endswith("'")
    ):
        gac = gac[1:-1]
    gac = os.path.expanduser(gac)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gac

# Ensure SSL certificate bundle is available for libraries that rely on OpenSSL
# This prevents intermittent SSL verification errors when environment variables
# (like GOOGLE_APPLICATION_CREDENTIALS) change how client libraries initialize TLS.
if not os.getenv("SSL_CERT_FILE"):
    try:
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except Exception:
        # If certifi isn't available for some reason, continue without setting it;
        # the environment's default will be used and any SSL errors will surface normally.
        pass

# Diagnostic and fallback for intermittent SSLContext creation failures.
def _ssl_diagnostic_and_fix():
    try:
        logger.debug("SSL diagnostic: SSL_CERT_FILE=%s SSL_CERT_DIR=%s REQUESTS_CA_BUNDLE=%s CURL_CA_BUNDLE=%s",
                     os.getenv('SSL_CERT_FILE'), os.getenv('SSL_CERT_DIR'), os.getenv('REQUESTS_CA_BUNDLE'), os.getenv('CURL_CA_BUNDLE'))
        # Try to create a TLS client context to detect early failures
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        logger.debug("SSLContext creation OK")
        return
    except Exception as e:
        logger.warning("Initial SSLContext creation failed: %s", e)

    # Attempt to repair common misconfigurations by forcing certifi bundle and removing other bundle envs
    try:
        cert_path = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_path
        for var in ('REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_DIR'):
            if os.getenv(var):
                logger.info("Unsetting %s (was %s)", var, os.getenv(var))
                os.environ.pop(var, None)
        # Retry SSLContext creation
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        logger.info("SSLContext creation succeeded after forcing certifi bundle: %s", cert_path)
    except Exception as e:
        logger.error("SSLContext creation still failing after attempting fix: %s", e)


_ssl_diagnostic_and_fix()

# If SERVICE_KEY_JSON is provided (e.g., in Render), write it to a temporary
# credentials file and set GOOGLE_APPLICATION_CREDENTIALS so Google libraries
# can pick it up. This handles JSON strings with escaped newlines correctly.
service_key_json = os.getenv("SERVICE_KEY_JSON")
if service_key_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    try:
        # If the env var was provided with surrounding quotes, strip them
        if (service_key_json.startswith('"') and service_key_json.endswith('"')) or (
            service_key_json.startswith("'") and service_key_json.endswith("'")
        ):
            service_key_json = service_key_json[1:-1]

        # Try to parse to validate JSON; if parsing fails, keep raw string
        parsed = None
        try:
            parsed = json.loads(service_key_json)
        except Exception:
            # Might already be a JSON string with escaped newlines; leave as-is
            parsed = None

        # Write to a secure temp file
        fd, temp_path = tempfile.mkstemp(prefix="googly_service_account_", suffix=".json")
        with os.fdopen(fd, "w") as f:
            if parsed is not None:
                json.dump(parsed, f)
            else:
                f.write(service_key_json)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
    except Exception:
        # Don't crash startup; let later validation report missing/invalid creds
        pass


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""

    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables with comprehensive validation."""

    # Gemini API Configuration
    gemini_api_key: str = Field(
        description="Gemini API key for AI services"
    )

    # Google Cloud Configuration
    google_cloud_project_id: str = Field(
        description="Google Cloud Project ID"
    )
    firestore_database_id: str = Field(
        default="(default)", description="Firestore database ID"
    )
    google_application_credentials: Optional[str] = Field(
        default=None,
        description="Path to Google Cloud service account key",
    )

    # Google Cloud Vision Configuration
    vision_api_enabled: bool = Field(
        default=True, description="Enable Google Cloud Vision API"
    )

    # Application Configuration
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Classification Configuration
    default_confidence_threshold_auto_accept: float = Field(
        default=0.85,
        description="Confidence threshold for auto-acceptance",
    )
    default_confidence_threshold_human_review: float = Field(
        default=0.60,
        description="Confidence threshold for human review",
    )
    default_top_k_buckets: int = Field(
        default=3, description="Number of top buckets to retrieve"
    )
    default_top_n_context_chunks: int = Field(
        default=5,
        description="Number of context chunks to retrieve",
    )

    # Performance Configuration
    max_concurrent_requests: int = Field(
        default=100, description="Maximum concurrent requests"
    )
    request_timeout: int = Field(
        default=300, description="Request timeout in seconds"
    )
    gemini_rate_limit: int = Field(
        default=60, description="Gemini API rate limit per minute"
    )

    # Security Configuration
    cors_origins: str = Field(
        default="*", description="CORS allowed origins (comma-separated)"
    )
    api_key_header: str = Field(
        default="X-API-Key", description="API key header name"
    )

    # Monitoring Configuration
    enable_metrics: bool = Field(
        default=True, description="Enable metrics collection"
    )
    metrics_port: int = Field(
        default=9090, description="Metrics server port"
    )
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_environments = ["development", "staging", "production", "test"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level value."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator(
        "default_confidence_threshold_auto_accept",
        "default_confidence_threshold_human_review",
    )
    @classmethod
    def validate_confidence_thresholds(cls, v):
        """Validate confidence threshold values."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence thresholds must be between 0.0 and 1.0")
        return v

    @field_validator("default_top_k_buckets", "default_top_n_context_chunks")
    @classmethod
    def validate_positive_integers(cls, v):
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError("Value must be a positive integer")
        return v

    @field_validator("port", "metrics_port")
    @classmethod
    def validate_port_numbers(cls, v):
        """Validate port numbers."""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("google_application_credentials")
    @classmethod
    def validate_credentials_path(cls, v):
        """Validate Google Cloud credentials path if provided."""
        if not v:
            return v

        # Strip surrounding quotes and expand ~
        v_str = str(v).strip()
        if (v_str.startswith('"') and v_str.endswith('"')) or (
            v_str.startswith("'") and v_str.endswith("'")
        ):
            v_str = v_str[1:-1]
        v_str = os.path.expanduser(v_str)

        if not Path(v_str).exists():
            logger.warning(f"Google Cloud credentials file not found: {v_str}")
        return v_str

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "validate_assignment": True,
        "env_prefix": "",
    }


# Global settings instance
settings = Settings(gemini_api_key=os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here"), google_cloud_project_id=os.getenv("GOOGLE_CLOUD_PROJECT_ID", "your_project_id_here"))


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
        if (
            not settings.gemini_api_key
            or settings.gemini_api_key == "your_gemini_api_key_here"
        ):
            raise ConfigurationError(
                "GEMINI_API_KEY is required and must be set to a valid API key"
            )

        if (
            not settings.google_cloud_project_id
            or settings.google_cloud_project_id == "your_project_id_here"
        ):
            raise ConfigurationError(
                "GOOGLE_CLOUD_PROJECT_ID is required and must be set to a valid project ID"
            )

        # Validate confidence threshold relationship
        if (
            settings.default_confidence_threshold_human_review
            >= settings.default_confidence_threshold_auto_accept
        ):
            raise ConfigurationError(
                "default_confidence_threshold_human_review must be less than default_confidence_threshold_auto_accept"
            )

        # Validate Google Cloud credentials if specified
        if settings.google_application_credentials:
            creds_path = Path(settings.google_application_credentials)
            if not creds_path.exists():
                raise ConfigurationError(
                    f"Google Cloud credentials file not found: {
                        settings.google_application_credentials
                    }"
                )
            if not creds_path.is_file():
                raise ConfigurationError(
                    f"Google Cloud credentials path is not a file: {
                        settings.google_application_credentials
                    }"
                )

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
                if (
                    not origin.startswith(("http://", "https://"))
                    and origin != "localhost"
                ):
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
        "your_gemini_api_key_here",
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
            missing_vars["SERVICE_KEY_JSON"] = (
                "Required for Render deployment: Google Cloud service account key as JSON string"
            )
    else:
        # Local development should have credentials file
        if settings.google_application_credentials:
            if not Path(settings.google_application_credentials).exists():
                missing_vars[
                    "GOOGLE_APPLICATION_CREDENTIALS"
                ] = f"Credentials file not found: {
                    settings.google_application_credentials
                }"

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
        "has_gemini_api_key": bool(
            settings.gemini_api_key
            and settings.gemini_api_key != "test_api_key_for_testing"
        ),
        "has_google_credentials": bool(settings.google_application_credentials),
    }


def is_render_deployment() -> bool:
    """
    Check if we're running on Render platform.

    Returns:
        bool: True if running on Render, False otherwise
    """
    return os.getenv("RENDER") == "true" or "render.com" in os.getenv(
        "RENDER_EXTERNAL_URL", ""
    )


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
        if (
            settings.google_application_credentials
            and Path(settings.google_application_credentials).exists()
        ):
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

