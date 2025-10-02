"""
Startup validation for critical dependencies and configuration.

This module provides comprehensive validation of system dependencies,
configuration completeness, and critical integrations at application startup.
"""

import sys
import importlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from ..exceptions import ConfigurationError, SystemError
from ..config.settings import get_config, SystemConfig
from ..models.config import Environment, DataFeed


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    passed: bool
    message: str
    resolution_steps: List[str]
    error_code: Optional[str] = None


@dataclass
class DependencyStatus:
    """Status of a system dependency."""
    name: str
    version: str
    compatible: bool
    issues: List[str]
    resolution_steps: List[str]


class StartupValidator:
    """Validates system dependencies and configuration at startup."""
    
    def __init__(self):
        self.validation_results: List[ValidationResult] = []
        self.dependency_statuses: List[DependencyStatus] = []
    
    def validate_all(self) -> bool:
        """
        Run all startup validations.
        
        Returns:
            bool: True if all validations pass, False otherwise
        """
        logger.info("Starting system validation...")
        
        # Clear previous results
        self.validation_results.clear()
        self.dependency_statuses.clear()
        
        # Run all validation checks
        self._validate_dependencies()
        self._validate_configuration()
        self._validate_critical_integrations()
        
        # Check if all validations passed
        all_passed = all(result.passed for result in self.validation_results)
        
        if all_passed:
            logger.info("All startup validations passed successfully")
        else:
            logger.error("Some startup validations failed")
            self._log_validation_summary()
        
        return all_passed
    
    def _validate_dependencies(self) -> None:
        """Validate critical system dependencies."""
        logger.info("Validating system dependencies...")
        
        # Check bcrypt and passlib compatibility
        bcrypt_result = self._check_bcrypt_passlib_compatibility()
        self.validation_results.append(bcrypt_result)
        
        # Check other critical dependencies
        critical_deps = [
            ('alpaca-py', 'alpaca'),
            ('sqlalchemy', 'sqlalchemy'),
            ('fastapi', 'fastapi'),
            ('pydantic', 'pydantic'),
        ]
        
        for dep_name, import_name in critical_deps:
            result = self._check_dependency(dep_name, import_name)
            self.validation_results.append(result)
    
    def _check_bcrypt_passlib_compatibility(self) -> ValidationResult:
        """Check bcrypt and passlib compatibility."""
        try:
            import bcrypt
            import passlib
            from passlib.hash import bcrypt as passlib_bcrypt
            
            # Test bcrypt version access
            bcrypt_version = getattr(bcrypt, '__version__', 'unknown')
            passlib_version = getattr(passlib, '__version__', 'unknown')
            
            # Test passlib can access bcrypt backend
            try:
                # This should not raise an AttributeError
                passlib_bcrypt.using(rounds=12).hash("test")
                
                return ValidationResult(
                    name="bcrypt_passlib_compatibility",
                    passed=True,
                    message=f"bcrypt ({bcrypt_version}) and passlib ({passlib_version}) are compatible",
                    resolution_steps=[]
                )
            except AttributeError as e:
                if "object has no attribute" in str(e):
                    return ValidationResult(
                        name="bcrypt_passlib_compatibility",
                        passed=False,
                        message=f"bcrypt/passlib compatibility issue: {e}",
                        resolution_steps=[
                            "Install compatible versions: pip install bcrypt==4.1.2 passlib[bcrypt]==1.7.4",
                            "Restart the application after updating dependencies",
                            "Verify installation: python -c 'import bcrypt, passlib; print(bcrypt.__version__, passlib.__version__)'"
                        ],
                        error_code="BCRYPT_PASSLIB_INCOMPATIBLE"
                    )
                else:
                    raise
                    
        except ImportError as e:
            return ValidationResult(
                name="bcrypt_passlib_compatibility",
                passed=False,
                message=f"Missing required dependencies: {e}",
                resolution_steps=[
                    "Install required packages: pip install bcrypt==4.1.2 passlib[bcrypt]==1.7.4",
                    "Ensure all dependencies are installed: pip install -r requirements.txt"
                ],
                error_code="MISSING_CRYPTO_DEPENDENCIES"
            )
        except Exception as e:
            return ValidationResult(
                name="bcrypt_passlib_compatibility",
                passed=False,
                message=f"Unexpected error checking bcrypt/passlib: {e}",
                resolution_steps=[
                    "Reinstall crypto dependencies: pip uninstall bcrypt passlib && pip install bcrypt==4.1.2 passlib[bcrypt]==1.7.4",
                    "Check for conflicting packages: pip list | grep -E '(bcrypt|passlib)'"
                ],
                error_code="CRYPTO_VALIDATION_ERROR"
            )
    
    def _check_dependency(self, dep_name: str, import_name: str) -> ValidationResult:
        """Check if a dependency is available and importable."""
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            
            return ValidationResult(
                name=f"dependency_{dep_name}",
                passed=True,
                message=f"{dep_name} ({version}) is available",
                resolution_steps=[]
            )
        except ImportError as e:
            return ValidationResult(
                name=f"dependency_{dep_name}",
                passed=False,
                message=f"Missing dependency {dep_name}: {e}",
                resolution_steps=[
                    f"Install missing dependency: pip install {dep_name}",
                    "Install all requirements: pip install -r requirements.txt"
                ],
                error_code="MISSING_DEPENDENCY"
            )
    
    def _validate_configuration(self) -> None:
        """Validate system configuration completeness."""
        logger.info("Validating system configuration...")
        
        try:
            config = get_config()
            
            # Validate Alpaca configuration
            alpaca_result = self._validate_alpaca_config(config)
            self.validation_results.append(alpaca_result)
            
            # Validate database configuration
            db_result = self._validate_database_config(config)
            self.validation_results.append(db_result)
            
            # Validate risk limits
            risk_result = self._validate_risk_limits(config)
            self.validation_results.append(risk_result)
            
        except ConfigurationError as e:
            self.validation_results.append(ValidationResult(
                name="configuration_loading",
                passed=False,
                message=f"Configuration loading failed: {e}",
                resolution_steps=[
                    "Check configuration file format and syntax",
                    "Verify all required environment variables are set",
                    "Review configuration documentation"
                ],
                error_code="CONFIG_LOAD_ERROR"
            ))
    
    def _validate_alpaca_config(self, config: SystemConfig) -> ValidationResult:
        """Validate Alpaca configuration."""
        issues = []
        resolution_steps = []
        
        if not config.alpaca.api_key:
            issues.append("Missing Alpaca API key")
            resolution_steps.append("Set ALPACA_API_KEY environment variable or add to config file")
        
        if not config.alpaca.secret_key:
            issues.append("Missing Alpaca secret key")
            resolution_steps.append("Set ALPACA_SECRET_KEY environment variable or add to config file")
        
        # Check if environment is properly configured as enum
        if not hasattr(config.alpaca, 'environment') or config.alpaca.environment is None:
            issues.append("Missing Alpaca environment configuration")
            resolution_steps.append("Set ALPACA_ENVIRONMENT environment variable to 'paper' or 'live'")
        
        # Check if data_feed is properly configured as enum  
        if not hasattr(config.alpaca, 'data_feed') or config.alpaca.data_feed is None:
            issues.append("Missing Alpaca data feed configuration")
            resolution_steps.append("Set ALPACA_DATA_FEED environment variable to 'iex', 'sip', or 'opra'")
        
        if not config.alpaca.base_url:
            issues.append("Missing Alpaca base URL")
            resolution_steps.append("Set ALPACA_BASE_URL or use default paper trading URL")
        
        if issues:
            return ValidationResult(
                name="alpaca_configuration",
                passed=False,
                message=f"Alpaca configuration issues: {'; '.join(issues)}",
                resolution_steps=resolution_steps,
                error_code="ALPACA_CONFIG_INCOMPLETE"
            )
        
        return ValidationResult(
            name="alpaca_configuration",
            passed=True,
            message="Alpaca configuration is complete",
            resolution_steps=[]
        )
    
    def _validate_database_config(self, config: SystemConfig) -> ValidationResult:
        """Validate database configuration."""
        if not config.database.url:
            return ValidationResult(
                name="database_configuration",
                passed=False,
                message="Database URL is not configured",
                resolution_steps=[
                    "Set DATABASE_URL environment variable",
                    "Add database configuration to config file",
                    "Use default SQLite: sqlite:///portfolio_automation.db"
                ],
                error_code="DATABASE_CONFIG_MISSING"
            )
        
        # Test database file accessibility for SQLite
        if config.database.url.startswith('sqlite:///'):
            db_path = config.database.url.replace('sqlite:///', '')
            db_file = Path(db_path)
            
            # Check if directory exists and is writable
            try:
                db_file.parent.mkdir(parents=True, exist_ok=True)
                # Test write access
                test_file = db_file.parent / '.write_test'
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError) as e:
                return ValidationResult(
                    name="database_configuration",
                    passed=False,
                    message=f"Database directory not writable: {e}",
                    resolution_steps=[
                        "Check directory permissions",
                        "Create database directory manually",
                        "Use alternative database location"
                    ],
                    error_code="DATABASE_ACCESS_ERROR"
                )
        
        return ValidationResult(
            name="database_configuration",
            passed=True,
            message="Database configuration is valid",
            resolution_steps=[]
        )
    
    def _validate_risk_limits(self, config: SystemConfig) -> ValidationResult:
        """Validate risk management configuration."""
        issues = []
        
        if config.risk_limits.max_position_size <= 0:
            issues.append("Max position size must be positive")
        
        if config.risk_limits.max_daily_loss <= 0:
            issues.append("Max daily loss must be positive")
        
        if not (0 < config.risk_limits.max_portfolio_concentration <= 1):
            issues.append("Portfolio concentration must be between 0 and 1")
        
        if not (0 < config.risk_limits.max_drawdown <= 1):
            issues.append("Max drawdown must be between 0 and 1")
        
        if issues:
            return ValidationResult(
                name="risk_limits_configuration",
                passed=False,
                message=f"Risk limits validation failed: {'; '.join(issues)}",
                resolution_steps=[
                    "Review risk limit values in configuration",
                    "Ensure all risk limits are positive numbers",
                    "Check percentage values are between 0 and 1"
                ],
                error_code="RISK_LIMITS_INVALID"
            )
        
        return ValidationResult(
            name="risk_limits_configuration",
            passed=True,
            message="Risk limits configuration is valid",
            resolution_steps=[]
        )
    
    def _validate_critical_integrations(self) -> None:
        """Validate critical system integrations."""
        logger.info("Validating critical integrations...")
        
        # Test Alpaca client creation
        alpaca_result = self._test_alpaca_client_creation()
        self.validation_results.append(alpaca_result)
    
    def _test_alpaca_client_creation(self) -> ValidationResult:
        """Test Alpaca client can be created without errors."""
        try:
            from ..api.alpaca_client import AlpacaClient
            from ..config.settings import get_config
            
            config = get_config()
            
            # Try to create client (don't actually connect)
            client = AlpacaClient(config.alpaca)
            
            return ValidationResult(
                name="alpaca_client_creation",
                passed=True,
                message="Alpaca client can be created successfully",
                resolution_steps=[]
            )
            
        except Exception as e:
            error_msg = str(e)
            resolution_steps = [
                "Check Alpaca configuration completeness",
                "Verify API credentials are valid",
                "Ensure alpaca-py package is installed correctly"
            ]
            
            # Add specific resolution steps based on error type
            if "environment" in error_msg.lower():
                resolution_steps.insert(0, "Add 'environment' field to AlpacaConfig (paper/live)")
            
            if "api_key" in error_msg.lower() or "secret" in error_msg.lower():
                resolution_steps.insert(0, "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
            
            return ValidationResult(
                name="alpaca_client_creation",
                passed=False,
                message=f"Alpaca client creation failed: {error_msg}",
                resolution_steps=resolution_steps,
                error_code="ALPACA_CLIENT_ERROR"
            )
    
    def _log_validation_summary(self) -> None:
        """Log a summary of validation results."""
        failed_validations = [r for r in self.validation_results if not r.passed]
        
        logger.error(f"Startup validation failed: {len(failed_validations)} issues found")
        
        for result in failed_validations:
            logger.error(f"❌ {result.name}: {result.message}")
            if result.resolution_steps:
                logger.error("   Resolution steps:")
                for step in result.resolution_steps:
                    logger.error(f"   - {step}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of all validation results."""
        passed = [r for r in self.validation_results if r.passed]
        failed = [r for r in self.validation_results if not r.passed]
        
        return {
            "total_checks": len(self.validation_results),
            "passed": len(passed),
            "failed": len(failed),
            "success_rate": len(passed) / len(self.validation_results) if self.validation_results else 0,
            "failed_checks": [
                {
                    "name": r.name,
                    "message": r.message,
                    "error_code": r.error_code,
                    "resolution_steps": r.resolution_steps
                }
                for r in failed
            ]
        }
    
    def raise_for_failures(self) -> None:
        """Raise an exception if any validations failed."""
        failed_validations = [r for r in self.validation_results if not r.passed]
        
        if failed_validations:
            error_messages = []
            resolution_steps = []
            
            for result in failed_validations:
                error_messages.append(f"{result.name}: {result.message}")
                resolution_steps.extend(result.resolution_steps)
            
            # Remove duplicate resolution steps
            unique_steps = list(dict.fromkeys(resolution_steps))
            
            raise SystemError(
                f"Startup validation failed:\n" + 
                "\n".join(f"- {msg}" for msg in error_messages) +
                "\n\nResolution steps:\n" +
                "\n".join(f"- {step}" for step in unique_steps),
                error_code="STARTUP_VALIDATION_FAILED",
                context={
                    "failed_checks": len(failed_validations),
                    "total_checks": len(self.validation_results),
                    "validation_summary": self.get_validation_summary()
                }
            )


def validate_startup() -> bool:
    """
    Convenience function to run startup validation.
    
    Returns:
        bool: True if all validations pass, False otherwise
    
    Raises:
        SystemError: If validation fails and strict mode is enabled
    """
    validator = StartupValidator()
    return validator.validate_all()


def validate_startup_strict() -> None:
    """
    Run startup validation in strict mode.
    
    Raises:
        SystemError: If any validation fails
    """
    validator = StartupValidator()
    validator.validate_all()
    validator.raise_for_failures()