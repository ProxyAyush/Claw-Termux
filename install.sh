#!/data/data/com.termux/files/usr/bin/bash

# Clawt Installer for Android (2026 Elite Edition)
set -e

echo "🚀 Starting Clawt Installation..."

# 1. Update and install basic system dependencies
echo "🔄 Updating package lists..."
pkg update -y

echo "📦 Installing system dependencies (python, git, curl)..."
pkg install python git curl -y

# 2. Install Python dependencies (Elite TUI stack)
echo "🐍 Installing Python libraries (httpx, rich, questionary)..."
pip install httpx rich questionary

# 3. Setup Alias for easy access
setup_alias() {
    local rc_file=$1
    # Create the file if it doesn't exist
    touch "$rc_file"
    # Remove old aliases
    sed -i "/alias claw=/d" "$rc_file"
    sed -i "/alias clawt=/d" "$rc_file"
    
    if ! grep -q "alias clawt=" "$rc_file"; then
        echo "" >> "$rc_file"
        echo "# Clawt Alias" >> "$rc_file"
        echo "alias clawt='PYTHONPATH=/data/data/com.termux/files/home/Claw-Termux python3 -m src.main'" >> "$rc_file"
        echo "✅ Added 'clawt' alias to $rc_file"
    fi
}

setup_alias "$HOME/.bashrc"
setup_alias "$HOME/.zshrc"

# 4. Final Instructions
echo -e "\n"
echo "========================================="
echo "🎉 Clawt Elite Installation Complete!"
echo "========================================="
echo "To start using the agent:"
echo "1. Run: source ~/.bashrc (or restart Termux)"
echo "2. Run: clawt"
echo ""
echo "✨ Features Ready: Arrow-key navigation, Rich Dashboard, Web Search."
echo "========================================="
