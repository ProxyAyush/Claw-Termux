import os

def run_onboarding():
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
        model = input("Enter model name (e.g. llama-3): ")
    else:
        api_url = default_url
        api_key = input(f"Enter your {provider_name} API Key: ")
        model = default_model
        
    # Save configs
    with open(".groq_api_key", "w") as f: f.write(api_key)
    with open(".groq_api_url", "w") as f: f.write(api_url)
    with open(".groq_model", "w") as f: f.write(model)
    with open(".groq_provider", "w") as f: f.write(provider_name)
    
    print(f"\n✅ Setup complete! Clawt is configured to use {provider_name}.")
    print("Run 'clawt' to start chatting.")

if __name__ == "__main__":
    run_onboarding()
