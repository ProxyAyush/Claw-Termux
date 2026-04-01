import os
import httpx
import json
import time
import questionary
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
        # Load from absolute file paths
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        key_file = REPO_ROOT / ".groq_api_key"
        if not self.api_key and key_file.exists():
            self.api_key = key_file.read_text().strip()

        self.model = model or os.environ.get("GROQ_MODEL")
        model_file = REPO_ROOT / ".groq_model"
        if not self.model and model_file.exists():
            self.model = model_file.read_text().strip()
        if not self.model:
            self.model = "gemini-2.0-flash"

        self.base_url = os.environ.get("GROQ_API_URL")
        url_file = REPO_ROOT / ".groq_api_url"
        if not self.base_url and url_file.exists():
            self.base_url = url_file.read_text().strip()
        
        # --- DEFINITIVE GEMINI OPENAI-SHIM FIX ---
        if self.base_url and "generativelanguage.googleapis.com" in self.base_url:
            # The OpenAI-compatible base URL should end with /openai/
            if not self.base_url.endswith("/openai/"):
                if "/openai/chat/completions" in self.base_url:
                    self.base_url = self.base_url.split("/chat/completions")[0]
                elif not self.base_url.endswith("/"):
                    self.base_url += "/"
            
            # OpenAI shim does NOT want the "models/" prefix
            if self.model.startswith("models/"):
                self.model = self.model.replace("models/", "")
        
        if not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        self.yolo_mode = False 
        self.memory_context = self._load_memory()

        # The "EMPLOYEE-GRADE" Master System Prompt
        self.master_system_prompt = """You are Clawt, an interactive agent specializing in high-end software engineering. 

# Agent Directives: Mechanical Overrides
1. THE "STEP 0" RULE: Before ANY structural refactor on a file >300 LOC, first remove all dead code.
2. PHASED EXECUTION: Max 5 files per phase. Verify after each phase.
3. FILE READ BUDGET: Use read_file with start_line/end_line for files >500 LOC.
4. FORCED VERIFICATION: Forbidden from reporting complete until tests/type-checks pass.

# Using Your Tools
- Use dedicated tools instead of bash for file operations.
- Use `execute_bash` for Termux operations and Android file access (e.g. ls /sdcard).
- Use `web_search` to stay up-to-date with 2026 tech.

{memory_instruction}
"""

    def _load_memory(self) -> str:
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
            memory_instr = f"\n# Memory & User Instructions\n{self.memory_context}"
        return self.master_system_prompt.format(memory_instruction=memory_instr)

    def _get_headers(self) -> Dict[str, str]:
        # Gemini OpenAI shim uses standard Bearer token
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _compact_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(messages) <= 12: return messages
        return [messages[0], messages[1]] + messages[-10:]

    def chat(self, messages: List[Dict[str, str]], role: str = "coordinator") -> Dict[Any, Any]:
        if not self.api_key: raise ValueError("API Key not set. Run setup.")
        if not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.get_system_prompt(role)})
        
        messages = self._compact_messages(messages)
        headers = self._get_headers()
        payload = {"model": self.model, "messages": messages, "tools": TOOLS_METADATA, "tool_choice": "auto"}
        
        # Determine the full URL
        full_url = self.base_url
        if not full_url.endswith("chat/completions"):
            if not full_url.endswith("/"): full_url += "/"
            full_url += "chat/completions"

        for attempt in range(3):
            with httpx.Client() as client:
                try:
                    response = client.post(full_url, headers=headers, json=payload, timeout=120.0)
                    if response.status_code == 400:
                        error_body = response.text
                        raise httpx.HTTPStatusError(f"400: {error_body}", request=response.request, response=response)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < 2:
                        time.sleep(3 * (attempt + 1))
                        continue
                    raise e

    def chat_with_tools(self, messages: List[Dict[str, str]], role: str = "coordinator", stream_callback=None):
        MAX_ITERATIONS = 15
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            try:
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
                    
                    is_sensitive = name in ["execute_bash", "edit_file", "web_search", "web_fetch", "spawn_agent"]
                    if is_sensitive:
                        if name == "execute_bash":
                            display = f"[bold cyan]$ {args.get('command')}"
                        elif name == "web_search":
                            display = f"[bold yellow]Searching: {args.get('query')}"
                        else:
                            display = f"[bold magenta]⚡ {name}({args})"

                        console.print(Panel(display, title=f"🛡️  Clawt Request: {name}", border_style="yellow"))
                        
                        if not self.yolo_mode:
                            choice = questionary.select(
                                "Allow this action?",
                                choices=[
                                    {"name": "Allow Once", "value": "y"},
                                    {"name": "Always for this Session", "value": "a"},
                                    {"name": "Edit Command", "value": "e"},
                                    {"name": "Deny", "value": "n"},
                                    {"name": "Quit", "value": "q"}
                                ],
                                default="y"
                            ).ask()

                            if choice == "n":
                                result = "Error: User denied permission for this action."
                            elif choice == "e":
                                if name == "execute_bash":
                                    args["command"] = questionary.text("Edit command:", default=args.get("command", "")).ask()
                                elif name == "web_search":
                                    args["query"] = questionary.text("Edit search query:", default=args.get("query", "")).ask()
                                result = handle_tool_call(name, args)
                            elif choice == "a":
                                self.yolo_mode = True
                                result = handle_tool_call(name, args)
                            elif choice == "q":
                                console.print("[bold red]Quitting session.[/bold red]")
                                return "User terminated session."
                            else:
                                result = handle_tool_call(name, args)
                        else:
                            result = handle_tool_call(name, args)
                    else:
                        if not self.yolo_mode:
                            console.print(f"[dim]⚡ Clawt: {name}[/dim]")
                        result = handle_tool_call(name, args)

                    if not isinstance(result, str): result = str(result)
                    if name == "execute_bash":
                        preview = result[:800] + "..." if len(result) > 800 else result
                        console.print(Panel(preview, title="📝 Output", border_style="dim"))

                    if len(result) > 8000:
                        result = result[:8000] + "\n... [Output truncated] ..."
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": name,
                        "content": result
                    })
                    console.print(f"[bold green]✓ Action Complete[/bold green]")
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 413:
                    if len(messages) > 3:
                        messages = [messages[0], messages[1], messages[-1]]
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
