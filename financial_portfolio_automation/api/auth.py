"""
Authentication and authorization for the REST API.

Provides JWT-based authentication, API key authentication, and role-based
access control for the portfolio management API.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel
import os
import hashlib
import secrets
from enum import Enum

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"
    TRADER = "trader"
    READONLY = "readonly"


class AuthUser(BaseModel):
    """Authenticated user model."""
    user_id: str
    username: str
    email: Optional[str] = None
    role: UserRole
    permissions: List[str] = []
    is_active: bool = True


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    role: Optional[str] = None


class UserInDB(BaseModel):
    """User model for database storage."""
    user_id: str
    username: str
    email: Optional[str] = None
    hashed_password: str
    role: UserRole
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    api_keys: List[str] = []


# Mock user database (replace with actual database in production)
fake_users_db = {
    "admin": UserInDB(
        user_id="1",
        username="admin",
        email="admin@example.com",
        hashed_password=pwd_context.hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(),
        api_keys=["admin-api-key-123"]
    ),
    "trader": UserInDB(
        user_id="2",
        username="trader",
        email="trader@example.com",
        hashed_password=pwd_context.hash("trader123"),
        role=UserRole.TRADER,
        is_active=True,
        created_at=datetime.now(),
        api_keys=["trader-api-key-456"]
    ),
    "readonly": UserInDB(
        user_id="3",
        username="readonly",
        email="readonly@example.com",
        hashed_password=pwd_context.hash("readonly123"),
        role=UserRole.READONLY,
        is_active=True,
        created_at=datetime.now(),
        api_keys=["readonly-api-key-789"]
    )
}

# Role permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        "portfolio:read", "portfolio:write",
        "analysis:read", "analysis:write",
        "execution:read", "execution:write",
        "monitoring:read", "monitoring:write",
        "reporting:read", "reporting:write",
        "strategies:read", "strategies:write",
        "users:read", "users:write",
        "system:read", "system:write"
    ],
    UserRole.TRADER: [
        "portfolio:read", "portfolio:write",
        "analysis:read", "analysis:write",
        "execution:read", "execution:write",
        "monitoring:read", "monitoring:write",
        "reporting:read", "reporting:write",
        "strategies:read", "strategies:write"
    ],
    UserRole.READONLY: [
        "portfolio:read",
        "analysis:read",
        "monitoring:read",
        "reporting:read",
        "strategies:read"
    ]
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    return fake_users_db.get(username)


def get_user_by_api_key(api_key: str) -> Optional[UserInDB]:
    """Get user by API key."""
    for user in fake_users_db.values():
        if api_key in user.api_keys:
            return user
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password."""
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "access":
            return None
        
        return TokenData(username=username, user_id=user_id, role=role)
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    api_key: Optional[str] = Security(api_key_header)
) -> AuthUser:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user = None
    
    # Try API key authentication first
    if api_key:
        user = get_user_by_api_key(api_key)
        if not user or not user.is_active:
            raise credentials_exception
    
    # Try JWT token authentication
    elif credentials:
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        user = get_user(token_data.username)
        if user is None or not user.is_active:
            raise credentials_exception
    
    else:
        raise credentials_exception
    
    # Convert to AuthUser
    permissions = ROLE_PERMISSIONS.get(user.role, [])
    return AuthUser(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        permissions=permissions,
        is_active=user.is_active
    )


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_checker


def require_role(required_role: UserRole):
    """Decorator to require specific role."""
    def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient role. Required: {required_role.value}"
            )
        return current_user
    
    return role_checker


def generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


# Authentication endpoints models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


class ApiKeyRequest(BaseModel):
    """API key generation request model."""
    name: str
    expires_in_days: Optional[int] = 365


class ApiKeyResponse(BaseModel):
    """API key response model."""
    api_key: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None