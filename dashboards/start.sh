#!/bin/bash

# TheRock Issue Analysis Dashboard Startup Script

set -e

echo "=================================="
echo "TheRock Issue Analysis Dashboard"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: Please run this script from the dashboards/ directory"
    exit 1
fi

# Check for .env file
if [ ! -f "backend/.env" ]; then
    echo "Error: backend/.env file not found!"
    echo "Please copy backend/.env.example to backend/.env and configure it."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Install backend dependencies if needed
echo "Checking backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "Starting backend API on http://localhost:8000..."
echo ""

# Start the backend
python app.py &
BACKEND_PID=$!

echo "Backend started (PID: $BACKEND_PID)"
echo ""

# Wait a moment for backend to start
sleep 3

# Start the frontend
cd ../frontend
echo "Starting frontend on http://localhost:3000..."
echo ""
python3 -m http.server 3000 &
FRONTEND_PID=$!

echo "Frontend started (PID: $FRONTEND_PID)"
echo ""
echo "=================================="
echo "Dashboard is ready!"
echo "=================================="
echo ""
echo "🌐 Open your browser and navigate to:"
echo "   http://localhost:3000"
echo ""
echo "📡 API is available at:"
echo "   http://localhost:8000"
echo "   http://localhost:8000/docs (Swagger UI)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

wait
