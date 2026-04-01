import os
import httpx
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.status import Status
from rich.markdown import Markdown
from .real_tools import TOOLS_METADATA, handle_tool_call

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")
console = Console()

class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        key_file = REPO_ROOT / ".groq_api_key"
        if not self.api_key and key_file.exists():
            self.api_key = key_file.read_text().strip()

        self.model = model or os.environ.get("GROQ_MODEL")
        model_file = REPO_ROOT / ".groq_model"
        if not self.model and model_file.exists():
            self.model = model_file.read_text().strip()
        if not self.model:
            self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

        self.base_url = os.environ.get("GROQ_API_URL")
        url_file = REPO_ROOT / ".groq_api_url"
        if not self.base_url and url_file.exists():
            self.base_url = url_file.read_text().strip()
        if not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        self.memory_context = self._load_memory()

        # The "EMPLOYEE-GRADE" Master System Prompt
        self.master_system_prompt = """You are Clawt, an interactive agent specializing in high-end software engineering. 

# Agent Directives: Mechanical Overrides
1. THE "STEP 0" RULE: Before ANY structural refactor on a file >300 LOC, first remove all dead code (props, imports, logs).
2. PHASED EXECUTION: Max 5 files per phase. Verify after each phase.
3. FILE READ BUDGET: Use read_file with start_line/end_line for files >500 LOC.
4. THE SENIOR DEV OVERRIDE: Propose structural fixes if architecture is flawed. Don't be lazy.
5. FORCED VERIFICATION: Forbidden from reporting complete until tests/type-checks pass.
6. EDIT INTEGRITY: Re-read before and after every edit.

# Using Your Tools
- Use dedicated tools (read_file, edit_file, glob_files, grep_files) instead of bash for file operations.
- Parallelize independent tool calls.
- Use `spawn_agent` for complex sub-tasks ($team mode).
- Use `mcp_tool` for external knowledge (GitHub/Search).

# Tone and Style
- Be extra concise. Lead with the action.
- Use file_path:line_number for references.

{memory_instruction}
"""

    def _load_memory(self) -> str:
        """Discovers CLAWT.md files from current directory up to root."""
        memory_content = []
        user_memory = Path.home() / ".clawt" / "CLAWT.md"
        if user_memory.exists():
            memory_content.append(f"--- GLOBAL USER RULES ---\n{user_memory.read_text()}\n")
        project_memory = REPO_ROOT / "CLAWT.md"
        if project_memory.exists():
            memory_content.append(f"--- PROJECT RULES (Clawt) ---\n{project_memory.read_text()}\n")
        return "\n".join(memory_content) if memory_content else ""

    def get_system_prompt(self, role: str = "coordinator") -> str:
        memory_instr = ""
        if self.memory_context:
            memory_instr = f"\n# Memory & User Instructions\n{self.memory_context}\nIMPORTANT: Adhere to these instructions exactly as written. They OVERRIDE default behavior."
        base = self.master_system_prompt.format(memory_instruction=memory_instr)
        
        if role == "verification":
            return base + "\n\n# VERIFICATION ROLE: Adversarial testing specialist. DO NOT modify files. Run adversarial probes (boundary, concurrency). End with VERDICT: PASS or FAIL."
        if role == "explore":
            return base + "\n\n# EXPLORE ROLE: Read-only search specialist. Optimized for speed and thoroughness. DO NOT modify files."
        if role == "worker":
            return base + "\n\n# WORKER ROLE: Implementation specialist. Follow the spec exactly. Self-verify your work before reporting."
        return base

    def _get_headers(self) -> Dict[str, str]:
        if "anthropic" in self.base_url.lower() and "messages" in self.base_url.lower():
            return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _compact_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ensures the message history doesn't exceed API limits by keeping only recent turns."""
        if len(messages) <= 15:
            return messages
        # Always keep the system prompt (at index 0)
        compacted = [messages[0]]
        # Keep the 14 most recent messages
        compacted.extend(messages[-14:])
        return compacted

    def chat(self, messages: List[Dict[str, str]], role: str = "coordinator") -> Dict[Any, Any]:
        if not self.api_key: raise ValueError("API Key not set. Run setup.")
        
        # Inject system prompt if not present
        if not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.get_system_prompt(role)})

        # Compact history to prevent 413 Payload Too Large
        messages = self._compact_messages(messages)

        headers = self._get_headers()
        payload = {"model": self.model, "messages": messages, "tools": TOOLS_METADATA, "tool_choice": "auto"}
        
        # Exponential Backoff for 429 errors
        max_retries = 3
        retry_delay = 2 # seconds
        
        for attempt in range(max_retries):
            with httpx.Client() as client:
                try:
                    response = client.post(self.base_url, headers=headers, json=payload, timeout=120.0)
                    if response.status_code == 400:
                        # Detailed 400 Diagnostics
                        error_body = response.text
                        raise httpx.HTTPStatusError(f"400 Bad Request: {error_body}", request=response.request, response=response)
                    
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise e

    def chat_with_tools(self, messages: List[Dict[str, str]], role: str = "coordinator", stream_callback=None):
        MAX_ITERATIONS = 15
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            try:
                # Elite "Thinking" status
                with Status(f"[bold blue]Clawt thinking... ({iteration}/{MAX_ITERATIONS})", console=console) as status:
                    response = self.chat(messages, role)
                    message = response["choices"][0]["message"]
                    messages.append(message)

                if message.get("content"):
                    if stream_callback: stream_callback(message["content"])
                    else: console.print(Markdown(message["content"]))

                if not message.get("tool_calls"):
                    return message.get("content", "")

                for tool_call in message["tool_calls"]:
                    name = tool_call["function"]["name"]
                    try: args = json.loads(tool_call["function"]["arguments"])
                    except: args = {}
                    
                    # Elite Tool Rendering
                    if name == "execute_bash":
                        cmd = args.get("command", "")
                        console.print(Panel(f"[bold cyan]$ {cmd}", title="🛠️ Clawt Shell", border_style="cyan"))
                    else:
                        console.print(f"[bold magenta]⚡ Clawt: {name}[/bold magenta]")

                    # Execute Tool
                    result = handle_tool_call(name, args)
                    
                    # Tool Result Rendering
                    if not isinstance(result, str): result = str(result)
                    
                    if name == "execute_bash":
                        preview = result[:800] + "..." if len(result) > 800 else result
                        console.print(Panel(preview, title="📝 Output", border_style="dim"))

                    # Aggressive Truncation for Tool Results
                    if len(result) > 8000:
                        result = result[:8000] + "\n... [Output truncated to prevent Payload Too Large error] ..."
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": name,
                        "content": result
                    })
                    
                    console.print(f"[bold green]✓ Done[/bold green]")
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 413:
                    if len(messages) > 2:
                        messages = [messages[0], messages[-1]]
                        continue
                raise e
        return "Max iterations reached."
        
    def stream_chat(self, messages: List[Dict[str, str]], role: str = "coordinator"):
        output_chunks = []
        def callback(text):
            if text:
                console.print(text, end="", flush=True)
                output_chunks.append(text)
        self.chat_with_tools(messages, role, stream_callback=callback)
        yield "".join(output_chunks)
