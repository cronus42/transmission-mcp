# Transmission MCP Server

A Model Context Protocol (MCP) server that provides tools for interacting with the Transmission BitTorrent client via its RPC API.

## Features

The server provides the following tools:

### Torrent Management
- **add_torrent**: Add new torrents by URL, magnet link, or base64-encoded .torrent file
- **remove_torrent**: Remove torrents with optional local data deletion
- **start_torrent**: Start/resume torrents by ID
- **stop_torrent**: Stop/pause torrents by ID
- **get_torrent_info**: Get detailed information about specific torrents
- **search_torrents**: Search torrents by name with optional status filtering

### Configuration
- **set_torrent_priority**: Set download priority (high/normal/low) for individual torrents
- **set_speed_limits**: Set global download/upload speed limits

### Monitoring
- **get_session_stats**: Get comprehensive Transmission session statistics

### Resources
The server also provides these resources for browsing:
- `transmission://session` - Current session information
- `transmission://torrents` - List of all torrents
- `transmission://stats` - Session statistics

## Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/transmission-mcp.git
cd transmission-mcp
```

2. Run the setup script:
```bash
./setup.sh
```

3. Configure your Transmission server settings (optional):
```bash
cp .env.example .env
# Edit .env with your Transmission server details
```

4. Ensure your Transmission daemon is running and RPC is enabled.

## Testing

Run the test script to verify connectivity:
```bash
python test-transmission.py
```

## Usage with MCP Client

### Warp Terminal Integration

1. Run the setup script:
```bash
./setup.sh
```

2. Configure Warp to use the MCP server:
```bash
warp mcp add-server --config mcp_config.json
```

Or manually start the server:
```bash
./start_transmission_server.sh
```

### Claude Desktop Configuration

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "transmission": {
      "command": "/path/to/transmission-mcp/start_transmission_server.sh",
      "env": {},
      "args": []
    }
  }
}
```

### Example Commands

Once connected via an MCP client, you can use commands like:

- "Add this magnet link: magnet:?xt=urn:btih:..."
- "Show me all torrents that are currently downloading"
- "Stop torrent with ID 5"
- "Get detailed info for torrent 3"
- "Set global download limit to 500 KB/s"
- "Search for torrents containing 'ubuntu'"
- "Show transmission statistics"

## Transmission Setup

Ensure your Transmission daemon has RPC enabled. In your Transmission settings:

1. Enable "Allow remote access"
2. Set RPC port (usually 9091)
3. Configure authentication if needed (the current implementation assumes no auth)
4. Ensure the RPC whitelist includes your client IP

For headless Transmission (transmission-daemon), edit `/etc/transmission-daemon/settings.json`:
```json
{
    "rpc-enabled": true,
    "rpc-port": 9091,
    "rpc-whitelist-enabled": false,
    "rpc-authentication-required": false
}
```

## Security Notes

- The current implementation assumes no RPC authentication is required
- For production use, consider implementing authentication
- Ensure proper network security (firewall rules, VPN, etc.)
- Configure the server connection using environment variables (.env file)

## API Reference

The server handles Transmission RPC API calls including:
- Session management with CSRF protection (X-Transmission-Session-Id header)
- Automatic retry on 409 errors to fetch new session IDs
- JSON RPC over HTTP POST requests
- Comprehensive error handling and logging

## Error Handling

The server includes robust error handling for:
- Network connectivity issues
- HTTP errors and status codes
- Transmission RPC errors
- Invalid torrent IDs or malformed requests
- Session ID management and CSRF protection
