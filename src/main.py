from __future__ import annotations
import argparse
import os
import re
import sys
from .groq_client import GroqClient
from .onboarding import run_onboarding, check_setup
from .session_store import load_session, DEFAULT_SESSION_DIR, save_session, StoredSession
from .query_engine import QueryEnginePort
from .port_manifest import build_port_manifest

# Global YOLO mode (Auto-approve)
YOLO_MODE = False

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clawt: The advanced Termux CLI agent')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    subparsers.add_parser('setup', help='run interactive setup')
    chat_parser = subparsers.add_parser('chat', help='start an interactive session (default)')
    chat_parser.add_argument('--session', help='resume session ID')
    chat_parser.add_argument('--yolo', action='store_true', help='enable auto-approve mode')
    
    subparsers.add_parser('models', help='list available models')
    subparsers.add_parser('update', help='update from github')
    subparsers.add_parser('summary', help='render workspace summary')
    
    return parser

def main(argv: list[str] | None = None) -> int:
    global YOLO_MODE
    parser = build_parser()
    args = parser.parse_args(argv)
    
    cmd = args.command or 'chat'
    
    if cmd == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and cmd in ['chat']:
        print("No API configuration found. Running setup...")
        if not run_onboarding(): return 1

    if cmd == 'update':
        print("\n🚀 Updating Clawt from GitHub...")
        import subprocess
        try:
            from .groq_client import REPO_ROOT
            subprocess.run(['git', '-C', str(REPO_ROOT), 'reset', '--hard', 'origin/main'], check=False)
            subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', 'origin', 'main'], check=True)
            print("✅ Update successful!")
        except Exception as e: print(f"❌ Update failed: {str(e)}")
        return 0

    if cmd == 'chat':
        yolo_from_args = getattr(args, 'yolo', False)
        YOLO_MODE = yolo_from_args
        client = GroqClient()
        session_id = getattr(args, 'session', None)
        
        if session_id:
            try:
                stored = load_session(session_id)
                messages = []
                for i, msg in enumerate(stored.messages):
                    role = "user" if i % 2 == 0 else "assistant"
                    messages.append({"role": role, "content": msg})
                print(f"Resumed session: {session_id}")
            except Exception:
                messages = []
        else:
            messages = []
            from uuid import uuid4
            session_id = uuid4().hex
        
        print(f"\n💬 Clawt Active [YOLO: {'ON' if YOLO_MODE else 'OFF'}]")
        print("Type '/' for commands, or 'exit' to stop.")
        
        while True:
            try:
                raw_input = input("\n👤 You: ").strip()
                if not raw_input: continue
                if raw_input.lower() in ['exit', 'quit']: break
                
                # Intercept Slash Commands
                if raw_input.startswith('/'):
                    cmd_parts = raw_input.split()
                    slash_cmd = cmd_parts[0].lower()
                    
                    if slash_cmd == '/' or slash_cmd == '/help':
                        print("\nAvailable Commands:")
                        print("  /help           - Show this help menu")
                        print("  /setup          - Change API keys or Provider")
                        print("  /yolo           - Toggle auto-approve mode")
                        print("  /model [id]     - Switch active model")
                        print("  /models         - List available 2026 models")
                        print("  /sessions       - List saved sessions")
                        print("  /load <id>      - Resume a session")
                        print("  /new            - Start a fresh session")
                        print("  /update         - Pull latest code and restart")
                        continue
                    
                    if slash_cmd == '/setup':
                        if run_onboarding():
                            print("🔄 Reloading configuration...")
                            client = GroqClient()
                        continue

                    if slash_cmd == '/yolo':
                        YOLO_MODE = not YOLO_MODE
                        print(f"✅ YOLO Mode: {'ON' if YOLO_MODE else 'OFF'}")
                        continue

                    if slash_cmd == '/model':
                        if len(cmd_parts) > 1:
                            new_model = cmd_parts[1]
                            from .groq_client import REPO_ROOT
                            (REPO_ROOT / ".groq_model").write_text(new_model)
                            client.model = new_model
                            print(f"✅ Model set to: {new_model}")
                        else:
                            print(f"✨ Active Model: {client.model}")
                            print("Tip: Use '/model <id>' to switch.")
                        continue

                    if slash_cmd == '/models':
                        print("\nPopular 2026 Models:")
                        print(" --- Google Gemini ---")
                        print(" - gemini-2.0-flash (Fast, Default)")
                        print(" - gemini-2.0-pro-exp (Powerful)")
                        print(" - gemini-1.5-flash")
                        print(" - gemini-1.5-pro")
                        print("\n --- Groq / OpenRouter ---")
                        print(" - meta-llama/llama-4-scout-17b-16e-instruct")
                        print(" - openai/gpt-oss-120b")
                        print(" - deepseek-chat")
                        print(" - gpt-4o")
                        continue

                    if slash_cmd == '/update':
                        print("\n🚀 Self-updating Clawt...")
                        import subprocess
                        try:
                            from .groq_client import REPO_ROOT
                            subprocess.run(['git', '-C', str(REPO_ROOT), 'reset', '--hard', 'origin/main'], check=False)
                            subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', 'origin', 'main'], check=True)
                            print("✅ Update successful! Restarting...")
                            os.execv(sys.executable, [sys.executable, '-m', 'src.main', 'chat', '--session', session_id])
                        except Exception as e: print(f"❌ Update failed: {str(e)}")
                        continue

                # Handle File Context (#)
                processed_prompt = raw_input
                file_refs = re.findall(r'#(\S+)', raw_input)
                for file_ref in file_refs:
                    if os.path.exists(file_ref):
                        try:
                            with open(file_ref, 'r') as f: content = f.read()
                            processed_prompt = processed_prompt.replace(f'#{file_ref}', f'\n--- FILE: {file_ref} ---\n{content}\n--- END FILE ---')
                            print(f"📎 Attached: {file_ref}")
                        except Exception as e: print(f"⚠️ Error reading {file_ref}: {str(e)}")

                messages.append({"role": "user", "content": processed_prompt})
                print("\n🤖 Clawt: ", end="", flush=True)
                for chunk in client.stream_chat(messages): pass 
                print("\n")
                
                try:
                    save_session(StoredSession(
                        session_id=session_id,
                        messages=tuple(m["content"] for m in messages if "content" in m),
                        input_tokens=0, output_tokens=0
                    ))
                except Exception: pass
                
            except KeyboardInterrupt: 
                print("\nGoodbye!")
                break
            except Exception as e: print(f"\n❌ Error: {str(e)}")
        return 0
    
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
