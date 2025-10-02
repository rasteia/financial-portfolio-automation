#!/usr/bin/env python3
"""
Example of integrating startup validation into an application.

This demonstrates how to use the startup validator in different scenarios:
1. CLI application with validation
2. Web application with health checks
3. Service with graceful degradation
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financial_portfolio_automation.utils import (
    initialize_application, 
    validate_environment, 
    get_system_status,
    StartupValidator
)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def example_cli_application():
    """Example CLI application with strict validation."""
    print("🖥️  CLI Application Example")
    print("-" * 40)
    
    # CLI applications typically want strict validation
    # and should exit if critical issues are found
    try:
        success = initialize_application(
            strict_validation=True,
            exit_on_failure=True  # Will exit on failure
        )
        
        if success:
            print("✅ CLI application started successfully")
            # Your CLI application logic here
            return True
        else:
            print("❌ CLI application failed to start")
            return False
            
    except Exception as e:
        print(f"💥 CLI application startup error: {e}")
        return False


def example_web_application():
    """Example web application with health check endpoint."""
    print("\n🌐 Web Application Example")
    print("-" * 40)
    
    # Web applications might want to start even with some issues
    # and provide health check endpoints
    try:
        success = initialize_application(
            strict_validation=False,  # Don't be strict
            exit_on_failure=False    # Don't exit, handle gracefully
        )
        
        if success:
            print("✅ Web application started successfully")
        else:
            print("⚠️  Web application started with warnings")
        
        # Simulate health check endpoint
        health_status = get_system_status()
        print(f"Health check status: {health_status['status']}")
        
        return True
        
    except Exception as e:
        print(f"💥 Web application startup error: {e}")
        return False


def example_service_with_degradation():
    """Example service that gracefully degrades functionality."""
    print("\n🔧 Service with Graceful Degradation Example")
    print("-" * 40)
    
    # Services might want to start with reduced functionality
    # if some components are unavailable
    validator = StartupValidator()
    validation_passed = validator.validate_all()
    
    if validation_passed:
        print("✅ All systems operational - full functionality available")
        available_features = ["trading", "monitoring", "reporting", "notifications"]
    else:
        print("⚠️  Some systems unavailable - running in degraded mode")
        
        # Determine available features based on validation results
        available_features = ["monitoring"]  # Always available
        
        summary = validator.get_validation_summary()
        for result in validator.validation_results:
            if result.passed:
                if "alpaca" in result.name:
                    available_features.append("trading")
                elif "database" in result.name:
                    available_features.append("reporting")
    
    print(f"Available features: {', '.join(available_features)}")
    return True


def example_quick_environment_check():
    """Example of quick environment validation."""
    print("\n⚡ Quick Environment Check Example")
    print("-" * 40)
    
    # Quick check without full initialization
    is_valid = validate_environment()
    
    if is_valid:
        print("✅ Environment is ready for deployment")
    else:
        print("❌ Environment has issues - check logs for details")
    
    return is_valid


def main():
    """Run all examples."""
    setup_logging()
    
    print("🚀 Startup Validation Integration Examples")
    print("=" * 60)
    
    examples = [
        ("CLI Application", example_cli_application),
        ("Web Application", example_web_application),
        ("Service with Degradation", example_service_with_degradation),
        ("Quick Environment Check", example_quick_environment_check),
    ]
    
    results = []
    for name, example_func in examples:
        try:
            result = example_func()
            results.append((name, result))
        except SystemExit:
            # Handle CLI application exit
            results.append((name, False))
        except Exception as e:
            print(f"💥 {name} failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Examples Summary:")
    
    for name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"  {name}: {status}")
    
    print("\n💡 Note: Failures are expected in this demo environment.")
    print("   In production, ensure all dependencies and configuration are properly set up.")


if __name__ == "__main__":
    main()