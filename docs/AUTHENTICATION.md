# Authentication System Guide

## Overview

The AODA Checker now includes a comprehensive authentication system with user management and role-based access control.

## Features

### User Authentication
- **Login/Logout**: Session-based authentication with cookies
- **JWT Support**: API authentication via Bearer tokens
- **Password Security**: Bcrypt hashing for password storage
- **Extensible**: Built to support multiple authentication methods (SAML, OAuth, LDAP)

### User Management (Admin Only)
- Create, edit, and delete user accounts
- Assign admin privileges
- Activate/deactivate users
- Track last login times

### Scan Ownership
- All scans are associated with the user who created them
- Users can only view and delete their own scans
- Admins can view all scans or filter by user

### Role-Based Access Control
- **Regular Users**: Can create scans and view their own results
- **Admin Users**: Full access to all scans and user management

## Initial Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database and Create Admin User

```bash
python init_auth.py
```

This will:
- Create all necessary database tables (users, scans, etc.)
- Create a default admin user with credentials:
  - **Username**: `admin`
  - **Password**: `admin123`

⚠️ **IMPORTANT**: Change the default password immediately after first login!

### 3. Start the Application

```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

Or use Docker:
```bash
docker compose up -d --build
```

### 4. First Login

1. Navigate to `http://localhost:8000/login`
2. Login with username `admin` and password `admin123`
3. Go to Admin > Users and edit the admin account to change the password

## User Guide

### For Regular Users

#### Logging In
1. Navigate to `/login`
2. Enter your username and password
3. Click "Sign In"

#### Creating Scans
1. After login, you'll see the scan form
2. Configure your scan settings
3. Click "Start Accessibility Scan"
4. View results when complete

#### Viewing History
1. Click "History" in the navigation
2. See all your previous scans
3. Click "View" to see detailed results
4. Click "Delete" to remove old scans

### For Admin Users

#### User Management
1. Click "Users" in the navigation
2. Use "Add New User" to create accounts
3. Click the edit icon to modify users
4. Click the delete icon to remove users (cannot delete yourself)

#### Viewing All Scans
1. Go to History page
2. Use the "Filter by User" dropdown:
   - "My Scans Only" - see your own scans
   - "All Users' Scans" - see everyone's scans
   - "Select User..." - filter by specific user

## API Usage

### Authentication

#### Login (Get JWT Token)
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Using JWT Token
```bash
curl -X GET http://localhost:8000/api/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### User Management (Admin Only)

#### List All Users
```bash
curl -X GET http://localhost:8000/admin/api/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

#### Create User
```bash
curl -X POST http://localhost:8000/admin/api/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepass123",
    "email": "user@example.com",
    "full_name": "New User",
    "is_admin": false
  }'
```

## Security Considerations

### Production Deployment

1. **Change Secret Key**: Set `SECRET_KEY` environment variable:
   ```bash
   export SECRET_KEY="your-very-secure-random-key-here"
   ```

2. **Use HTTPS**: Enable `https_only` in session middleware when using HTTPS

3. **Strong Passwords**: Enforce password complexity requirements

4. **Environment Variables**: Store sensitive config in `.env`:
   ```
   SECRET_KEY=your-secure-key
   DATABASE_URL=mysql+aiomysql://user:pass@host:port/db
   ```

### Password Policy
- Minimum 8 characters recommended
- Use bcrypt hashing (automatically handled)
- Passwords are never stored in plain text

## Extending Authentication

### Adding New Authentication Methods

The system is designed to support multiple authentication backends:

1. **SAML 2.0**: For enterprise SSO
2. **OAuth 2.0**: For social login (Google, GitHub, etc.)
3. **LDAP**: For Active Directory integration

To add a new method:

1. Create a new authentication module in `src/auth/providers/`
2. Implement the authentication logic
3. Update `User` model's `auth_method` field
4. Add route in `src/web/auth_routes.py`

Example structure:
```python
# src/auth/providers/saml_provider.py
class SAMLAuthProvider:
    async def authenticate(self, saml_response):
        # Parse SAML response
        # Create or update user
        # Return user object
        pass
```

## Troubleshooting

### Cannot Login
- Verify user exists and is active
- Check password is correct
- Check database connection
- Review server logs for errors

### Session Expires
- Sessions last 8 hours by default
- Configure `JWT_EXPIRATION_MINUTES` in config
- Login again to get new session

### Permission Denied
- Verify user has correct role (admin vs regular user)
- Check scan ownership for access to results
- Admins can view all scans

### Database Errors
- Ensure database is running
- Check `DATABASE_URL` is correct
- Run `python init_auth.py` to create tables
- Check MySQL connection and credentials

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-this-secret-key-in-production` | Secret key for sessions and JWT |
| `JWT_ALGORITHM` | `HS256` | Algorithm for JWT encoding |
| `JWT_EXPIRATION_MINUTES` | `480` | Session duration (8 hours) |
| `DATABASE_URL` | MySQL connection string | Database connection URL |

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Email address (optional)
- `hashed_password`: Bcrypt hashed password
- `full_name`: Display name
- `is_admin`: Admin flag
- `is_active`: Account status
- `auth_method`: Authentication method (manual, saml, oauth, ldap)
- `created_at`: Account creation timestamp
- `updated_at`: Last modification timestamp
- `last_login`: Last login timestamp

### Scans Table (Updated)
- Added `user_id`: Foreign key to users table
- All other fields remain the same

## Support

For issues or questions:
1. Check this documentation
2. Review server logs
3. Check database connection
4. Verify environment variables

## Future Enhancements

Planned features:
- [ ] Password reset functionality
- [ ] Email verification
- [ ] Two-factor authentication (2FA)
- [ ] SAML 2.0 provider
- [ ] OAuth 2.0 providers (Google, GitHub)
- [ ] LDAP/Active Directory integration
- [ ] Audit logging
- [ ] API rate limiting
- [ ] Password complexity requirements

