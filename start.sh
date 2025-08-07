#!/bin/bash

# Print colorful messages
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting GOG Repo Manager...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}🔄 Activating virtual environment...${NC}"
source venv/bin/activate

# Install Python requirements
echo -e "${BLUE}📥 Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Install npm dependencies and build the UI
echo -e "${BLUE}🌐 Setting up web interface...${NC}"
cd ui
npm install
npm run build
cd ..

# Start both servers
echo -e "${GREEN}✨ Starting servers...${NC}"
echo -e "${GREEN}🔗 Web interface will be available at: http://localhost:3000${NC}"

# Start the Python server in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Start the UI server
cd ui && python -m http.server 3000 --directory build &
UI_PID=$!

# Handle script termination
trap "kill $UVICORN_PID $UI_PID" SIGINT SIGTERM EXIT

# Keep the script running
wait
