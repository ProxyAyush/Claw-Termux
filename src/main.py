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
    # Make command optional, defaulting to 'chat'
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
    
    # Default to 'chat' if no command provided
    cmd = args.command or 'chat'
    
    if cmd == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and cmd in ['chat', 'turn-loop']:
        print("No API configuration found. Running setup...")
        if not run_onboarding(): return 1

    if cmd == 'update':
        print("\n🚀 Updating Clawt from GitHub...")
        import subprocess
        try:
            repo_path = "/data/data/com.termux/files/home/Claw-Termux"
            subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/main'], check=False)
            subprocess.run(['git', '-C', repo_path, 'pull', 'origin', 'main'], check=True)
            print("✅ Update successful!")
        except Exception as e: print(f"❌ Update failed: {str(e)}")
        return 0

    if cmd == 'summary':
        engine = QueryEnginePort(build_port_manifest())
        print(engine.render_summary())
        return 0

    if cmd == 'chat':
        yolo_from_args = getattr(args, 'yolo', False)
        YOLO_MODE = yolo_from_args
        client = GroqClient()
        session_id = getattr(args, 'session', None)
        
        if session_id:
            try:
                # We need to bridge the old QueryEnginePort session loading with our new loop
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
            # Create a fresh session ID for this run
            from uuid import uuid4
            session_id = uuid4().hex
        
        print(f"\n💬 Clawt Active [YOLO: {'ON' if YOLO_MODE else 'OFF'}]")
        print("Type '/' for commands, or 'exit' to stop.")
        
        while True:
            try:
                raw_input = input("\n👤 You: ").strip()
                if not raw_input: continue
                if raw_input.lower() in ['exit', 'quit']: break
                
                if raw_input.startswith('/'):
                    if raw_input == '/':
                        print("\nAvailable Commands:")
                        print("  /help           - Show this help menu")
                        print("  /yolo           - Toggle auto-approve mode")
                        print("  /model [id]     - Switch active model")
                        print("  /sessions       - List saved sessions")
                        print("  /load <id>      - Resume a session")
                        print("  /new            - Start a fresh session")
                        print("  /update         - Pull latest code and restart")
                        continue

                    cmd_parts = raw_input.split()
                    slash_cmd = cmd_parts[0].lower()
                    
                    if slash_cmd == '/help':
                        # Already handled above, but for consistency
                        continue
                    
                    if slash_cmd == '/yolo':
                        YOLO_MODE = not YOLO_MODE
                        print(f"✅ YOLO Mode: {'ON' if YOLO_MODE else 'OFF'}")
                        continue

                    if slash_cmd == '/model':
                        if len(cmd_parts) > 1:
                            new_model = cmd_parts[1]
                            # Use absolute path for consistency
                            from .groq_client import REPO_ROOT
                            (REPO_ROOT / ".groq_model").write_text(new_model)
                            client.model = new_model
                            print(f"✅ Model: {new_model}")
                        else:
                            print(f"✨ Active Model: {client.model}")
                        continue

                    if slash_cmd == '/new':
                        messages = []
                        from uuid import uuid4
                        session_id = uuid4().hex
                        print(f"✨ Started fresh session: {session_id}")
                        continue
                        
                    if slash_cmd == '/sessions':
                        if DEFAULT_SESSION_DIR.exists():
                            for s in DEFAULT_SESSION_DIR.glob("*.json"): print(f" - {s.stem}")
                        continue
                        
                    if slash_cmd == '/load' and len(cmd_parts) > 1:
                        sid = cmd_parts[1]
                        try:
                            stored = load_session(sid)
                            messages = []
                            for i, msg in enumerate(stored.messages):
                                role = "user" if i % 2 == 0 else "assistant"
                                messages.append({"role": role, "content": msg})
                            session_id = sid
                            print(f"✅ Resumed: {sid}")
                        except Exception as e:
                            print(f"❌ Load failed: {str(e)}")
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
                        except Exception as e:
                            print(f"❌ Update failed: {str(e)}")
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
                full_response = ""
                for chunk in client.stream_chat(messages):
                    # client.stream_chat now populates messages internally via chat_with_tools
                    pass 
                print("\n")
                
                # Manual session save
                try:
                    save_session(StoredSession(
                        session_id=session_id,
                        messages=tuple(m["content"] for m in messages if "content" in m),
                        input_tokens=0, output_tokens=0 # Dummy usage for now
                    ))
                except Exception: pass
                
            except KeyboardInterrupt: break
            except Exception as e: print(f"\n❌ Error: {str(e)}")
        return 0
    
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
