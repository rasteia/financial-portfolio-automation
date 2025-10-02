#!/usr/bin/env python3
"""
Test script for startup validator functionality.

This script tests the startup validation system to ensure it properly
detects dependency and configuration issues.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financial_portfolio_automation.utils.startup_validator import StartupValidator
from financial_portfolio_automation.utils.startup import initialize_application, get_system_status


def setup_logging():
    """Setup logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_startup_validator():
    """Test the startup validator functionality."""
    print("🧪 Testing Startup Validator...")
    print("=" * 50)
    
    # Create validator instance
    validator = StartupValidator()
    
    # Run validation
    print("Running startup validation...")
    validation_passed = validator.validate_all()
    
    # Get summary
    summary = validator.get_validation_summary()
    
    print(f"\n📊 Validation Summary:")
    print(f"Total checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']:.1%}")
    
    if summary['failed_checks']:
        print(f"\n❌ Failed Checks:")
        for check in summary['failed_checks']:
            print(f"  - {check['name']}: {check['message']}")
            if check['resolution_steps']:
                print(f"    Resolution steps:")
                for step in check['resolution_steps']:
                    print(f"      • {step}")
    
    print(f"\n✅ Overall Result: {'PASSED' if validation_passed else 'FAILED'}")
    return validation_passed


def test_system_status():
    """Test system status functionality."""
    print("\n🔍 Testing System Status...")
    print("=" * 50)
    
    status = get_system_status()
    print(f"System Status: {status['status']}")
    
    if status['validation_summary']:
        summary = status['validation_summary']
        print(f"Validation: {summary['passed']}/{summary['total_checks']} passed")
    
    return status['status'] == 'healthy'


def test_initialization():
    """Test application initialization."""
    print("\n🚀 Testing Application Initialization...")
    print("=" * 50)
    
    try:
        # Test non-strict mode first
        success = initialize_application(strict_validation=False, exit_on_failure=False)
        print(f"Non-strict initialization: {'SUCCESS' if success else 'FAILED'}")
        return success
    except Exception as e:
        print(f"Initialization failed with error: {e}")
        return False


def main():
    """Run all startup validator tests."""
    setup_logging()
    
    print("🔧 Financial Portfolio Automation - Startup Validator Test")
    print("=" * 60)
    
    # Run tests
    results = []
    
    try:
        results.append(("Startup Validator", test_startup_validator()))
        results.append(("System Status", test_system_status()))
        results.append(("Application Initialization", test_initialization()))
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Results Summary:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n🎯 Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    if not all_passed:
        print("\n💡 Note: Some failures may be expected if dependencies or configuration are incomplete.")
        print("   Check the resolution steps above to fix any issues.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)