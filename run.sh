#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "========================================="
echo " Starting Job Hunt Assistant & Scraper "
echo "========================================="

# Determine the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Ensure venv is set up
if [ ! -d "venv" ]; then
    echo "Creating python virtual environment..."
    python3 -m venv venv
    echo "Installing required backend dependencies..."
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r backend/requirements.txt
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Launch uvicorn web server
echo "Starting web server on http://localhost:8000 ..."
echo "Press Ctrl+C to terminate the application."
echo "========================================="

python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
