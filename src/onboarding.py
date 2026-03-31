import os
from pathlib import Path

PROVIDERS = {
    "1": ("Groq", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "2": ("OpenRouter", "https://openrouter.ai/api/v1/chat/completions", "anthropic/claude-3.5-sonnet"),
    "3": ("OpenAI", "https://api.openai.com/v1/chat/completions", "gpt-4o"),
    "4": ("DeepSeek", "https://api.deepseek.com/chat/completions", "deepseek-chat"),
    "5": ("Anthropic", "https://api.anthropic.com/v1/messages", "claude-3-5-sonnet-20241022"),
    "6": ("Together AI", "https://api.together.xyz/v1/chat/completions", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

def run_onboarding():
    print("\n" + "="*40)
    print("      Welcome to claw-code (Termux)      ")
    print("="*40)
    print("\nPlease select your AI Provider:")
    for key, (name, _, _) in PROVIDERS.items():
        print(f"  {key}. {name}")
    print("  0. Custom Endpoint")
    
    choice = input("\nEnter choice (1-6, 0): ").strip()
    
    provider_name = ""
    api_url = ""
    default_model = ""
    
    if choice in PROVIDERS:
        provider_name, api_url, default_model = PROVIDERS[choice]
    elif choice == "0":
        provider_name = "Custom"
        api_url = input("Enter API URL (e.g., https://api.proxy.com/v1/chat/completions): ").strip()
        default_model = input("Enter default model ID: ").strip()
    else:
        print("Invalid choice. Defaulting to Groq.")
        provider_name, api_url, default_model = PROVIDERS["1"]

    print(f"\nSetting up {provider_name}...")
    api_key = input(f"Please enter your {provider_name} API Key: ").strip()
    
    if not api_key:
        print("Warning: No API key provided. Setup incomplete.")
        return False

    # Save to files
    with open(".groq_api_key", "w") as f:
        f.write(api_key)
    with open(".groq_api_url", "w") as f:
        f.write(api_url)
    with open(".groq_model", "w") as f:
        f.write(default_model)
    with open(".groq_provider", "w") as f:
        f.write(provider_name)

    print("\n" + "-"*40)
    print("✅ Setup Successful!")
    print(f"Provider: {provider_name}")
    print(f"Model:    {default_model}")
    print(f"Config saved to local .groq_* files.")
    print("-"*40 + "\n")
    return True

def check_setup():
    return os.path.exists(".groq_api_key")
