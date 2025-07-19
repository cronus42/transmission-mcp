#!/usr/bin/env python3
"""
Transmission MCP Server

A Model Context Protocol server that provides tools for interacting with
Transmission torrent client via its RPC API.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Union
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.server.stdio
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("transmission-mcp")

# Transmission server configuration from environment variables
TRANSMISSION_HOST = os.getenv("TRANSMISSION_HOST", "localhost")
TRANSMISSION_PORT = int(os.getenv("TRANSMISSION_PORT", "9091"))
TRANSMISSION_USERNAME = os.getenv("TRANSMISSION_USERNAME")
TRANSMISSION_PASSWORD = os.getenv("TRANSMISSION_PASSWORD")
TRANSMISSION_URL = f"http://{TRANSMISSION_HOST}:{TRANSMISSION_PORT}/transmission/rpc"

# Global session ID for CSRF protection
transmission_session_id = None

class TransmissionClient:
    """Client for interacting with Transmission RPC API"""
    
    def __init__(self, url: str):
        self.url = url
        self.session_id = None
        
    async def _make_request(self, method: str, arguments: Dict[str, Any] = None, tag: int = None) -> Dict[str, Any]:
        """Make a request to the Transmission RPC API"""
        global transmission_session_id
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Add session ID if we have one
        if transmission_session_id:
            headers["X-Transmission-Session-Id"] = transmission_session_id
        
        payload = {
            "method": method,
            "arguments": arguments or {},
        }
        
        if tag:
            payload["tag"] = tag
        
        # Set up authentication if credentials are provided
        auth = None
        if TRANSMISSION_USERNAME and TRANSMISSION_PASSWORD:
            auth = httpx.BasicAuth(TRANSMISSION_USERNAME, TRANSMISSION_PASSWORD)
        
        async with httpx.AsyncClient(timeout=30.0, auth=auth) as client:
            try:
                response = await client.post(
                    self.url,
                    json=payload,
                    headers=headers
                )
                
                # Handle CSRF protection (409 error)
                if response.status_code == 409:
                    # Get new session ID from response headers
                    new_session_id = response.headers.get("X-Transmission-Session-Id")
                    if new_session_id:
                        transmission_session_id = new_session_id
                        headers["X-Transmission-Session-Id"] = new_session_id
                        
                        # Retry the request
                        response = await client.post(
                            self.url,
                            json=payload,
                            headers=headers
                        )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.RequestError as e:
                raise Exception(f"Network error: {e}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")

# Create the server
app = Server("transmission-mcp")
transmission_client = TransmissionClient(TRANSMISSION_URL)

@app.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="transmission://session",
            name="Transmission Session Info",
            description="Current Transmission session information and statistics",
            mimeType="application/json",
        ),
        Resource(
            uri="transmission://torrents",
            name="All Torrents",
            description="List of all torrents in Transmission",
            mimeType="application/json",
        ),
        Resource(
            uri="transmission://stats",
            name="Transmission Statistics",
            description="Transmission session statistics",
            mimeType="application/json",
        ),
    ]

@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a specific resource"""
    try:
        if uri == "transmission://session":
            result = await transmission_client._make_request("session-get")
            return json.dumps(result.get("arguments", {}), indent=2)
            
        elif uri == "transmission://torrents":
            result = await transmission_client._make_request("torrent-get", {
                "fields": [
                    "id", "name", "status", "totalSize", "percentDone", "rateDownload", 
                    "rateUpload", "uploadRatio", "eta", "peersConnected", "downloadDir",
                    "error", "errorString", "addedDate", "doneDate", "trackerStats"
                ]
            })
            return json.dumps(result.get("arguments", {}), indent=2)
            
        elif uri == "transmission://stats":
            result = await transmission_client._make_request("session-stats")
            return json.dumps(result.get("arguments", {}), indent=2)
            
        else:
            raise ValueError(f"Unknown resource: {uri}")
            
    except Exception as e:
        return f"Error reading resource {uri}: {str(e)}"

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="add_torrent",
            description="Add a new torrent by URL or magnet link",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Torrent URL, magnet link, or base64-encoded .torrent file",
                    },
                    "download_dir": {
                        "type": "string",
                        "description": "Download directory (optional)",
                    },
                    "paused": {
                        "type": "boolean",
                        "description": "Start paused (optional, default false)",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="remove_torrent",
            description="Remove a torrent by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID to remove",
                    },
                    "delete_local_data": {
                        "type": "boolean",
                        "description": "Also delete local data (default false)",
                        "default": False,
                    },
                },
                "required": ["torrent_id"],
            },
        ),
        Tool(
            name="start_torrent",
            description="Start/resume a torrent by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID to start",
                    },
                },
                "required": ["torrent_id"],
            },
        ),
        Tool(
            name="stop_torrent",
            description="Stop/pause a torrent by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID to stop",
                    },
                },
                "required": ["torrent_id"],
            },
        ),
        Tool(
            name="get_torrent_info",
            description="Get detailed information about a specific torrent",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID to get info for",
                    },
                },
                "required": ["torrent_id"],
            },
        ),
        Tool(
            name="set_torrent_priority",
            description="Set download priority for a torrent",
            inputSchema={
                "type": "object",
                "properties": {
                    "torrent_id": {
                        "type": "integer",
                        "description": "Torrent ID",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "normal", "low"],
                        "description": "Priority level",
                    },
                },
                "required": ["torrent_id", "priority"],
            },
        ),
        Tool(
            name="set_speed_limits",
            description="Set global download/upload speed limits",
            inputSchema={
                "type": "object",
                "properties": {
                    "download_limit": {
                        "type": "integer",
                        "description": "Download speed limit in KB/s (0 = unlimited)",
                    },
                    "upload_limit": {
                        "type": "integer",
                        "description": "Upload speed limit in KB/s (0 = unlimited)",
                    },
                },
            },
        ),
        Tool(
            name="search_torrents",
            description="Search torrents by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (torrent name)",
                    },
                    "status_filter": {
                        "type": "string",
                        "enum": ["all", "downloading", "seeding", "paused", "completed"],
                        "description": "Filter by status (optional)",
                        "default": "all",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_session_stats",
            description="Get Transmission session statistics",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "add_torrent":
            url = arguments["url"]
            download_dir = arguments.get("download_dir")
            paused = arguments.get("paused", False)
            
            args = {}
            
            # Handle different URL types
            if url.startswith("magnet:"):
                args["filename"] = url
            elif url.startswith("http"):
                args["filename"] = url
            else:
                # Assume it's base64-encoded torrent data
                args["metainfo"] = url
                
            if download_dir:
                args["download-dir"] = download_dir
                
            args["paused"] = paused
            
            result = await transmission_client._make_request("torrent-add", args)
            
            if result.get("result") == "success":
                torrent_added = result.get("arguments", {}).get("torrent-added")
                torrent_duplicate = result.get("arguments", {}).get("torrent-duplicate")
                
                if torrent_added:
                    return [types.TextContent(
                        type="text",
                        text=f"Successfully added torrent '{torrent_added['name']}' (ID: {torrent_added['id']})"
                    )]
                elif torrent_duplicate:
                    return [types.TextContent(
                        type="text",
                        text=f"Torrent already exists: '{torrent_duplicate['name']}' (ID: {torrent_duplicate['id']})"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="Torrent added successfully"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to add torrent: {result.get('result', 'Unknown error')}"
                )]

        elif name == "remove_torrent":
            torrent_id = arguments["torrent_id"]
            delete_local_data = arguments.get("delete_local_data", False)
            
            args = {
                "ids": [torrent_id],
                "delete-local-data": delete_local_data
            }
            
            result = await transmission_client._make_request("torrent-remove", args)
            
            if result.get("result") == "success":
                action = "removed and local data deleted" if delete_local_data else "removed"
                return [types.TextContent(
                    type="text",
                    text=f"Torrent {torrent_id} successfully {action}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to remove torrent: {result.get('result', 'Unknown error')}"
                )]

        elif name == "start_torrent":
            torrent_id = arguments["torrent_id"]
            
            result = await transmission_client._make_request("torrent-start", {"ids": [torrent_id]})
            
            if result.get("result") == "success":
                return [types.TextContent(
                    type="text",
                    text=f"Torrent {torrent_id} started successfully"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to start torrent: {result.get('result', 'Unknown error')}"
                )]

        elif name == "stop_torrent":
            torrent_id = arguments["torrent_id"]
            
            result = await transmission_client._make_request("torrent-stop", {"ids": [torrent_id]})
            
            if result.get("result") == "success":
                return [types.TextContent(
                    type="text",
                    text=f"Torrent {torrent_id} stopped successfully"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to stop torrent: {result.get('result', 'Unknown error')}"
                )]

        elif name == "get_torrent_info":
            torrent_id = arguments["torrent_id"]
            
            result = await transmission_client._make_request("torrent-get", {
                "ids": [torrent_id],
                "fields": [
                    "id", "name", "status", "totalSize", "percentDone", "rateDownload", 
                    "rateUpload", "uploadRatio", "eta", "peersConnected", "downloadDir",
                    "error", "errorString", "addedDate", "doneDate", "trackerStats",
                    "files", "fileStats", "pieces", "pieceCount", "pieceSize"
                ]
            })
            
            if result.get("result") == "success":
                torrents = result.get("arguments", {}).get("torrents", [])
                if torrents:
                    torrent = torrents[0]
                    
                    # Format status
                    status_map = {
                        0: "Stopped", 1: "Check queued", 2: "Checking", 3: "Download queued",
                        4: "Downloading", 5: "Seed queued", 6: "Seeding"
                    }
                    status = status_map.get(torrent.get("status", 0), "Unknown")
                    
                    info = f"""Torrent Information:
Name: {torrent.get('name', 'N/A')}
ID: {torrent.get('id', 'N/A')}
Status: {status}
Size: {torrent.get('totalSize', 0) / 1024 / 1024:.2f} MB
Progress: {torrent.get('percentDone', 0) * 100:.1f}%
Download Rate: {torrent.get('rateDownload', 0) / 1024:.1f} KB/s
Upload Rate: {torrent.get('rateUpload', 0) / 1024:.1f} KB/s
Ratio: {torrent.get('uploadRatio', 0):.2f}
ETA: {torrent.get('eta', -1) if torrent.get('eta', -1) != -1 else 'Unknown'} seconds
Peers: {torrent.get('peersConnected', 0)}
Download Dir: {torrent.get('downloadDir', 'N/A')}
"""
                    if torrent.get('error'):
                        info += f"Error: {torrent.get('errorString', 'N/A')}\n"
                    
                    return [types.TextContent(type="text", text=info)]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Torrent {torrent_id} not found"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to get torrent info: {result.get('result', 'Unknown error')}"
                )]

        elif name == "set_torrent_priority":
            torrent_id = arguments["torrent_id"]
            priority = arguments["priority"]
            
            priority_map = {"high": 1, "normal": 0, "low": -1}
            priority_value = priority_map.get(priority, 0)
            
            result = await transmission_client._make_request("torrent-set", {
                "ids": [torrent_id],
                "bandwidthPriority": priority_value
            })
            
            if result.get("result") == "success":
                return [types.TextContent(
                    type="text",
                    text=f"Torrent {torrent_id} priority set to {priority}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to set priority: {result.get('result', 'Unknown error')}"
                )]

        elif name == "set_speed_limits":
            args = {}
            
            if "download_limit" in arguments:
                limit = arguments["download_limit"]
                args["speed-limit-down-enabled"] = limit > 0
                args["speed-limit-down"] = limit
                
            if "upload_limit" in arguments:
                limit = arguments["upload_limit"]
                args["speed-limit-up-enabled"] = limit > 0
                args["speed-limit-up"] = limit
            
            result = await transmission_client._make_request("session-set", args)
            
            if result.get("result") == "success":
                return [types.TextContent(
                    type="text",
                    text="Speed limits updated successfully"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to set speed limits: {result.get('result', 'Unknown error')}"
                )]

        elif name == "search_torrents":
            query = arguments["query"].lower()
            status_filter = arguments.get("status_filter", "all")
            
            result = await transmission_client._make_request("torrent-get", {
                "fields": ["id", "name", "status", "totalSize", "percentDone", "rateDownload", "rateUpload"]
            })
            
            if result.get("result") == "success":
                torrents = result.get("arguments", {}).get("torrents", [])
                
                # Filter by name
                matching_torrents = [t for t in torrents if query in t.get("name", "").lower()]
                
                # Filter by status
                if status_filter != "all":
                    status_map = {
                        "downloading": [4],
                        "seeding": [6],
                        "paused": [0],
                        "completed": [6]
                    }
                    if status_filter in status_map:
                        matching_torrents = [t for t in matching_torrents if t.get("status") in status_map[status_filter]]
                
                if matching_torrents:
                    results = []
                    for torrent in matching_torrents:
                        status_map = {
                            0: "Stopped", 1: "Check queued", 2: "Checking", 3: "Download queued",
                            4: "Downloading", 5: "Seed queued", 6: "Seeding"
                        }
                        status = status_map.get(torrent.get("status", 0), "Unknown")
                        
                        result_text = f"ID: {torrent.get('id')} | {torrent.get('name')} | Status: {status} | Progress: {torrent.get('percentDone', 0) * 100:.1f}%"
                        results.append(result_text)
                    
                    return [types.TextContent(
                        type="text",
                        text=f"Found {len(matching_torrents)} matching torrents:\n" + "\n".join(results)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="No torrents found matching the search criteria"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to search torrents: {result.get('result', 'Unknown error')}"
                )]

        elif name == "get_session_stats":
            result = await transmission_client._make_request("session-stats")
            
            if result.get("result") == "success":
                stats = result.get("arguments", {})
                
                current = stats.get("current-stats", {})
                cumulative = stats.get("cumulative-stats", {})
                
                stats_text = f"""Transmission Session Statistics:

Current Session:
- Download Speed: {current.get('downloadSpeed', 0) / 1024:.1f} KB/s
- Upload Speed: {current.get('uploadSpeed', 0) / 1024:.1f} KB/s
- Downloaded: {current.get('downloadedBytes', 0) / 1024 / 1024:.2f} MB
- Uploaded: {current.get('uploadedBytes', 0) / 1024 / 1024:.2f} MB
- Files Added: {current.get('filesAdded', 0)}
- Active Torrents: {stats.get('activeTorrentCount', 0)}
- Paused Torrents: {stats.get('pausedTorrentCount', 0)}
- Total Torrents: {stats.get('torrentCount', 0)}

Cumulative:
- Downloaded: {cumulative.get('downloadedBytes', 0) / 1024 / 1024 / 1024:.2f} GB
- Uploaded: {cumulative.get('uploadedBytes', 0) / 1024 / 1024 / 1024:.2f} GB
- Files Added: {cumulative.get('filesAdded', 0)}
- Sessions: {cumulative.get('sessionCount', 0)}
- Uptime: {cumulative.get('secondsActive', 0) / 3600:.1f} hours
"""
                
                return [types.TextContent(type="text", text=stats_text)]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to get session stats: {result.get('result', 'Unknown error')}"
                )]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
