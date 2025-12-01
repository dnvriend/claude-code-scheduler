#!/usr/bin/env bash
# Run claude-code-scheduler GUI with verbose logging
# Logs are written to ./logs/scheduler.log

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scheduler.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Rotate log if it exists and is large
if [[ -f "$LOG_FILE" && $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 1048576 ]]; then
    mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d-%H%M%S).bak"
fi

echo "Starting claude-code-scheduler GUI with TRACE logging..."
echo "Log file: $LOG_FILE"
echo "Use 'tail -f $LOG_FILE' to follow logs"
echo ""

cd "$PROJECT_DIR"
claude-code-scheduler gui -vvv 2>&1 | tee "$LOG_FILE"
