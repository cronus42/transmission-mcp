# Transmission MCP Server - Warp Setup Guide

## Quick Setup

1. **Navigate to the project directory:**
   ```bash
   cd transmission-mcp
   ```

2. **Run the setup script:**
   ```bash
   ./setup.sh
   ```

3. **Test the connection (optional):**
   ```bash
   source venv/bin/activate && python test-transmission.py
   ```

## Warp Integration Options

### Option 1: Using Warp's MCP Integration (Recommended)
If Warp has native MCP support:
```bash
# Add the server to Warp's MCP configuration
warp mcp add-server --config mcp_config.json

# Or manually configure using the JSON:
cat mcp_config.json
```

### Option 2: Manual Startup
```bash
# Start the MCP server manually
./start_transmission_server.sh
```

### Option 3: Background Service
```bash
# Run as background process
nohup ./start_transmission_server.sh > transmission-mcp.log 2>&1 &
```

## Configuration

- **Server Settings**: Copy `.env.example` to `.env` and edit environment variables
- **Environment**: Set TRANSMISSION_HOST, TRANSMISSION_PORT, etc.
- **MCP Config**: Modify `mcp_config.json` as needed

## Verification

Once running, you should be able to:
- Ask Warp: "Show me my torrents"
- Add torrents: "Add this magnet link: magnet:?xt=..."
- Control torrents: "Stop torrent 5" or "Start all paused torrents"
- Get stats: "Show transmission statistics"

## Troubleshooting

1. **Connection Issues**: Verify Transmission daemon is running on the configured host:port
2. **Permission Issues**: Ensure scripts are executable (`chmod +x *.sh`)
3. **Python Issues**: Verify virtual environment is activated
4. **Configuration Issues**: Check `.env` file for correct Transmission server settings
5. **Log Issues**: Check `transmission-mcp.log` if running as background service

## File Structure
```
transmission-mcp/
├── transmission_server.py      # Main MCP server
├── requirements.txt           # Python dependencies  
├── setup.sh                  # Setup script
├── start_transmission_server.sh # Startup script
├── test-transmission.py      # Connectivity test
├── mcp_config.json          # Warp MCP configuration
├── .env.example             # Environment template
├── README.md                # Full documentation
├── WARP_SETUP.md           # This file
└── venv/                   # Python virtual environment
```
