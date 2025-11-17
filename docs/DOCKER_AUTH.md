# Docker Deployment Guide - With Authentication

## Overview

When you rebuild the Docker container, **YES, the authentication system will be automatically set up**, including:

✅ All database tables (users, scans, pages, violations)  
✅ Default admin user created automatically  
✅ Authentication system ready to use  

---

## Quick Answer: Yes, It Will Work! 🎉

When you run:
```bash
docker compose up -d --build
```

Or:
```bash
./docker-rebuild.sh
```

The system will automatically:
1. Build the new Docker image with all authentication code
2. Start MySQL database
3. Wait for MySQL to be ready
4. Run `scripts/init_db.py` to create scan tables
5. **Run `init_auth.py` to create auth tables and admin user** ✅
6. Start the application

**Default admin credentials will be created:**
- Username: `admin`
- Password: `admin123`

---

## How It Works

### The Docker Entrypoint Script

The `docker-entrypoint.sh` script now includes:

```bash
# Initialize database tables
echo "🔧 Initializing database tables..."
python3 scripts/init_db.py

# Initialize authentication system and create admin user
echo "🔐 Initializing authentication system..."
python3 init_auth.py
```

This runs **every time** the container starts, ensuring:
- If tables don't exist, they're created
- If admin user doesn't exist, it's created
- If everything already exists, it skips gracefully

---

## Step-by-Step: Rebuild with Authentication

### Option 1: Quick Rebuild (Recommended)

```bash
./docker-rebuild.sh
```

This script will:
1. Stop existing containers
2. Build new image (with authentication code)
3. Start services
4. Initialize database and auth
5. Show you the logs

### Option 2: Manual Commands

```bash
# Stop current containers
docker compose down

# Rebuild from scratch (no cache)
docker compose build --no-cache

# Start everything
docker compose up -d

# Watch the logs to see initialization
docker compose logs -f aoda-checker
```

### Option 3: Complete Reset (Fresh Start)

⚠️ **Warning**: This deletes ALL data including scans and users!

```bash
# Stop containers
docker compose down

# Remove database volume (deletes all data)
rm -rf ./mysql/*

# Rebuild and start
docker compose up -d --build

# Watch initialization
docker compose logs -f aoda-checker
```

---

## What Happens During Container Startup

### 1. MySQL Starts
```
⏳ Waiting for MySQL to be ready...
✅ MySQL is ready!
```

### 2. Database Tables Created
```
🔧 Initializing database tables...
Creating table: scans
Creating table: page_scans
Creating table: violations
✅ Database tables initialized successfully!
```

### 3. Authentication Initialized
```
🔐 Initializing authentication system...
Creating database tables...
Tables created successfully!

Creating default admin user...
==================================================
⚠️  IMPORTANT: Change this password after first login!
==================================================

✅ Default admin user created successfully!

   Username: admin
   Password: admin123

==================================================
⚠️  SECURITY WARNING:
   Please login and change the default password immediately!
   Go to: http://localhost:8080/login
==================================================

✅ Authentication system initialized successfully!
```

### 4. Application Starts
```
🚀 Starting AODA Checker Web Application...
✅ Application is running!
   Access at: http://localhost:8080
```

---

## Verifying Authentication Setup

### Check Container Logs

```bash
docker compose logs aoda-checker | grep -A 10 "Initializing authentication"
```

You should see:
```
🔐 Initializing authentication system...
✅ Default admin user created successfully!
   Username: admin
   Password: admin123
```

### Test Login

1. Open browser: **http://localhost:8080/login**
2. Login with `admin` / `admin123`
3. You should see the scan form with navigation

### Check Database

```bash
# Connect to MySQL container
docker compose exec mysql mysql -u aoda_user -paoda_password aoda_checker

# List tables
SHOW TABLES;
```

You should see:
```
+------------------------+
| Tables_in_aoda_checker |
+------------------------+
| page_scans            |
| scans                 |
| users                 |  <-- Authentication table
| violations            |
+------------------------+
```

### Check Users Table

```bash
# In MySQL shell
SELECT id, username, is_admin, created_at FROM users;
```

You should see:
```
+----+----------+----------+---------------------+
| id | username | is_admin | created_at          |
+----+----------+----------+---------------------+
|  1 | admin    |        1 | 2025-11-17 12:34:56 |
+----+----------+----------+---------------------+
```

---

## Environment Variables

### Setting a Secure Secret Key (Production)

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and set:
```bash
SECRET_KEY="your-super-secure-random-key-here"
```

Generate a secure key:
```bash
openssl rand -hex 32
```

### Using Custom Environment Variables

The `docker-compose.yml` reads from environment:
```yaml
environment:
  - SECRET_KEY=${SECRET_KEY:-change-this-secret-key-in-production}
  - JWT_EXPIRATION_MINUTES=${JWT_EXPIRATION_MINUTES:-480}
  - DATABASE_URL=mysql+aiomysql://aoda_user:aoda_password@mysql:3306/aoda_checker
```

