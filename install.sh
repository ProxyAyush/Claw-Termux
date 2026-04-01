#!/data/data/com.termux/files/usr/bin/bash

# Clawt Installer for Android (2026 Elite Edition)
set -e

echo "🚀 Starting Clawt Elite Installation..."

# 1. Update and install basic system dependencies
echo "🔄 Updating package lists..."
pkg update -y || echo "⚠️ Warning: pkg update failed, attempting to continue..."

echo "📦 Installing system dependencies (python, git, curl)..."
pkg install python git curl -y

# 2. Install Python dependencies (Elite TUI stack)
echo "🐍 Installing Python libraries (httpx, rich, questionary, googlesearch-python)..."
pip install httpx rich questionary googlesearch-python

# 3. Install Elite Search Engine (Direct Binary Bypass)
echo "🔍 Installing 'ddgr' structured search engine..."
mkdir -p "$HOME/bin"
curl -skL https://raw.githubusercontent.com/jarun/ddgr/master/ddgr > "$HOME/bin/ddgr"
chmod +x "$HOME/bin/ddgr"
echo "✅ Elite Search Engine (ddgr) installed to $HOME/bin/ddgr"

# 4. Setup Alias for easy access
setup_alias() {
    local rc_file=$1
    [ -f "$rc_file" ] || touch "$rc_file"
    
    # Remove old aliases to prevent duplicates
    sed -i "/alias clawt=/d" "$rc_file"
    
    echo "" >> "$rc_file"
    echo "# Clawt Elite Alias" >> "$rc_file"
    echo "export PATH=\$PATH:\$HOME/bin" >> "$rc_file"
    echo "alias clawt='PYTHONPATH=/data/data/com.termux/files/home/Claw-Termux python3 -m src.main'" >> "$rc_file"
    echo "✅ Added 'clawt' alias and path to $rc_file"
}

setup_alias "$HOME/.bashrc"
setup_alias "$HOME/.zshrc"

# 5. Final Instructions
echo -e "\n"
echo "========================================="
echo "🎉 Clawt Elite Installation Complete!"
echo "========================================="
echo "To start using the elite agent:"
echo "1. Run: source ~/.bashrc (or restart Termux)"
echo "2. Run: clawt"
echo ""
echo "✨ Features Ready: Elite Google Search, Surgical Editing, Rich TUI Dashboard."
echo "Created by Dr. Ayush Yadav"
echo "========================================="
