# AODA Compliance Checker

An automated AODA/WCAG AA compliance checker that crawls websites and generates accessibility reports with user authentication, scheduled scans, and email notifications.

## Quick Start

The fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd aoda-checker

# Copy environment file
cp .env.example .env

# Build and start with Docker
docker compose up -d

# Access the application at http://localhost:8080
```

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Important:** Change the admin password immediately after first login!

## Prerequisites

- **Docker & Docker Compose** (recommended)
- OR **Python 3.10+** for local installation

## Installation

### Option 1: Docker (Recommended)

Docker handles all dependencies, database setup, and email testing automatically.

```bash
# Start all services (MySQL, MailHog, Application)
docker compose up -d

# View logs
docker compose logs -f aoda-checker

# Stop services
docker compose down
```

The application includes:
- **MySQL 8.4** database on port 3306
- **MailHog** email testing on port 8025 (web UI)
- **Application** on port 8080

### Option 2: Local Installation

Only use this if you cannot use Docker.

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Setup MySQL 8.4 locally and create database
mysql -u root -p < scripts/create_database.sql

# Initialize database tables
python scripts/init_db.py

# Create admin user
python init_auth.py

# Start the application
python main.py web
```

## Configuration

All configuration is done through the `.env` file. Copy `.env.example` to `.env` and modify as needed.

### Required Settings

```env
# Application URL (update for production)
APP_URL="http://localhost:8080"

# Security - CHANGE THIS IN PRODUCTION!
# Generate with: openssl rand -hex 32
SECRET_KEY="change-this-secret-key-in-production"

# Database Connection (Docker uses mysql service name)
DATABASE_URL="mysql+aiomysql://aoda_user:aoda_password@mysql:3306/aoda_checker"
```

### Timezone Configuration

```env
# Default: America/Toronto
TIMEZONE="America/Toronto"
TZ="America/Toronto"
```

### Email/SMTP Configuration

Email is required for scheduled scan notifications.

#### Development (Default - MailHog)

MailHog captures all emails for testing without sending real emails:

```env
SMTP_HOST="mailhog"
SMTP_PORT=1025
SMTP_USERNAME=""
SMTP_PASSWORD=""
SMTP_USE_TLS=false
SMTP_FROM_EMAIL="noreply@aoda-checker.local"
SMTP_FROM_NAME="AODA Compliance Checker"
```

View emails at: http://localhost:8025

#### Production (Gmail Example)

```env
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_USE_TLS=true
SMTP_FROM_EMAIL="noreply@your-domain.com"
SMTP_FROM_NAME="AODA Compliance Checker"
```

**Gmail Setup:**
1. Enable 2-Factor Authentication in your Google Account
2. Generate App Password at: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password)

**Other SMTP Providers:**
- Office 365: `smtp.office365.com:587`
- Outlook: `smtp-mail.outlook.com:587`
- Yahoo: `smtp.mail.yahoo.com:587`
- SendGrid: `smtp.sendgrid.net:587`

### Database Configuration (Advanced)

```env
DATABASE_URL="mysql+aiomysql://user:password@host:port/database"
DATABASE_ECHO=false          # Set to true for SQL debug logging
DB_POOL_SIZE=10             # Connection pool size
DB_MAX_OVERFLOW=20          # Max overflow connections
```

### Application Settings (Advanced)

```env
HOST="0.0.0.0"              # Bind address
PORT=8080                   # Application port
MAX_PAGES_DEFAULT=50        # Default max pages to scan
MAX_DEPTH_DEFAULT=3         # Default crawl depth
REQUEST_DELAY=0.2           # Delay between requests (seconds)
TIMEOUT=20000               # Page load timeout (ms)
ENABLE_SCREENSHOTS=false    # Enable page screenshots (impacts performance)
```

## Accessing the Application

After starting the services:

- **Web Application:** http://localhost:8080
- **Email Testing (MailHog):** http://localhost:8025
- **MySQL Database:** localhost:3306

## User Management

### Creating Additional Users

1. Log in as admin
2. Click "Admin" in the left sidebar
3. Click "Create New User"
4. Fill in user details (username, email, password, role)
5. Click "Create User"

### User Roles

- **Admin:** Full access, can manage users, view all scans, access admin panel
- **User:** Can create and view their own scans, schedule scans

## Testing Email Configuration

1. Log in as admin
2. Click "Test Email" in the left sidebar
3. Enter an email address
4. Click "Send Test Email"
5. For development: Check MailHog at http://localhost:8025
6. For production: Check the recipient's inbox

## Scheduled Scans Setup

1. Run a scan from the main page
2. Go to "Scan History" in the left sidebar
3. Click the "Schedule" button on any completed scan
4. Configure:
   - **Frequency:** Daily, Weekly, Monthly, or Yearly
   - **Time:** When to run (uses timezone from `.env`)
   - **Days:** (For weekly) Which days to run
   - **Email Notifications:** Choose to receive alerts on violations
5. Click "Schedule Scan"
6. View scheduled scan logs under "Scheduled Scan Logs" in the sidebar

## Rebuilding After Configuration Changes

If you modify `.env` or code:

```bash
# Rebuild containers
docker compose down
docker compose build
docker compose up -d
```

## Troubleshooting

### Application won't start
- Check logs: `docker compose logs -f aoda-checker`
- Ensure MySQL is healthy: `docker compose ps`
- Wait 30-40 seconds for MySQL to fully initialize

### Database connection errors
- Verify `DATABASE_URL` in `.env`
- For Docker: Use `mysql` as hostname, not `localhost`
- Ensure MySQL container is running: `docker compose ps mysql`

### Email not sending
- For development: Check MailHog at http://localhost:8025
- Verify SMTP settings in `.env`
- Use "Test Email" feature in admin panel
- Check application logs for SMTP errors

### Scheduled scans not running
- Verify timezone is set correctly in `.env`
- Check "Scheduled Scan Logs" for error messages
- Ensure email configuration is working (for notifications)
- Container must be running continuously

### Permission issues with reports
```bash
# Fix permissions on reports directory
chmod -R 777 reports/
```

## Backup and Restore

### Backup Database

```bash
# Create backup
docker exec aoda-mysql mysqldump -u aoda_user -paoda_password aoda_checker > backup.sql
```

### Restore Database

```bash
# Restore from backup
docker exec -i aoda-mysql mysql -u aoda_user -paoda_password aoda_checker < backup.sql
```

## Security Recommendations for Production

1. **Change Secret Key:** Generate new secret with `openssl rand -hex 32`
2. **Change MySQL Password:** Update in both `.env` and `docker-compose.yml`
3. **Change Admin Password:** Do this immediately after first login
4. **Use HTTPS:** Configure reverse proxy (nginx/Apache) with SSL certificate
5. **Configure Real SMTP:** Replace MailHog with production email service
6. **Firewall:** Restrict access to MySQL port (3306)
7. **Regular Backups:** Automate database backups
8. **Update APP_URL:** Set to your production domain

## License

MIT

## Author

Patrick Thibaudeau


