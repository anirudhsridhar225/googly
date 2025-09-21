#!/bin/bash

# Render Start Script for Legal Document Severity Classification System

echo "Starting Legal Document Severity Classification System on Render..."

# Set production environment variables
export ENVIRONMENT="production"
export DEBUG="false"

# Use PORT environment variable provided by Render
if [ -z "$PORT" ]; then
    export PORT=8000
fi

echo "Starting server on port $PORT..."

# Start the FastAPI application with uvicorn
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers ${WORKERS:-2}