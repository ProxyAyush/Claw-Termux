from __future__ import annotations

import argparse
import os
import re
import sys

from .bootstrap_graph import build_bootstrap_graph
from .command_graph import build_command_graph
from .commands import execute_command, get_command, get_commands, render_command_index
from .direct_modes import run_deep_link, run_direct_connect
from .parity_audit import run_parity_audit
from .permissions import ToolPermissionContext
from .port_manifest import build_port_manifest
from .query_engine import QueryEnginePort
from .remote_runtime import run_remote_mode, run_ssh_mode, run_teleport_mode
from .runtime import PortRuntime
from .session_store import load_session
from .setup import run_setup
from .tool_pool import assemble_tool_pool
from .tools import execute_tool, get_tool, get_tools, render_tool_index


from .onboarding import run_onboarding, check_setup

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clawt: The advanced Termux CLI agent')
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('setup', help='run interactive setup for API provider and key')
    chat_parser = subparsers.add_parser('chat', help='start an interactive clawt session')
    chat_parser.add_argument('--session', help='resume a specific session ID')
    subparsers.add_parser('summary', help='render a Markdown summary')
    subparsers.add_parser('models', help='list available models')
    set_model_parser = subparsers.add_parser('set-model', help='set the active model')
    set_model_parser.add_argument('model_id')
    subparsers.add_parser('update', help='update clawt from github')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    if args.command == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and args.command in ['chat', 'turn-loop']:
        print("No API configuration found. Running setup...")
        if not run_onboarding():
            return 1

    if args.command == 'update':
        print("\n🚀 Updating Clawt from GitHub...")
        import subprocess
        try:
            repo_path = "/data/data/com.termux/files/home/Claw-Termux"
            subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/main'], check=False)
            subprocess.run(['git', '-C', repo_path, 'pull', 'origin', 'main'], check=True)
            print("✅ Update successful!")
        except Exception as e:
            print(f"❌ Update failed: {str(e)}")
        return 0

    if args.command == 'chat':
        if args.session:
            try:
                engine = QueryEnginePort.from_saved_session(args.session)
                print(f"Resuming session: {args.session}")
            except Exception:
                engine = QueryEnginePort.from_workspace()
        else:
            engine = QueryEnginePort.from_workspace()
            
        print("\n💬 Starting Clawt (Type '/' for commands, or 'exit' to stop)")
        
        while True:
            try:
                raw_input = input("\n👤 You: ").strip()
                if not raw_input: continue
                if raw_input.lower() in ['exit', 'quit']: break
                
                # Handle Slash Commands
                if raw_input.startswith('/'):
                    if raw_input == '/':
                        print("\nAvailable Commands:")
                        print("  /help           - Show help")
                        print("  /model [id]     - View/Change model")
                        print("  /sessions       - List sessions")
                        print("  /load <id>      - Resume session")
                        print("  /new            - Start fresh")
                        print("  /update         - Self-update")
                        print("  /summary        - Session stats")
                        continue

                    parts = raw_input.split()
                    cmd = parts[0].lower()
                    
                    if cmd == '/update':
                        print("\n🚀 Self-updating Clawt...")
                        import subprocess
                        try:
                            repo_path = "/data/data/com.termux/files/home/Claw-Termux"
                            subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/main'], check=False)
                            subprocess.run(['git', '-C', repo_path, 'pull', 'origin', 'main'], check=True)
                            print("✅ Update successful! Restarting...")
                            os.execv(sys.executable, [sys.executable, '-m', 'src.main', 'chat', '--session', engine.session_id])
                        except Exception as e:
                            print(f"❌ Update failed: {str(e)}")
                        continue

                    if cmd == '/model':
                        if len(parts) > 1:
                            new_model = parts[1]
                            with open(".groq_model", "w") as f: f.write(new_model)
                            engine.client.model = new_model
                            print(f"✅ Model: {new_model}")
                        else:
                            print(f"✨ Active Model: {engine.client.model}")
                        continue

                    if cmd == '/summary':
                        print("\n" + engine.render_summary())
                        continue

                    if cmd == '/sessions':
                        from .session_store import DEFAULT_SESSION_DIR
                        if DEFAULT_SESSION_DIR.exists():
                            for s in DEFAULT_SESSION_DIR.glob("*.json"): print(f" - {s.stem}")
                        continue

                    if cmd == '/load' and len(parts) > 1:
                        engine = QueryEnginePort.from_saved_session(parts[1])
                        print(f"Resumed: {parts[1]}")
                        continue

                    if cmd == '/new':
                        engine = QueryEnginePort.from_workspace()
                        print(f"New session: {engine.session_id}")
                        continue

                # Handle File Context (#)
                processed_prompt = raw_input
                file_refs = re.findall(r'#(\S+)', raw_input)
                for file_ref in file_refs:
                    if os.path.exists(file_ref):
                        with open(file_ref, 'r') as f: content = f.read()
                        processed_prompt = processed_prompt.replace(f'#{file_ref}', f'\n--- FILE: {file_ref} ---\n{content}\n--- END FILE ---')
                        print(f"📎 Attached: {file_ref}")

                # Agent Loop
                engine.mutable_messages.append({"role": "user", "content": processed_prompt})
                engine.transcript_store.append(processed_prompt)

                print("\n🤖 Clawt: ", end="", flush=True)
                full_response = ""
                for chunk in engine.client.stream_chat(engine.mutable_messages):
                    print(chunk, end="", flush=True)
                    full_response += chunk
                print("\n")
                
                engine.transcript_store.append(full_response)
                
                try: engine.persist_session()
                except: pass
                
            except KeyboardInterrupt: break
            except Exception as e: print(f"\n❌ Error: {str(e)}")
        return 0

    if args.command == 'summary':
        print(QueryEnginePort(build_port_manifest()).render_summary())
        return 0
    if args.command == 'models':
        print("Latest Models: meta-llama/llama-4-scout-17b-16e-instruct, openai/gpt-oss-120b, qwen/qwen3-32b")
        return 0
    if args.command == 'set-model':
        with open(".groq_model", "w") as f: f.write(args.model_id)
        print(f"Model set to: {args.model_id}")
        return 0
    
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
