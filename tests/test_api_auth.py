"""
Tests for API authentication and authorization.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import jwt

from financial_portfolio_automation.api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    authenticate_user,
    get_user,
    get_user_by_api_key,
    UserRole,
    AuthUser,
    SECRET_KEY,
    ALGORITHM
)


class TestAuthentication:
    """Test cases for authentication functionality."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20  # Bcrypt hashes are long
        
        # Verify correct password
        assert verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert verify_password("wrong_password", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT access token creation."""
        data = {"sub": "testuser", "user_id": "123", "role": "trader"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == "123"
        assert payload["role"] == "trader"
        assert payload["type"] == "access"
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        data = {"sub": "testuser", "user_id": "123"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50
        
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "testuser", "user_id": "123", "role": "trader"}
        token = create_access_token(data)
        
        token_data = verify_token(token)
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == "123"
        assert token_data.role == "trader"
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        token_data = verify_token(invalid_token)
        assert token_data is None
    
    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        # Create token that expires immediately
        data = {"sub": "testuser", "user_id": "123", "role": "trader"}
        expired_time = datetime.utcnow() - timedelta(seconds=1)
        
        payload = data.copy()
        payload.update({"exp": expired_time, "type": "access"})
        
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        token_data = verify_token(expired_token)
        assert token_data is None
    
    def test_verify_refresh_token_as_access(self):
        """Test that refresh tokens are rejected for access token verification."""
        data = {"sub": "testuser", "user_id": "123"}
        refresh_token = create_refresh_token(data)
        
        token_data = verify_token(refresh_token)
        assert token_data is None  # Should reject refresh token
    
    def test_get_user_existing(self):
        """Test getting existing user."""
        user = get_user("admin")
        assert user is not None
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
    
    def test_get_user_nonexistent(self):
        """Test getting non-existent user."""
        user = get_user("nonexistent_user")
        assert user is None
    
    def test_get_user_by_api_key_existing(self):
        """Test getting user by existing API key."""
        user = get_user_by_api_key("admin-api-key-123")
        assert user is not None
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
    
    def test_get_user_by_api_key_nonexistent(self):
        """Test getting user by non-existent API key."""
        user = get_user_by_api_key("nonexistent-api-key")
        assert user is None
    
    def test_authenticate_user_valid(self):
        """Test user authentication with valid credentials."""
        user = authenticate_user("admin", "admin123")
        assert user is not None
        assert user.username == "admin"
        assert user.role == UserRole.ADMIN
    
    def test_authenticate_user_invalid_password(self):
        """Test user authentication with invalid password."""
        user = authenticate_user("admin", "wrong_password")
        assert user is None
    
    def test_authenticate_user_nonexistent(self):
        """Test user authentication with non-existent user."""
        user = authenticate_user("nonexistent_user", "password")
        assert user is None


class TestAuthorization:
    """Test cases for authorization functionality."""
    
    def test_user_role_permissions(self):
        """Test that user roles have correct permissions."""
        from financial_portfolio_automation.api.auth import ROLE_PERMISSIONS
        
        # Admin should have all permissions
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert "portfolio:read" in admin_perms
        assert "portfolio:write" in admin_perms
        assert "execution:write" in admin_perms
        assert "system:write" in admin_perms
        
        # Trader should have trading permissions but not system admin
        trader_perms = ROLE_PERMISSIONS[UserRole.TRADER]
        assert "portfolio:read" in trader_perms
        assert "portfolio:write" in trader_perms
        assert "execution:write" in trader_perms
        assert "system:write" not in trader_perms
        
        # Read-only should only have read permissions
        readonly_perms = ROLE_PERMISSIONS[UserRole.READONLY]
        assert "portfolio:read" in readonly_perms
        assert "portfolio:write" not in readonly_perms
        assert "execution:write" not in readonly_perms
        assert "system:write" not in readonly_perms
    
    def test_auth_user_model(self):
        """Test AuthUser model creation."""
        auth_user = AuthUser(
            user_id="123",
            username="testuser",
            email="test@example.com",
            role=UserRole.TRADER,
            permissions=["portfolio:read", "portfolio:write"],
            is_active=True
        )
        
        assert auth_user.user_id == "123"
        assert auth_user.username == "testuser"
        assert auth_user.email == "test@example.com"
        assert auth_user.role == UserRole.TRADER
        assert "portfolio:read" in auth_user.permissions
        assert auth_user.is_active is True
    
    def test_user_role_enum(self):
        """Test UserRole enumeration."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.TRADER == "trader"
        assert UserRole.READONLY == "readonly"
        
        # Test that all roles are valid strings
        for role in UserRole:
            assert isinstance(role.value, str)
            assert len(role.value) > 0


class TestAPIKeyAuthentication:
    """Test cases for API key authentication."""
    
    def test_api_key_generation(self):
        """Test API key generation."""
        from financial_portfolio_automation.api.auth import generate_api_key
        
        api_key = generate_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) > 20  # Should be reasonably long
        
        # Generate another key and ensure they're different
        api_key2 = generate_api_key()
        assert api_key != api_key2
    
    def test_api_key_hashing(self):
        """Test API key hashing."""
        from financial_portfolio_automation.api.auth import hash_api_key
        
        api_key = "test-api-key-123"
        hashed = hash_api_key(api_key)
        
        assert isinstance(hashed, str)
        assert hashed != api_key
        assert len(hashed) == 64  # SHA256 hex digest length
        
        # Same key should produce same hash
        hashed2 = hash_api_key(api_key)
        assert hashed == hashed2