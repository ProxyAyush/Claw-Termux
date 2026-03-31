# Claw-Termux (Clawt)

**Claw-Termux** (branded as **Clawt**) is an optimized, Android-first version of an agentic CLI coding assistant. This project is specifically designed to run seamlessly on **Termux** by replacing heavy, build-intensive dependencies with a lightweight, high-performance engine.

## 🚀 Key Features

- **⚡ Blazing Fast:** Powered by **Groq** for near-instant tool-calling and code generation.
- **🤖 Fully Agentic:** Implements a sophisticated "Chat -> Tool Call -> Execute -> Feedback" loop.
- **🛠️ Built-in Tools:** Functional Termux-side tools for `execute_bash`, `read_file`, `write_file`, `edit_file`, `glob`, and `grep`.
- **🌍 Universal API Support:** Out-of-the-box support for **Groq, OpenRouter, DeepSeek, OpenAI**, and **Together AI**.
- **📱 Termux Optimized:** Zero Rust/C-build requirements; works on any Android device with Termux.

## 📦 Installation

```bash
pkg install git python -y
git clone https://github.com/ProxyAyush/Claw-Termux.git
cd Claw-Termux
chmod +x install.sh
./install.sh
source ~/.bashrc
clawt
```

## 🎮 Commands

Inside the `clawt` shell, use `/` to access the command menu:

- `/help`: Show this help message.
- `/model`: Switch to a different model.
- `/models`: List available models for your provider.
- `/sessions`: List saved conversation sessions.
- `/load <id>`: Load a specific session.
- `/new`: Start a fresh conversation.
- `/update`: Pull latest changes from GitHub and restart.
- `/summary`: Get a summary of the current session.
- `/reset`: Clear the current conversation history.

## 📝 Legal Notice

- **Owner:** Dr. Ayush Yadav (ayushiamazon1@gmail.com)
- **Legal Disclaimer:** This is an independent project. All code is shared for educational and research purposes.
- **Attribution:** Based on the original architecture by Sigrid Jin/instructkr. See [NOTICE](./NOTICE) for full attributions.

---
Maintained with ❤️ by **Dr. Ayush Yadav**
