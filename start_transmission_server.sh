#!/bin/bash

# Transmission MCP Server Startup Script
# Change to the directory where this script is located
cd "$(dirname "$0")"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Start the MCP server
python transmission_server.py
