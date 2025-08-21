#!/bin/bash

# Start the FastAPI server in the background
echo "Starting FastAPI server..."
uvicorn fastapi_app:app --reload &
FASTAPI_PID=$!

# Give the server a moment to start
sleep 3

# Run the API tests
echo -e "\nRunning API tests..."
python test_api_endpoints.py

# Keep the server running in the foreground
echo -e "\nFastAPI server is running at http://localhost:8000"
echo "Press Ctrl+C to stop the server"

# Wait for the server to be stopped
wait $FASTAPI_PID
