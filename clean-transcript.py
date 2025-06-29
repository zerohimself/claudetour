#!/usr/bin/env python3
"""
Clean ANSI escape sequences from script transcript files
Can be used standalone or integrated into the wrapper
"""
import sys
import re
from pathlib import Path

def clean_ansi(text):
    """Remove ANSI escape sequences and clean up control characters"""
    
    # Remove various ANSI escape sequences
    patterns = [
        r'\x1b\[[0-9;]*[mGKHF]',  # Color and cursor movement
        r'\x1b\[[0-9;]*[A-Za-z]',  # Other escape sequences
        r'\x1b\]0;[^\x07]*\x07',   # Terminal title
        r'\x1b[>=]',               # Terminal mode
        r'\x1b\[\?[0-9;]*[hl]',    # Terminal settings
        r'\x1b\[[0-9;]*J',         # Clear screen
        r'\x1b\[[0-9;]*K',         # Clear line
        r'\x08+',                  # Backspaces
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    
    # Handle carriage returns (often used for progress bars)
    # Split by \n, then for each line, only keep the last \r-delimited part
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if '\r' in line:
            # Keep only the last segment after \r (final state of the line)
            parts = line.split('\r')
            line = parts[-1]
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Remove null bytes and other control chars (except newline and tab)
    text = ''.join(char for char in text 
                   if ord(char) >= 32 or char in '\n\t')
    
    return text

def extract_claude_session(text):
    """Extract key Claude session information"""
    
    # Find Claude welcome box
    welcome_match = re.search(r'╭[─]+╮\s*│\s*✻ Welcome to Claude Code!.*?╰[─]+╯', 
                             text, re.DOTALL)
    
    # Find command attempts (multiple patterns)
    commands = []
    
    # Pattern 1: Direct bash commands
    bash_pattern = r'(?:Human|You):\s*(?:bash|Bash).*?"([^"]+)"'
    commands.extend(re.findall(bash_pattern, text))
    
    # Pattern 2: Command shown in output
    cmd_pattern = r'\$\s+([^\n]+)'
    commands.extend(re.findall(cmd_pattern, text))
    
    # Find ClauDEtour interactions
    claudetour_events = []
    claudetour_pattern = r'(CLAUDETOUR[^:]*:.*?)(?=\n|$)'
    for match in re.finditer(claudetour_pattern, text):
        claudetour_events.append(match.group(1))
    
    return {
        'has_welcome': bool(welcome_match),
        'commands': commands,
        'claudetour_events': claudetour_events,
        'clean_text': text
    }

def process_transcript(input_file, output_file=None):
    """Process a transcript file"""
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: {input_file} not found")
        return
    
    # Read the raw transcript
    with open(input_path, 'rb') as f:
        raw_content = f.read()
    
    # Try to decode with error handling
    try:
        text = raw_content.decode('utf-8')
    except UnicodeDecodeError:
        # Fallback to latin-1 which accepts all bytes
        text = raw_content.decode('latin-1')
    
    # Clean the text
    cleaned = clean_ansi(text)
    
    # Extract session info
    session_info = extract_claude_session(cleaned)
    
    # Determine output file
    if output_file is None:
        output_file = input_path.with_suffix('.clean.log')
    
    # Write cleaned version
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print(f"Cleaned transcript written to: {output_file}")
    
    # Show summary
    print(f"\nSession summary:")
    print(f"  Claude welcome: {'Yes' if session_info['has_welcome'] else 'No'}")
    print(f"  Commands found: {len(session_info['commands'])}")
    print(f"  ClauDEtour events: {len(session_info['claudetour_events'])}")
    
    if session_info['commands']:
        print(f"\nSample commands:")
        for cmd in session_info['commands'][:5]:
            print(f"  - {cmd}")
    
    if session_info['claudetour_events']:
        print(f"\nClauDEtour events:")
        for event in session_info['claudetour_events'][:5]:
            print(f"  - {event}")

def main():
    if len(sys.argv) < 2:
        print("Usage: clean-transcript.py <transcript_file> [output_file]")
        print("\nThis tool removes ANSI escape sequences from script transcripts")
        print("If output_file is not specified, creates .clean.log version")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    process_transcript(input_file, output_file)

if __name__ == "__main__":
    main()