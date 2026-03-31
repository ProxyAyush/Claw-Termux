# 🤖 Claw-Termux

An optimized, Android-first fork of **claw-code**. This project replaces heavy Rust-based dependencies (like `pydantic-core`) with a lightweight `httpx` provider, specifically to solve the "failed to build wheel" issues on Termux.

### **✨ Why Claw-Termux?**
- **🛠️ Zero-Build Install:** No Rust/C compiler issues on Android.
- **🌍 Universal Provider:** One-click setup for **Groq, OpenRouter, DeepSeek, OpenAI, Anthropic**, and more.
- **📱 Termux Native:** Built-in installer and interactive CLI optimized for mobile screens.
- **⚡ Ultra-Fast:** Uses high-performance streaming for instant responses.

### **📦 One-Command Installation**
Paste this into your Termux to install everything automatically:
```bash
pkg install git python -y && \
git clone https://github.com/YOUR_GITHUB_USERNAME/Claw-Termux.git && \
cd Claw-Termux && \
chmod +x install.sh && \
./install.sh
```

### **🚀 How to Use**
1. **First-time Setup:**
   ```bash
   claw setup
   ```
2. **Start a Conversation:**
   ```bash
   claw turn-loop "Your prompt"
   ```
3. **Change Models:**
   ```bash
   claw set-model llama-3.1-8b-instant
   ```
4. **List Models:**
   ```bash
   claw models
   ```

### **🔒 Security**
Your API keys are stored locally in hidden `.groq_*` files inside the project folder. They are never uploaded or shared.

---

### **📜 Credits & Legal**
- **Original Project:** Based on the excellent clean-room rewrite [claw-code](https://github.com/instructkr/claw-code) by [Sigrid Jin (instructkr)](https://github.com/instructkr).
- **Termux Fork:** This specialized fork is maintained by **Dr. Ayush Yadav**.
- **Legal Disclaimer:** This is an independent project and is **not affiliated with, endorsed by, or maintained by Anthropic**. All code is shared for educational and research purposes.
- **License:** Distributed under the MIT License. See `LICENSE` for details.
