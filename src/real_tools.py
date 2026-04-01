import os
import json
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DDGR_PATH = "/data/data/com.termux/files/home/bin/ddgr"

def execute_bash(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120.0)
        return (result.stdout + "\n" + result.stderr).strip()
    except Exception as e: return f"Error: {str(e)}"

def list_dir(path: str = ".") -> str:
    """High-signal directory listing."""
    try:
        cmd = f"ls -F '{path}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        if result.returncode != 0: return f"Error: {result.stderr}"
        return result.stdout.strip() if result.stdout else "(Empty directory)"
    except Exception as e: return f"Error: {str(e)}"

def read_file(file_path: str, start_line: int = 1, end_line: int = None) -> str:
    path = Path(file_path)
    if not path.exists(): return f"Error: File {file_path} does not exist."
    try:
        lines = path.read_text().splitlines()
        if end_line is None: end_line = len(lines)
        subset = lines[start_line-1:end_line]
        return "\n".join([f"{start_line + i:4} | {line}" for i, line in enumerate(subset)])
    except Exception as e: return f"Error: {str(e)}"

def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    path = Path(file_path)
    if not path.exists(): return f"Error: File {file_path} does not exist."
    try:
        content = path.read_text()
        if old_string not in content: return "Error: Match not found."
        if content.count(old_string) > 1: return "Error: Multiple matches."
        path.write_text(content.replace(old_string, new_string))
        return f"Successfully updated {file_path}."
    except Exception as e: return f"Error: {str(e)}"

def google_search(query: str) -> str:
    """Elite Search using the robust 'ddgr' engine."""
    try:
        # Check if ddgr exists
        if not os.path.exists(DDGR_PATH):
            # Try to install it if missing
            subprocess.run(f"mkdir -p {os.path.dirname(DDGR_PATH)} && curl -skL https://raw.githubusercontent.com/jarun/ddgr/master/ddgr > {DDGR_PATH} && chmod +x {DDGR_PATH}", shell=True)
        
        cmd = f"{DDGR_PATH} --json '{query}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        
        if result.returncode != 0: return "Error: ddgr search failed."
            
        data = json.loads(result.stdout)
        formatted = []
        for i, res in enumerate(data[:8]):
            formatted.append(f"{i+1}. {res['title']}\n   Snippet: {res['abstract']}\n   Link: {res['url']}")
        return "\n\n".join(formatted) if formatted else "No results found."
    except Exception as e: return f"Error: Search failed: {str(e)}"

def web_fetch(url: str) -> str:
    try:
        cmd = f"curl -skL -A '{USER_AGENT}' '{url}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        content = re.sub(r'<(script|style).*?>.*?</\1>', '', result.stdout, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<.*?>', ' ', content, flags=re.DOTALL)
        return re.sub(r'\s+', ' ', content).strip()[:8000]
    except Exception as e: return f"Error: {str(e)}"

def spawn_agent(objective: str, role: str = "worker") -> str:
    from .groq_client import GroqClient
    client = GroqClient()
    return client.chat_with_tools([{"role": "user", "content": objective}], role=role)

TOOLS_METADATA = [
    {"type": "function", "function": {"name": "execute_bash", "description": "Run shell commands.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "list_dir", "description": "List files and folders (folders end with /).", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "google_search", "description": "Elite research search tool.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "Read full text content of a URL.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Edit a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["file_path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "glob_files", "description": "Find files.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}}
]

def handle_tool_call(name: str, args: Dict[str, Any]) -> str:
    if name == "execute_bash": return execute_bash(args["command"])
    if name == "list_dir": return list_dir(args.get("path", "."))
    if name == "google_search": return google_search(args["query"])
    if name == "web_fetch": return web_fetch(args["url"])
    if name == "read_file": return read_file(args.get("file_path"))
    if name == "edit_file": return edit_file(args.get("file_path"), args.get("old_string"), args.get("new_string"))
    if name == "glob_files":
        import glob
        files = glob.glob(args.get("pattern", "*"), recursive=True)
        return "\n".join(files) if files else "No files found."
    return f"Unknown tool: {name}"
