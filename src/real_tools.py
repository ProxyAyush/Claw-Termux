import os
import json
import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def execute_bash(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120.0)
        return (result.stdout + "\n" + result.stderr).strip()
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
    """Hybrid Elite Search: High-fidelity results using a robust bot-proof engine."""
    try:
        # Use Lite mode for 100% reliability in Termux
        url = f"https://lite.duckduckgo.com/lite/search?q={query.replace(' ', '+')}"
        cmd = f"curl -skL -A '{USER_AGENT}' '{url}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30.0)
        
        # High-fidelity parsing of titles and external links
        links = re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', result.stdout)
        
        formatted = []
        for i, (link, title) in enumerate(links):
            if "duckduckgo.com" not in link and not link.startswith("/") and len(formatted) < 8:
                clean_title = re.sub(r'<.*?>', '', title).strip()
                # Extract source name from link
                source = link.split("//")[-1].split("/")[0]
                formatted.append(f"{len(formatted)+1}. {clean_title}\n   Source: {source}\n   Link: {link}")
        
        return "\n\n".join(formatted) if formatted else "No results found. (Check internet connection)"
    except Exception as e: return f"Error: Search engine failure: {str(e)}"

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
    {"type": "function", "function": {"name": "google_search", "description": "High-grade research tool for elite documentation and tech fixes.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "Read full text content of a URL.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Edit a file.", "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["file_path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "glob_files", "description": "Find files.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}}
]

def handle_tool_call(name: str, args: Dict[str, Any]) -> str:
    if name == "execute_bash": return execute_bash(args["command"])
    if name == "google_search": return google_search(args["query"])
    if name == "web_fetch": return web_fetch(args["url"])
    if name == "read_file": return read_file(args.get("file_path"))
    if name == "edit_file": return edit_file(args.get("file_path"), args.get("old_string"), args.get("new_string"))
    if name == "glob_files":
        import glob
        files = glob.glob(args.get("pattern", "*"), recursive=True)
        return "\n".join(files) if files else "No files found."
    return f"Unknown tool: {name}"
