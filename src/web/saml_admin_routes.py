"""SAML2 admin configuration routes."""
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.database.saml_repository import SAMLConfigRepository
from src.web.dependencies import get_current_admin_user
from src.database.models import User
from src.utils.saml_utils import (
    generate_certificates,
    save_certificates,
    certificates_exist,
    parse_idp_metadata,
    fetch_idp_metadata_from_url,
    generate_metadata
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/admin/saml-config", response_class=HTMLResponse)
async def saml_config_page(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """SAML configuration page."""
    saml_repo = SAMLConfigRepository(db)
    config = await saml_repo.get_or_create_config()

    # Convert attribute_mapping to JSON string for display
    attribute_mapping_json = json.dumps(config.attribute_mapping or {}, indent=2)

    # Check if certificates exist
    certs_exist = certificates_exist()

    return templates.TemplateResponse(
        "admin_saml_config.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "admin",
            "config": config,
            "attribute_mapping_json": attribute_mapping_json,
            "certs_exist": certs_exist
        }
    )


@router.post("/api/admin/saml-config")
async def update_saml_config(
    request: Request,
    enabled: bool = Form(False),
    sp_entity_id: str = Form(""),
    sp_acs_url: str = Form(""),
    sp_sls_url: str = Form(""),
    idp_entity_id: str = Form(""),
    idp_sso_url: str = Form(""),
    idp_sls_url: str = Form(""),
    idp_x509_cert: str = Form(""),
    org_name: str = Form(""),
    org_display_name: str = Form(""),
    org_url: str = Form(""),
    technical_contact_email: str = Form(""),
    attribute_mapping: str = Form("{}"),
    auto_provision_users: bool = Form(False),
    default_user_role_is_admin: bool = Form(False),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update SAML configuration."""
    try:
        # Parse attribute mapping JSON
        try:
            attr_mapping = json.loads(attribute_mapping)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid attribute mapping JSON")

        # Update configuration
        saml_repo = SAMLConfigRepository(db)
        await saml_repo.update_config(
            enabled=enabled,
            sp_entity_id=sp_entity_id.strip() if sp_entity_id else None,
            sp_acs_url=sp_acs_url.strip() if sp_acs_url else None,
            sp_sls_url=sp_sls_url.strip() if sp_sls_url else None,
            idp_entity_id=idp_entity_id.strip() if idp_entity_id else None,
            idp_sso_url=idp_sso_url.strip() if idp_sso_url else None,
            idp_sls_url=idp_sls_url.strip() if idp_sls_url else None,
            idp_x509_cert=idp_x509_cert.strip() if idp_x509_cert else None,
            org_name=org_name.strip() if org_name else None,
            org_display_name=org_display_name.strip() if org_display_name else None,
            org_url=org_url.strip() if org_url else None,
            technical_contact_email=technical_contact_email.strip() if technical_contact_email else None,
            attribute_mapping=attr_mapping,
            auto_provision_users=auto_provision_users,
            default_user_role_is_admin=default_user_role_is_admin
        )

        logger.info(f"SAML configuration updated by admin user: {current_user.username}")

        return JSONResponse(
            content={"success": True, "message": "SAML configuration updated successfully"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating SAML configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")


class CertificateRequest(BaseModel):
    """Certificate generation request."""
    cn: str
    org: str
    country: str
    state: str
    city: str
    email: str
    ou: str


@router.post("/api/admin/saml-generate-certificates")
async def generate_saml_certificates(
    cert_request: CertificateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate SAML SP certificates."""
    try:
        logger.info(f"Generating SAML certificates for: {cert_request.cn}")

        # Generate certificates
        cert_pem, key_pem = generate_certificates(
            cn=cert_request.cn,
            org=cert_request.org,
            country=cert_request.country,
            state=cert_request.state,
            city=cert_request.city,
            email=cert_request.email,
            ou=cert_request.ou
        )

        # Save certificates
        save_certificates(cert_pem, key_pem)

        logger.info(f"SAML certificates generated successfully by admin: {current_user.username}")

        return JSONResponse(
            content={"success": True, "message": "Certificates generated successfully"},
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error generating certificates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating certificates: {str(e)}")


@router.get("/api/admin/saml-download-metadata")
async def download_saml_metadata(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Download SP metadata.xml file."""
    try:
        saml_repo = SAMLConfigRepository(db)
        config = await saml_repo.get_config()

        if not config or not config.sp_entity_id:
            raise HTTPException(status_code=400, detail="SAML configuration is incomplete")

        if not certificates_exist():
            raise HTTPException(status_code=400, detail="Certificates not generated")

        config_dict = saml_repo.config_to_dict(config)
        metadata_xml = generate_metadata(config_dict)

        # Decode bytes to string
        if isinstance(metadata_xml, bytes):
            metadata_xml = metadata_xml.decode('utf-8')

        from fastapi.responses import Response
        return Response(
            content=metadata_xml,
            media_type='application/xml',
            headers={'Content-Disposition': 'attachment; filename="metadata.xml"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating metadata: {str(e)}")


class ParseMetadataRequest(BaseModel):
    """Parse IdP metadata request."""
    metadata_source: str  # 'xml' or 'url'
    idp_metadata_xml: str = ""
    idp_metadata_url: str = ""


@router.post("/api/admin/saml-parse-metadata")
async def parse_saml_metadata(
    parse_request: ParseMetadataRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Parse IdP metadata XML or fetch from URL."""
    try:
        if parse_request.metadata_source == 'url':
            # Fetch from URL
            metadata_url = parse_request.idp_metadata_url.strip()
            if not metadata_url:
                raise HTTPException(status_code=400, detail="Please provide a metadata URL")

            if not metadata_url.startswith(('http://', 'https://')):
                raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

            try:
                idp_info = await fetch_idp_metadata_from_url(metadata_url)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            # Parse XML content
            metadata_xml = parse_request.idp_metadata_xml
            if not metadata_xml:
                raise HTTPException(status_code=400, detail="Please provide metadata XML")

            try:
                idp_info = parse_idp_metadata(metadata_xml)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Validate parsed data
        if not idp_info.get('idp_entity_id'):
            raise HTTPException(
                status_code=400,
                detail="Could not find Entity ID in metadata. The XML may not be valid SAML metadata."
            )

        if not idp_info.get('idp_sso_url'):
            raise HTTPException(
                status_code=400,
                detail="Could not find SSO URL in metadata. The XML may not contain an IDPSSODescriptor."
            )

        logger.info(f"IdP metadata parsed successfully by admin: {current_user.username}")

        return JSONResponse(
            content={
                "success": True,
                "message": "IdP metadata parsed successfully",
                "data": idp_info
            },
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

