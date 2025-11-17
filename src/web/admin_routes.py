"""Admin routes for user management."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.database.user_repository import UserRepository
from src.web.dependencies import get_current_admin_user
from src.database.models import User

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


class CreateUserRequest(BaseModel):
    """Create user request model."""
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    """Update user request model."""
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Render the admin users management page."""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_users()
    
    return templates.TemplateResponse(
        "admin_users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": users
        }
    )


@router.get("/api/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (API endpoint)."""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_users()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "auth_method": user.auth_method,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        for user in users
    ]


@router.post("/users/create")
async def create_user_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    email: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    is_admin: bool = Form(False),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (form submission)."""
    user_repo = UserRepository(db)
    
    # Check if username already exists
    if await user_repo.username_exists(username):
        users = await user_repo.get_all_users()
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": f"Username '{username}' already exists"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if email already exists
    if email and await user_repo.email_exists(email):
        users = await user_repo.get_all_users()
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": f"Email '{email}' already exists"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Create user
    await user_repo.create_user(
        username=username,
        password=password,
        email=email if email else None,
        full_name=full_name if full_name else None,
        is_admin=is_admin
    )
    
    return RedirectResponse(url="/admin/users?success=User created successfully", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/users", response_model=dict)
async def create_user_api(
    user_request: CreateUserRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (API endpoint)."""
    user_repo = UserRepository(db)
    
    # Check if username already exists
    if await user_repo.username_exists(user_request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_request.username}' already exists"
        )
    
    # Check if email already exists
    if user_request.email and await user_repo.email_exists(user_request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_request.email}' already exists"
        )
    
    # Create user
    new_user = await user_repo.create_user(
        username=user_request.username,
        password=user_request.password,
        email=user_request.email,
        full_name=user_request.full_name,
        is_admin=user_request.is_admin
    )
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "is_admin": new_user.is_admin,
        "is_active": new_user.is_active
    }


@router.post("/users/{user_id}/edit")
async def edit_user_form(
    request: Request,
    user_id: int,
    username: str = Form(...),
    email: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    is_admin: bool = Form(False),
    is_active: bool = Form(True),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a user (form submission)."""
    user_repo = UserRepository(db)
    
    # Check if username already exists (excluding current user)
    if await user_repo.username_exists(username, exclude_user_id=user_id):
        users = await user_repo.get_all_users()
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": f"Username '{username}' already exists"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if email already exists (excluding current user)
    if email and await user_repo.email_exists(email, exclude_user_id=user_id):
        users = await user_repo.get_all_users()
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": f"Email '{email}' already exists"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Update user
    updated_user = await user_repo.update_user(
        user_id=user_id,
        username=username,
        email=email if email else None,
        full_name=full_name if full_name else None,
        password=password if password else None,
        is_admin=is_admin,
        is_active=is_active
    )
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return RedirectResponse(url="/admin/users?success=User updated successfully", status_code=status.HTTP_303_SEE_OTHER)


@router.put("/api/users/{user_id}")
async def update_user_api(
    user_id: int,
    user_request: UpdateUserRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a user (API endpoint)."""
    user_repo = UserRepository(db)
    
    # Check if username already exists (excluding current user)
    if user_request.username and await user_repo.username_exists(user_request.username, exclude_user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_request.username}' already exists"
        )
    
    # Check if email already exists (excluding current user)
    if user_request.email and await user_repo.email_exists(user_request.email, exclude_user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_request.email}' already exists"
        )
    
    # Update user
    updated_user = await user_repo.update_user(
        user_id=user_id,
        username=user_request.username,
        email=user_request.email,
        full_name=user_request.full_name,
        password=user_request.password,
        is_admin=user_request.is_admin,
        is_active=user_request.is_active
    )
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": updated_user.id,
        "username": updated_user.username,
        "email": updated_user.email,
        "full_name": updated_user.full_name,
        "is_admin": updated_user.is_admin,
        "is_active": updated_user.is_active
    }


@router.post("/users/{user_id}/delete")
async def delete_user_form(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (form submission)."""
    # Prevent deleting yourself
    if user_id == current_user.id:
        return RedirectResponse(
            url="/admin/users?error=Cannot delete your own account",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    user_repo = UserRepository(db)
    success = await user_repo.delete_user(user_id)
    
    if not success:
        return RedirectResponse(
            url="/admin/users?error=User not found",
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    return RedirectResponse(
        url="/admin/users?success=User deleted successfully",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.delete("/api/users/{user_id}")
async def delete_user_api(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (API endpoint)."""
    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user_repo = UserRepository(db)
    success = await user_repo.delete_user(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

