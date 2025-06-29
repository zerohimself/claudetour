#!/bin/bash
# Claude wrapper with unified session logging
# This captures full console output and correlates with interceptor logs

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

# Create timestamp function for consistent formatting
get_timestamp() {
    date -u +%Y-%m-%dT%H:%M:%S.%3NZ
}

# Log session start to both session file and main log
log_entry() {
    local entry="$1"
    echo "$entry" >> "$LOG_DIR/${SESSION_ID}.jsonl"
    echo "$entry" >> "$MAIN_LOG"
}

# Start session
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

log_entry "$START_ENTRY"

# Print info for user
echo "ClauDEtour wrapper active - Session: $SESSION_ID" >&2
echo "Logs: $LOG_DIR/${SESSION_ID}.*" >&2
echo "" >&2

# Run claude with output capture
if [ -t 1 ]; then
    # Interactive mode - use script to capture terminal output with timestamps
    # -f forces output flush, -t adds timing info
    script -q -f -t 2>"$LOG_DIR/${SESSION_ID}.timing" \
        -c "$CLAUDE_CMD $(printf '%q ' "$@")" \
        "$LOG_DIR/${SESSION_ID}.transcript"
    EXIT_CODE=$?
    
    # Clean the transcript automatically if cleaner exists
    CLEANER="$(dirname "$0")/clean-transcript.py"
    if [ -x "$CLEANER" ]; then
        echo "Cleaning transcript..." >&2
        "$CLEANER" "$LOG_DIR/${SESSION_ID}.transcript" "$LOG_DIR/${SESSION_ID}.log" >&2
    fi
else
    # Non-interactive - use tee
    # Capture both stdout and stderr
    { $CLAUDE_CMD "$@" 2>&1; echo $? > "$LOG_DIR/${SESSION_ID}.exitcode"; } | \
        tee -a "$LOG_DIR/${SESSION_ID}.transcript"
    EXIT_CODE=$(cat "$LOG_DIR/${SESSION_ID}.exitcode" 2>/dev/null || echo 1)
    rm -f "$LOG_DIR/${SESSION_ID}.exitcode"
fi

# End session
END_TIME=$(get_timestamp)
END_ENTRY=$(jq -n \
    --arg type "session_end" \
    --arg session_id "$SESSION_ID" \
    --arg ts "$END_TIME" \
    --argjson exit_code "$EXIT_CODE" \
    --arg start_time "$START_TIME" \
    --arg end_time "$END_TIME" \
    '{type: $type, session_id: $session_id, ts: $ts, exit_code: $exit_code, start_time: $start_time, end_time: $end_time}')

log_entry "$END_ENTRY"

# Create session summary
SUMMARY=$(jq -n \
    --arg session_id "$SESSION_ID" \
    --arg transcript "$LOG_DIR/${SESSION_ID}.transcript" \
    --arg session_log "$LOG_DIR/${SESSION_ID}.jsonl" \
    --arg main_log "$MAIN_LOG" \
    --argjson exit_code "$EXIT_CODE" \
    '{session_id: $session_id, transcript: $transcript, session_log: $session_log, main_log: $main_log, exit_code: $exit_code}')

echo "" >&2
echo "Session complete. Summary:" >&2
echo "$SUMMARY" | jq . >&2

exit $EXIT_CODE