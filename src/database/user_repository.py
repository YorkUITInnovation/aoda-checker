"""Repository for user database operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.utils.auth import get_password_hash


class UserRepository:
    """Repository for managing user records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        id_number: Optional[str] = None,
        is_admin: bool = False,
        auth_method: str = "manual"
    ) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            id_number=id_number,
            is_admin=is_admin,
            is_active=True,
            auth_method=auth_method,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all_users(self) -> List[User]:
        """Get all users."""
        result = await self.session.execute(
            select(User).order_by(User.username)
        )
        return list(result.scalars().all())

    async def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        id_number: Optional[str] = None,
        password: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> Optional[User]:
        """Update a user's information."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return None
        
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if id_number is not None:
            user.id_number = id_number
        if password is not None:
            user.hashed_password = get_password_hash(password)
        if is_admin is not None:
            user.is_admin = is_admin
        if is_active is not None:
            user.is_active = is_active
        
        user.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return False
        
        await self.session.delete(user)
        await self.session.commit()
        return True

    async def update_last_login(self, user_id: int):
        """Update the user's last login timestamp."""
        user = await self.get_user_by_id(user_id)
        
        if user:
            user.last_login = datetime.utcnow()
            await self.session.commit()

    async def username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if a username already exists."""
        query = select(User).where(User.username == username)
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if an email already exists."""
        if not email:
            return False
        
        query = select(User).where(User.email == email)
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

