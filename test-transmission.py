#!/usr/bin/env python3
"""
Test script for Transmission MCP Server

This script tests the connectivity to the Transmission daemon and verifies
that the MCP server can successfully communicate with it.
"""

import asyncio
import json
import os
from transmission_server import TransmissionClient

async def test_transmission():
    """Test basic Transmission connectivity"""
    # Use environment variables or defaults
    host = os.getenv("TRANSMISSION_HOST", "localhost")
    port = int(os.getenv("TRANSMISSION_PORT", "9091"))
    url = f"http://{host}:{port}/transmission/rpc"
    
    print(f"Testing connection to: {url}")
    client = TransmissionClient(url)
    
    try:
        print("Testing Transmission connection...")
        
        # Test session info
        result = await client._make_request("session-get")
        print(f"✅ Session connection successful!")
        print(f"Session ID obtained: {client.session_id is not None}")
        
        # Test getting torrents
        result = await client._make_request("torrent-get", {
            "fields": ["id", "name", "status", "totalSize", "percentDone"]
        })
        
        torrents = result.get("arguments", {}).get("torrents", [])
        print(f"✅ Found {len(torrents)} torrents")
        
        # Print first few torrents as example
        for i, torrent in enumerate(torrents[:3]):
            status_map = {
                0: "Stopped", 1: "Check queued", 2: "Checking", 3: "Download queued",
                4: "Downloading", 5: "Seed queued", 6: "Seeding"
            }
            status = status_map.get(torrent.get("status", 0), "Unknown")
            print(f"  {i+1}. {torrent.get('name', 'N/A')} - {status} - {torrent.get('percentDone', 0) * 100:.1f}%")
        
        # Test session stats
        result = await client._make_request("session-stats")
        stats = result.get("arguments", {})
        print(f"✅ Session stats retrieved")
        print(f"  Active torrents: {stats.get('activeTorrentCount', 0)}")
        print(f"  Total torrents: {stats.get('torrentCount', 0)}")
        
        print("\n🎉 All tests passed! Transmission MCP server should work correctly.")
        
    except Exception as e:
        print(f"❌ Error testing Transmission connection: {e}")
        print("Please check:")
        print(f"- Transmission daemon is running on {host}:{port}")
        print("- RPC is enabled in Transmission settings")
        print("- Network connectivity to the server")
        print("- Set TRANSMISSION_HOST and TRANSMISSION_PORT environment variables if needed")

if __name__ == "__main__":
    asyncio.run(test_transmission())
