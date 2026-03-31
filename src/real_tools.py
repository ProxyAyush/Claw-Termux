import subprocess
import os

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
    """Reads the content of a file."""
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' does not exist."
        with open(abs_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Writes content to a file, creating directories if needed."""
    try:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file: {str(e)}"

def list_dir(path: str = ".") -> str:
    """Lists files and folders in a directory."""
    try:
        abs_path = os.path.abspath(path)
        files = os.listdir(abs_path)
        return "\n".join(files) if files else "(Empty directory)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

# Tools Metadata for Groq/OpenAI format
TOOLS_METADATA = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Execute a shell command in Termux (e.g. ls, grep, pkg install, git)",
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
            "description": "Read the contents of a file",
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
            "description": "Create a new file or overwrite an existing one",
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
            "name": "list_dir",
            "description": "List files and folders in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to list (defaults to '.')"}
                }
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
    elif name == "list_dir":
        return list_dir(args.get("path", "."))
    return f"Unknown tool: {name}"
