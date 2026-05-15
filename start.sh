#!/bin/bash

echo "========================================="
echo "  LLM Council Local Startup"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: run this from the project directory"
    exit 1
fi

PYTHON_BIN=$(command -v python3 || command -v python)
if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python is not installed"
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm is not installed"
    exit 1
fi

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

if check_port 8000; then
    echo "Backend already running on port 8000"
else
    echo "Starting backend on port 8000..."
    cd backend
    "$PYTHON_BIN" main.py &
    BACKEND_PID=$!
    cd ..
    echo "Backend started (PID: $BACKEND_PID)"
fi

echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Backend failed to start"
        exit 1
    fi
    sleep 1
done

if check_port 3000; then
    echo "Frontend already running on port 3000"
else
    echo "Starting frontend on port 3000..."
    cd frontend
    if [ ! -x "node_modules/.bin/next" ]; then
        echo "Installing frontend dependencies..."
        npm install || {
            echo "Frontend dependency install failed"
            exit 1
        }
    fi
    npm run dev &
    FRONTEND_PID=$!
    cd ..
    echo "Frontend started (PID: $FRONTEND_PID)"
fi

echo ""
echo "========================================="
echo "  LLM Council is running!"
echo "========================================="
echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
