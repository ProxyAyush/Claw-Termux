import subprocess
import os
import glob
import re
import httpx

def execute_bash(command: str) -> str:
    """Executes a bash command in Termux and returns the output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
        return output if output else "(Success, but no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def read_file(path: str) -> str:
    """Reads the content of a file with line numbers."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
        with open(abs_path, 'r') as f:
            lines = f.readlines()
            # Add line numbers for surgical edits
            numbered_lines = [f"{i+1}: {line}" for i, line in enumerate(lines)]
            return "".join(numbered_lines)
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
            return f"Error: Could not find exact match for 'old_string'. Ensure you have read the file and provided the exact text including whitespace."
        
        if content.count(old_string) > 1:
            return f"Error: 'old_string' is not unique. Provide more context to identify the specific location."
            
        new_content = content.replace(old_string, new_string)
        with open(abs_path, 'w') as f:
            f.write(new_content)
        return f"Successfully edited {path}"
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
        # Use native grep for speed in Termux
        cmd = f"grep -rnE \"{pattern}\" {path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout if result.stdout else "No matches found."
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

# Tools Metadata for Groq/OpenAI format
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a shell command in Termux. Reserve for system commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with line numbers. Essential before editing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file. Use 'edit_file' instead for modifying existing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgically replace a unique string in a file. Requires exact match of 'old_string'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "old_string": {"type": "string", "description": "The exact string to be replaced"},
                    "new_string": {"type": "string", "description": "The string to replace it with"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files by pattern matching (e.g. src/**/*.py).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "The glob pattern"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_files",
            "description": "Search file contents using a regex pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern"},
                    "path": {"type": "string", "description": "Path to search (defaults to '.')"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch the raw content of a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"}
                },
                "required": ["url"]
            }
        }
    }
]

def handle_tool_call(name: str, args: dict) -> str:
    if name == "execute_bash":
        return execute_bash(args.get("command", ""))
    elif name == "read_file":
        return read_file(args.get("path", ""))
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
    return f"Unknown tool: {name}"
