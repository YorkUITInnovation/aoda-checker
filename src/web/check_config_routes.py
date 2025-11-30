"""Routes for check configuration management."""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.database.models import CheckConfiguration, CheckSeverity, User
from src.database.check_repository import CheckConfigRepository
from src.web.dependencies import get_current_admin_user, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/checks", tags=["admin", "checks"])
user_router = APIRouter(prefix="/api/checks", tags=["checks"])

templates = Jinja2Templates(directory="templates")


class CheckConfigUpdate(BaseModel):
    """Model for updating check configuration."""
    enabled: bool
    severity: CheckSeverity


class CheckConfigResponse(BaseModel):
    """Response model for check configuration."""
    id: int
    check_id: str
    check_name: str
    description: str | None
    enabled: bool
    severity: str
    wcag_criterion: str | None
    wcag_level: str | None
    aoda_required: bool
    wcag21_only: bool
    check_type: str
    help_url: str | None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CheckConfigResponse])
async def get_all_checks(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all check configurations."""
    repo = CheckConfigRepository(db)
    checks = await repo.get_all_checks()
    
    return [
        CheckConfigResponse(
            id=check.id,
            check_id=check.check_id,
            check_name=check.check_name,
            description=check.description,
            enabled=check.enabled,
            severity=check.severity.value,
            wcag_criterion=check.wcag_criterion,
            wcag_level=check.wcag_level,
            aoda_required=check.aoda_required,
            wcag21_only=check.wcag21_only,
            check_type=check.check_type,
            help_url=check.help_url
        )
        for check in checks
    ]


@router.put("/{check_id}")
async def update_check(
    check_id: str,
    update: CheckConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a check configuration."""
    repo = CheckConfigRepository(db)
    
    check = await repo.update_check(
        check_id=check_id,
        enabled=update.enabled,
        severity=update.severity
    )
    
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")
    
    return {
        "message": "Check configuration updated successfully",
        "check_id": check.check_id,
        "enabled": check.enabled,
        "severity": check.severity.value
    }


@router.post("/initialize")
async def initialize_checks(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize default check configurations."""
    repo = CheckConfigRepository(db)
    
    try:
        await repo.initialize_default_checks()
        return {"message": "Default checks initialized successfully"}
    except Exception as e:
        logger.error(f"Error initializing checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/", response_model=List[CheckConfigResponse])
async def get_user_checks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all check configurations with user-specific overrides."""
    repo = CheckConfigRepository(db)
    checks = await repo.get_user_checks(current_user.id)

    return [
        CheckConfigResponse(
            id=check["id"],
            check_id=check["check_id"],
            check_name=check["check_name"],
            description=check["description"],
            enabled=check["enabled"],
            severity=check["severity"],
            wcag_criterion=check["wcag_criterion"],
            wcag_level=check["wcag_level"],
            aoda_required=check["aoda_required"],
            wcag21_only=check["wcag21_only"],
            check_type=check["check_type"],
            help_url=check["help_url"]
        )
        for check in checks
    ]


@user_router.put("/{check_id}")
async def update_user_check(
    check_id: str,
    update: CheckConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user-specific check configuration (create override)."""
    repo = CheckConfigRepository(db)

    try:
        user_check = await repo.update_user_check(
            user_id=current_user.id,
            check_id=check_id,
            enabled=update.enabled,
            severity=update.severity
        )

        return {
            "message": "User check configuration updated successfully",
            "check_id": check_id,
            "enabled": user_check.enabled,
            "severity": user_check.severity.value
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.delete("/{check_id}")
async def reset_user_check(
    check_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset user check configuration to default (remove override)."""
    repo = CheckConfigRepository(db)

    deleted = await repo.reset_user_check(current_user.id, check_id)

    if not deleted:
        return {"message": "No user override to reset", "check_id": check_id}

    return {"message": "User check configuration reset to default", "check_id": check_id}


@user_router.post("/reset-all")
async def reset_all_user_checks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset all user check configurations to defaults."""
    repo = CheckConfigRepository(db)

    count = await repo.reset_all_user_checks(current_user.id)

    return {
        "message": f"Reset {count} user check configuration(s) to defaults",
        "count": count
    }
