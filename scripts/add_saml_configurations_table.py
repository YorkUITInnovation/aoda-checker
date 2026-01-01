"""Add SAML configuration table."""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def add_saml_configurations_table():
    """Add saml_configurations table to database."""

    # Get database URL from environment or use default
    database_url = os.getenv(
        'DATABASE_URL',
        'mysql+aiomysql://aoda_user:aoda_password@mysql:3306/aoda_checker'
    )

    # Create engine
    engine = create_async_engine(database_url, echo=True)

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS saml_configurations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        enabled BOOLEAN NOT NULL DEFAULT FALSE,
        sp_entity_id VARCHAR(512),
        sp_acs_url VARCHAR(512),
        sp_sls_url VARCHAR(512),
        idp_entity_id VARCHAR(512),
        idp_sso_url VARCHAR(512),
        idp_sls_url VARCHAR(512),
        idp_x509_cert TEXT,
        org_name VARCHAR(255),
        org_display_name VARCHAR(255),
        org_url VARCHAR(512),
        technical_contact_email VARCHAR(255),
        attribute_mapping JSON,
        auto_provision_users BOOLEAN NOT NULL DEFAULT FALSE,
        default_user_role_is_admin BOOLEAN NOT NULL DEFAULT FALSE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    async with engine.begin() as conn:
        print("Creating saml_configurations table...")
        await conn.execute(text(create_table_sql))
        print("✅ saml_configurations table created successfully!")

    await engine.dispose()


if __name__ == "__main__":
    print("Adding SAML configurations table...")
    asyncio.run(add_saml_configurations_table())
    print("Migration complete!")

