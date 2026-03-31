from __future__ import annotations
import argparse
import os
import re
import sys
from .groq_client import GroqClient
from .onboarding import run_onboarding, check_setup
from .session_store import load_session, DEFAULT_SESSION_DIR

# Global YOLO mode (Auto-approve)
YOLO_MODE = False

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clawt: The advanced Termux CLI agent')
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('setup', help='run interactive setup')
    chat_parser = subparsers.add_parser('chat', help='start an interactive session')
    chat_parser.add_argument('--session', help='resume session ID')
    chat_parser.add_argument('--yolo', action='store_true', help='enable auto-approve mode')
    subparsers.add_parser('models', help='list available models')
    subparsers.add_parser('update', help='update from github')
    return parser

def main(argv: list[str] | None = None) -> int:
    global YOLO_MODE
    parser = build_parser()
    args = parser.parse_args(argv)
    
    if args.command == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and args.command == 'chat':
        print("No API configuration found. Running setup...")
        if not run_onboarding(): return 1

    if args.command == 'update':
        print("\n🚀 Updating Clawt from GitHub...")
        import subprocess
        try:
            repo_path = "/data/data/com.termux/files/home/Claw-Termux"
            subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/main'], check=False)
            subprocess.run(['git', '-C', repo_path, 'pull', 'origin', 'main'], check=True)
            print("✅ Update successful!")
        except Exception as e: print(f"❌ Update failed: {str(e)}")
        return 0

    if args.command == 'chat':
        YOLO_MODE = args.yolo
        client = GroqClient()
        messages = []
        session_id = args.session or "default"
        
        print(f"\n💬 Clawt Active [YOLO: {'ON' if YOLO_MODE else 'OFF'}]")
        print("Type '/' for commands, or 'exit' to stop.")
        
        while True:
            try:
                raw_input = input("\n👤 You: ").strip()
                if not raw_input: continue
                if raw_input.lower() in ['exit', 'quit']: break
                
                if raw_input.startswith('/'):
                    cmd_parts = raw_input.split()
                    cmd = cmd_parts[0].lower()
                    
                    if cmd == '/help':
                        print("\nAvailable Commands:")
                        print("  /yolo           - Toggle auto-approve mode")
                        print("  /model [id]     - Switch model")
                        print("  /sessions       - List saved sessions")
                        print("  /new            - Clear history")
                        print("  /mcp            - List active MCP servers")
                        print("  /update         - Self-update")
                        continue
                    
                    if cmd == '/yolo':
                        YOLO_MODE = not YOLO_MODE
                        print(f"✅ YOLO Mode: {'ON' if YOLO_MODE else 'OFF'}")
                        continue

                    if cmd == '/model' and len(cmd_parts) > 1:
                        new_model = cmd_parts[1]
                        with open(".groq_model", "w") as f: f.write(new_model)
                        client.model = new_model
                        print(f"✅ Model: {new_model}")
                        continue

                    if cmd == '/new':
                        messages = []
                        print("✨ Session reset.")
                        continue

                # Handle File Context (#)
                processed_prompt = raw_input
                file_refs = re.findall(r'#(\S+)', raw_input)
                for file_ref in file_refs:
                    if os.path.exists(file_ref):
                        with open(file_ref, 'r') as f: content = f.read()
                        processed_prompt = processed_prompt.replace(f'#{file_ref}', f'\n--- FILE: {file_ref} ---\n{content}\n--- END FILE ---')
                        print(f"📎 Attached: {file_ref}")

                messages.append({"role": "user", "content": processed_prompt})
                
                print("\n🤖 Clawt: ", end="", flush=True)
                for chunk in client.stream_chat(messages):
                    pass # Output is handled in stream_chat callback
                print("\n")
                
            except KeyboardInterrupt: break
            except Exception as e: print(f"\n❌ Error: {str(e)}")
        return 0
    
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
