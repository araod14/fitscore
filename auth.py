"""
Authentication and authorization module with JWT support.
"""

from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, Roles
from database import get_db
from models import User
from schemas import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        if sub is None or username is None:
            return None
        # sub can be int or str depending on how token was created
        user_id = int(sub) if isinstance(sub, (int, str)) else None
        if user_id is None:
            return None
        return TokenData(user_id=user_id, username=username, role=role)
    except (JWTError, ValueError):
        return None


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user from JWT token.
    Returns None if no token or invalid token (for optional auth).
    """
    # Try to get token from cookie if not in header
    if not token:
        token = request.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]

    if not token:
        return None

    token_data = decode_token(token)
    if not token_data:
        return None

    user = await get_user_by_id(db, token_data.user_id)
    if not user or not user.is_active:
        return None

    return user


async def get_current_user_required(
    current_user: Annotated[Optional[User], Depends(get_current_user)]
) -> User:
    """
    Require a valid authenticated user.
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user_required)]
) -> User:
    """
    Require an admin user.
    Raises 403 if not admin.
    """
    if current_user.role != Roles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_current_judge_or_admin(
    current_user: Annotated[User, Depends(get_current_user_required)]
) -> User:
    """
    Require a judge or admin user.
    Raises 403 if not judge or admin.
    """
    if current_user.role not in [Roles.ADMIN, Roles.JUDGE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Judge or admin privileges required",
        )
    return current_user


def require_roles(*roles: str):
    """
    Dependency factory for requiring specific roles.
    Usage: Depends(require_roles(Roles.ADMIN, Roles.JUDGE))
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user_required)]
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(roles)}",
            )
        return current_user
    return role_checker


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: str = Roles.VIEWER
) -> User:
    """Create a new user."""
    # Check if username exists
    existing = await get_user_by_username(db, username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        password_hash=get_password_hash(password),
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
