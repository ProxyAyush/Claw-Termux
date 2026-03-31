#!/data/data/com.termux/files/usr/bin/bash

# Claw-Termux Installer for Android
set -e

echo "🚀 Starting Claw-Termux Installation..."

# 1. Update and install basic system dependencies
echo "🔄 Updating package lists..."
pkg update -y

echo "📦 Installing system dependencies (python, git, curl)..."
pkg install python git curl -y

# 2. Install Python dependencies
echo "🐍 Installing Python libraries..."
# We use --no-cache-dir to save space on mobile
# We explicitly install httpx as it is our primary provider engine
pip install httpx

# 3. Setup Alias for easy access
# Supports both Bash and Zsh
setup_alias() {
    local rc_file=$1
    # Create the file if it doesn't exist, then add the alias
    touch "$rc_file"
    # Remove old alias if exists
    sed -i "/alias claw=/d" "$rc_file"
    sed -i "/alias clawt=/d" "$rc_file"

    if ! grep -q "alias clawt=" "$rc_file"; then
        echo "" >> "$rc_file"
        echo "# Claw-Termux Alias" >> "$rc_file"
        echo "alias clawt='PYTHONPATH=/data/data/com.termux/files/home/Claw-Termux python3 -m src.main chat'" >> "$rc_file"
        echo "✅ Added 'clawt' alias to $rc_file"
    fi
}


setup_alias "$HOME/.bashrc"
setup_alias "$HOME/.zshrc"

# 4. Final Instructions
echo -e "\n"
echo "========================================="
echo "🎉 Claw-Termux Installation Complete!"
echo "========================================="
echo "To start using the agent:"
echo "1. Run: source ~/.bashrc (or restart Termux)"
echo "2. Run: claw setup"
echo ""
echo "Note: If you are using a non-standard shell,"
echo "add this to your config: alias claw='PYTHONPATH=$HOME/Claw-Termux python3 -m src.main'"
echo "========================================="