Set them before starting:
```bash
export SECRET_KEY="my-secure-key"
export JWT_EXPIRATION_MINUTES=480
docker compose up -d --build
```

---

## Updating the Application

### Adding New Code

1. Make your code changes
2. Rebuild:
   ```bash
   docker compose up -d --build
   ```
3. Check logs:
   ```bash
   docker compose logs -f aoda-checker
   ```

### Updating Dependencies

1. Update `requirements.txt`
2. Rebuild (no cache):
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

### Database Migrations

If you change database schema:

1. Stop containers:
   ```bash
   docker compose down
   ```

2. Backup data (optional):
   ```bash
   docker compose exec mysql mysqldump -u aoda_user -paoda_password aoda_checker > backup.sql
   ```

3. Rebuild:
   ```bash
   docker compose up -d --build
   ```

---

## Troubleshooting

### Authentication Tables Not Created

Check logs:
```bash
docker compose logs aoda-checker | grep "auth"
```

If you see errors, manually initialize:
```bash
docker compose exec aoda-checker python3 init_auth.py
```

### Admin User Already Exists

If you see:
```
⚠️  Admin user already exists!
```

This is normal! The script detects existing admin and skips creation.

### Cannot Connect to Database

1. Check MySQL is running:
   ```bash
   docker compose ps
   ```

2. Check MySQL logs:
   ```bash
   docker compose logs mysql
   ```

3. Verify connection:
   ```bash
   docker compose exec aoda-checker python3 -c "
   import pymysql
   conn = pymysql.connect(
       host='mysql',
       user='aoda_user',
       password='aoda_password',
       database='aoda_checker'
   )
   print('✅ Connection successful!')
   conn.close()
   "
   ```

### Reset Everything

Complete reset (deletes ALL data):
```bash
docker compose down -v
rm -rf ./mysql/*
docker compose up -d --build
```

---

## Port Configuration

### Default Ports

- **Application**: http://localhost:8080
- **MySQL**: localhost:3306

### Changing Application Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8080"  # Access at http://localhost:9000
```

Then rebuild:
```bash
docker compose up -d --build
```

### Changing MySQL Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "3307:3306"  # MySQL on port 3307
```

---

## Production Deployment

### Security Checklist

Before deploying to production:

- [ ] Set secure `SECRET_KEY` in environment
- [ ] Change MySQL root password
- [ ] Change database user password
- [ ] Update `DATABASE_URL` in environment
- [ ] Enable HTTPS (reverse proxy recommended)
- [ ] Change admin password after first login
- [ ] Set up regular database backups
- [ ] Configure firewall rules
- [ ] Monitor logs for suspicious activity

### Recommended Setup

```bash
# Set secure environment variables
export SECRET_KEY="$(openssl rand -hex 32)"
export MYSQL_ROOT_PASSWORD="$(openssl rand -hex 16)"
export MYSQL_PASSWORD="$(openssl rand -hex 16)"

# Update docker-compose.yml with your passwords

# Build and start
docker compose up -d --build

# Check everything is running
docker compose ps

# View logs
docker compose logs -f
```

### Using Reverse Proxy (Nginx)

Create `nginx.conf`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Backup and Restore

### Backup Database

```bash
# Backup all data
docker compose exec mysql mysqldump -u aoda_user -paoda_password aoda_checker > backup_$(date +%Y%m%d).sql

# Backup just users
docker compose exec mysql mysqldump -u aoda_user -paoda_password aoda_checker users > users_backup.sql
```

### Restore Database

```bash
# Restore from backup
docker compose exec -T mysql mysql -u aoda_user -paoda_password aoda_checker < backup_20251117.sql
```

### Export User List

```bash
docker compose exec mysql mysql -u aoda_user -paoda_password aoda_checker -e "SELECT username, email, is_admin, created_at FROM users" > users.txt
```

---

## Summary

**When you rebuild the Docker container:**

✅ **All authentication code is included**  
✅ **Database tables are created automatically**  
✅ **Admin user is created automatically**  
✅ **Application is ready to use immediately**  

**Just run:**
```bash
docker compose up -d --build
```

**Then access:**
```
http://localhost:8080/login
Username: admin
Password: admin123
```

**Don't forget to change the admin password!**

---

## Quick Commands Reference

```bash
# Rebuild everything
docker compose up -d --build

# View logs
docker compose logs -f aoda-checker

# Check status
docker compose ps

# Stop everything
docker compose down

# Complete reset (deletes data!)
docker compose down -v && rm -rf ./mysql/* && docker compose up -d --build

# Access MySQL shell
docker compose exec mysql mysql -u aoda_user -paoda_password aoda_checker

# Manually run auth init
docker compose exec aoda-checker python3 init_auth.py

# View authentication logs
docker compose logs aoda-checker | grep -A 10 "authentication"
```

---

**Your authentication system is Docker-ready! Just rebuild and it works! 🚀**

