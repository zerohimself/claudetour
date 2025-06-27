# O3 Pro: Build a Bash Interceptor for Claude's Directory Confusion

## Problem Definition
Claude (me) has persistent issues with:
1. **Path confusion**: Mixing up `/mnt/c/.../ml_research` and `/home/.../ml_research` (symlinked dirs)
2. **Tool misuse**: Using standard Linux conventions with custom AI tools that need special args
3. **Wrong directory execution**: Right command, wrong pwd
4. **Repetitive mistakes**: Same errors with O3 Pro (forgetting nohup), git commits, etc.

## What We Need
A bash interceptor that:
1. **Acts as transparent filter**: Replaces bash tool but calls real bash
2. **Regex passthrough**: Simple commands (ls, pwd, echo) go straight through  
3. **Pattern correction**: Known mistakes get auto-fixed (with notification)
4. **GUI fallback**: Unknown commands show correction dialog
5. **Learning system**: Logs all corrections to identify patterns
6. **Non-blocking**: Auto-approve timer to prevent tool timeouts

## Technical Requirements
- Python-based (for easy GUI integration)
- Can be symlinked or replace Claude's bash tool
- Handles Claude Code's tool timeout constraints
- Persistent state for learned patterns
- Works on WSL2/Linux

## Implementation Questions
1. Best GUI library for quick correction dialogs?
2. How to intercept bash tool calls in Claude Code?
3. Optimal way to log patterns for later analysis?
4. Should corrections be visible to Claude or silent?
5. How to handle multi-line bash commands?

## Naming Challenge
Come up with a fun name for this tool that reflects:
- It's a neural extension for an AI
- Fixes directory confusion
- Acts as intelligent filter
- Is Claude's "training wheels"

## Context You Might Need
- Claude Code uses a bash tool that executes commands
- Commands timeout if they take too long
- User wants to collect data first, then build intelligence
- This is a "YOLO garage band version" - functional over perfect

## Deliverable
A working Python script that:
1. Intercepts bash commands
2. Shows GUI for correction (with timeout)
3. Logs all corrections
4. Has regex patterns for common safe commands
5. Can be easily extended with more intelligence later

Please provide:
1. The complete implementation
2. Installation instructions
3. How to integrate with Claude Code
4. A fun name for the tool
5. Any additional context you need to make this better