#!/bin/bash
# Docker Build Validation Script
# This script checks all Docker-related files for common issues

set -e

echo "🔍 Docker Build Validation Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

errors=0
warnings=0

# Check 1: Dockerfile exists
echo "📄 Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    echo -e "${GREEN}✓${NC} Dockerfile exists"
else
    echo -e "${RED}✗${NC} Dockerfile not found"
    errors=$((errors + 1))
fi

# Check 2: docker-compose.yml exists and is valid
echo "📄 Checking docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml exists"
    if docker compose config --quiet 2>/dev/null; then
        echo -e "${GREEN}✓${NC} docker-compose.yml syntax is valid"
    else
        echo -e "${RED}✗${NC} docker-compose.yml has syntax errors"
        errors=$((errors + 1))
    fi
else
    echo -e "${RED}✗${NC} docker-compose.yml not found"
    errors=$((errors + 1))
fi

# Check 3: requirements.txt exists
echo "📄 Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt exists"
    echo -e "   $(wc -l < requirements.txt) dependencies listed"
else
    echo -e "${RED}✗${NC} requirements.txt not found"
    errors=$((errors + 1))
fi

# Check 4: docker-entrypoint.sh exists and is valid
echo "📄 Checking docker-entrypoint.sh..."
if [ -f "docker-entrypoint.sh" ]; then
    echo -e "${GREEN}✓${NC} docker-entrypoint.sh exists"
    if bash -n docker-entrypoint.sh 2>/dev/null; then
        echo -e "${GREEN}✓${NC} docker-entrypoint.sh syntax is valid"
    else
        echo -e "${RED}✗${NC} docker-entrypoint.sh has syntax errors"
        errors=$((errors + 1))
    fi
    if [ -x "docker-entrypoint.sh" ]; then
        echo -e "${YELLOW}⚠${NC} docker-entrypoint.sh is executable (will be set in Dockerfile)"
        warnings=$((warnings + 1))
    fi
else
    echo -e "${RED}✗${NC} docker-entrypoint.sh not found"
    errors=$((errors + 1))
fi

# Check 5: Required directories exist
echo "📁 Checking required directories..."
required_dirs=("src" "scripts" "templates" "static")
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} Directory '$dir' exists"
    else
        echo -e "${RED}✗${NC} Directory '$dir' not found"
        errors=$((errors + 1))
    fi
done

# Check 6: Required Python files exist
echo "🐍 Checking required Python files..."
required_files=(
    "main.py"
    "src/__init__.py"
    "src/config.py"
    "src/web/app.py"
    "src/database/session.py"
    "src/database/models.py"
    "scripts/init_db.py"
)
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} File '$file' exists"
    else
        echo -e "${RED}✗${NC} File '$file' not found"
        errors=$((errors + 1))
    fi
done

# Check 7: .dockerignore exists
echo "📄 Checking .dockerignore..."
if [ -f ".dockerignore" ]; then
    echo -e "${GREEN}✓${NC} .dockerignore exists"
else
    echo -e "${YELLOW}⚠${NC} .dockerignore not found (recommended for faster builds)"
    warnings=$((warnings + 1))
fi

# Check 8: Database initialization script exists
echo "🗄️ Checking database setup..."
if [ -f "scripts/create_database.sql" ]; then
    echo -e "${GREEN}✓${NC} Database SQL script exists"
else
    echo -e "${YELLOW}⚠${NC} scripts/create_database.sql not found"
    warnings=$((warnings + 1))
fi

# Summary
echo ""
echo "=================================="
echo "📊 Validation Summary"
echo "=================================="
if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "Your Docker setup is ready to build."
    exit 0
elif [ $errors -eq 0 ]; then
    echo -e "${YELLOW}⚠ $warnings warning(s) found${NC}"
    echo "Your Docker setup should work, but there are some recommendations."
    exit 0
else
    echo -e "${RED}✗ $errors error(s) and $warnings warning(s) found${NC}"
    echo "Please fix the errors before building."
    exit 1
fi

