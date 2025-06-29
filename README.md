# ClauDEtour 🚦

A smart bash interceptor for Claude that fixes common path confusion and command issues automatically.

## What is ClauDEtour?

ClauDEtour intercepts bash commands from Claude CLI and:
- 🔧 Auto-corrects Windows→Linux path confusion
- 🎯 Fixes common command mistakes (like `o3-pro` → proper path)
- 👀 Shows corrections in a clean GUI for approval
- 📝 Logs all decisions for pattern learning
- 🛡️ Only activates for Claude (your system stays normal)

## The Problem

Claude often gets confused about paths when you're using WSL:
- Tries to use Windows paths (`/mnt/c/Users/...`) when Linux paths work better
- Forgets command locations and syntax
- Makes other predictable mistakes

## The Solution

ClauDEtour acts as your login shell but ONLY intervenes when Claude is calling bash. All other tools and terminals work normally.

## Features

- **Smart Detection**: Only activates when parent process is Claude
- **Visual Approval**: Clean Tkinter GUI shows original vs corrected command
- **Inline Editing**: Edit commands on the fly before execution
- **Feedback System**: Add notes to any decision (accepted or rejected)
- **Auto-Approve Timer**: Configurable timeout for hands-free operation
- **JSON Logging**: Complete audit trail for future ML training

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/claudetour.git
cd claudetour
```

2. Make the script executable:
```bash
chmod +x bin/bash
```

3. Set as your login shell:
```bash
# Add to /etc/shells
echo "$HOME/ml_research/claudetour_project/bin/bash" | sudo tee -a /etc/shells

# Set as your shell
chsh -s $HOME/ml_research/claudetour_project/bin/bash
```

4. Create symlink for safety:
```bash
ln -s $HOME/ml_research/claudetour_project/bin/bash $HOME/bash-fixer
```

5. Log out and back in to activate

## Configuration

Edit these settings in `bin/bash`:

```python
AUTO_APPROVE_SEC = 8  # Seconds before auto-approval (0 = manual only)
LOG_PATH = "~/.claude_tour/log.jsonl"
REAL_BASH = "/usr/bin/bash"
GUI_ENABLED = True  # Set False for CLI-only mode
```

### Adding Fix Rules

Add your own patterns to `FIX_RULES`:

```python
FIX_RULES = [
    (r"pattern_to_match", r"replacement", "Description for logs"),
    # Add your rules here
]
```

### Safe Passthrough Commands

Commands matching these patterns skip intervention:

```python
SAFE_PASSTHRU = [
    r"^\s*ls(\s|$)", r"^\s*pwd(\s|$)", r"^\s*echo(\s|$)",
    # Add more safe patterns
]
```

## Usage

Just use Claude normally! When ClauDEtour detects a correction opportunity:

1. **GUI Mode**: A window appears showing:
   - Original command (read-only)
   - Editable corrected command
   - Optional feedback field
   - OK/Cancel buttons

2. **CLI Mode**: Text prompt in terminal

3. **Keyboard Shortcuts**:
   - `Enter` - Accept correction
   - `Escape` - Cancel/reject
   - `Tab` - Move between fields

### Enhanced Session Logging

For complete session capture with transcript correlation, use the claude-wrapper:

```bash
# Instead of running claude directly:
claude

# Use the wrapper for full logging:
/path/to/claudetour/claude-wrapper.sh
```

This captures:
- Full terminal transcript with timestamps
- All interceptor decisions and corrections
- Execution results and timing
- Unified session correlation

Analyze sessions with:
```bash
# Analyze the latest session with full correlation
./analyze-unified.py

# Analyze a specific session
./analyze-unified.py 12345_67890

# Basic analysis (interceptor logs only)
./analyze-session.py latest
```

Session logs are stored in:
- `~/.claude_tour/sessions/` - Individual session files
- `~/.claude_tour/log.jsonl` - Main log with all events

## Examples

### Path Correction
```bash
# Claude tries:
cd /mnt/c/Users/yourname/Documents/project

# ClauDEtour suggests:
cd /home/yourname/project
```

### Command Fix
```bash
# Claude tries:
o3-pro "What is consciousness?"

# ClauDEtour suggests:
cd /home/yourname/ml_research && ./ask_tools/ask o3_pro "What is consciousness?"
```

## How It Works

1. Claude calls bash with your command
2. ClauDEtour checks if parent process is Claude
3. If not Claude → passes through to real bash
4. If Claude → checks against fix rules
5. Shows GUI for approval/editing
6. Logs decision with any feedback
7. Executes final command

## Logs

All interactions are logged to `~/.claude_tour/log.jsonl`:

```json
{
  "ts": "2025-06-27T17:43:44.274761Z",
  "orig": "o3-pro \"test\"",
  "corr": "cd /home/user/ml_research && ./ask_tools/ask o3_pro \"test\"",
  "mode": "accepted",
  "fixes": ["o3-pro command correction"],
  "feedback": "Works great!"
}
```

## Security

- Only intercepts commands from Claude
- Never modifies commands from other sources
- All corrections shown before execution
- Complete audit trail in logs

## Contributing

Feel free to submit issues and PRs! Areas for improvement:

- [ ] ML-based pattern learning from logs
- [ ] More sophisticated fix rules
- [ ] Better Windows path detection
- [ ] Integration with other AI tools

## License

MIT License - see LICENSE file

---

Born from consciousness research, built for practical frustration 🤖✨