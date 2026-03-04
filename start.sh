#!/bin/bash
# ═══════════════════════════════════════════════════════
# 🐙 Octopus AI — Start Script
# Launches both the backend API and frontend dev server
# ═══════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  🐙  Octopus AI — Starting..."
echo "  ═══════════════════════════════"
echo ""

# ── Check Python ──────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python 3 is required but not installed."
    exit 1
fi

# ── Setup virtual environment if needed ───────────────
if [ ! -d "venv" ]; then
    echo "  📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# ── Install dependencies ─────────────────────────────
echo "  📦 Installing Python dependencies..."
pip install -q -r backend/requirements.txt

# ── Copy .env if not exists ───────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  📝 Created .env file — please add your API keys!"
fi

# ── Start Backend ─────────────────────────────────────
echo "  🚀 Starting backend on http://localhost:8000"
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# ── Start Frontend ────────────────────────────────────
echo "  🎨 Starting frontend on http://localhost:5500"
cd frontend
python3 -m http.server 5500 &
FRONTEND_PID=$!
cd ..

echo ""
echo "  ═══════════════════════════════════════════════"
echo "  🐙 Octopus AI is running!"
echo "  "
echo "  🎨 Frontend: http://localhost:5500"
echo "  ⚙️  Backend:  http://localhost:8000"
echo "  📖 API Docs: http://localhost:8000/docs"
echo "  "
echo "  Press Ctrl+C to stop all services"
echo "  ═══════════════════════════════════════════════"
echo ""

# ── Trap SIGINT to kill both processes ────────────────
cleanup() {
    echo ""
    echo "  🐙 Shutting down Octopus AI..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo "  👋 Goodbye!"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
