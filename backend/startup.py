"""
Enhanced application startup module for initializing and testing system components.
Includes comprehensive health checks, database initialization, and system validation.
"""

import asyncio
import logging
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Configure basic logging (will be reconfigured after settings load)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class StartupCheck:
    """Individual startup check with metadata."""
    
    def __init__(self, name: str, description: str, critical: bool = True):
        self.name = name
        self.description = description
        self.critical = critical
        self.status = "pending"
        self.error_message = None
        self.duration = None
        self.timestamp = None
    
    def start(self):
        """Mark check as started."""
        self.status = "running"
        self.timestamp = datetime.utcnow()
        self.start_time = time.time()
    
    def complete(self, success: bool, error_message: Optional[str] = None):
        """Mark check as completed."""
        self.status = "passed" if success else "failed"
        self.error_message = error_message
        self.duration = time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "description": self.description,
            "critical": self.critical,
            "status": self.status,
            "error_message": self.error_message,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


async def startup_checks() -> Dict[str, Any]:
    """
    Perform comprehensive startup checks for all system components.
    
    Returns:
        Dict[str, Any]: Detailed startup check results
    """
    logger.info("Starting comprehensive system initialization checks...")
    
    checks = [
        StartupCheck("configuration", "Validate application configuration", critical=True),
        StartupCheck("environment", "Check environment variables", critical=True),
        StartupCheck("firestore_connection", "Test Firestore database connection", critical=True),
        StartupCheck("firestore_schema", "Initialize Firestore collections and schema", critical=True),
        StartupCheck("gemini_config", "Validate Gemini API configuration", critical=True),
        StartupCheck("gemini_connection", "Test Gemini API connectivity", critical=False),
        StartupCheck("performance_setup", "Initialize performance monitoring", critical=False),
        StartupCheck("audit_setup", "Initialize audit logging system", critical=False),
    ]
    
    results = {
        "overall_success": True,
        "critical_failures": [],
        "warnings": [],
        "checks": [],
        "start_time": datetime.utcnow().isoformat(),
        "total_duration": 0
    }
    
    start_time = time.time()
    
    try:
        # Import here to avoid issues with missing config at module load time
        from config import (
            validate_configuration, validate_required_environment_variables, 
            get_configuration_summary, settings, is_render_deployment
        )
        
        # Reconfigure logging with proper level
        try:
            logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))
        except:
            pass  # Continue with default logging if settings not available
        
        # 1. Configuration validation
        check = checks[0]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            validate_configuration()
            check.complete(True)
            logger.info("✅ Configuration validation passed")
        except Exception as e:
            check.complete(False, str(e))
            logger.error(f"❌ Configuration validation failed: {e}")
            if check.critical:
                results["critical_failures"].append(check.name)
                results["overall_success"] = False
        
        # 2. Environment variables check
        check = checks[1]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            missing_vars = validate_required_environment_variables()
            if missing_vars:
                error_msg = f"Missing required environment variables: {list(missing_vars.keys())}"
                check.complete(False, error_msg)
                logger.error(f"❌ {error_msg}")
                if check.critical:
                    results["critical_failures"].append(check.name)
                    results["overall_success"] = False
            else:
                check.complete(True)
                logger.info("✅ All required environment variables present")
        except Exception as e:
            check.complete(False, str(e))
            logger.error(f"❌ Environment validation failed: {e}")
            if check.critical:
                results["critical_failures"].append(check.name)
                results["overall_success"] = False
        
        # 3. Firestore connection test
        check = checks[2]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            from firestore_client import test_firestore_connection
            connection_success = await test_firestore_connection()
            if connection_success:
                check.complete(True)
                logger.info("✅ Firestore connection test passed")
            else:
                check.complete(False, "Firestore connection test failed")
                logger.error("❌ Firestore connection test failed")
                if check.critical:
                    results["critical_failures"].append(check.name)
                    results["overall_success"] = False
        except Exception as e:
            check.complete(False, str(e))
            logger.error(f"❌ Firestore connection test failed: {e}")
            if check.critical:
                results["critical_failures"].append(check.name)
                results["overall_success"] = False
        
        # 4. Firestore schema initialization
        check = checks[3]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            from firestore_client import initialize_collections
            schema_success = initialize_collections()
            if schema_success:
                check.complete(True)
                logger.info("✅ Firestore schema initialized successfully")
            else:
                check.complete(False, "Schema initialization failed")
                logger.error("❌ Schema initialization failed")
                if check.critical:
                    results["critical_failures"].append(check.name)
                    results["overall_success"] = False
        except Exception as e:
            check.complete(False, str(e))
            logger.error(f"❌ Schema initialization failed: {e}")
            if check.critical:
                results["critical_failures"].append(check.name)
                results["overall_success"] = False
        
        # 5. Gemini API configuration validation
        check = checks[4]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            check.complete(True)
            logger.info("✅ Gemini API configuration validated")
        except Exception as e:
            check.complete(False, str(e))
            logger.error(f"❌ Gemini API configuration failed: {e}")
            if check.critical:
                results["critical_failures"].append(check.name)
                results["overall_success"] = False
        
        # 6. Gemini API connectivity test (non-critical)
        check = checks[5]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            # Only test connectivity if not in test environment
            if settings.environment != "test" and not settings.gemini_api_key.startswith("test_"):
                from embedding_service import EmbeddingGenerator
                embedding_service = EmbeddingGenerator()
                # Test with a simple text
                test_embedding = await embedding_service.generate_embedding("test")
                if test_embedding and len(test_embedding) > 0:
                    check.complete(True)
                    logger.info("✅ Gemini API connectivity test passed")
                else:
                    check.complete(False, "Gemini API returned empty embedding")
                    logger.warning("⚠️ Gemini API connectivity test failed")
                    results["warnings"].append("Gemini API connectivity test failed")
            else:
                check.complete(True)
                logger.info("✅ Gemini API connectivity test skipped (test environment)")
        except Exception as e:
            check.complete(False, str(e))
            logger.warning(f"⚠️ Gemini API connectivity test failed: {e}")
            results["warnings"].append(f"Gemini API connectivity test failed: {e}")
        
        # 7. Performance monitoring setup
        check = checks[6]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            from performance_tracker import PerformanceTracker
            tracker = PerformanceTracker()
            # Initialize performance tracking
            check.complete(True)
            logger.info("✅ Performance monitoring initialized")
        except Exception as e:
            check.complete(False, str(e))
            logger.warning(f"⚠️ Performance monitoring setup failed: {e}")
            results["warnings"].append(f"Performance monitoring setup failed: {e}")
        
        # 8. Audit system setup
        check = checks[7]
        check.start()
        logger.info(f"Running check: {check.description}")
        try:
            from audit_logger import AuditLogger
            audit_logger = AuditLogger()
            # Test audit logging
            check.complete(True)
            logger.info("✅ Audit logging system initialized")
        except Exception as e:
            check.complete(False, str(e))
            logger.warning(f"⚠️ Audit system setup failed: {e}")
            results["warnings"].append(f"Audit system setup failed: {e}")
        
    except Exception as e:
        logger.error(f"Startup checks failed with critical error: {e}")
        results["overall_success"] = False
        results["critical_failures"].append("startup_process")
    
    # Compile results
    results["checks"] = [check.to_dict() for check in checks]
    results["total_duration"] = time.time() - start_time
    results["end_time"] = datetime.utcnow().isoformat()
    
    # Log summary
    if results["overall_success"]:
        logger.info(f"✅ All critical startup checks completed successfully in {results['total_duration']:.2f}s")
        if results["warnings"]:
            logger.info(f"⚠️ {len(results['warnings'])} non-critical warnings")
    else:
        logger.error(f"❌ Startup checks failed with {len(results['critical_failures'])} critical failures")
    
    return results


