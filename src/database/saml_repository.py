"""Repository for SAML configuration database operations."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import SAMLConfiguration


class SAMLConfigRepository:
    """Repository for managing SAML configuration."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_config(self) -> Optional[SAMLConfiguration]:
        """Get the SAML configuration (there should only be one row)."""
        result = await self.session.execute(
            select(SAMLConfiguration).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_config(self) -> SAMLConfiguration:
        """Get or create the SAML configuration."""
        config = await self.get_config()

        if config is None:
            # Create default configuration
            config = SAMLConfiguration(
                enabled=False,
                auto_provision_users=False,
                default_user_role_is_admin=False,
                attribute_mapping={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.session.add(config)
            await self.session.commit()
            await self.session.refresh(config)

        return config

    async def update_config(
        self,
        enabled: Optional[bool] = None,
        sp_entity_id: Optional[str] = None,
        sp_acs_url: Optional[str] = None,
        sp_sls_url: Optional[str] = None,
        sp_valid_until: Optional[str] = None,
        idp_entity_id: Optional[str] = None,
        idp_sso_url: Optional[str] = None,
        idp_sls_url: Optional[str] = None,
        idp_x509_cert: Optional[str] = None,
        org_name: Optional[str] = None,
        org_display_name: Optional[str] = None,
        org_url: Optional[str] = None,
        technical_contact_email: Optional[str] = None,
        attribute_mapping: Optional[Dict[str, str]] = None,
        auto_provision_users: Optional[bool] = None,
        default_user_role_is_admin: Optional[bool] = None
    ) -> SAMLConfiguration:
        """Update SAML configuration.

        Args:
            enabled: Whether SAML is enabled
            sp_entity_id: Service Provider Entity ID
            sp_acs_url: Assertion Consumer Service URL
            sp_sls_url: Single Logout Service URL
            sp_valid_until: Metadata validity period in ISO format
            idp_entity_id: Identity Provider Entity ID
            idp_sso_url: Identity Provider SSO URL
            idp_sls_url: Identity Provider SLS URL
            idp_x509_cert: Identity Provider X.509 certificate
            org_name: Organization name
            org_display_name: Organization display name
            org_url: Organization URL
            technical_contact_email: Technical contact email
            attribute_mapping: Mapping of SAML attributes to user fields
            auto_provision_users: Whether to auto-provision users
            default_user_role_is_admin: Whether new users should be admin

        Returns:
            Updated SAML configuration
        """
        config = await self.get_or_create_config()

        if enabled is not None:
            config.enabled = enabled
        if sp_entity_id is not None:
            config.sp_entity_id = sp_entity_id
        if sp_acs_url is not None:
            config.sp_acs_url = sp_acs_url
        if sp_sls_url is not None:
            config.sp_sls_url = sp_sls_url
        if sp_valid_until is not None:
            config.sp_valid_until = sp_valid_until
        if idp_entity_id is not None:
            config.idp_entity_id = idp_entity_id
        if idp_sso_url is not None:
            config.idp_sso_url = idp_sso_url
        if idp_sls_url is not None:
            config.idp_sls_url = idp_sls_url
        if idp_x509_cert is not None:
            config.idp_x509_cert = idp_x509_cert
        if org_name is not None:
            config.org_name = org_name
        if org_display_name is not None:
            config.org_display_name = org_display_name
        if org_url is not None:
            config.org_url = org_url
        if technical_contact_email is not None:
            config.technical_contact_email = technical_contact_email
        if attribute_mapping is not None:
            config.attribute_mapping = attribute_mapping
        if auto_provision_users is not None:
            config.auto_provision_users = auto_provision_users
        if default_user_role_is_admin is not None:
            config.default_user_role_is_admin = default_user_role_is_admin

        config.updated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(config)
        return config

    def config_to_dict(self, config: SAMLConfiguration) -> Dict[str, Any]:
        """Convert SAMLConfiguration model to dictionary for SAML utils.

        Args:
            config: SAMLConfiguration instance

        Returns:
            Dictionary representation
        """
        return {
            'enabled': config.enabled,
            'sp_entity_id': config.sp_entity_id or '',
            'sp_acs_url': config.sp_acs_url or '',
            'sp_sls_url': config.sp_sls_url or '',
            'sp_valid_until': config.sp_valid_until or '',
            'idp_entity_id': config.idp_entity_id or '',
            'idp_sso_url': config.idp_sso_url or '',
            'idp_sls_url': config.idp_sls_url or '',
            'idp_x509_cert': config.idp_x509_cert or '',
            'org_name': config.org_name or '',
            'org_display_name': config.org_display_name or '',
            'org_url': config.org_url or '',
            'technical_contact_email': config.technical_contact_email or '',
            'attribute_mapping': config.attribute_mapping or {},
            'auto_provision_users': config.auto_provision_users,
            'default_user_role_is_admin': config.default_user_role_is_admin
        }

