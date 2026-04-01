import os
import questionary
from pathlib import Path

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")

# --- 2026 DEFINITIVE FREE TIER MODELS (Google AI Studio) ---
GEMINI_MODELS = [
    "gemini-3.1-flash-lite-preview", # Best for starting (High Limit)
    "gemini-3-flash-preview",      # Agentic Reasoning
    "gemini-2.5-flash-lite",       # Stable Workhorse
    "gemma-3-27b"                  # High-Volume Open Model
]

GROQ_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct", 
    "openai/gpt-oss-120b", 
    "llama-3.3-70b-versatile"
]

def check_setup() -> bool:
    return (REPO_ROOT / ".groq_api_key").exists() and (REPO_ROOT / ".groq_api_url").exists()

def run_onboarding() -> bool:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]🤖 CLAW-TERMUX SETUP[/bold cyan]\n[dim]Configure your elite engineering environment[/dim]",
        border_style="cyan"
    ))
    
    providers = {
        "Groq": "https://api.groq.com/openai/v1/chat/completions",
        "Google Gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
        "DeepSeek": "https://api.deepseek.com/chat/completions",
        "OpenAI": "https://api.openai.com/v1/chat/completions",
        "Custom": ""
    }
    
    provider_name = questionary.select("Select your LLM Provider:", choices=list(providers.keys())).ask()
    if not provider_name: return False
    
    api_url = providers[provider_name]
    
    if provider_name == "Custom":
        api_url = questionary.text("Enter your custom API URL:").ask()
        api_key = questionary.password("Enter your API Key:").ask()
        model = questionary.text("Enter model name:").ask()
    else:
        api_key = questionary.password(f"Enter your {provider_name} API Key:").ask()
        if provider_name == "Google Gemini":
            model = questionary.select(
                "Select Initial Gemini Model (Lite recommended for high limits):", 
                choices=GEMINI_MODELS, 
                default="gemini-3.1-flash-lite-preview"
            ).ask()
        elif provider_name == "Groq":
            model = questionary.select("Select Initial Groq Model:", choices=GROQ_MODELS, default="meta-llama/llama-4-scout-17b-16e-instruct").ask()
        else:
            model = "gpt-4o" if provider_name == "OpenAI" else "meta-llama/llama-3.1-405b-instruct"
        
    if not api_key:
        console.print("[bold red]Error: API Key is required.[/bold red]")
        return False
        
    try:
        (REPO_ROOT / ".groq_api_key").write_text(api_key)
        (REPO_ROOT / ".groq_api_url").write_text(api_url)
        (REPO_ROOT / ".groq_model").write_text(model)
        (REPO_ROOT / ".groq_provider").write_text(provider_name)
        
        console.print(f"\n[bold green]✅ Setup complete! Clawt is configured to use {provider_name} with {model}.[/bold green]")
        return True
    except Exception as e:
        console.print(f"\n[bold red]❌ Setup failed: {str(e)}[/bold red]")
        return False

if __name__ == "__main__":
    run_onboarding()
