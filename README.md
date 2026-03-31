# 🤖 Claw-Termux

**Claw-Termux** is an optimized, Android-first version of the Claude Code agent harness. This project is specifically designed to run seamlessly on **Termux** by replacing heavy, build-intensive dependencies with a lightweight, high-performance engine.

### **✨ Key Improvements**
- **🛠️ Zero-Build Install:** Replaced `pydantic-core` and other Rust-based requirements with a lightweight `httpx` provider to solve "failed to build wheel" errors on Android.
- **🌍 Universal API Support:** Out-of-the-box support for **Groq, OpenRouter, DeepSeek, OpenAI, Anthropic**, and **Together AI**.
- **📱 Termux-First UX:** Includes a dedicated `install.sh` and an interactive `setup` wizard for mobile users.
- **⚡ High-Speed Streaming:** Optimized for low-latency responses even on mobile networks.

---

### **📦 One-Command Installation**
Paste this into your Termux to install everything automatically:

```bash
pkg install git python -y && \
git clone https://github.com/ProxyAyush/Claw-Termux.git && \
cd Claw-Termux && \
chmod +x install.sh && \
./install.sh
```

---

### **🚀 Getting Started**
Once installed, you can use the `claw` command from anywhere:

1. **Initialize Setup:**
   ```bash
   claw setup
   ```
   *(Follow the prompts to select your provider and enter your API key)*

2. **Start a Conversation:**
   ```bash
   claw turn-loop "Your prompt"
   ```

3. **Management Commands:**
   - `claw models`: List available models.
   - `claw set-model <id>`: Switch your active model.
   - `claw summary`: See a technical summary of your workspace.

---

### **🔒 Security**
Your API keys are stored locally in hidden `.groq_*` files inside the project folder. They are never uploaded, logged, or shared.

---

### **📜 Credits & Legal**
- **Maintainer:** [Dr. Ayush Yadav](https://github.com/ProxyAyush)
- **Original Research:** Based on the clean-room rewrite [claw-code](https://github.com/instructkr/claw-code) by [Sigrid Jin (instructkr)](https://github.com/instructkr).
- **Legal Disclaimer:** This is an independent project and is **not affiliated with, endorsed by, or maintained by Anthropic**. All code is shared for educational and research purposes.
- **License:** Distributed under the MIT License. See `LICENSE` for details.
