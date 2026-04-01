import os
import questionary
from pathlib import Path

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")

def check_setup() -> bool:
    """Checks if the required API configuration files exist in the REPO_ROOT."""
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
        "Groq": ("https://api.groq.com/openai/v1/chat/completions", "meta-llama/llama-4-scout-17b-16e-instruct"),
        "Google Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-3.1-flash-preview"),
        "OpenRouter": ("https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.1-405b-instruct"),
        "DeepSeek": ("https://api.deepseek.com/chat/completions", "deepseek-v4"),
        "OpenAI": ("https://api.openai.com/v1/chat/completions", "gpt-5-mini"),
        "Custom": ("", "")
    }
    
    provider_name = questionary.select(
        "Select your LLM Provider:",
        choices=list(providers.keys())
    ).ask()
    
    if not provider_name: return False
    
    default_url, default_model = providers[provider_name]
    
    if provider_name == "Custom":
        api_url = questionary.text("Enter your custom API URL:").ask()
        api_key = questionary.password("Enter your API Key:").ask()
        model = questionary.text("Enter model name:").ask()
    else:
        api_url = default_url
        api_key = questionary.password(f"Enter your {provider_name} API Key:").ask()
        model = default_model
        
    if not api_key:
        console.print("[bold red]Error: API Key is required.[/bold red]")
        return False
        
    try:
        # Save configs to REPO_ROOT using absolute paths
        (REPO_ROOT / ".groq_api_key").write_text(api_key)
        (REPO_ROOT / ".groq_api_url").write_text(api_url)
        (REPO_ROOT / ".groq_model").write_text(model)
        (REPO_ROOT / ".groq_provider").write_text(provider_name)
        
        console.print(f"\n[bold green]✅ Setup complete! Clawt is configured to use {provider_name}.[/bold green]")
        return True
    except Exception as e:
        console.print(f"\n[bold red]❌ Setup failed: {str(e)}[/bold red]")
        return False

if __name__ == "__main__":
    run_onboarding()
