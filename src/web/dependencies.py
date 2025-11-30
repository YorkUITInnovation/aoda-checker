"""FastAPI dependencies for authentication."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.models import User
from src.database.user_repository import UserRepository
from src.utils.auth import decode_access_token, verify_password

# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get the current authenticated user from JWT token or session."""
    user_id = None
    
    # First, try to get user from session (cookie-based)
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
    
    # If not in session, try JWT token
    if not user_id and credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if payload:
            user_id = payload.get("sub")
    
    if not user_id:
        return None
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(int(user_id))
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Get the current active user, raise exception if not authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def authenticate_user(username: str, password: str, db: AsyncSession) -> Optional[User]:
    """Authenticate a user by username and password."""
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_username(username)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if not user.is_active:
        return None
    
    return user

