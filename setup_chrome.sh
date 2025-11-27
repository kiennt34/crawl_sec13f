#!/bin/bash
# Setup script for Chrome/Chromium and ChromeDriver for IAPD zip extraction

set -e

echo "Setting up Chrome/Chromium and ChromeDriver for Selenium..."

# Check if running on Ubuntu/Debian
if [ -f /etc/debian_version ]; then
    echo "Detected Debian/Ubuntu system"
    
    # Update package list
    echo "Updating package list..."
    sudo apt-get update
    
    # Install Chromium and ChromeDriver
    echo "Installing Chromium browser and ChromeDriver..."
    sudo apt-get install -y chromium-browser chromium-chromedriver
    
    # Verify installation
    echo ""
    echo "Verifying installation..."
    if command -v chromium-browser &> /dev/null; then
        echo "✓ Chromium installed: $(chromium-browser --version)"
    else
        echo "✗ Chromium not found"
    fi
    
    if command -v chromedriver &> /dev/null; then
        echo "✓ ChromeDriver installed: $(chromedriver --version)"
    else
        echo "✗ ChromeDriver not found"
    fi
    
elif [ -f /etc/redhat-release ]; then
    echo "Detected RedHat/CentOS system"
    echo "Please install Chrome manually from: https://www.google.com/chrome/"
    echo "And ChromeDriver from: https://chromedriver.chromium.org/downloads"
else
    echo "Unknown Linux distribution"
    echo "Please install Chrome/Chromium and ChromeDriver manually"
fi

echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "You can now run: python extract_iapd_zip.py"

