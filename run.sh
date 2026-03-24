#!/bin/bash

USB_DIR="$(cd "$(dirname "$0")" && pwd)"

export OLLAMA_MODELS="$USB_DIR/models"
export OLLAMA_HOME="$USB_DIR/.ollama"
export PATH="$USB_DIR/bin/linux:$PATH"

echo "==============================="
echo "   Alfred"
echo "   Running on Linux"
echo "==============================="

chmod +x "$USB_DIR/bin/linux/ollama"

echo "Starting server..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

sleep 4

ollama list | grep -q "qwen-coder" || \
    ollama create qwen-coder -f "$USB_DIR/Modelfile"

echo "Starting UI server..."
(
    cd "$USB_DIR/ui" || exit
    python3 -m http.server 8080 > /tmp/ui.log 2>&1
) &
UI_PID=$!

echo "Starting mode server..."
python3 "$USB_DIR/mode-server.py" > /tmp/mode.log 2>&1 &
MODE_PID=$!

sleep 1

xdg-open "http://localhost:8080/index.html" 2>/dev/null

echo ""
echo "Alfred is ready at http://localhost:8080"
echo "Press Ctrl+C to shut everything down."

trap '
echo "Shutting down..."
pkill -f ollama
pkill -f "python3 -m http.server"
kill $MODE_PID 2>/dev/null
' EXIT INT TERM

wait $OLLAMA_PID