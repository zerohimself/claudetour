#!/usr/bin/env python3
"""
Unified session analyzer for ClauDEtour
Correlates claude-wrapper transcripts with interceptor logs
"""
import json
import sys
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def parse_transcript(transcript_file):
    """Parse key events from the transcript"""
    events = []
    
    try:
        with open(transcript_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Look for bash commands in the transcript
        # Claude shows commands with a specific pattern
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Look for bash tool invocations
            if 'bash -c' in line or 'Bash' in line:
                events.append({
                    'type': 'command_attempt',
                    'line': i,
                    'content': line.strip()
                })
                
            # Look for ClauDEtour messages
            if 'CLAUDETOUR' in line:
                events.append({
                    'type': 'claudetour_action',
                    'line': i,
                    'content': line.strip()
                })
                
            # Look for error messages
            if 'error' in line.lower() or 'failed' in line.lower():
                events.append({
                    'type': 'potential_error',
                    'line': i,
                    'content': line.strip()
                })
                
    except Exception as e:
        print(f"Error parsing transcript: {e}")
        
    return events

def analyze_unified_session(session_id=None):
    """Analyze a session with both transcript and interceptor logs"""
    
    sessions_dir = Path.home() / ".claude_tour" / "sessions"
    log_file = Path.home() / ".claude_tour" / "log.jsonl"
    
    if not session_id:
        # Find the latest session
        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if "session_id" in entry:
                            session_id = entry["session_id"]
                    except:
                        pass
        
        if not session_id:
            print("No sessions found")
            return
    
    print(f"\n{'='*80}")
    print(f"Unified Session Analysis: {session_id}")
    print(f"{'='*80}")
    
    # Check for transcript and session files
    transcript_file = sessions_dir / f"{session_id}.transcript"
    timing_file = sessions_dir / f"{session_id}.timing"
    session_log = sessions_dir / f"{session_id}.jsonl"
    
    print(f"\nSession files:")
    print(f"  Transcript: {'✓' if transcript_file.exists() else '✗'} {transcript_file}")
    print(f"  Timing:     {'✓' if timing_file.exists() else '✗'} {timing_file}")
    print(f"  Session log: {'✓' if session_log.exists() else '✗'} {session_log}")
    
    # Parse session metadata
    session_start = None
    session_end = None
    if session_log.exists():
        with open(session_log) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "session_start":
                        session_start = entry
                    elif entry.get("type") == "session_end":
                        session_end = entry
                except:
                    pass
    
    if session_start:
        print(f"\nSession metadata:")
        print(f"  Started: {session_start.get('ts')}")
        print(f"  Working dir: {session_start.get('pwd')}")
        print(f"  User: {session_start.get('user')}@{session_start.get('hostname')}")
        print(f"  Command: {' '.join(session_start.get('args', []))}")
    
    if session_end:
        print(f"  Ended: {session_end.get('ts')}")
        print(f"  Exit code: {session_end.get('exit_code')}")
    
    # Parse transcript for events
    if transcript_file.exists():
        print(f"\nTranscript analysis:")
        events = parse_transcript(transcript_file)
        
        # Count event types
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event['type']] += 1
            
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")
            
        # Show sample events
        if events:
            print(f"\nSample events from transcript:")
            for event in events[:10]:  # First 10 events
                print(f"  Line {event['line']}: {event['type']}")
                print(f"    {event['content'][:100]}...")
    
    # Analyze interceptor logs for this session
    print(f"\nInterceptor activity:")
    
    decisions = []
    executions = []
    corrections = 0
    rejections = 0
    errors = 0
    
    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line)
                
                if entry.get("session_id") != session_id:
                    continue
                    
                if entry.get("type") == "decision":
                    decisions.append(entry)
                    if entry.get("mode") == "rejected":
                        rejections += 1
                    elif entry.get("fixes"):
                        corrections += 1
                        
                elif entry.get("type") == "execution":
                    executions.append(entry)
                    if entry.get("returncode", 0) != 0:
                        errors += 1
                        
            except json.JSONDecodeError:
                pass
    
    print(f"  Commands intercepted: {len(decisions)}")
    print(f"  Corrections applied: {corrections}")
    print(f"  Commands rejected: {rejections}")
    print(f"  Execution errors: {errors}")
    
    # Show timeline of decisions with correlation
    if decisions:
        print(f"\nCommand timeline:")
        for decision in decisions:
            print(f"\n  [{decision.get('ts')}] ID: {decision.get('id')}")
            print(f"    Original: {decision.get('orig')}")
            
            if decision.get('fixes'):
                print(f"    Fixes: {', '.join(decision['fixes'])}")
                
            if decision.get('corr') != decision.get('orig'):
                print(f"    Corrected: {decision.get('corr')}")
                
            print(f"    Status: {decision.get('mode', 'accepted')}")
            
            if decision.get('feedback'):
                print(f"    Feedback: {decision['feedback']}")
                
            # Find corresponding execution
            exec_entry = next((e for e in executions if e.get('decision_id') == decision.get('id')), None)
            if exec_entry:
                print(f"    Execution: {exec_entry.get('returncode')} in {exec_entry.get('duration_ms')}ms")
                if exec_entry.get('stderr'):
                    print(f"    Stderr: {exec_entry['stderr'][:100]}...")
    
    # Correlation insights
    print(f"\nCorrelation insights:")
    
    # Find commands in transcript that match intercepted commands
    if transcript_file.exists() and decisions:
        with open(transcript_file, 'r', encoding='utf-8', errors='replace') as f:
            transcript = f.read()
            
        matched = 0
        for decision in decisions:
            cmd = decision.get('orig', '')
            if cmd in transcript:
                matched += 1
                
        print(f"  Commands found in transcript: {matched}/{len(decisions)}")
        
    # Calculate time windows
    if decisions and executions:
        total_thinking_time = 0
        total_exec_time = 0
        
        for exec_entry in executions:
            if exec_entry.get('duration_ms'):
                total_exec_time += exec_entry['duration_ms']
                
        print(f"  Total execution time: {total_exec_time}ms")
        
    print(f"\nAnalysis complete.")

def main():
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        if session_id == "latest":
            session_id = None
    else:
        session_id = None
        
    analyze_unified_session(session_id)

if __name__ == "__main__":
    main()