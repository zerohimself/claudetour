#!/usr/bin/env python3
"""
Analyze ClauDEtour session logs to understand correction patterns
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

def analyze_session(session_id=None, log_file=None):
    """Analyze a specific session or the latest one"""
    
    if not log_file:
        log_file = Path.home() / ".claude_tour" / "log.jsonl"
    
    sessions = defaultdict(lambda: {
        "decisions": [],
        "executions": [],
        "corrections": 0,
        "rejections": 0,
        "errors": 0,
        "duration_total_ms": 0
    })
    
    # Read all log entries
    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line)
                
                # Skip debug entries for analysis
                if entry.get("debug"):
                    continue
                    
                sid = entry.get("session_id", "unknown")
                
                # Only analyze specific session if requested
                if session_id and sid != session_id:
                    continue
                
                if entry.get("type") == "decision":
                    sessions[sid]["decisions"].append(entry)
                    
                    # Count corrections and rejections
                    if entry.get("mode") == "rejected":
                        sessions[sid]["rejections"] += 1
                    elif entry.get("fixes"):
                        sessions[sid]["corrections"] += 1
                        
                elif entry.get("type") == "execution":
                    sessions[sid]["executions"].append(entry)
                    
                    # Track errors and timing
                    if entry.get("returncode", 0) != 0:
                        sessions[sid]["errors"] += 1
                    sessions[sid]["duration_total_ms"] += entry.get("duration_ms", 0)
                    
            except json.JSONDecodeError:
                pass
    
    # Print analysis
    for sid, data in sessions.items():
        if not data["decisions"]:  # Skip empty sessions
            continue
            
        print(f"\n{'='*60}")
        print(f"Session: {sid}")
        print(f"{'='*60}")
        
        print(f"\nSummary:")
        print(f"  Total commands: {len(data['decisions'])}")
        print(f"  Corrections applied: {data['corrections']}")
        print(f"  Commands rejected: {data['rejections']}")
        print(f"  Execution errors: {data['errors']}")
        print(f"  Total execution time: {data['duration_total_ms']}ms")
        
        # Show common corrections
        corrections = defaultdict(int)
        for decision in data["decisions"]:
            for fix in decision.get("fixes", []):
                corrections[fix] += 1
        
        if corrections:
            print(f"\nCommon corrections:")
            for fix, count in sorted(corrections.items(), key=lambda x: x[1], reverse=True):
                print(f"  {fix}: {count} times")
        
        # Show rejected commands
        rejected = []
        for decision in data["decisions"]:
            if decision.get("mode") == "rejected":
                rejected.append({
                    "original": decision.get("orig"),
                    "suggested": decision.get("corr"),
                    "feedback": decision.get("feedback", "")
                })
        
        if rejected:
            print(f"\nRejected commands:")
            for r in rejected[:5]:  # Show first 5
                print(f"  Original: {r['original']}")
                print(f"  Suggested: {r['suggested']}")
                if r['feedback']:
                    print(f"  Feedback: {r['feedback']}")
                print()
        
        # Show errors
        errors = []
        for exec_entry in data["executions"]:
            if exec_entry.get("returncode", 0) != 0:
                # Find the corresponding decision
                decision_id = exec_entry.get("decision_id")
                decision = next((d for d in data["decisions"] if d.get("id") == decision_id), None)
                
                if decision:
                    errors.append({
                        "command": decision.get("corr", decision.get("orig")),
                        "returncode": exec_entry.get("returncode"),
                        "stderr": exec_entry.get("stderr", "")[:200]
                    })
        
        if errors:
            print(f"\nFailed commands:")
            for e in errors[:5]:  # Show first 5
                print(f"  Command: {e['command']}")
                print(f"  Exit code: {e['returncode']}")
                if e['stderr']:
                    print(f"  Error: {e['stderr']}")
                print()

if __name__ == "__main__":
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if session_id == "latest":
        # Find the latest session
        log_file = Path.home() / ".claude_tour" / "log.jsonl"
        latest_session = None
        
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if "session_id" in entry:
                        latest_session = entry["session_id"]
                except:
                    pass
        
        session_id = latest_session
    
    analyze_session(session_id)