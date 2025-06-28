#!/usr/bin/env python3
"""
ClauDEtour – a neural-ish bash interceptor for Claude

Features
• Regex passthrough for obviously-safe commands
• Automatic path / flag corrections (editable GUI)
• GUI falls back to TTY prompt when no $DISPLAY
• Auto-approve after N seconds to prevent tool time-outs
• JSON-lines log of every decision for later learning
• Drop-in replacement for `bash -lc "CMD"` as used by Claude Code
"""
import os, sys, json, re, shlex, time, threading, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

###############################################################################
# Config – edit here or export env-vars
###############################################################################
AUTO_APPROVE_SEC = int(os.getenv("CLAUDETOUR_AUTO", "0"))   # 0 = manual approval required
LOG_PATH         = Path(os.getenv("CLAUDETOUR_LOG",
                                   "~/.claude_tour/log.jsonl")).expanduser()
REAL_BASH        = os.getenv("CLAUDETOUR_REAL_BASH", "/usr/bin/bash")   # adjust if needed
GUI_ENABLED      = os.getenv("CLAUDETOUR_GUI", "1") == "1"

# Regexes that go straight through (fast path)
SAFE_PASSTHRU = [
    r"^\s*ls(\s|$)", r"^\s*pwd(\s|$)", r"^\s*echo(\s|$)",
    r"^\s*cat\s+[^\|;&]+$", r"^\s*which\s+\w+$", r"^\s*ps\s",
    r"^\s*grep\s", r"^\s*tail\s", r"^\s*head\s", r"^\s*export\s",
]

# Known 1-liners we always fix automatically (editable)
FIX_RULES = [
    # (pattern, replacement, description_for_log)
    (r"/mnt/c/Users/.+?/ml_research", "/home/zerohimself/src/ml_research",
     "Windows→Linux path canonicalisation"),
    (r"^o3-pro\b", "cd /home/zerohimself/src/ml_research && ./ask_tools/ask o3_pro",
     "o3-pro command correction with cd"),
    (r"^\./ask_tools/ask o3_pro ([^-])", r"./ask_tools/ask o3_pro -f \1",
     "o3_pro needs -f flag for files"),
    (r"(^|\s)python(\s+[^\s]+\.py\b)",
     r"\1python3\2", "python→python3"),
    (r"\bnohup\s+([^&]+)$", r"nohup \1 &",
     "forgotten ampersand after nohup"),
]

