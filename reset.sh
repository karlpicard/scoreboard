#!/usr/bin/env bash
# reset.sh - wipe database, logs, caches, and restart the scoreboard server
#
# This helper shell script performs a full reset of the scoreboard
# environment. It kills any running server on the designated port,
# removes the SQLite database (score.db) and the JSON change log
# (changes.log), clears compiled Python bytecode and any temporary
# session/cache directories, then starts a fresh instance of the
# Flask/SocketIO app.  Useful for development or to recover from
# a corrupted state.
#
# Usage:
#     ./reset.sh          # default port 6050
#     ./reset.sh 5001     # choose alternate port
#

PORT=${1:-6050}

# kill any server listening on the port
pids=$(lsof -ti tcp:${PORT})
if [ -n "$pids" ]; then
    echo "killing existing server process(es) on port $PORT: $pids"
    kill -9 $pids 2>/dev/null || true
fi

# remove database and log files
rm -f score.db changes.log

# clear python bytecode caches and any other temporary cache directories
find . -type d -name "__pycache__" -print0 | xargs -0 rm -rf 2>/dev/null

echo "cleared __pycache__ directories"

# remove any session or temp folders that might be created by the app
for d in tmp session cache; do
    if [ -d "$d" ]; then
        echo "removing directory $d"
        rm -rf "$d"
    fi
done

# remove stray .pyc files
find . -type f -name "*.pyc" -print0 | xargs -0 rm -f 2>/dev/null
echo "cleared pyc files and temp/session directories"
echo "starting server on port $PORT"
python app.py --port $PORT &

echo "Server started (PID $!)"