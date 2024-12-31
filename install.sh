#!/bin/bash

echo "=== Installation Setup ==="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "Checking Python version..."
if ! command_exists python3; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

python_version=$(python3 --version | cut -d' ' -f2)
echo "Found Python version: $python_version"

# Create virtual environment
echo -e "\n=== Creating Virtual Environment ==="
if [ -d "venv" ]; then
    echo "Found existing venv, removing..."
    rm -rf venv
fi

echo "Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n=== Upgrading pip ==="
python3 -m pip install --upgrade pip

# Install requirements
echo -e "\n=== Installing Requirements ==="
pip install -r requirements.txt

# Install playwright browsers
echo -e "\n=== Installing Playwright Browsers ==="
playwright install

# Check if credentials file exists
echo -e "\n=== Checking Configuration ==="
if [ ! -f "credentials.json" ] && [ -f "rename_to_credentials.json" ]; then
    echo "Creating credentials.json template..."
    cp rename_to_credentials.json credentials.json
    echo "Please edit credentials.json with your login details"
fi

echo -e "\n=== Installation Complete ==="
echo "You can now run the application with: . ./start.sh"

# Deactivate virtual environment
deactivate
