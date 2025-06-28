#!/bin/bash
# Claude wrapper with unified session logging

# Get the actual claude command path
CLAUDE_CMD=$(which claude)

# Generate session ID (PID_timestamp)
SESSION_ID="$$_$(date +%s)"
export CLAUDETOUR_SESSION_ID="$SESSION_ID"

# Log directory
LOG_DIR="$HOME/.claude_tour/sessions"
mkdir -p "$LOG_DIR"

# Start session log
echo "{\"type\": \"session_start\", \"session_id\": \"$SESSION_ID\", \"ts\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\", \"args\": $(printf '%s\n' "$@" | jq -R . | jq -s .)}" >> "$LOG_DIR/${SESSION_ID}.jsonl"

# Run claude with output capture
if [ -t 1 ]; then
    # Interactive mode - use script to capture terminal output
    script -q -c "$CLAUDE_CMD $*" "$LOG_DIR/${SESSION_ID}.transcript"
    EXIT_CODE=$?
else
    # Non-interactive - use tee
    $CLAUDE_CMD "$@" 2>&1 | tee -a "$LOG_DIR/${SESSION_ID}.transcript"
    EXIT_CODE=${PIPESTATUS[0]}
fi

# End session log
echo "{\"type\": \"session_end\", \"session_id\": \"$SESSION_ID\", \"ts\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\", \"exit_code\": $EXIT_CODE}" >> "$LOG_DIR/${SESSION_ID}.jsonl"

# Also log to main file for backwards compatibility
echo "{\"type\": \"session_end\", \"session_id\": \"$SESSION_ID\", \"ts\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\", \"exit_code\": $EXIT_CODE}" >> "$HOME/.claude_tour/log.jsonl"

exit $EXIT_CODE