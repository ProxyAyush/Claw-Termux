from __future__ import annotations
import argparse
import os
import re
import sys
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from .groq_client import GroqClient, REPO_ROOT
from .onboarding import run_onboarding, check_setup
from .session_store import load_session, DEFAULT_SESSION_DIR, save_session, StoredSession

console = Console()

MODEL_OPTIONS = [
    "gemini-3.1-pro",
    "gemini-3.1-flash",
    "gemini-2.5-flash",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-120b",
    "deepseek-chat"
]

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]🤖 CLAW-TERMUX (CLAWT)[/bold cyan]\n[dim]The Elite Engineering Agent for Android[/dim]",
        border_style="cyan",
        padding=(1, 4)
    ))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clawt: The advanced Termux CLI agent')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    subparsers.add_parser('setup', help='run interactive setup')
    chat_parser = subparsers.add_parser('chat', help='start an interactive session')
    chat_parser.add_argument('--session', help='resume session ID')
    chat_parser.add_argument('--yolo', action='store_true', help='enable auto-approve mode')
    subparsers.add_parser('models', help='list available models')
    subparsers.add_parser('update', help='update from github')
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    cmd = args.command or 'chat'
    
    if cmd == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and cmd in ['chat']:
        print_banner()
        console.print("[yellow]No API configuration found. Running setup...[/yellow]")
        if not run_onboarding(): return 1

    if cmd == 'update':
        print_banner()
        console.print("\n🚀 [bold cyan]Updating Clawt from GitHub...[/bold cyan]")
        import subprocess
        try:
            subprocess.run(['git', '-C', str(REPO_ROOT), 'reset', '--hard', 'origin/main'], check=False)
            subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', 'origin', 'main'], check=True)
            console.print("[bold green]✅ Update successful![/bold green]")
        except Exception as e: console.print(f"[bold red]❌ Update failed: {str(e)}[/bold red]")
        return 0

    if cmd == 'chat':
        print_banner()
        client = GroqClient()
        client.yolo_mode = getattr(args, 'yolo', False)
        
        session_id = getattr(args, 'session', None)
        if session_id:
            try:
                stored = load_session(session_id)
                messages = []
                for i, msg in enumerate(stored.messages):
                    role = "user" if i % 2 == 0 else "assistant"
                    messages.append({"role": role, "content": msg})
                console.print(f"[dim]Resumed session: {session_id}[/dim]")
            except Exception: messages = []
        else:
            messages = []
            from uuid import uuid4
            session_id = uuid4().hex
        
        console.print(f"[bold green]💬 Clawt Active[/bold green] [dim]| Model: {client.model} | YOLO: {'ON' if client.yolo_mode else 'OFF'}[/dim]")
        console.print("[dim]Type '/' for commands, or 'exit' to stop.[/dim]\n")
        
        while True:
            try:
                raw_input = console.input("[bold blue]👤 You:[/bold blue] ").strip()
                if not raw_input: continue
                if raw_input.lower() in ['exit', 'quit']: break
                
                if raw_input.startswith('/'):
                    cmd_parts = raw_input.split()
                    slash_cmd = cmd_parts[0].lower()
                    
                    if slash_cmd == '/' or slash_cmd == '/help':
                        table = Table(title="Available Commands", border_style="cyan")
                        table.add_column("Command", style="cyan", no_wrap=True)
                        table.add_column("Action", style="dim")
                        table.add_row("/help", "Show this help menu")
                        table.add_row("/setup", "Change API keys or Provider")
                        table.add_row("/yolo", "Toggle auto-approve (YOLO) mode")
                        table.add_row("/model", "Interactive model picker (Arrow Keys)")
                        table.add_row("/update", "Pull latest code and restart")
                        table.add_row("/new", "Start a fresh session")
                        table.add_row("/load", "Load a saved session (Arrow Keys)")
                        console.print(table)
                        continue
                    
                    if slash_cmd == '/setup':
                        if run_onboarding():
                            console.print("[green]🔄 Reloading configuration...[/green]")
                            client = GroqClient()
                        continue

                    if slash_cmd == '/yolo':
                        client.yolo_mode = not client.yolo_mode
                        console.print(f"🛡️  YOLO Mode: [bold]{'ON (Auto-Approve)' if client.yolo_mode else 'OFF (Protected)'}[/bold]")
                        continue

                    if slash_cmd == '/model':
                        new_model = questionary.select(
                            "Select a Model:",
                            choices=MODEL_OPTIONS,
                            default=client.model if client.model in MODEL_OPTIONS else MODEL_OPTIONS[0]
                        ).ask()
                        
                        if new_model:
                            (REPO_ROOT / ".groq_model").write_text(new_model)
                            client.model = new_model
                            console.print(f"[bold green]✅ Model set to:[/bold green] {new_model}")
                        continue

                    if slash_cmd == '/update':
                        console.print("\n🚀 [bold cyan]Self-updating Clawt...[/bold cyan]")
                        import subprocess
                        try:
                            subprocess.run(['git', '-C', str(REPO_ROOT), 'reset', '--hard', 'origin/main'], check=False)
                            subprocess.run(['git', '-C', str(REPO_ROOT), 'pull', 'origin', 'main'], check=True)
                            console.print("[bold green]✅ Update successful! Restarting...[/bold green]")
                            os.execv(sys.executable, [sys.executable, '-m', 'src.main', 'chat', '--session', session_id])
                        except Exception as e: console.print(f"[bold red]❌ Update failed: {str(e)}[/bold red]")
                        continue

                    if slash_cmd == '/new':
                        messages = []
                        from uuid import uuid4
                        session_id = uuid4().hex
                        console.print(f"[bold blue]✨ Started fresh session: {session_id}[/bold blue]")
                        continue
                        
                    if slash_cmd == '/load':
                        if DEFAULT_SESSION_DIR.exists():
                            sessions = [s.stem for s in DEFAULT_SESSION_DIR.glob("*.json")]
                            if not sessions:
                                console.print("[yellow]No saved sessions found.[/yellow]")
                                continue
                                
                            sid = questionary.select("Select a Session:", choices=sessions).ask()
                            if sid:
                                try:
                                    stored = load_session(sid)
                                    messages = []
                                    for i, msg in enumerate(stored.messages):
                                        role = "user" if i % 2 == 0 else "assistant"
                                        messages.append({"role": role, "content": msg})
                                    session_id = sid
                                    console.print(f"[bold green]✅ Resumed:[/bold green] {sid}")
                                except Exception as e: console.print(f"[bold red]❌ Load failed: {str(e)}[/bold red]")
                        else: console.print("[yellow]No session directory found.[/yellow]")
                        continue

                # Handle File Context (#)
                processed_prompt = raw_input
                file_refs = re.findall(r'#(\S+)', raw_input)
                for file_ref in file_refs:
                    if os.path.exists(file_ref):
                        try:
                            with open(file_ref, 'r') as f: content = f.read()
                            processed_prompt = processed_prompt.replace(f'#{file_ref}', f'\n--- FILE: {file_ref} ---\n{content}\n--- END FILE ---')
                            console.print(f"[dim]📎 Attached: {file_ref}[/dim]")
                        except Exception as e: console.print(f"[red]⚠️ Error reading {file_ref}: {str(e)}[/red]")

                messages.append({"role": "user", "content": processed_prompt})
                console.print("\n[bold cyan]🤖 Clawt:[/bold cyan]")
                res = client.chat_with_tools(messages)
                if res == "User terminated session.": break
                
                console.print("\n" + "─" * console.width + "\n", style="dim")
                
                try:
                    save_session(StoredSession(
                        session_id=session_id,
                        messages=tuple(m["content"] for m in messages if "content" in m),
                        input_tokens=0, output_tokens=0
                    ))
                except Exception: pass
                
            except KeyboardInterrupt: 
                console.print("\n[bold red]Goodbye![/bold red]")
                break
            except Exception as e: console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]")
        return 0
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
