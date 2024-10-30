#!/bin/bash
# server.sh

function stop_server() {
    echo "Stopping FastAPI server..."
    pid=$(lsof -t -i:8000)
    if [ ! -z "$pid" ]; then
        kill -9 $pid
        echo "Server stopped (PID: $pid)"
    else
        echo "No server running on port 8000"
    fi
}

function start_server() {
    echo "Starting FastAPI server..."
    uvicorn main:app --reload --port 8000
}

function restart_server() {
    stop_server
    sleep 2
    start_server
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac