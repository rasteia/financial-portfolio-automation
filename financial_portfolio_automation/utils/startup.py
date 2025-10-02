"""
Application startup utilities with validation.

This module provides utilities for application startup including
dependency validation, configuration checks, and system initialization.
"""

import logging
import sys
from typing import Optional

from .startup_validator import StartupValidator
from ..exceptions import SystemError


logger = logging.getLogger(__name__)


def initialize_application(strict_validation: bool = True, 
                         exit_on_failure: bool = True) -> bool:
    """
    Initialize the application with comprehensive startup validation.
    
    Args:
        strict_validation: If True, raise exceptions on validation failures
        exit_on_failure: If True, exit the application on validation failures
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    logger.info("Initializing Financial Portfolio Automation System...")
    
    try:
        # Run startup validation
        validator = StartupValidator()
        validation_passed = validator.validate_all()
        
        if not validation_passed:
            summary = validator.get_validation_summary()
            logger.error(f"Startup validation failed: {summary['failed']}/{summary['total_checks']} checks failed")
            
            # Log detailed failure information
            for failed_check in summary['failed_checks']:
                logger.error(f"❌ {failed_check['name']}: {failed_check['message']}")
                if failed_check['resolution_steps']:
                    logger.error("   Resolution steps:")
                    for step in failed_check['resolution_steps']:
                        logger.error(f"   - {step}")
            
            if strict_validation:
                validator.raise_for_failures()
            
            if exit_on_failure:
                logger.critical("Application startup failed. Exiting...")
                sys.exit(1)
            
            return False
        
        logger.info("✅ All startup validations passed successfully")
        logger.info("🚀 Financial Portfolio Automation System initialized")
        return True
        
    except SystemError as e:
        logger.critical(f"Critical system error during startup: {e}")
        if exit_on_failure:
            sys.exit(1)
        raise
    except Exception as e:
        logger.critical(f"Unexpected error during startup: {e}")
        if exit_on_failure:
            sys.exit(1)
        raise


def validate_environment() -> bool:
    """
    Quick environment validation without full initialization.
    
    Returns:
        bool: True if environment is valid, False otherwise
    """
    try:
        validator = StartupValidator()
        return validator.validate_all()
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False


def get_system_status() -> dict:
    """
    Get comprehensive system status including validation results.
    
    Returns:
        dict: System status information
    """
    try:
        validator = StartupValidator()
        validator.validate_all()
        
        return {
            "status": "healthy" if all(r.passed for r in validator.validation_results) else "unhealthy",
            "validation_summary": validator.get_validation_summary(),
            "timestamp": None  # Could add timestamp if needed
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "validation_summary": None,
            "timestamp": None
        }