#!/bin/bash
# Docker Build Troubleshooting Script

echo "================================================"
echo "Docker Build Troubleshooting"
echo "================================================"
echo ""

# Solution 1: Restart Docker daemon
echo "Solution 1: Restarting Docker daemon..."
sudo systemctl restart docker
if [ $? -eq 0 ]; then
    echo "✓ Docker daemon restarted"
else
    echo "✗ Failed to restart Docker daemon (may need sudo)"
fi

echo ""
echo "Waiting 5 seconds for Docker to stabilize..."
sleep 5

# Solution 2: Try to pull the base image directly
echo ""
echo "Solution 2: Testing if we can pull ubuntu:22.04..."
docker pull ubuntu:22.04 2>&1 | tail -5

# Solution 3: Configure Docker DNS
echo ""
echo "Solution 3: Checking Docker DNS configuration..."
if [ -f /etc/docker/daemon.json ]; then
    echo "Current Docker daemon.json:"
    cat /etc/docker/daemon.json
else
    echo "No /etc/docker/daemon.json found"
fi

echo ""
echo "================================================"
echo "Alternative Solutions:"
echo "================================================"
echo ""
echo "If the above didn't work, try these manual steps:"
echo ""
echo "1. Configure Docker DNS (create /etc/docker/daemon.json):"
echo '   sudo nano /etc/docker/daemon.json'
echo '   Add:'
echo '   {'
echo '     "dns": ["8.8.8.8", "8.8.4.4"]'
echo '   }'
echo '   Then: sudo systemctl restart docker'
echo ""
echo "2. Check if you have network connectivity:"
echo '   ping -c 3 8.8.8.8'
echo ""
echo "3. If behind a proxy, configure Docker proxy:"
echo '   sudo mkdir -p /etc/systemd/system/docker.service.d'
echo '   sudo nano /etc/systemd/system/docker.service.d/http-proxy.conf'
echo ""
echo "4. Try building with --network=host:"
echo '   docker-compose build --network=host'
echo ""
echo "5. Check firewall settings:"
echo '   sudo ufw status'
echo ""

