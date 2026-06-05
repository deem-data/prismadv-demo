#!/bin/bash
# Start PrismaDV Demo - Frontend & Backend

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting PrismaDV Demo...${NC}"

# Trap to cleanup on exit
cleanup() {
    echo -e "\n${RED}🛑 Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✅ Servers stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}📦 Starting Backend (port 8000)...${NC}"
uv run uvicorn prismadv.api.v1.app:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo -e "${GREEN}🎨 Starting Frontend...${NC}"
npm --prefix frontend run dev &
FRONTEND_PID=$!

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Both servers started!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Backend:  ${GREEN}http://localhost:8000${NC}"
echo -e "Frontend: ${GREEN}http://localhost:3000${NC}"
echo -e "API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "\nPress ${RED}Ctrl+C${NC} to stop both servers"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