###############################################################################
# Utilities
###############################################################################
def log(decision: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as fh:
        fh.write(json.dumps(decision, ensure_ascii=False) + "\n")

def apply_fixes(cmd: str):
    fixed = cmd
    applied = []
    for pat, repl, note in FIX_RULES:
        new = re.sub(pat, repl, fixed)
        if new != fixed:
            applied.append(note)
            fixed = new
    return fixed, applied

def safe_passthrough(cmd: str):
    return any(re.search(pat, cmd) for pat in SAFE_PASSTHRU)

###############################################################################
# GUI helpers (Tkinter because it is baked into Python)
###############################################################################
def gui_ask(original: str, corrected: str, auto_sec: int):
    # headless?
    if not GUI_ENABLED or "DISPLAY" not in os.environ:
        return cli_ask(original, corrected, auto_sec)

    import tkinter as tk
    from tkinter import scrolledtext

    result = {"answer": "accept", "timer_active": True, "feedback": ""}  # default auto-answer
    def ok():     
        # Get the edited text and feedback
        edited = t2.get("1.0", "end-1c").strip()
        result["edited"] = edited
        result["feedback"] = feedback_text.get("1.0", "end-1c").strip()
        result["answer"] = "accept"
        result["timer_active"] = False
        root.destroy()
    def cancel(): 
        result["answer"] = "reject"
        result["feedback"] = feedback_text.get("1.0", "end-1c").strip()
        result["timer_active"] = False
        root.destroy()

    root = tk.Tk();  root.title("ClauDEtour – command correction")
    root.bell()  # BEEP!
    
    # Show original as read-only label
    tk.Label(root, text="Original command:").pack(anchor="w", padx=5, pady=(5,0))
    tk.Label(root, text=original, font=("monospace", 10), bg="#f0f0f0", relief="sunken", anchor="w").pack(fill="x", padx=5, pady=(0,10))
    
    # Editable text box with the correction
    tk.Label(root, text="Edit command (or accept suggestion):").pack(anchor="w", padx=5)
    t2 = scrolledtext.ScrolledText(root, height=3, width=80, font=("monospace", 10))
    t2.insert("1.0", corrected)
    t2.pack(padx=5, pady=5)
    t2.focus()  # Focus on the editable field
    
    # Select all text for easy replacement
    t2.tag_add("sel", "1.0", "end-1c")

    # Feedback field (optional)
    tk.Label(root, text="Feedback (optional):").pack(anchor="w", padx=5, pady=(10,0))
    feedback_text = scrolledtext.ScrolledText(root, height=2, width=80, font=("monospace", 9))
    feedback_text.pack(padx=5, pady=(0,5))

    bframe = tk.Frame(root); bframe.pack(pady=5)
    ok_text = "OK" if auto_sec == 0 else f"OK ({auto_sec})"
    ok_btn = tk.Button(bframe, text=ok_text, command=ok, bg="#4CAF50", fg="white", padx=20)
    ok_btn.pack(side="left", padx=5)
    tk.Button(bframe, text="Cancel", command=cancel, padx=20).pack(side="left", padx=5)
    
    # Allow Enter to submit (from command field only)
    t2.bind('<Return>', lambda e: ok())
    root.bind('<Escape>', lambda e: cancel())

    def countdown(sec):
        if not result["timer_active"] or sec <= 0:
            if result["timer_active"]:
                ok()
            return
        ok_btn.config(text=f"OK ({sec})")
        root.after(1000, countdown, sec-1)
    if auto_sec > 0:
        countdown(auto_sec)
    root.mainloop()

    # Return the result with feedback
    if result["answer"] == "reject":
        return original, "rejected", result["feedback"]
    else:
        # Return the edited text (which might be unchanged)
        edited = result.get("edited", corrected)
        mode = "edited" if edited != corrected else "accepted"
        return edited, mode, result["feedback"]

def cli_ask(original: str, corrected: str, auto_sec: int):
    """TTY fallback when no GUI available"""
    print("ClauDEtour suggestion:")
    print(" ─ original : ", original)
    print(" ─ corrected: ", corrected)
    prompt = "[Enter]=accept  e=edit  n=reject"
    if auto_sec > 0:
        prompt += f" (auto in {auto_sec}s)"
    print(f"{prompt} › ", end="", flush=True)

    def timer():
        time.sleep(auto_sec)
        try:
            # inject newline to stdin to auto-proceed
            import termios, fcntl
            fd = sys.stdin.fileno()
            fcntl.ioctl(fd, termios.TIOCSTI, b"\n")
        except Exception:
            pass
    if auto_sec > 0:
        threading.Thread(target=timer, daemon=True).start()

    choice = sys.stdin.readline().strip()
    if choice == "e":
        print("# Enter new command, end with EOF (Ctrl-D)")
        edited = sys.stdin.read()
        return edited.strip("\n"), "edited", ""
    if choice == "n":
        print("Why was this correction rejected? (optional, press Enter to skip): ", end="", flush=True)
        feedback = sys.stdin.readline().strip()
        return original, "rejected", feedback
    return corrected, "accepted", ""

###############################################################################
# Core
###############################################################################
def run_real_bash(cmdline: str, decision_id: str, session_id: str):
    """Run command and capture output for logging"""
    import subprocess
    from datetime import datetime, timezone
    
    start_time = datetime.now(timezone.utc)
    
    # Run command and capture output
    proc = subprocess.Popen(
        [REAL_BASH, "-lc", cmdline],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate()
    returncode = proc.returncode
    
    end_time = datetime.now(timezone.utc)
    duration_ms = int((end_time - start_time).total_seconds() * 1000)
    
    # Log execution result
    result = {
        "ts": end_time.isoformat().replace('+00:00', 'Z'),
        "type": "execution",
        "session_id": session_id,
        "decision_id": decision_id,
        "returncode": returncode,
        "duration_ms": duration_ms,
        "stdout_lines": len(stdout.splitlines()) if stdout else 0,
        "stderr_lines": len(stderr.splitlines()) if stderr else 0,
    }
    
    # Include actual output for errors or if there's important info
    if returncode != 0:
        result["stdout"] = stdout[:1000]  # First 1000 chars
        result["stderr"] = stderr[:1000]
    elif stderr:
        result["stderr"] = stderr[:500]  # Warnings/info
    
    log(result)
    
    # Print output as normal
    if stdout:
        print(stdout, end='')
    if stderr:
        print(stderr, end='', file=sys.stderr)
    
    return returncode

def get_claude_session_info():
    """Get Claude session PID and start time for correlation"""
    try:
        ppid = os.getppid()
        # Walk up process tree to find the main Claude process
        current_pid = ppid
        claude_pid = None
        
        for _ in range(5):  # Max 5 levels up
            cmdline_path = Path(f"/proc/{current_pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text()
                if "claude" in cmdline and "node" in cmdline:
                    claude_pid = current_pid
                    break
            # Get parent of current
            stat_path = Path(f"/proc/{current_pid}/stat")
            if stat_path.exists():
                stat_parts = stat_path.read_text().split()
                current_pid = int(stat_parts[3])  # ppid is 4th field
            else:
                break
        
        if claude_pid:
            # Get process start time for session identification
            stat_path = Path(f"/proc/{claude_pid}/stat")
            if stat_path.exists():
                stat_parts = stat_path.read_text().split(')')
                if len(stat_parts) > 1:
                    # Start time is field 22 after the command name
                    fields = stat_parts[1].split()
                    if len(fields) >= 20:
                        start_time = fields[19]
                        return claude_pid, start_time
        
        return ppid, "unknown"
    except:
        return os.getppid(), "unknown"

def main():
    # Check if we're being called by Claude
    try:
        # Get parent process info
        ppid = os.getppid()
        parent_cmd = Path(f"/proc/{ppid}/cmdline").read_text().split('\0')[0]
        is_claude = "claude" in parent_cmd or "node" in parent_cmd
    except:
        is_claude = False
    
    # If not called by Claude, just pass through to real bash
    if not is_claude:
        os.execv(REAL_BASH, [REAL_BASH] + sys.argv[1:])
        return
    
    # Get Claude session info - check env var first
    session_id = os.getenv("CLAUDETOUR_SESSION_ID")
    if not session_id:
        claude_pid, claude_start = get_claude_session_info()
        session_id = f"{claude_pid}_{claude_start}"
    
    # Debug: log what we received from Claude
    debug_decision = {
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "debug": True,
        "session_id": session_id,
        "argv": sys.argv,
        "parent": parent_cmd if 'parent_cmd' in locals() else "unknown"
    }
    log(debug_decision)
    
    # Handle Claude's calling pattern: bash -c -l "eval 'command'..."
    cmd = None
    
    # Claude passes: bash -c -l "eval 'actual command'..."
    # So argv looks like: ['bash', '-c', '-l', 'eval ...']
    if "-c" in sys.argv and "-l" in sys.argv:
        # Find the eval command (should be after -l)
        l_idx = sys.argv.index("-l")
        if l_idx + 1 < len(sys.argv):
            full_cmd = sys.argv[l_idx + 1]
            # Extract the actual command from the eval wrapper
            # Pattern: eval 'actual command' < /dev/null && pwd -P >| /tmp/...
            import re
            match = re.search(r"eval '([^']+)'", full_cmd)
            if match:
                cmd = match.group(1)
            else:
                cmd = full_cmd  # Fallback to full command
    
    # If no command detected, fall through to real bash
    if cmd is None:
        os.execv(REAL_BASH, [REAL_BASH] + sys.argv[1:])
        return

    # Generate unique decision ID for correlation
    import uuid
    decision_id = str(uuid.uuid4())[:8]
    
    decision = {
        "id": decision_id,
        "session_id": session_id,
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "type": "decision",
        "orig": cmd, "corr": None, "mode": None,
        "passthru": False, "fixes": [],
    }

    # Fast path
    if safe_passthrough(cmd):
        decision["passthru"] = True
        decision["corr"] = cmd
        log(decision)
        sys.exit(run_real_bash(cmd, decision_id, session_id))

    # Apply automatic rules
    corrected, fixes = apply_fixes(cmd)
    decision["fixes"] = fixes

    # If nothing changed, still ask?
    if corrected == cmd:
        # unknown / suspicious – ask anyway
        corrected, mode, feedback = gui_ask(cmd, cmd, AUTO_APPROVE_SEC)
        decision["corr"], decision["mode"] = corrected, mode
    else:
        corrected, mode, feedback = gui_ask(cmd, corrected, AUTO_APPROVE_SEC)
        decision["corr"], decision["mode"] = corrected, mode
    
    # Log feedback if provided (for both accept and reject)
    if feedback:
        decision["feedback"] = feedback

    log(decision)
    
    # If user rejected, print clear error message
    if mode == "rejected":
        print(f"\n⚠️ CLAUDETOUR INTERCEPTOR: User REJECTED command correction [ID: {decision_id}]", file=sys.stderr)
        print(f"   Original: {cmd}", file=sys.stderr)
        print(f"   Suggested: {corrected}", file=sys.stderr)
        print(f"   sys.argv: {sys.argv}", file=sys.stderr)
        print(f"   stdin.isatty: {sys.stdin.isatty()}", file=sys.stderr)
        if feedback:
            print(f"   User feedback: {feedback}", file=sys.stderr)
        print("   [EXECUTION BLOCKED BY USER]", file=sys.stderr)
        
        # Log rejection result
        log({
            "id": decision_id + "-result",
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "type": "execution",
            "session_id": session_id,
            "decision_id": decision_id,
            "returncode": 1,
            "status": "rejected"
        })
        sys.exit(1)
    
    # Show what happened with the command
    if mode == "edited":
        print(f"\n✏️  CLAUDETOUR: Command was EDITED by user [ID: {decision_id}]", file=sys.stderr)
        if feedback:
            print(f"   Feedback: {feedback}", file=sys.stderr)
    elif feedback:  # Only show if there's feedback, regardless of mode
        print(f"\n💬 CLAUDETOUR: {feedback} [ID: {decision_id}]", file=sys.stderr)
    
    sys.exit(run_real_bash(corrected, decision_id, session_id))

###############################################################################
if __name__ == "__main__":
    main()