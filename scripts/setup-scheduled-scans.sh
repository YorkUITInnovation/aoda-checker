#!/bin/bash
# Quick setup script for scheduled scans feature

echo "================================================"
echo "Scheduled Scans Feature - Setup Script"
echo "================================================"

# Step 1: Run database migration
echo ""
echo "Step 1: Running database migration..."
docker-compose exec -T web python scripts/add_scheduled_scans_table.py

if [ $? -eq 0 ]; then
    echo "✓ Database migration completed successfully"
else
    echo "✗ Database migration failed"
    exit 1
fi

# Step 2: Check if email settings are configured
echo ""
echo "Step 2: Checking email configuration..."
if docker-compose exec -T web printenv | grep -q "SMTP_HOST"; then
    echo "✓ SMTP_HOST is configured"
else
    echo "⚠ SMTP_HOST not configured - emails will not be sent"
    echo "  Add email settings to your docker-compose.yml or .env file"
fi

# Step 3: Restart application to load scheduler
echo ""
echo "Step 3: Restarting application to initialize scheduler..."
docker-compose restart web

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Navigate to your application's /history page"
echo "2. Click the 'Schedule' button on any scan"
echo "3. Configure your scheduled scan settings"
echo "4. Submit to create your first scheduled scan"
echo ""
echo "To configure email notifications:"
echo "Add these environment variables to docker-compose.yml:"
echo "  SMTP_HOST=smtp.gmail.com"
echo "  SMTP_PORT=587"
echo "  SMTP_USERNAME=your-email@example.com"
echo "  SMTP_PASSWORD=your-app-password"
echo "  SMTP_USE_TLS=true"
echo "  SMTP_FROM_EMAIL=noreply@example.com"
echo "  SMTP_FROM_NAME=AODA Checker"
echo ""
echo "Then restart: docker-compose restart web"
echo ""

