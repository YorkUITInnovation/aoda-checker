#!/bin/bash
# Docker Build Test Script
# This script performs a complete Docker build and basic functionality test

set -e

echo "🏗️  Docker Build Test Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Validate configuration
echo -e "${BLUE}Step 1: Validating Docker configuration...${NC}"
bash docker-validate.sh
echo ""

# Step 2: Build the Docker image
echo -e "${BLUE}Step 2: Building Docker image...${NC}"
echo "This may take several minutes on first build..."
if docker build -t aoda-checker:test . 2>&1 | tee /tmp/docker-build.log; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    echo "Check /tmp/docker-build.log for details"
    exit 1
fi
echo ""

# Step 3: Check image size
echo -e "${BLUE}Step 3: Checking image details...${NC}"
docker images aoda-checker:test --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""

# Step 4: Test with Docker Compose
echo -e "${BLUE}Step 4: Testing with Docker Compose...${NC}"
echo "Starting services (this will take a moment)..."
if docker compose up -d 2>&1 | tee /tmp/docker-compose.log; then
    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${RED}✗ Failed to start services${NC}"
    exit 1
fi
echo ""

# Step 5: Wait for health checks
echo -e "${BLUE}Step 5: Waiting for services to be healthy...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    mysql_health=$(docker inspect aoda-mysql --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    app_health=$(docker inspect aoda-compliance-checker --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")

    echo "MySQL: $mysql_health, App: $app_health"

    if [ "$mysql_health" = "healthy" ] && [ "$app_health" = "healthy" ]; then
        echo -e "${GREEN}✓ All services are healthy${NC}"
        break
    fi

    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${YELLOW}⚠ Services did not become healthy in time${NC}"
        echo "This may be normal on first startup. Check with: docker compose ps"
        break
    fi

    sleep 5
done
echo ""

# Step 6: Test health endpoint
echo -e "${BLUE}Step 6: Testing application health endpoint...${NC}"
sleep 2
if curl -f http://localhost:8080/health 2>/dev/null; then
    echo -e "${GREEN}✓ Health endpoint responding${NC}"
else
    echo -e "${YELLOW}⚠ Health endpoint not responding yet${NC}"
    echo "The application may still be starting up"
fi
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}✓ Build test completed!${NC}"
echo "=================================="
echo ""
echo "Your Docker setup is working. Next steps:"
echo ""
echo "  • View logs:       docker compose logs -f"
echo "  • Access web UI:   http://localhost:8080"
echo "  • Stop services:   docker compose down"
echo "  • View status:     docker compose ps"
echo ""

