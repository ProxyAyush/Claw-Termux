import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")

def execute_bash(command: str) -> str:
    """Executes a shell command and returns stdout/stderr combined."""
    try:
        # 120s timeout for complex operations
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
    """Surgically replaces a string in a file. Required for Senior SWE mode."""
    path = Path(file_path)
    if not path.exists():
        return f"Error: File {file_path} does not exist."
    try:
        content = path.read_text()
        if old_string not in content:
            return f"Error: Could not find exact match for 'old_string' in {file_path}."
        
        # Ensure only one replacement happens to prevent accidental corruption
        if content.count(old_string) > 1:
            return f"Error: Multiple matches found for 'old_string'. Be more specific with your context."
            
        new_content = content.replace(old_string, new_string)
        path.write_text(new_content)
        return f"Successfully updated {file_path}."
    except Exception as e:
        return f"Error: {str(e)}"

def spawn_agent(objective: str, role: str = "worker") -> str:
    """
    SWARMING MODE ($team): Launches a specialized sub-agent to handle a sub-task.
    Roles: research, worker, verification.
    """
    from .groq_client import GroqClient
    client = GroqClient()
    messages = [{"role": "user", "content": objective}]
    # Run the sub-agent loop
    return client.chat_with_tools(messages, role=role)

def mcp_tool(server: str, tool: str, arguments: Dict[str, Any]) -> str:
    """Placeholder for Model Context Protocol (MCP) tool integration."""
    return f"MCP Tool {tool} on {server} called with {arguments}. (Integration Pending)"

# --- DEFINITIONS FOR THE LLM ---
TOOLS_METADATA = [
    {
        "name": "execute_bash",
        "description": "Run any shell command in Termux. Use for git, testing, or system info.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute."}
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file with line numbers. Use start_line and end_line for large files.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "start_line": {"type": "integer", "default": 1},
                "end_line": {"type": "integer"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "edit_file",
        "description": "Surgically replace a specific block of text in a file. Provide the EXACT old_string to match.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_string": {"type": "string", "description": "Exact text to replace."},
                "new_string": {"type": "string", "description": "Replacement text."}
            },
            "required": ["file_path", "old_string", "new_string"]
        }
    },
    {
        "name": "spawn_agent",
        "description": "SWARMING MODE: Use for complex sub-tasks. Objective should be a clear prompt for the agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "role": {"type": "string", "enum": ["worker", "research", "verification"], "default": "worker"}
            },
            "required": ["objective"]
        }
    },
    {
        "name": "glob_files",
        "description": "Find files matching a pattern (e.g. src/**/*.py).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"}
            },
            "required": ["pattern"]
        }
    }
]

def handle_tool_call(name: str, args: Dict[str, Any]) -> str:
    if name == "execute_bash": return execute_bash(args["command"])
    if name == "read_file": return read_file(args["file_path"], args.get("start_line", 1), args.get("end_line"))
    if name == "edit_file": return edit_file(args["file_path"], args["old_string"], args["new_string"])
    if name == "spawn_agent": return spawn_agent(args["objective"], args.get("role", "worker"))
    if name == "glob_files":
        import glob
        files = glob.glob(args["pattern"], recursive=True)
        return "\n".join(files) if files else "No files found."
    return f"Unknown tool: {name}"
