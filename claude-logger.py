#!/usr/bin/env python3
"""
Claude session logger with intelligent output parsing
Captures structured logs without ANSI escape sequences
"""
import sys
import os
import re
import json
import pty
import select
import termios
import tty
from datetime import datetime, timezone
from pathlib import Path
import subprocess

class ClaudeLogger:
    def __init__(self, session_id):
        self.session_id = session_id
        self.log_dir = Path.home() / ".claude_tour" / "sessions"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handles
        self.raw_log = open(self.log_dir / f"{session_id}.raw", "wb")
        self.clean_log = open(self.log_dir / f"{session_id}.log", "w", encoding="utf-8")
        self.structured_log = open(self.log_dir / f"{session_id}.jsonl", "a")
        
        # State tracking
        self.current_command = None
        self.in_claude_response = False
        self.buffer = ""
        
    def clean_ansi(self, text):
        """Remove ANSI escape sequences and control characters"""
        # Remove ANSI escape sequences
        text = re.sub(r'\x1b\[[0-9;]*[mGKHJF]', '', text)
        text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
        text = re.sub(r'\x1b\]0;[^\x07]*\x07', '', text)
        text = re.sub(r'\x1b[>=]', '', text)
        
        # Remove carriage returns but keep newlines
        text = text.replace('\r\n', '\n').replace('\r', '')
        
        # Remove other control characters except newline and tab
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text
    
    def parse_claude_output(self, text):
        """Extract structured information from Claude's output"""
        clean = self.clean_ansi(text)
        
        # Detect Claude's box headers
        if '✻ Welcome to Claude Code!' in clean:
            self.log_event("session_start", {"welcome": True})
            
        # Detect commands being run
        bash_pattern = r'(?:Bash|bash -c.*?)"([^"]+)"'
        matches = re.findall(bash_pattern, clean)
        for cmd in matches:
            self.log_event("command_attempt", {"command": cmd})
            
        # Detect ClauDEtour interceptor messages
        if 'CLAUDETOUR' in clean:
            if 'REJECTED' in clean:
                self.log_event("command_rejected", {"output": clean})
            elif 'EDITED' in clean:
                self.log_event("command_edited", {"output": clean})
            elif 'Command corrected' in clean:
                self.log_event("command_corrected", {"output": clean})
                
        # Detect tool use markers
        if '<function_calls>' in text:
            self.in_claude_response = True
            self.log_event("tool_use_start", {})
        elif '