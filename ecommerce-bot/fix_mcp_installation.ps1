# PowerShell script to fix MCP installation in virtual environment

Write-Host "Fixing MCP installation in virtual environment..." -ForegroundColor Green

# Activate virtual environment
& ..\venv\Scripts\Activate.ps1

# Upgrade pip first
Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install MCP and FastMCP
Write-Host "`nInstalling MCP SDK..." -ForegroundColor Yellow
python -m pip install mcp

# Also try installing fastmcp if available
Write-Host "`nTrying to install FastMCP..." -ForegroundColor Yellow
python -m pip install fastmcp

# Verify installation
Write-Host "`nVerifying installation..." -ForegroundColor Yellow
python -c "import mcp; print(f'MCP installed: {mcp.__file__}')"

# Test the server
Write-Host "`nTesting MCP server..." -ForegroundColor Yellow
python check_mcp_installation.py