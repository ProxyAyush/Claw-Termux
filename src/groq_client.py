import os
import httpx
import json
import time
from typing import List, Dict, Any, Optional
from .real_tools import TOOLS_METADATA, handle_tool_call

class GroqClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key and os.path.exists(".groq_api_key"):
            try:
                with open(".groq_api_key", "r") as f:
                    self.api_key = f.read().strip()
            except Exception:
                pass

        self.model = model or os.environ.get("GROQ_MODEL")
        if not self.model and os.path.exists(".groq_model"):
            try:
                with open(".groq_model", "r") as f:
                    self.model = f.read().strip()
            except Exception:
                pass
        if not self.model:
            self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

        self.base_url = os.environ.get("GROQ_API_URL")
        if not self.base_url and os.path.exists(".groq_api_url"):
            try:
                with open(".groq_api_url", "r") as f:
                    self.base_url = f.read().strip()
            except Exception:
                pass
        if not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"

        # The "Goldmine" System Prompt rebranded for Clawt
        self.system_prompt = """You are Clawt, an interactive CLI agent specializing in software engineering tasks. Your primary goal is to help users safely and effectively in their Termux environment.

# Core Mandates
- **Direct Action:** You are a senior software engineer. Perform tasks autonomously using tools.
- **High-Signal Output:** Focus on intent and technical rationale. Avoid filler, apologies, and mechanical tool-use narration.
- **Surgical Updates:** Use targeted file edits. Validate all changes.
- **Security:** Never log or commit secrets. Protect system integrity.

# Tool Usage
- Use `execute_bash` for shell commands, `read_file` to understand code, and `write_file` to apply changes.
- Always verify your work. If you run a command, check the output. If you edit a file, verify the content.

# Operational Guidelines
- **Role:** Peer programmer. Concise, direct, monospace-friendly.
- **Context:** Respect the workspace conventions. consolidated logic into clean abstractions.
- **Status:** You are Clawt. You are not affiliated with Anthropic. You are a standalone Termux-optimized agent.
"""

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("API Key not set. Run setup.")
        
        # Inject system prompt if not present
        if not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        headers = self._get_headers()
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS_METADATA,
            "tool_choice": "auto"
        }
        
        with httpx.Client() as client:
            response = client.post(self.base_url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json()

    def chat_with_tools(self, messages: List[Dict[str, str]], stream_callback=None):
        """Handles the agent loop: Chat -> Tool Call -> Execute -> Chat again."""
        while True:
            response = self.chat(messages)
            message = response["choices"][0]["message"]
            messages.append(message)

            if message.get("content") and stream_callback:
                stream_callback(message["content"])

            if not message.get("tool_calls"):
                return message["content"]

            # Process Tool Calls
            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                
                if stream_callback:
                    stream_callback(f"\n[Clawt executing {name} with {args}...]\n")
                
                result = handle_tool_call(name, args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": name,
                    "content": result
                })
                
                if stream_callback:
                    stream_callback(f"[Result: {result[:100]}...]\n")
        
    def stream_chat(self, messages: List[Dict[str, str]]):
        # For simplicity in tool use, we'll use non-streaming for tool-looping logic
        # but yield chunks for the UI.
        def callback(text):
            self._current_stream_text = text
            
        full_content = self.chat_with_tools(messages, stream_callback=callback)
        yield full_content
