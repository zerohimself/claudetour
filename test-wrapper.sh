#!/bin/bash
# Quick test of the claude-wrapper and interceptor integration

echo "ClauDEtour Wrapper Test"
echo "======================="
echo ""
echo "This will demonstrate the unified logging system."
echo ""

# Check if wrapper exists
WRAPPER="./claude-wrapper.sh"
if [ ! -f "$WRAPPER" ]; then
    echo "Error: claude-wrapper.sh not found"
    exit 1
fi

echo "To test the wrapper:"
echo "1. Run: $WRAPPER"
echo "2. In Claude, try some commands that trigger corrections:"
echo "   - cd /mnt/c/Users/yourname/Documents"
echo "   - o3-pro 'test question'"
echo "   - python script.py"
echo ""
echo "3. Exit Claude"
echo ""
echo "4. Analyze the session:"
echo "   ./analyze-unified.py"
echo ""
echo "The analyzer will show:"
echo "- Full transcript of the session"
echo "- All interceptor decisions"
echo "- Correlations between transcript and corrections"
echo "- Timing and execution results"
echo ""
echo "Session logs will be in: ~/.claude_tour/sessions/"