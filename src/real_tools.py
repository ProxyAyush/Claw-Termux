import os
import json
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, List

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")

def execute_bash(command: str) -> str:
    """Executes a shell command and returns stdout/stderr combined."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120.0
        )
        return (result.stdout + "\n" + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error: {str(e)}"

def read_file(file_path: str, start_line: int = 1, end_line: int = None) -> str:
    """Reads a file with line numbers and optional range."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File {file_path} does not exist."
    try:
        lines = path.read_text().splitlines()
        if end_line is None:
            end_line = len(lines)
        subset = lines[start_line-1:end_line]
        output = []
        for i, line in enumerate(subset):
            output.append(f"{start_line + i:4} | {line}")
        return "\n".join(output)
    except Exception as e:
        return f"Error: {str(e)}"

def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Surgically replaces a string in a file."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File {file_path} does not exist."
    try:
        content = path.read_text()
        if old_string not in content:
            return f"Error: Could not find exact match for 'old_string' in {file_path}."
        if content.count(old_string) > 1:
            return f"Error: Multiple matches found for 'old_string'. Be more specific with your context."
        new_content = content.replace(old_string, new_string)
        path.write_text(new_content)
        return f"Successfully updated {file_path}."
    except Exception as e:
        return f"Error: {str(e)}"

def web_search(query: str) -> str:
    """Performs a web search using DuckDuckGo (lite version for Termux compatibility)."""
    try:
        # Use curl to fetch text results from DuckDuckGo lite
        cmd = f"curl -sL 'https://lite.duckduckgo.com/lite/search?q={query.replace(' ', '+')}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        
        if result.returncode != 0:
            return "Error: Failed to fetch search results."
            
        # Basic parsing of the HTML to extract links and titles
        html = result.stdout
        # Extract titles and links (DuckDuckGo Lite uses <a> tags for results)
        matches = re.findall(r'<a rel="nofollow" href="([^"]+)">([^<]+)</a>', html)
        
        formatted_results = []
        for i, (url, title) in enumerate(matches[:8]): # Top 8 results
            if "duckduckgo.com" not in url:
                formatted_results.append(f"{i+1}. {title}\n   Link: {url}")
        
        return "\n\n".join(formatted_results) if formatted_results else "No relevant search results found."
    except Exception as e:
        return f"Error: Web search failed: {str(e)}"

def web_fetch(url: str) -> str:
    """Fetches the text content of a URL (removes HTML tags)."""
    try:
        # Use curl and then strip tags using regex
        cmd = f"curl -sL '{url}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        
        if result.returncode != 0:
            return f"Error: Failed to fetch content from {url}."
            
        content = result.stdout
        # Remove script and style tags
        content = re.sub(r'<(script|style).*?>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE)
        # Remove all other tags
        content = re.sub(r'<.*?>', ' ', content, flags=re.DOTALL)
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content[:5000] # Return first 5000 chars for context management
    except Exception as e:
        return f"Error: Failed to fetch {url}: {str(e)}"

def spawn_agent(objective: str, role: str = "worker") -> str:
    """SWARMING MODE ($team): Launches a specialized sub-agent."""
    from .groq_client import GroqClient
    client = GroqClient()
    messages = [{"role": "user", "content": objective}]
    return client.chat_with_tools(messages, role=role)

# --- CORRECTED TOOL SCHEMA FOR GEMINI/OPENAI ---
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Run any shell command in Termux. Use for git, testing, or system operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a real-time web search for information, documentation, or latest tech fixes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Retrieve and read the text content of a specific URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "start_line": {"type": "integer", "default": 1},
                    "end_line": {"type": "integer"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgically replace a specific block of text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"}
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_agent",
            "description": "SWARMING MODE: Use for complex sub-tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "objective": {"type": "string"},
                    "role": {"type": "string", "enum": ["worker", "research", "verification"], "default": "worker"}
                },
                "required": ["objective"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files matching a pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    }
]

def handle_tool_call(name: str, args: Dict[str, Any]) -> str:
    if name == "execute_bash": return execute_bash(args["command"])
    if name == "web_search": return web_search(args["query"])
    if name == "web_fetch": return web_fetch(args["url"])
    if name == "read_file": return read_file(args["file_path"], args.get("start_line", 1), args.get("end_line"))
    if name == "edit_file": return edit_file(args["file_path"], args["old_string"], args["new_string"])
    if name == "spawn_agent": return spawn_agent(args["objective"], args.get("role", "worker"))
    if name == "glob_files":
        import glob
        files = glob.glob(args["pattern"], recursive=True)
        return "\n".join(files) if files else "No files found."
    return f"Unknown tool: {name}"
