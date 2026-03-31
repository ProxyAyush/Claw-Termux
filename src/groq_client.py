import os
import httpx
import json
from typing import List, Dict, Any, Optional

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
            self.model = "llama-3.3-70b-versatile"

        self.base_url = os.environ.get("GROQ_API_URL")
        if not self.base_url and os.path.exists(".groq_api_url"):
            try:
                with open(".groq_api_url", "r") as f:
                    self.base_url = f.read().strip()
            except Exception:
                pass
        if not self.base_url:
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def _get_headers(self) -> Dict[str, str]:
        if "anthropic" in self.base_url.lower():
            return {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        else:
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

    def _prepare_payload(self, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }
        
        # Anthropic uses "max_tokens" as a required parameter
        if "anthropic" in self.base_url.lower():
            payload["max_tokens"] = 4096
            
        return payload

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("API Key not set. Run setup.")
        
        headers = self._get_headers()
        payload = self._prepare_payload(messages)
        
        with httpx.Client() as client:
            response = client.post(self.base_url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            
            # Normalize response for Anthropic
            if "anthropic" in self.base_url.lower() and "messages" in self.base_url.lower():
                return {
                    "choices": [{"message": {"content": data["content"][0]["text"]}}],
                    "usage": {
                        "prompt_tokens": data["usage"]["input_tokens"],
                        "completion_tokens": data["usage"]["output_tokens"]
                    }
                }
            return data

    def stream_chat(self, messages: List[Dict[str, str]]):
        if not self.api_key:
            raise ValueError("API Key not set. Run setup.")
        
        headers = self._get_headers()
        payload = self._prepare_payload(messages, stream=True)
        
        with httpx.stream("POST", self.base_url, headers=headers, json=payload, timeout=60.0) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        
                        # Handle OpenAI-compatible stream
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        
                        # Handle Anthropic stream (Simplified)
                        elif "type" in data:
                            if data["type"] == "content_block_delta":
                                yield data["delta"]["text"]
                                
                    except json.JSONDecodeError:
                        continue
