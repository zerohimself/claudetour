Below is a “garage-band but fully working” prototype that fulfils every requirement on the list.  It is designed to be dropped in front of the real bash and to grow with you as you discover new error modes.

────────────────────────────  1.  COMPLETE IMPLEMENTATION  ────────────────────────────
Save as  claudetour.py  (the default fun name is “ClauDEtour”; change at will).

```python
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
from datetime import datetime
from pathlib import Path

###############################################################################
# Config – edit here or export env-vars
###############################################################################
AUTO_APPROVE_SEC = int(os.getenv("CLAUDETOUR_AUTO", "8"))   # auto-OK after 8 s
LOG_PATH         = Path(os.getenv("CLAUDETOUR_LOG",
                                   "~/.claude_tour/log.jsonl")).expanduser()
REAL_BASH        = os.getenv("CLAUDETOUR_REAL_BASH", "/usr/bin/bash")   # adjust if needed
GUI_ENABLED      = os.getenv("CLAUDETOUR_GUI", "1") == "1"

# Regexes that go straight through (fast path)
SAFE_PASSTHRU = [
    r"^\s*ls(\s|$)", r"^\s*pwd(\s|$)", r"^\s*echo(\s|$)",
    r"^\s*cat\s+[^\|;&]+$",
]

# Known 1-liners we always fix automatically (editable)
FIX_RULES = [
    # (pattern, replacement, description_for_log)
    (r"/mnt/c/Users/.+?/ml_research", "/home/ubuntu/ml_research",
     "Windows→Linux path canonicalisation"),
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

    result = {"answer": "accept"}  # default auto-answer
    def ok():     result["answer"] = "accept";  root.destroy()
    def edit():   result["answer"] = "edit";    root.destroy()
    def cancel(): result["answer"] = "reject";  root.destroy()

    root = tk.Tk();  root.title("ClauDEtour – command correction")
    tk.Label(root, text="Original ↴").pack(anchor="w")
    t1 = scrolledtext.ScrolledText(root, height=3, width=80);  t1.insert("1.0", original);  t1.config(state="disabled"); t1.pack()
    tk.Label(root, text="Corrected ↴").pack(anchor="w")
    t2 = scrolledtext.ScrolledText(root, height=3, width=80);  t2.insert("1.0", corrected); t2.pack()

    bframe = tk.Frame(root); bframe.pack(pady=4)
    tk.Button(bframe, text=f"OK ({auto_sec})", command=ok).pack(side="left", padx=4)
    tk.Button(bframe, text="Edit", command=edit).pack(side="left", padx=4)
    tk.Button(bframe, text="Cancel", command=cancel).pack(side="left", padx=4)

    def countdown(sec):
        if sec <= 0:
            ok(); return
        for widget in bframe.winfo_children():
            if widget.cget("text").startswith("OK"):
                widget.config(text=f"OK ({sec})")
        root.after(1000, countdown, sec-1)
    countdown(auto_sec)
    root.mainloop()

    if result["answer"] == "edit":
        # quick-n-dirty edit: open $EDITOR or nano in tmp file
        editor = os.getenv("EDITOR", "nano")
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write(corrected); tf.flush()
            subprocess.call([editor, tf.name])
            tf.seek(0); corrected = tf.read()
        return corrected.strip("\n"), "edited"
    elif result["answer"] == "reject":
        return original, "rejected"
    else:
        return corrected, "accepted"

def cli_ask(original: str, corrected: str, auto_sec: int):
    """TTY fallback when no GUI available"""
    print("ClauDEtour suggestion:")
    print(" ─ original : ", original)
    print(" ─ corrected: ", corrected)
    print(f"[Enter]=accept  e=edit  n=reject (auto in {auto_sec}s) › ", end="", flush=True)

    def timer():
        time.sleep(auto_sec)
        try:
            # inject newline to stdin to auto-proceed
            import termios, fcntl
            fd = sys.stdin.fileno()
            fcntl.ioctl(fd, termios.TIOCSTI, b"\n")
        except Exception:
            pass
    threading.Thread(target=timer, daemon=True).start()

    choice = sys.stdin.readline().strip()
    if choice == "e":
        print("# Enter new command, end with EOF (Ctrl-D)")
        edited = sys.stdin.read()
        return edited.strip("\n"), "edited"
    if choice == "n":
        return original, "rejected"
    return corrected, "accepted"

###############################################################################
# Core
###############################################################################
def run_real_bash(cmdline: str):
    return subprocess.call([REAL_BASH, "-lc", cmdline])

def main():
    # mimic  `bash -lc "CMD"`
    if "-c" in sys.argv or "-lc" in sys.argv:
        # Find the last argument (cmd string)
        cmd = sys.argv[-1]
    else:   # interactive fall-through
        os.execv(REAL_BASH, [REAL_BASH] + sys.argv[1:])
        return

    decision = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "orig": cmd, "corr": None, "mode": None,
        "passthru": False, "fixes": [],
    }

    # Fast path
    if safe_passthrough(cmd):
        decision["passthru"] = True
        decision["corr"] = cmd
        log(decision)
        sys.exit(run_real_bash(cmd))

    # Apply automatic rules
    corrected, fixes = apply_fixes(cmd)
    decision["fixes"] = fixes

    # If nothing changed, still ask?
    if corrected == cmd:
        # unknown / suspicious – ask anyway
        corrected, mode = gui_ask(cmd, cmd, AUTO_APPROVE_SEC)
        decision["corr"], decision["mode"] = corrected, mode
    else:
        corrected, mode = gui_ask(cmd, corrected, AUTO_APPROVE_SEC)
        decision["corr"], decision["mode"] = corrected, mode

    log(decision)
    sys.exit(run_real_bash(corrected))

###############################################################################
if __name__ == "__main__":
    main()
```

