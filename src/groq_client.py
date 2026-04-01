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
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        key_file = REPO_ROOT / ".groq_api_key"
        if not self.api_key and key_file.exists():
            self.api_key = key_file.read_text().strip()

        self.model = model or os.environ.get("GROQ_MODEL")
        model_file = REPO_ROOT / ".groq_model"
        if not self.model and model_file.exists():
            self.model = model_file.read_text().strip()
        if not self.model:
            self.model = "gemini-3.1-flash-lite-preview" 

        self.base_url = os.environ.get("GROQ_API_URL")
        url_file = REPO_ROOT / ".groq_api_url"
        if not self.base_url and url_file.exists():
            self.base_url = url_file.read_text().strip()
        
        if not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"

        self.provider = self._detect_provider()
        
        # --- DEFINITIVE NORMALIZATION ---
        if self.provider == "Google Gemini":
            if "/chat/completions" in self.base_url:
                self.base_url = self.base_url.split("/chat/completions")[0]
            if not self.base_url.endswith("/"): self.base_url += "/"
            if "openai" not in self.base_url: self.base_url += "openai/"
            if self.model.startswith("models/"):
                self.model = self.model.replace("models/", "")
        
        self.yolo_mode = False 
        self.slow_mode = True # Enabled by default for Free Tier safety
        self._last_request_time = 0
        self._tokens_used = 0
        
        self.memory_context = self._load_memory()

        self.master_system_prompt = """You are Clawt, an interactive agent specializing in high-end software engineering. 

# Agent Directives
1. THE "STEP 0" RULE: Before ANY structural refactor on a file >300 LOC, first remove all dead code.
2. PHASED EXECUTION: Max 5 files per phase. Verify after each phase.
3. FORCED VERIFICATION: Forbidden from reporting complete until tests/type-checks pass.

# Using Your Tools
- Use `list_dir` to explore directories. Folders end with /.
- Use `google_search` for technical indexing.
- Use `execute_bash` for Termux operations and Android file access (e.g. ls /sdcard).

{memory_instruction}
"""

    def _detect_provider(self) -> str:
        prov_file = REPO_ROOT / ".groq_provider"
        if prov_file.exists():
            return prov_file.read_text().strip()
        if "googleapis.com" in self.base_url: return "Google Gemini"
        if "groq.com" in self.base_url: return "Groq"
        return "Custom"

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
        memory_instr = f"\n# Memory\n{self.memory_context}" if self.memory_context else ""
        return self.master_system_prompt.format(memory_instruction=memory_instr)

    def _get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _compact_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls") and msg.get("content") is None:
                msg["content"] = ""
        if len(messages) <= 12: return messages
        return [messages[0], messages[1]] + messages[-10:]

    def chat(self, messages: List[Dict[str, Any]], role: str = "coordinator") -> Dict[Any, Any]:
        if not self.api_key: raise ValueError("API Key not set. Run setup.")
        if not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.get_system_prompt(role)})
        
        # --- SLOW MODE: RPM MANAGEMENT ---
        if self.slow_mode:
            # Aim for 12 RPM (5s interval) to be safe
            elapsed = time.time() - self._last_request_time
            if elapsed < 5.0:
                wait_time = 5.0 - elapsed
                console.print(f"[dim]🕒 Slow Mode: Waiting {wait_time:.1f}s for API safety...[/dim]")
                time.sleep(wait_time)

        compacted = self._compact_messages(messages)
        headers = self._get_headers()
        payload = {"model": self.model, "messages": compacted, "tools": TOOLS_METADATA, "tool_choice": "auto"}
        
        url = self.base_url
        if "chat/completions" not in url:
            if not url.endswith("/"): url += "/"
            url += "chat/completions"

        max_retries = 3
        for attempt in range(max_retries):
            with httpx.Client() as client:
                try:
                    self._last_request_time = time.time()
                    response = client.post(url, headers=headers, json=payload, timeout=120.0)
                    if response.status_code == 400:
                        raise httpx.HTTPStatusError(f"400 Bad Request: {response.text}", request=response.request, response=response)
                    response.raise_for_status()
                    
                    res_json = response.json()
                    # Track tokens
                    if "usage" in res_json:
                        self._tokens_used = res_json["usage"].get("total_tokens", 0)
                    
                    return res_json
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [429, 503]:
                        if attempt < max_retries - 1:
                            wait_time = 10 * (attempt + 1)
                            console.print(f"[dim]⚠️  API Overload. Waiting {wait_time}s...[/dim]")
                            time.sleep(wait_time)
                            continue
                        else:
                            fallback_model = "gemini-2.5-flash-lite"
                            if self.model != fallback_model and self.provider == "Google Gemini":
                                console.print(f"\n[orange3]⚠️  Failing over to stable workhorse: {fallback_model}...[/orange3]")
                                self.model = fallback_model
                                payload["model"] = fallback_model
                                response = client.post(url, headers=headers, json=payload, timeout=120.0)
                                response.raise_for_status()
                                return response.json()
                    raise e

    def chat_with_tools(self, messages: List[Dict[str, Any]], role: str = "coordinator", stream_callback=None):
        MAX_ITERATIONS = 15
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            try:
                with Status(f"[bold blue]Clawt thinking... ({iteration}/{MAX_ITERATIONS})", console=console) as status:
                    response = self.chat(messages, role)
                    message = response["choices"][0]["message"]
                    if message.get("tool_calls") and message.get("content") is None:
                        message["content"] = ""
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
                    
                    is_sensitive = name in ["execute_bash", "edit_file", "google_search", "web_fetch", "spawn_agent"]
                    if is_sensitive:
                        if name == "execute_bash": display = f"[bold cyan]$ {args.get('command')}"
                        elif name == "google_search": display = f"[bold yellow]Google: {args.get('query')}"
                        else: display = f"[bold magenta]⚡ {name}({args})"

                        console.print(Panel(display, title=f"🛡️  Clawt Request: {name}", border_style="yellow"))
                        
                        if not self.yolo_mode:
                            choices_map = {"Allow Once": "y", "Always for this Session": "a", "Edit Command": "e", "Deny": "n", "Quit": "q"}
                            label = questionary.select("Allow this action?", choices=list(choices_map.keys()), default="Allow Once").ask()
                            choice = choices_map.get(label, "n")

                            if choice == "n": result = "Error: User denied permission."
                            elif choice == "e":
                                if name == "execute_bash": args["command"] = questionary.text("Edit command:", default=args.get("command", "")).ask()
                                elif name == "google_search": args["query"] = questionary.text("Edit search query:", default=args.get("query", "")).ask()
                                result = handle_tool_call(name, args)
                            elif choice == "a":
                                self.yolo_mode = True
                                result = handle_tool_call(name, args)
                            elif choice == "q": return "User terminated session."
                            else: result = handle_tool_call(name, args)
                        else: result = handle_tool_call(name, args)
                    else:
                        if not self.yolo_mode: console.print(f"[dim]⚡ Clawt: {name}[/dim]")
                        result = handle_tool_call(name, args)

                    if not isinstance(result, str): result = str(result)
                    if name == "execute_bash":
                        preview = result[:800] + "..." if len(result) > 800 else result
                        console.print(Panel(preview, title="📝 Output", border_style="dim"))

                    if len(result) > 8000: result = result[:8000] + "\n... [Truncated] ..."
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": name, 
                        "content": result
                    })
                    console.print(f"[bold green]✓ Done[/bold green]")
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 413:
                    if len(messages) > 3:
                        messages = [messages[0], messages[1], messages[-1]]
                        continue
                raise e
        return "Max iterations reached."
        
    def stream_chat(self, messages: List[Dict[str, Any]], role: str = "coordinator"):
        output_chunks = []
        def callback(text):
            if text:
                console.print(text, end="", flush=True)
                output_chunks.append(text)
        self.chat_with_tools(messages, role, stream_callback=callback)
        yield "".join(output_chunks)