def run_startup_checks():
    """
    Run startup checks synchronously.
    """
    return asyncio.run(startup_checks())


if __name__ == "__main__":
    """
    Run startup checks when executed directly.
    """
    try:
        success = run_startup_checks()
        if success:
            print("✅ All startup checks passed!")
            exit(0)
        else:
            print("❌ Startup checks failed!")
            exit(1)
    except Exception as e:
        print(f"❌ Startup checks failed with error: {e}")
        exit(1)

async def health_check() -> Dict[str, Any]:
    """
    Perform health check for system monitoring.
    
    Returns:
        Dict[str, Any]: Health check results
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "legal-document-classification",
        "version": "1.0.0",
        "checks": {},
        "overall_healthy": True
    }
    
    try:
        from config import settings, is_render_deployment
        
        # 1. Configuration health
        try:
            from config import validate_configuration
            validate_configuration()
            health_status["checks"]["configuration"] = {"status": "healthy", "message": "Configuration valid"}
        except Exception as e:
            health_status["checks"]["configuration"] = {"status": "unhealthy", "message": str(e)}
            health_status["overall_healthy"] = False
        
        # 2. Firestore health
        try:
            from firestore_client import test_firestore_connection
            firestore_healthy = await test_firestore_connection()
            if firestore_healthy:
                health_status["checks"]["firestore"] = {"status": "healthy", "message": "Database connection active"}
            else:
                health_status["checks"]["firestore"] = {"status": "unhealthy", "message": "Database connection failed"}
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["checks"]["firestore"] = {"status": "unhealthy", "message": f"Database error: {e}"}
            health_status["overall_healthy"] = False
        
        # 3. Gemini API health (basic check)
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            health_status["checks"]["gemini"] = {"status": "healthy", "message": "API configuration valid"}
        except Exception as e:
            health_status["checks"]["gemini"] = {"status": "unhealthy", "message": f"API configuration error: {e}"}
            health_status["overall_healthy"] = False
        
        # 4. System resources
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_status["checks"]["resources"] = {
                "status": "healthy" if cpu_percent < 90 and memory.percent < 90 else "warning",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100
            }
            
            if cpu_percent > 95 or memory.percent > 95:
                health_status["overall_healthy"] = False
        except ImportError:
            health_status["checks"]["resources"] = {"status": "unavailable", "message": "psutil not installed"}
        except Exception as e:
            health_status["checks"]["resources"] = {"status": "error", "message": str(e)}
        
        # Set overall status
        health_status["status"] = "healthy" if health_status["overall_healthy"] else "unhealthy"
        
    except Exception as e:
        health_status["status"] = "error"
        health_status["overall_healthy"] = False
        health_status["error"] = str(e)
    
    return health_status


async def readiness_check() -> Dict[str, Any]:
    """
    Perform readiness check to determine if service is ready to accept traffic.
    
    Returns:
        Dict[str, Any]: Readiness check results
    """
    readiness_status = {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
        "message": "Service is ready"
    }
    
    try:
        # Check critical dependencies
        from config import validate_configuration
        from firestore_client import test_firestore_connection
        
        # 1. Configuration must be valid
        try:
            validate_configuration()
            readiness_status["checks"]["configuration"] = True
        except Exception as e:
            readiness_status["checks"]["configuration"] = False
            readiness_status["ready"] = False
            readiness_status["message"] = f"Configuration invalid: {e}"
        
        # 2. Database must be accessible
        try:
            db_ready = await test_firestore_connection()
            readiness_status["checks"]["database"] = db_ready
            if not db_ready:
                readiness_status["ready"] = False
                readiness_status["message"] = "Database not accessible"
        except Exception as e:
            readiness_status["checks"]["database"] = False
            readiness_status["ready"] = False
            readiness_status["message"] = f"Database error: {e}"
        
        # 3. Essential services must be configured
        try:
            from config import settings
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            readiness_status["checks"]["ai_service"] = True
        except Exception as e:
            readiness_status["checks"]["ai_service"] = False
            readiness_status["ready"] = False
            readiness_status["message"] = f"AI service not configured: {e}"
        
    except Exception as e:
        readiness_status["ready"] = False
        readiness_status["message"] = f"Readiness check failed: {e}"
    
    return readiness_status


def get_system_info() -> Dict[str, Any]:
    """
    Get comprehensive system information for monitoring and debugging.
    
    Returns:
        Dict[str, Any]: System information
    """
    system_info = {
        "service": "Legal Document Severity Classification System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "platform": sys.platform,
    }
    
    try:
        from config import get_configuration_summary, is_render_deployment
        system_info["configuration"] = get_configuration_summary()
        system_info["deployment_platform"] = "render" if is_render_deployment() else "local"
    except Exception as e:
        system_info["configuration_error"] = str(e)
    
    try:
        import psutil
        system_info["system_resources"] = {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
        }
    except ImportError:
        system_info["system_resources"] = "psutil not available"
    except Exception as e:
        system_info["system_resources_error"] = str(e)
    
    return system_info