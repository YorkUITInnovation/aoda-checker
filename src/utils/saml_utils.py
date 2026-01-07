"""SAML2 authentication utilities."""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
from lxml import etree
import re
from typing import Dict, Optional
from pathlib import Path


def generate_certificates(cn: str, org: str, country: str, state: str, city: str, email: str, ou: str) -> tuple[str, str]:
    """Generate self-signed certificate for SAML SP.

    Args:
        cn: Common Name
        org: Organization
        country: Country code (2 letters)
        state: State or Province
        city: City/Locality
        email: Email address
        ou: Organizational Unit

    Returns:
        Tuple of (certificate_pem, private_key_pem)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
        x509.NameAttribute(NameOID.LOCALITY_NAME, city),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ou),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
    ])

    # Create certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=3650)  # 10 years
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(cn)]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True,
    ).sign(private_key, hashes.SHA256(), default_backend())

    # Serialize certificate
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

    # Serialize private key
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    return cert_pem, key_pem


def get_certs_directory() -> Path:
    """Get the certificates directory path."""
    certs_dir = Path("saml_certs")
    certs_dir.mkdir(exist_ok=True)
    return certs_dir


def save_certificates(cert_pem: str, key_pem: str) -> None:
    """Save certificates to files.

    Args:
        cert_pem: Certificate in PEM format
        key_pem: Private key in PEM format
    """
    certs_dir = get_certs_directory()

    with open(certs_dir / "sp.crt", "w") as f:
        f.write(cert_pem)

    with open(certs_dir / "sp.key", "w") as f:
        f.write(key_pem)


def load_certificates() -> tuple[Optional[str], Optional[str]]:
    """Load certificates from files.

    Returns:
        Tuple of (certificate_pem, private_key_pem) or (None, None) if not found
    """
    certs_dir = get_certs_directory()
    cert_path = certs_dir / "sp.crt"
    key_path = certs_dir / "sp.key"

    if not cert_path.exists() or not key_path.exists():
        return None, None

    with open(cert_path, "r") as f:
        cert_pem = f.read()

    with open(key_path, "r") as f:
        key_pem = f.read()

    return cert_pem, key_pem


def certificates_exist() -> bool:
    """Check if certificates exist."""
    cert, key = load_certificates()
    return cert is not None and key is not None


def create_saml_settings(config: Dict, cert_pem: Optional[str] = None, key_pem: Optional[str] = None) -> Dict:
    """Create SAML settings dictionary for python3-saml.

    Args:
        config: SAML configuration dictionary
        cert_pem: Optional certificate PEM (will load from file if not provided)
        key_pem: Optional private key PEM (will load from file if not provided)

    Returns:
        SAML settings dictionary
    """
    # Load certificates if not provided
    if cert_pem is None or key_pem is None:
        cert_pem, key_pem = load_certificates()
        if cert_pem is None:
            cert_pem = ""
        if key_pem is None:
            key_pem = ""

    settings = {
        "strict": False,
        "debug": True,
        "sp": {
            "entityId": config.get('sp_entity_id', ''),
            "assertionConsumerService": {
                "url": config.get('sp_acs_url', ''),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "singleLogoutService": {
                "url": config.get('sp_sls_url', ''),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:2.0:nameid-format:transient",
            "x509cert": cert_pem,
            "privateKey": key_pem
        },
        "idp": {
            "entityId": config.get('idp_entity_id', ''),
            "singleSignOnService": {
                "url": config.get('idp_sso_url', ''),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "singleLogoutService": {
                "url": config.get('idp_sls_url', ''),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": config.get('idp_x509_cert', '')
        },
        "security": {
            "nameIdEncrypted": False,
            "authnRequestsSigned": True,
            "logoutRequestSigned": True,
            "logoutResponseSigned": True,
            "signMetadata": False,
            "wantMessagesSigned": False,
            "wantAssertionsSigned": False,
            "wantNameId": True,
            "wantNameIdEncrypted": False,
            "wantAssertionEncrypted": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
        }
    }

    # Add organization info if available
    if config.get('org_name'):
        settings['organization'] = {
            "en-US": {
                "name": config.get('org_name', ''),
                "displayname": config.get('org_display_name', ''),
                "url": config.get('org_url', '')
            }
        }

    # Add contact info if available
    if config.get('technical_contact_email'):
        settings['contactPerson'] = {
            "technical": {
                "givenName": "Technical Support",
                "emailAddress": config.get('technical_contact_email', '')
            }
        }

    return settings


def generate_metadata(config: Dict) -> bytes:
    """Generate SAML SP metadata XML.

    Args:
        config: SAML configuration dictionary

    Returns:
        Metadata XML as bytes
    """
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    settings_dict = create_saml_settings(config)
    settings = OneLogin_Saml2_Settings(settings_dict)
    metadata = settings.get_sp_metadata()

    # Add validUntil attribute if configured
    valid_until = config.get('sp_valid_until')
    if valid_until:
        try:
            # Parse the metadata XML
            root = etree.fromstring(metadata)

            # Add validUntil attribute to EntityDescriptor
            # Note: The root element should be EntityDescriptor
            if root.tag.endswith('EntityDescriptor'):
                root.set('validUntil', valid_until)

            # Serialize back to bytes
            metadata = etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)
        except Exception as e:
            # If there's any issue, log it but continue with original metadata
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to add validUntil attribute to metadata: {str(e)}")

    return metadata


def parse_idp_metadata(metadata_content: bytes | str) -> Dict[str, str]:
    """Parse IdP metadata XML and extract required information.

    Args:
        metadata_content: XML string or bytes containing IdP metadata

    Returns:
        Dictionary with extracted IdP information

    Raises:
        ValueError: If metadata parsing fails
    """
    try:
        # Parse XML
        if isinstance(metadata_content, str):
            metadata_content = metadata_content.encode('utf-8')

        root = etree.fromstring(metadata_content)

        # Define namespaces
        namespaces = {
            'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }

        result = {
            'idp_entity_id': '',
            'idp_sso_url': '',
            'idp_sls_url': '',
            'idp_x509_cert': ''
        }

        # Extract Entity ID
        entity_id = root.get('entityID')
        if entity_id:
            result['idp_entity_id'] = entity_id

        # Find IDPSSODescriptor
        idp_descriptor = root.find('.//md:IDPSSODescriptor', namespaces)

        if idp_descriptor is not None:
            # Extract SSO URL
            sso_service = idp_descriptor.find(
                './/md:SingleSignOnService[@Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"]',
                namespaces
            )
            if sso_service is None:
                # Try HTTP-POST binding if Redirect not found
                sso_service = idp_descriptor.find(
                    './/md:SingleSignOnService[@Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"]',
                    namespaces
                )
            if sso_service is not None:
                result['idp_sso_url'] = sso_service.get('Location', '')

            # Extract SLO URL (optional)
            slo_service = idp_descriptor.find(
                './/md:SingleLogoutService[@Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"]',
                namespaces
            )
            if slo_service is None:
                # Try HTTP-POST binding
                slo_service = idp_descriptor.find(
                    './/md:SingleLogoutService[@Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"]',
                    namespaces
                )
            if slo_service is not None:
                result['idp_sls_url'] = slo_service.get('Location', '')

            # Extract X509 Certificate
            cert_element = idp_descriptor.find('.//ds:X509Certificate', namespaces)
            if cert_element is not None and cert_element.text:
                # Clean up certificate text (remove whitespace and newlines)
                cert_text = re.sub(r'\s+', '', cert_element.text)
                result['idp_x509_cert'] = cert_text

        return result

    except Exception as e:
        raise ValueError(f"Error parsing IdP metadata: {str(e)}")


async def fetch_idp_metadata_from_url(url: str) -> Dict[str, str]:
    """Fetch IdP metadata from a URL.

    Args:
        url: URL to fetch metadata from

    Returns:
        Parsed IdP information

    Raises:
        ValueError: If metadata fetching or parsing fails
    """
    import httpx
    import ssl

    try:
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Fetch metadata with httpx
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                url,
                headers={
                    'User-Agent': 'AODA-Checker-SAML/1.0',
                    'Accept': 'application/xml, text/xml, */*'
                },
                timeout=10.0
            )
            response.raise_for_status()
            metadata_content = response.content
            return parse_idp_metadata(metadata_content)

    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP Error {e.response.status_code}: Could not fetch metadata from URL.")
    except httpx.RequestError as e:
        raise ValueError(f"Request Error: {str(e)}. Please check the URL and your internet connection.")
    except Exception as e:
        raise ValueError(f"Error fetching metadata: {str(e)}")


def prepare_fastapi_request(request) -> Dict:
    """Prepare FastAPI request for python3-saml.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary formatted for python3-saml
    """
    return {
        'https': 'on' if request.url.scheme == 'https' else 'off',
        'http_host': request.url.netloc,
        'server_port': str(request.url.port) if request.url.port else ('443' if request.url.scheme == 'https' else '80'),
        'script_name': request.url.path,
        'get_data': dict(request.query_params),
        'post_data': {},  # Will be filled from form data
        'query_string': request.url.query.encode('utf-8') if request.url.query else b''
    }

