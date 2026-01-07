"""Authentication routes."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from src.database import get_db
from src.database.user_repository import UserRepository
from src.web.dependencies import authenticate_user, get_current_user, get_current_active_user
from src.utils.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.database.models import User
from src.database.upgrade_runner import check_and_run_upgrades
from src.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
settings = Settings()


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/", current_user: User = Depends(get_current_user)):
    """Render the login page."""
    # If already logged in, redirect to the next page or home
    if current_user:
        return RedirectResponse(url=next, status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("login.html", {
        "request": request,
        "next": next
    })


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: AsyncSession = Depends(get_db)
):
    """Handle login form submission."""
    user = await authenticate_user(username, password, db)
    
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
                "next": next
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Update last login
    user_repo = UserRepository(db)
    await user_repo.update_last_login(user.id)
    
    # Store user_id in session
    request.session['user_id'] = user.id
    request.session['username'] = user.username
    request.session['is_admin'] = user.is_admin
    
    # If admin user, check and run database upgrades
    if user.is_admin:
        try:
            logger.info(f"Admin user {user.username} logged in, checking for database upgrades...")
            upgrade_result = await check_and_run_upgrades(db, settings.app_version)

            if upgrade_result['upgrades_applied'] > 0:
                logger.info(f"Applied {upgrade_result['upgrades_applied']} database upgrade(s)")
                # Store upgrade notification in session
                request.session['upgrade_notification'] = {
                    'count': upgrade_result['upgrades_applied'],
                    'version': upgrade_result['target_version']
                }
            elif not upgrade_result['success']:
                logger.error(f"Database upgrade failed: {upgrade_result.get('errors', [])}")
                # Don't block login, but log the error
        except Exception as e:
            logger.error(f"Error during database upgrade check: {str(e)}")
            # Don't block login on upgrade failure

    # Redirect to the next page or home
    redirect_url = next if next and next.startswith('/') else "/"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/login", response_model=TokenResponse)
async def api_login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """API endpoint for login (returns JWT token)."""
    user = await authenticate_user(login_request.username, login_request.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user_repo = UserRepository(db)
    await user_repo.update_last_login(user.id)
    
    # If admin user, check and run database upgrades
    if user.is_admin:
        try:
            logger.info(f"Admin user {user.username} logged in via API, checking for database upgrades...")
            upgrade_result = await check_and_run_upgrades(db, settings.app_version)

            if upgrade_result['upgrades_applied'] > 0:
                logger.info(f"Applied {upgrade_result['upgrades_applied']} database upgrade(s)")
            elif not upgrade_result['success']:
                logger.error(f"Database upgrade failed: {upgrade_result.get('errors', [])}")
        except Exception as e:
            logger.error(f"Error during database upgrade check: {str(e)}")
            # Don't block login on upgrade failure

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/api/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "auth_method": current_user.auth_method
    }


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Render the user profile page."""
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "profile"
        }
    )


@router.post("/profile/update")
async def update_profile(
    request: Request,
    email: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    id_number: str = Form(None),
    current_password: str = Form(None),
    new_password: str = Form(None),
    confirm_password: str = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile."""
    user_repo = UserRepository(db)
    error = None
    success = None

    # If changing password, validate
    if new_password:
        if not current_password:
            error = "Current password is required to change password"
        elif new_password != confirm_password:
            error = "New passwords do not match"
        elif len(new_password) < 6:
            error = "New password must be at least 6 characters"
        else:
            # Verify current password
            user = await authenticate_user(current_user.username, current_password, db)
            if not user:
                error = "Current password is incorrect"

    if not error:
        try:
            # Update user information
            updated_user = await user_repo.update_user(
                user_id=current_user.id,
                email=email if email else None,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None,
                id_number=id_number if id_number else None,
                password=new_password if new_password else None
            )

            if updated_user:
                success = "Profile updated successfully!"
                # Refresh current_user to show updated data
                current_user = updated_user
            else:
                error = "Failed to update profile"
        except Exception as e:
            error = f"Error updating profile: {str(e)}"

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "error": error,
            "success": success,
            "active_page": "profile"
        }
    )