────────────────────────────  2.  INSTALLATION  ────────────────────────────
1. Put the script somewhere on disk and  `chmod +x claudetour.py`
2. Choose one of the two interception methods (no sudo needed for ①):
   ① Prepend a directory to PATH  
      mkdir -p ~/.claude_tour/bin  
      ln -s /full/path/claudetour.py ~/.claude_tour/bin/bash  
      export PATH="$HOME/.claude_tour/bin:$PATH"
   ② Rename the real bash (dangerous; only if you know what you’re doing)  
      sudo mv /usr/bin/bash /usr/bin/bash_real  
      sudo ln -s /full/path/claudetour.py /usr/bin/bash  
      export CLAUDETOUR_REAL_BASH=/usr/bin/bash_real
3. Test:  
   bash -lc "pwd"      → should just passthrough  
   bash -lc "nohup sleep 1" → should auto-add ampersand.

────────────────────────────  3.  INTEGRATION WITH CLAUDE CODE  ─────────────
Anthropic’s Code Runner calls  `bash -lc "<your command>"`.  
Because ClauDEtour honours that interface, as soon as the PATH trick above is active, every execution inside the Claude Code sandbox will be routed through the interceptor.  The auto-approve timer prevents the GUI from blocking and thus avoids the built-in timeout.

If you cannot modify PATH inside the Claude environment, set the environment variable that tells the tool which shell to use (many deployments respect `$SHELL`):

export SHELL="$HOME/.claude_tour/bin/bash"

────────────────────────────  4.  FUN NAME  ────────────────────────────────
“ClauDEtour”  
Because it detours every command, fixes the path, and puts Claude back on track.  
(Other rejected brainstorms: WheelBash, PathSentry, BashfulMentor, SynapseSh.)

────────────────────────────  5.  EXTENDING THE INTELLIGENCE  ──────────────
• Every execution appends a JSON-line to  ~/.claude_tour/log.jsonl  
  Point any notebook / pandas script at it and mine for recurring slip-ups.  
• Add new automatic rules to FIX_RULES (pattern, replacement, note).  
• Replace the simple regex engine with spaCy, GPT-powered analysis, or
  a reinforcement learner—just keep the outer interface the same.

────────────────────────────  6.  OPEN QUESTIONS / NEXT STEPS  ──────────────
1. Multi-line commands are handled but naïvely (they are passed as one blob to bash).  
   For more surgical edits, split on ‘;’ or  ‘&&’ and walk the AST (bashlex).
2. GUI library: Tkinter is available everywhere.  If you prefer “zenity” on WSL-g, set `CLAUDETOUR_GUI=zenity` and implement a tiny wrapper.
3. Visibility:  The dialog shows the fix; if you want silent auto-fixes, set `AUTO_APPROVE_SEC=0` and `CLAUDETOUR_GUI=0`.
4. Security: You are executing whatever you type.  Strictly limit automatic rewrites to non-destructive commands unless you add a real sandbox.

Enjoy your new training wheels!