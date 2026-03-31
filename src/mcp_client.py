import subprocess
import json
import os
import threading
from typing import Dict, Any, List, Optional

class McpClient:
    """A simple MCP (Model Context Protocol) client for Clawt."""
    
    def __init__(self, command: List[str]):
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def _ensure_process(self):
        if self.process is None or self.process.poll() is not None:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        with self._lock:
            try:
                self._ensure_process()
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments}
                }
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                
                response_line = self.process.stdout.readline()
                if not response_line:
                    return "Error: MCP server returned empty response."
                
                response = json.loads(response_line)
                if "error" in response:
                    return f"MCP Error: {json.dumps(response['error'])}"
                
                result = response.get("result", {})
                # MCP results are usually a list of content blocks
                content = result.get("content", [])
                text_results = [c.get("text", "") for c in content if c.get("type") == "text"]
                return "\n".join(text_results) if text_results else str(result)
                
            except Exception as e:
                return f"Error calling MCP tool: {str(e)}"

# Global registry of MCP servers for Clawt
# In a real app, these would be loaded from a config file
MCP_SERVERS = {
    "google_search": ["npx", "-y", "@modelcontextprotocol/server-google-search"],
    "github": ["npx", "-y", "@modelcontextprotocol/server-github"],
    "postgres": ["npx", "-y", "@modelcontextprotocol/server-postgres"],
}

_active_clients: Dict[str, McpClient] = {}

def call_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
    if server_name not in MCP_SERVERS:
        return f"Error: MCP server '{server_name}' not configured."
    
    if server_name not in _active_clients:
        _active_clients[server_name] = McpClient(MCP_SERVERS[server_name])
        
    return _active_clients[server_name].call_tool(tool_name, arguments)
