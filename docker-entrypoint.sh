#!/bin/bash
# Wait for MySQL to be ready and initialize database tables

set -e

echo "⏳ Waiting for MySQL to be ready..."

# Wait for MySQL to be ready
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python3 -c "
import pymysql
import sys
try:
    conn = pymysql.connect(
        host='mysql',
        user='aoda_user',
        password='aoda_password',
        database='aoda_checker',
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Connection attempt failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ MySQL is ready!"
        break
    fi

    attempt=$((attempt + 1))
    echo "Attempt $attempt/$max_attempts - MySQL not ready yet, waiting..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ MySQL did not become ready in time"
    exit 1
fi

# Initialize database tables
echo "🔧 Initializing database tables..."
python3 scripts/init_db.py

if [ $? -eq 0 ]; then
    echo "✅ Database tables initialized successfully!"
else
    echo "⚠️  Database table initialization failed, but continuing..."
fi

# Initialize authentication system and create admin user
echo "🔐 Initializing authentication system..."
if python3 init_auth.py 2>&1 | tee /tmp/init_auth.log; then
    echo "✅ Authentication system initialized successfully!"
    # Check if admin was created or already exists
    if grep -q "Admin user already exists" /tmp/init_auth.log; then
        echo "   ℹ️  Admin user already exists, skipping creation"
    else
        echo "   Default admin credentials:"
        echo "   Username: admin"
        echo "   Password: admin123"
        echo "   ⚠️  Please change the password after first login!"
    fi
else
    exit_code=$?
    echo "⚠️  Authentication initialization encountered an issue (exit code: $exit_code)"
    # Check if it's just because admin already exists
    if grep -q "Admin user already exists" /tmp/init_auth.log || grep -q "Duplicate entry" /tmp/init_auth.log; then
        echo "   ℹ️  Admin user already exists, continuing..."
    else
        echo "   ⚠️  There may be an issue, but continuing to start the application..."
        echo "   Check logs above for details"
    fi
fi

# Run database migration to add user_id to scans table
echo "🔄 Running database migrations..."
if python3 migrate_add_user_id.py 2>&1 | tee /tmp/migrate.log; then
    echo "✅ Database migrations completed successfully!"
else
    exit_code=$?
    echo "⚠️  Migration encountered an issue (exit code: $exit_code)"
    # Check if it's just because column already exists
    if grep -q "already exists" /tmp/migrate.log; then
        echo "   ℹ️  Migration already applied, continuing..."
    else
        echo "   ⚠️  There may be an issue, but continuing to start the application..."
    fi
fi

# Start the application
echo "🚀 Starting AODA Compliance Checker..."
exec python main.py web --port 8080 --host 0.0.0.0

