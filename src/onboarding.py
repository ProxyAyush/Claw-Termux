import os
from pathlib import Path

# Absolute path to the repository root
REPO_ROOT = Path("/data/data/com.termux/files/home/Claw-Termux")

def check_setup() -> bool:
    """Checks if the required API configuration files exist in the REPO_ROOT."""
    return (REPO_ROOT / ".groq_api_key").exists() and (REPO_ROOT / ".groq_api_url").exists()

def run_onboarding() -> bool:
    print("Welcome to Clawt (Claw-Termux) Setup!")
    print("-----------------------------------")
    
    providers = {
        "1": ("Groq", "https://api.groq.com/openai/v1/chat/completions", "meta-llama/llama-4-scout-17b-16e-instruct"),
        "2": ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.1-405b-instruct"),
        "3": ("OpenAI", "https://api.openai.com/v1/chat/completions", "gpt-4o"),
        "4": ("DeepSeek", "https://api.deepseek.com/chat/completions", "deepseek-chat"),
        "5": ("Custom", "", "")
    }
    
    print("\nSelect your LLM Provider:")
    for key, (name, _, _) in providers.items():
        print(f"{key}. {name}")
        
    choice = input("\nChoice [1-5]: ")
    if choice not in providers:
        print("Invalid choice. Defaulting to Groq.")
        choice = "1"
        
    provider_name, default_url, default_model = providers[choice]
    
    if choice == "5":
        api_url = input("Enter your custom API URL: ")
        api_key = input("Enter your API Key: ")
        model = input("Enter model name: ")
    else:
        api_url = default_url
        api_key = input(f"Enter your {provider_name} API Key: ")
        model = default_model
        
    try:
        # Save configs to REPO_ROOT using absolute paths
        (REPO_ROOT / ".groq_api_key").write_text(api_key)
        (REPO_ROOT / ".groq_api_url").write_text(api_url)
        (REPO_ROOT / ".groq_model").write_text(model)
        (REPO_ROOT / ".groq_provider").write_text(provider_name)
        
        print(f"\n✅ Setup complete! Clawt is configured to use {provider_name}.")
        return True
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_onboarding()
