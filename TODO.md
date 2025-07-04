# ClauDEtour TODO

## Unified Logging System (NEW)
- [x] Add session tracking to interceptor logs
- [x] Create decision ID correlation between approval and execution
- [x] Log execution results with timing and output metrics
- [x] Create session analyzer tool
- [x] Create claude-wrapper to capture full console output
- [x] Create unified analyzer for transcript correlation
- [ ] Integrate with Claude's native logging (clog)
- [ ] Build visualization tools for session analysis
- [ ] Create ML training data exporter

## Installation & Structure
- [ ] Move interceptor to proper system location (e.g., `/opt/claudetour/`)
- [ ] Create proper installation script
- [ ] Handle symlinks properly during install
- [ ] Add update mechanism

## Windows Integration
- [ ] Build Windows Tkinter interface for WSL voice dictation support
- [ ] Research passthrough mechanisms for Windows GUI
- [ ] Test cross-platform GUI compatibility

## Pattern Learning & Auto-Correction
- [ ] Implement chat log correlation with correction logs
- [ ] Build pattern analysis tools
- [ ] Create ML training pipeline from logs
- [ ] Auto-accepter system based on confidence scores

## Smart Path Resolution
- [ ] Fuzzy path finding - if only one file matches partial path, auto-correct
- [ ] Directory existence validation before execution
- [ ] Smart path canonicalization (Windows → Linux)
- [ ] Handle relative vs absolute path confusion

## Per-Tool Customization
- [ ] Create tool-specific correction modules
- [ ] o3-pro specific fixes:
  - [ ] Detect missing `-f` flag for file inputs
  - [ ] Fix stdin/pipe attempts
  - [ ] Correct parameter ordering
- [ ] Git command improvements
- [ ] Python/pip environment detection

## UI/UX Improvements
- [ ] Auto-suggestion with confidence levels
- [ ] Separate "edit suggestion" mode
- [ ] Quick-fix buttons for common corrections
- [ ] Keyboard shortcuts for power users
- [ ] Better feedback mechanism (not just text field)
- [ ] Fix Tab key erasing command in edit field
- [ ] Make original command field selectable/copyable
- [ ] Add Ctrl+A to select all in edit field
- [ ] Prevent focus issues with Tab navigation

## Analysis Tools
- [ ] Log analyzer script to find patterns
- [ ] Visualization of correction frequencies
- [ ] Success/failure rate tracking
- [ ] Time saved calculator

## Integration
- [ ] Claude chat log integration
- [ ] Export corrections as shareable rules
- [ ] Community rule sharing mechanism
- [ ] Integration with other AI tools (Cursor, Copilot, etc.)

## Technical Debt
- [ ] Better error handling
- [ ] Unit tests
- [ ] Performance optimization for large commands
- [ ] Async GUI to prevent blocking

## Documentation
- [ ] Video tutorial
- [ ] More examples in README
- [ ] Troubleshooting guide
- [ ] Rule writing guide