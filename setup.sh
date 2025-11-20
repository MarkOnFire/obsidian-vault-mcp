#!/bin/bash
# Setup script for Obsidian Vault MCP server

set -e

echo "Obsidian Vault MCP Server - Setup"
echo "=================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Create virtual environment
echo "1. Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ✓ Virtual environment already exists"
else
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
fi

# 2. Install dependencies
echo ""
echo "2. Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -e .
echo "   ✓ Dependencies installed"

# 3. Create logs directory
echo ""
echo "3. Setting up logs directory..."
LOGS_DIR="/Users/mriechers/Developer/obsidian-config/logs"
if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    echo "   ✓ Created logs directory: $LOGS_DIR"
else
    echo "   ✓ Logs directory exists: $LOGS_DIR"
fi

# 4. Test vault access
echo ""
echo "4. Testing vault access..."
export OBSIDIAN_VAULT_PATH="/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"

if [ ! -d "$OBSIDIAN_VAULT_PATH" ]; then
    echo "   ✗ ERROR: Vault not found at: $OBSIDIAN_VAULT_PATH"
    echo "   Please check iCloud sync status"
    exit 1
fi

echo "   ✓ Vault accessible: $OBSIDIAN_VAULT_PATH"

# 5. Run test operations
echo ""
echo "5. Running test operations..."
python test_operations.py
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo "   ✓ All tests passed!"
else
    echo ""
    echo "   ✗ Tests failed. Check error messages above."
    exit 1
fi

# 6. Show next steps
echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Update Claude for Desktop config:"
echo "   File: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo "   Add this to the 'mcpServers' section:"
echo ""
echo '   "obsidian-vault": {'
echo '     "command": "'"$SCRIPT_DIR/venv/bin/python"'",'
echo '     "args": ["-m", "obsidian_vault_mcp"],'
echo '     "env": {'
echo '       "OBSIDIAN_VAULT_PATH": "'"$OBSIDIAN_VAULT_PATH"'"'
echo '     }'
echo '   }'
echo ""
echo "2. Restart Claude for Desktop"
echo ""
echo "3. Test in conversation:"
echo '   "Read my Project Dashboard note"'
echo ""
echo "See QUICKSTART.md for more details."
echo ""
