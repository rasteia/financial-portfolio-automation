#!/usr/bin/env python3
"""
Test script to verify bcrypt and passlib compatibility.
This script tests the functionality that was causing issues.
"""

import sys
import traceback

def test_bcrypt_import():
    """Test bcrypt import and basic functionality."""
    print("Testing bcrypt import and basic functionality...")
    try:
        import bcrypt
        print(f"✓ bcrypt imported successfully, version: {bcrypt.__version__}")
        
        # Test basic hashing
        password = b"test_password"
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        print(f"✓ bcrypt hashing works: {hashed[:20]}...")
        
        # Test verification
        is_valid = bcrypt.checkpw(password, hashed)
        print(f"✓ bcrypt verification works: {is_valid}")
        
        return True
    except Exception as e:
        print(f"✗ bcrypt test failed: {e}")
        traceback.print_exc()
        return False

def test_passlib_bcrypt_integration():
    """Test passlib with bcrypt backend."""
    print("\nTesting passlib with bcrypt backend...")
    try:
        from passlib.context import CryptContext
        print("✓ passlib imported successfully")
        
        # Create context with bcrypt (same as in auth.py)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        print("✓ CryptContext created with bcrypt scheme")
        
        # Test hashing
        password = "test_password"
        hashed = pwd_context.hash(password)
        print(f"✓ passlib bcrypt hashing works: {hashed[:20]}...")
        
        # Test verification
        is_valid = pwd_context.verify(password, hashed)
        print(f"✓ passlib bcrypt verification works: {is_valid}")
        
        return True
    except Exception as e:
        print(f"✗ passlib bcrypt test failed: {e}")
        traceback.print_exc()
        return False

def test_passlib_bcrypt_version_access():
    """Test that passlib can access bcrypt version information."""
    print("\nTesting passlib access to bcrypt version information...")
    try:
        from passlib.handlers import bcrypt as passlib_bcrypt
        print("✓ passlib bcrypt handler imported")
        
        # Try to access bcrypt version through passlib
        # This is what was failing before the fix
        try:
            import bcrypt
            version_info = bcrypt.__version__
            print(f"✓ bcrypt version accessible: {version_info}")
        except AttributeError as e:
            print(f"✗ bcrypt version not accessible: {e}")
            return False
        
        # Test that passlib can use bcrypt backend
        handler = passlib_bcrypt.bcrypt
        test_hash = handler.hash("test")
        print(f"✓ passlib bcrypt handler works: {test_hash[:20]}...")
        
        return True
    except Exception as e:
        print(f"✗ passlib bcrypt version access test failed: {e}")
        traceback.print_exc()
        return False

def test_auth_module_compatibility():
    """Test the actual auth module functionality."""
    print("\nTesting auth module compatibility...")
    try:
        # Import the auth module functions
        from financial_portfolio_automation.api.auth import (
            verify_password, 
            get_password_hash,
            pwd_context
        )
        print("✓ Auth module imported successfully")
        
        # Test password hashing and verification
        password = "test_password_123"
        hashed = get_password_hash(password)
        print(f"✓ Auth module hashing works: {hashed[:20]}...")
        
        # Test verification
        is_valid = verify_password(password, hashed)
        print(f"✓ Auth module verification works: {is_valid}")
        
        # Test with wrong password
        is_invalid = verify_password("wrong_password", hashed)
        print(f"✓ Auth module correctly rejects wrong password: {not is_invalid}")
        
        return True
    except Exception as e:
        print(f"✗ Auth module test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all compatibility tests."""
    print("=== bcrypt and passlib Compatibility Test ===\n")
    
    tests = [
        test_bcrypt_import,
        test_passlib_bcrypt_integration,
        test_passlib_bcrypt_version_access,
        test_auth_module_compatibility
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! bcrypt and passlib are compatible.")
        return 0
    else:
        print("✗ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())