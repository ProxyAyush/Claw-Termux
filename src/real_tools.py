import subprocess
import os
import glob
import re
import httpx
import json
from typing import Dict, Any, List, Optional
from .mcp_client import call_mcp_tool

def execute_bash(command: str) -> str:
    """Executes a bash command in Termux and returns the output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        return output if output else "(Success, but no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(path: str, start_line: int = 1, end_line: int = None) -> str:
    """Reads a file with line numbers. Supports range reading to avoid truncation."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
        with open(abs_path, 'r') as f:
            lines = f.readlines()
        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line if end_line else total_lines)
        selected_lines = lines[start_idx:end_idx]
        numbered_lines = [f"{start_idx + i + 1}: {line}" for i, line in enumerate(selected_lines)]
        output = "".join(numbered_lines)
        if end_idx < total_lines:
            output += f"\n... [File truncated. Total lines: {total_lines}. Use start_line/end_line to read more] ..."
        return output
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Creates a new file or overwrites an existing one."""
    try:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file: {str(e)}"

def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Surgically replaces old_string with new_string in a file."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
        with open(abs_path, 'r') as f:
            content = f.read()
        if old_string not in content:
            return f"Error: Could not find exact match for 'old_string'. The Edit tool requires an EXACT match (whitespace/indentation). Read the file again to confirm current state."
        if content.count(old_string) > 1:
            return f"Error: 'old_string' is not unique ({content.count(old_string)} matches). Provide more surrounding context lines."
        new_content = content.replace(old_string, new_string)
        with open(abs_path, 'w') as f:
            f.write(new_content)
        return f"Successfully edited {path}. RE-READ the file to verify the change if this was a complex edit."
    except Exception as e:
        return f"Error editing file: {str(e)}"

def glob_files(pattern: str) -> str:
    """Finds files matching a glob pattern."""
    try:
        files = glob.glob(pattern, recursive=True)
        return "\n".join(files) if files else "No matches found."
    except Exception as e:
        return f"Error globbing files: {str(e)}"

def grep_files(pattern: str, path: str = ".") -> str:
    """Searches for a regex pattern in file contents."""
    try:
        cmd = f"grep -rnE \"{pattern}\" {path} | head -n 100"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout
        if not output:
            return "No matches found."
        line_count = output.count('\n')
        if line_count >= 100:
            output += "\n... [Search results truncated at 100 matches. Use narrower scope or more specific regex] ..."
        return output
    except Exception as e:
        return f"Error grepping files: {str(e)}"

def web_fetch(url: str) -> str:
    """Fetches the content of a URL."""
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def spawn_agent(prompt: str, subagent_type: str = "worker") -> str:
    """Spawns a specialized sub-agent (worker, verification, explore)."""
    from .groq_client import GroqClient
    print(f"\n[🚀 Spawning {subagent_type} agent...]")
    client = GroqClient()
    messages = [{"role": "user", "content": prompt}]
    # Handle specialized role instructions
    if subagent_type == "verification":
        messages.insert(0, {"role": "system", "content": "You are a VERIFICATION agent. Your only job is to try to break the code. DO NOT modify files. End with VERDICT: PASS or FAIL."})
    elif subagent_type == "explore":
        messages.insert(0, {"role": "system", "content": "You are an EXPLORE agent. Your job is READ-ONLY research. DO NOT modify files."})
    else:
        messages.insert(0, {"role": "system", "content": "You are a WORKER agent. Your job is to implement the task and self-verify."})
        
    result = client.chat_with_tools(messages)
    return f"\n--- {subagent_type.upper()} AGENT RESULT ---\n{result}\n--- END AGENT RESULT ---"

# Tools Metadata
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a shell command. Use for system tasks, git, or verification.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with line numbers. Use for files >500 LOC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgically replace a UNIQUE string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files by pattern.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Search file contents with regex.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch raw URL content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_agent",
            "description": "Launch a specialized agent (worker, verification, explore) to handle a sub-task autonomously.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The detailed task for the agent"},
                    "subagent_type": {"type": "string", "enum": ["worker", "verification", "explore"]}
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_tool",
            "description": "Call a tool from an external MCP server (google_search, github, postgres).",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_name": {"type": "string"},
                    "tool_name": {"type": "string"},
                    "arguments": {"type": "object"}
                },
                "required": ["server_name", "tool_name", "arguments"]
            }
        }
    }
]

def handle_tool_call(name: str, args: dict) -> str:
    if name == "execute_bash":
        return execute_bash(args.get("command", ""))
    elif name == "read_file":
        return read_file(args.get("path", ""), args.get("start_line", 1), args.get("end_line"))
    elif name == "write_file":
        return write_file(args.get("path", ""), args.get("content", ""))
    elif name == "edit_file":
        return edit_file(args.get("path", ""), args.get("old_string", ""), args.get("new_string", ""))
    elif name == "glob_files":
        return glob_files(args.get("pattern", ""))
    elif name == "grep_files":
        return grep_files(args.get("pattern", ""), args.get("path", "."))
    elif name == "web_fetch":
        return web_fetch(args.get("url", ""))
    elif name == "spawn_agent":
        return spawn_agent(args.get("prompt", ""), args.get("subagent_type", "worker"))
    elif name == "mcp_tool":
        return call_mcp_tool(args.get("server_name", ""), args.get("tool_name", ""), args.get("arguments", {}))
    return f"Unknown tool: {name}"
