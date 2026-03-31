import os
import httpx
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from .real_tools import TOOLS_METADATA, handle_tool_call

class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model or os.environ.get("GROQ_MODEL") or "meta-llama/llama-4-scout-17b-16e-instruct"
        self.base_url = os.environ.get("GROQ_API_URL") or "https://api.groq.com/openai/v1/chat/completions"
        
        # Discover and Load CLAWT.md (Memory)
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
- Use `spawn_agent` for complex sub-tasks (Research, Implementation, Verification).
- Use `mcp_tool` for external knowledge (Search, GitHub).

# Tone and Style
- Be extra concise. Lead with the action.
- Use file_path:line_number for references.

{memory_instruction}
"""

    def _load_memory(self) -> str:
        """Discovers CLAWT.md files from current directory up to root."""
        memory_content = []
        current_path = Path(os.getcwd()).resolve()
        
        # Load User Global Memory (~/.clawt/CLAWT.md)
        user_memory = Path.home() / ".clawt" / "CLAWT.md"
        if user_memory.exists():
            memory_content.append(f"--- GLOBAL USER RULES ---\n{user_memory.read_text()}\n")
            
        # Traverse up to find Project Memory
        path = current_path
        while path != path.parent:
            clawt_md = path / "CLAWT.md"
            if clawt_md.exists():
                memory_content.append(f"--- PROJECT RULES ({path.name}) ---\n{clawt_md.read_text()}\n")
            path = path.parent
            
        if memory_content:
            return "\n".join(memory_content)
        return ""

    def get_system_prompt(self, role: str = "coordinator") -> str:
        memory_instr = ""
        if self.memory_context:
            memory_instr = f"\n# Memory & User Instructions\n{self.memory_context}\nIMPORTANT: Adhere to these instructions exactly as written. They OVERRIDE default behavior."
            
        base = self.master_system_prompt.format(memory_instruction=memory_instr)
        
        # Specialized Role Addendums
        if role == "verification":
            return base + "\n\n# VERIFICATION ROLE: Adversarial testing specialist. DO NOT modify files. Run adversarial probes (boundary, concurrency). End with VERDICT: PASS or FAIL."
        if role == "explore":
            return base + "\n\n# EXPLORE ROLE: Read-only search specialist. Optimized for speed and thoroughness. DO NOT modify files."
        if role == "worker":
            return base + "\n\n# WORKER ROLE: Implementation specialist. Follow the spec exactly. Self-verify your work before reporting."
            
        return base

    def _get_headers(self) -> Dict[str, str]:
        if "anthropic" in self.base_url.lower():
            return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, messages: List[Dict[str, str]], role: str = "coordinator") -> Dict[ Any, Any]:
        if not self.api_key: raise ValueError("API Key not set.")
        
        # Ensure system prompt is present and correct for the role
        messages = [m for m in messages if m.get("role") != "system"]
        messages.insert(0, {"role": "system", "content": self.get_system_prompt(role)})

        headers = self._get_headers()
        
        # OpenAI/Groq Payload
        payload = {"model": self.model, "messages": messages, "tools": TOOLS_METADATA, "tool_choice": "auto"}
        
        with httpx.Client() as client:
            response = client.post(self.base_url, headers=headers, json=payload, timeout=120.0)
            response.raise_for_status()
            return response.json()

    def chat_with_tools(self, messages: List[Dict[str, str]], role: str = "coordinator", stream_callback=None):
        MAX_ITERATIONS = 20
        iteration = 0
        while iteration < MAX_ITERATIONS:
            iteration += 1
            response = self.chat(messages, role)
            message = response["choices"][0]["message"]
            messages.append(message)
            
            if message.get("content") and stream_callback:
                stream_callback(message["content"])
                
            if not message.get("tool_calls"):
                return message.get("content", "")
                
            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                try: args = json.loads(tool_call["function"]["arguments"])
                except: args = {}
                
                if stream_callback: stream_callback(f"\n[⚡ Clawt: {name}]\n")
                
                # Execute Tool
                result = handle_tool_call(name, args)
                
                # Append result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": name,
                    "content": str(result)
                })
                
                if stream_callback: stream_callback(f"[✓ Done]\n")
                
        return "Max iterations reached."

    def stream_chat(self, messages: List[Dict[str, str]], role: str = "coordinator"):
        output_chunks = []
        def callback(text):
            if text:
                print(text, end="", flush=True)
                output_chunks.append(text)
        self.chat_with_tools(messages, role, stream_callback=callback)
        yield "".join(output_chunks)
