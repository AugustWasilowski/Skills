#!/usr/bin/env bash
# Scratch launcher (Leo): start MACU Studio detached so it survives a Claude session restart.
set -e
cd /mnt/f/MACU/macu-pipeline/studio
export MACU_STUDIO_HOST=0.0.0.0
export MACU_STUDIO_PORT=8774
LOG=/tmp/macu-studio.log
: > "$LOG"
nohup setsid .venv/bin/uvicorn macu_studio.main:app --host 0.0.0.0 --port 8774 >"$LOG" 2>&1 < /dev/null &
echo "launched pid $!"
