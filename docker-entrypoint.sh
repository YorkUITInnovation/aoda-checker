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

# Start the application
echo "🚀 Starting AODA Compliance Checker..."
exec python main.py web --port 8080 --host 0.0.0.0

