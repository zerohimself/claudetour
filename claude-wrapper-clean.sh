#!/bin/bash
# Claude wrapper with CLEAN transcript logging (no ANSI escape codes)

# Get the actual claude command path
CLAUDE_CMD=$(which claude)
if [ -z "$CLAUDE_CMD" ]; then
    echo "Error: claude command not found in PATH" >&2
    exit 1
fi

# Generate session ID (PID_timestamp)
SESSION_ID="$$_$(date +%s)"
export CLAUDETOUR_SESSION_ID="$SESSION_ID"

# Log directory
LOG_DIR="$HOME/.claude_tour/sessions"
MAIN_LOG="$HOME/.claude_tour/log.jsonl"
mkdir -p "$LOG_DIR"

# Create timestamp function
get_timestamp() {
    date -u +%Y-%m-%dT%H:%M:%S.%3NZ
}

# Log session start
START_TIME=$(get_timestamp)
START_ENTRY=$(jq -n \
    --arg type "session_start" \
    --arg session_id "$SESSION_ID" \
    --arg ts "$START_TIME" \
    --arg cmd "$CLAUDE_CMD" \
    --argjson args "$(printf '%s\n' "$@" | jq -R . | jq -s .)" \
    --arg pwd "$PWD" \
    --arg user "$USER" \
    --arg hostname "$(hostname)" \
    '{type: $type, session_id: $session_id, ts: $ts, cmd: $cmd, args: $args, pwd: $pwd, user: $user, hostname: $hostname}')

echo "$START_ENTRY" >> "$LOG_DIR/${SESSION_ID}.jsonl"
echo "$START_ENTRY" >> "$MAIN_LOG"

# Print info
echo "ClauDEtour wrapper active - Session: $SESSION_ID" >&2
echo "Clean logs: $LOG_DIR/${SESSION_ID}.log" >&2
echo "" >&2

# Function to clean ANSI codes and control characters
clean_output() {
    # Remove ANSI escape sequences
    # Also remove carriage returns and other control chars
    # But keep newlines and tabs
    sed -E 's/\x1b\[[0-9;]*[mGKHJF]//g' | \
    sed 's/\r//g' | \
    sed 's/\x1b\[[0-9;]*[A-Za-z]//g' | \
    sed 's/\x1b\]0;[^\x07]*\x07//g' | \
    sed 's/\x1b[>=]//g' | \
    tr -d '\000-\010\013-\014\016-\037' | \
    cat -v | sed 's/\^M//g'
}

# Run claude with output capture and cleaning
if [ -t 1 ]; then
    # Interactive mode - use script but pipe through cleaner
    # Create a named pipe for real-time cleaning
    PIPE_DIR="/tmp/claudetour_$$"
    mkdir -p "$PIPE_DIR"
    PIPE="$PIPE_DIR/pipe"
    mkfifo "$PIPE"
    
    # Start the cleaner in background
    clean_output < "$PIPE" > "$LOG_DIR/${SESSION_ID}.log" &
    CLEANER_PID=$!
    
    # Also save raw version for debugging
    script -q -f -c "$CLAUDE_CMD $(printf '%q ' "$@")" "$PIPE"
    EXIT_CODE=$?
    
    # Cleanup
    wait $CLEANER_PID
    rm -rf "$PIPE_DIR"
else
    # Non-interactive - simpler approach
    $CLAUDE_CMD "$@" 2>&1 | tee >(clean_output > "$LOG_DIR/${SESSION_ID}.log")
    EXIT_CODE=${PIPESTATUS[0]}
fi

# End session
END_TIME=$(get_timestamp)
END_ENTRY=$(jq -n \
    --arg type "session_end" \
    --arg session_id "$SESSION_ID" \
    --arg ts "$END_TIME" \
    --argjson exit_code "$EXIT_CODE" \
    '{type: $type, session_id: $session_id, ts: $ts, exit_code: $exit_code}')

echo "$END_ENTRY" >> "$LOG_DIR/${SESSION_ID}.jsonl"
echo "$END_ENTRY" >> "$MAIN_LOG"

echo "" >&2
echo "Session complete. Clean log: $LOG_DIR/${SESSION_ID}.log" >&2

exit $EXIT_CODE