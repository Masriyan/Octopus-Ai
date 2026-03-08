#!/bin/bash
uvicorn main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!
echo "Server started with PID $SERVER_PID"
sleep 5 # wait for server to bind

python tests/e2e_test.py

echo "Killing server..."
kill $SERVER_PID
