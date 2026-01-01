"""SAML2 authentication routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from onelogin.saml2.auth import OneLogin_Saml2_Auth

from src.database import get_db
from src.database.saml_repository import SAMLConfigRepository
from src.database.user_repository import UserRepository
from src.utils.saml_utils import create_saml_settings, prepare_fastapi_request

router = APIRouter()
logger = logging.getLogger(__name__)


async def init_saml_auth(request: Request, db: AsyncSession) -> OneLogin_Saml2_Auth:
    """Initialize SAML Auth object.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        OneLogin_Saml2_Auth instance

    Raises:
        HTTPException: If SAML is not enabled or configured
    """
    saml_repo = SAMLConfigRepository(db)
    config = await saml_repo.get_config()

    if not config or not config.enabled:
        raise HTTPException(status_code=400, detail="SAML authentication is not enabled")

    config_dict = saml_repo.config_to_dict(config)
    settings = create_saml_settings(config_dict)

    req = prepare_fastapi_request(request)
    auth = OneLogin_Saml2_Auth(req, settings)
    return auth


@router.get("/saml/login")
async def saml_login(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Initiate SAML SSO login."""
    try:
        auth = await init_saml_auth(request, db)
        sso_url = auth.login()
        return RedirectResponse(url=sso_url, status_code=303)
    except HTTPException as e:
        logger.error(f"SAML login error: {e.detail}")
        return RedirectResponse(url=f"/login?error=saml_not_configured", status_code=303)
    except Exception as e:
        logger.error(f"SAML login error: {str(e)}")
        return RedirectResponse(url=f"/login?error=saml_error", status_code=303)


@router.post("/saml/acs")
async def saml_acs(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Assertion Consumer Service - handles SAML response."""
    try:
        # Get form data for SAML response
        form_data = await request.form()

        # Prepare request with POST data
        req = prepare_fastapi_request(request)
        req['post_data'] = dict(form_data)

        # Initialize SAML auth
        saml_repo = SAMLConfigRepository(db)
        config = await saml_repo.get_config()

        if not config or not config.enabled:
            raise HTTPException(status_code=400, detail="SAML authentication is not enabled")

        config_dict = saml_repo.config_to_dict(config)
        settings = create_saml_settings(config_dict)

        auth = OneLogin_Saml2_Auth(req, settings)
        auth.process_response()

        errors = auth.get_errors()

        if len(errors) == 0:
            # Get user attributes from SAML response
            attributes = auth.get_attributes()
            name_id = auth.get_nameid()
            session_index = auth.get_session_index()

            logger.info(f"SAML authentication successful for NameID: {name_id}")
            logger.debug(f"SAML attributes: {attributes}")

            # Map SAML attributes to user fields
            attribute_mapping = config.attribute_mapping or {}

            user_data = {
                'username': name_id,  # Default to NameID
                'email': None,
                'first_name': None,
                'last_name': None,
                'id_number': None
            }

            # Apply attribute mapping
            for saml_attr, user_field in attribute_mapping.items():
                if saml_attr in attributes:
                    value = attributes[saml_attr]
                    # Get first value if it's a list
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0]

                    if user_field in user_data:
                        user_data[user_field] = value

            # Look up user by email or username
            user_repo = UserRepository(db)
            user = None

            # Try to find user by email first if provided
            if user_data['email']:
                user = await user_repo.get_user_by_email(user_data['email'])

            # Try to find by username if not found by email
            if not user and user_data['username']:
                user = await user_repo.get_user_by_username(user_data['username'])

            # Auto-provision user if not found and enabled
            if not user:
                if config.auto_provision_users:
                    logger.info(f"Auto-provisioning new SAML user: {user_data['username']}")

                    # Create new user with SAML auth method
                    # Generate a random password (won't be used for SAML users)
                    import secrets
                    random_password = secrets.token_urlsafe(32)

                    user = await user_repo.create_user(
                        username=user_data['username'],
                        password=random_password,
                        email=user_data['email'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        id_number=user_data['id_number'],
                        is_admin=config.default_user_role_is_admin,
                        auth_method='saml'
                    )
                else:
                    # User not found and auto-provisioning is disabled
                    logger.warning(f"SAML user not found and auto-provisioning disabled: {user_data['username']}")
                    return RedirectResponse(
                        url="/login?error=account_not_created",
                        status_code=303
                    )

            # Check if user is active
            if not user.is_active:
                logger.warning(f"Inactive user attempted SAML login: {user.username}")
                return RedirectResponse(url="/login?error=account_inactive", status_code=303)

            # Update last login
            await user_repo.update_last_login(user.id)

            # Store user session
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['is_admin'] = user.is_admin
            request.session['saml_session_index'] = session_index
            request.session['saml_name_id'] = name_id

            logger.info(f"User {user.username} logged in via SAML")

            # Redirect to home or dashboard
            return RedirectResponse(url="/", status_code=303)
        else:
            # SAML authentication failed
            error_msg = ', '.join(errors)
            logger.error(f"SAML authentication failed: {error_msg}")
            return RedirectResponse(url=f"/login?error=saml_auth_failed", status_code=303)

    except Exception as e:
        logger.error(f"SAML ACS error: {str(e)}", exc_info=True)
        return RedirectResponse(url=f"/login?error=saml_error", status_code=303)


@router.get("/saml/sls")
async def saml_sls(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Single Logout Service."""
    try:
        auth = await init_saml_auth(request, db)

        url = auth.process_slo()
        errors = auth.get_errors()

        if len(errors) == 0:
            # Clear session
            request.session.clear()

            if url is not None:
                return RedirectResponse(url=url, status_code=303)
            else:
                return RedirectResponse(url="/login", status_code=303)
        else:
            error_msg = ', '.join(errors)
            logger.error(f"SLS error: {error_msg}")

            # Clear session anyway
            request.session.clear()
            return RedirectResponse(url="/login", status_code=303)

    except Exception as e:
        logger.error(f"SAML SLS error: {str(e)}")

        # Clear session
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)


@router.get("/saml/metadata")
async def saml_metadata(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Display SP metadata XML."""
    from src.utils.saml_utils import generate_metadata, certificates_exist

    saml_repo = SAMLConfigRepository(db)
    config = await saml_repo.get_config()

    if not config or not config.sp_entity_id:
        raise HTTPException(status_code=400, detail="SAML configuration is incomplete")

    if not certificates_exist():
        raise HTTPException(status_code=400, detail="Certificates not generated. Please generate certificates first.")

    config_dict = saml_repo.config_to_dict(config)

    try:
        metadata_xml = generate_metadata(config_dict)

        # Decode bytes to string for XML response
        if isinstance(metadata_xml, bytes):
            metadata_xml = metadata_xml.decode('utf-8')

        from fastapi.responses import Response
        return Response(
            content=metadata_xml,
            media_type='application/xml',
            headers={'Content-Disposition': 'inline; filename="metadata.xml"'}
        )
    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating metadata: {str(e)}")

