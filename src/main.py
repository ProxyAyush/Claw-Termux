from __future__ import annotations

import argparse
import os
import re

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
    parser = argparse.ArgumentParser(description='Python porting workspace for the Claude Code rewrite effort')
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('setup', help='run interactive setup for API provider and key')
    subparsers.add_parser('chat', help='start an interactive chat session')
    subparsers.add_parser('summary', help='render a Markdown summary of the Python porting workspace')
    subparsers.add_parser('manifest', help='print the current Python workspace manifest')
    subparsers.add_parser('models', help='list available Groq models')
    set_model_parser = subparsers.add_parser('set-model', help='set the Groq model to use')
    set_model_parser.add_argument('model_id')
    subparsers.add_parser('parity-audit', help='compare the Python workspace against the local ignored TypeScript archive when available')
    subparsers.add_parser('setup-report', help='render the startup/prefetch setup report')
    subparsers.add_parser('command-graph', help='show command graph segmentation')
    subparsers.add_parser('tool-pool', help='show assembled tool pool with default settings')
    subparsers.add_parser('bootstrap-graph', help='show the mirrored bootstrap/runtime graph stages')
    list_parser = subparsers.add_parser('subsystems', help='list the current Python modules in the workspace')
    list_parser.add_argument('--limit', type=int, default=32)

    commands_parser = subparsers.add_parser('commands', help='list mirrored command entries from the archived snapshot')
    commands_parser.add_argument('--limit', type=int, default=20)
    commands_parser.add_argument('--query')
    commands_parser.add_argument('--no-plugin-commands', action='store_true')
    commands_parser.add_argument('--no-skill-commands', action='store_true')

    tools_parser = subparsers.add_parser('tools', help='list mirrored tool entries from the archived snapshot')
    tools_parser.add_argument('--limit', type=int, default=20)
    tools_parser.add_argument('--query')
    tools_parser.add_argument('--simple-mode', action='store_true')
    tools_parser.add_argument('--no-mcp', action='store_true')
    tools_parser.add_argument('--deny-tool', action='append', default=[])
    tools_parser.add_argument('--deny-prefix', action='append', default=[])

    route_parser = subparsers.add_parser('route', help='route a prompt across mirrored command/tool inventories')
    route_parser.add_argument('prompt')
    route_parser.add_argument('--limit', type=int, default=5)

    bootstrap_parser = subparsers.add_parser('bootstrap', help='build a runtime-style session report from the mirrored inventories')
    bootstrap_parser.add_argument('prompt')
    bootstrap_parser.add_argument('--limit', type=int, default=5)

    loop_parser = subparsers.add_parser('turn-loop', help='run a small stateful turn loop for the mirrored runtime')
    loop_parser.add_argument('prompt')
    loop_parser.add_argument('--limit', type=int, default=5)
    loop_parser.add_argument('--max-turns', type=int, default=3)
    loop_parser.add_argument('--structured-output', action='store_true')

    flush_parser = subparsers.add_parser('flush-transcript', help='persist and flush a temporary session transcript')
    flush_parser.add_argument('prompt')

    load_session_parser = subparsers.add_parser('load-session', help='load a previously persisted session')
    load_session_parser.add_argument('session_id')

    remote_parser = subparsers.add_parser('remote-mode', help='simulate remote-control runtime branching')
    remote_parser.add_argument('target')
    ssh_parser = subparsers.add_parser('ssh-mode', help='simulate SSH runtime branching')
    ssh_parser.add_argument('target')
    teleport_parser = subparsers.add_parser('teleport-mode', help='simulate teleport runtime branching')
    teleport_parser.add_argument('target')
    direct_parser = subparsers.add_parser('direct-connect-mode', help='simulate direct-connect runtime branching')
    direct_parser.add_argument('target')
    deep_link_parser = subparsers.add_parser('deep-link-mode', help='simulate deep-link runtime branching')
    deep_link_parser.add_argument('target')

    show_command = subparsers.add_parser('show-command', help='show one mirrored command entry by exact name')
    show_command.add_argument('name')
    show_tool = subparsers.add_parser('show-tool', help='show one mirrored tool entry by exact name')
    show_tool.add_argument('name')

    exec_command_parser = subparsers.add_parser('exec-command', help='execute a mirrored command shim by exact name')
    exec_command_parser.add_argument('name')
    exec_command_parser.add_argument('prompt')

    exec_tool_parser = subparsers.add_parser('exec-tool', help='execute a mirrored tool shim by exact name')
    exec_tool_parser.add_argument('name')
    exec_tool_parser.add_argument('payload')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    if args.command == 'setup':
        return 0 if run_onboarding() else 1
        
    if not check_setup() and args.command in ['chat', 'turn-loop', 'route', 'bootstrap', 'flush-transcript']:
        print("No API configuration found. Running setup...")
        if not run_onboarding():
            return 1

    if args.command == 'chat':
        engine = QueryEnginePort.from_workspace()
        print("\n💬 Starting Claw-Termux Chat")
        print("Type '/help' for commands, or 'exit' to stop.")
        
        while True:
            try:
                raw_input = input("\n👤 You: ").strip()
                if not raw_input:
                    continue
                
                # Handle Exit
                if raw_input.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                # Handle Slash Commands
                if raw_input.startswith('/'):
                    parts = raw_input.split()
                    cmd = parts[0].lower()
                    
                    if cmd == '/help':
                        print("\nAvailable Commands:")
                        print("  /help           - Show this help message")
                        print("  /model [id]     - View or change the current model")
                        print("  /models         - List available Groq models")
                        print("  /clear          - Clear conversation history")
                        print("  /summary        - Show session summary")
                        print("  /reset          - Full reset of the engine")
                        print("\nContext Referencing:")
                        print("  #filename       - Include file content in your prompt")
                        continue
                    
                    if cmd == '/model':
                        if len(parts) > 1:
                            new_model = parts[1]
                            with open(".groq_model", "w") as f:
                                f.write(new_model)
                            engine.client.model = new_model
                            print(f"Model updated to: {new_model}")
                        else:
                            print(f"Current model: {engine.client.model}")
                        continue
                    
                    if cmd == '/models':
                        models = [
                            "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
                            "mixtral-8x7b-32768", "gemma2-9b-it",
                            "deepseek-r1-distill-llama-70b", "qwen-2.5-32b"
                        ]
                        print("Available Models:")
                        for m in models: print(f" - {m}")
                        continue
                        
                    if cmd == '/clear':
                        engine.mutable_messages = []
                        engine.transcript_store.entries = []
                        print("Conversation history cleared.")
                        continue
                        
                    if cmd == '/summary':
                        print("\n" + engine.render_summary())
                        continue

                    if cmd == '/reset':
                        engine = QueryEnginePort.from_workspace()
                        print("Engine reset.")
                        continue
                
                # Handle Context Referencing (#file)
                processed_prompt = raw_input
                import re
                file_refs = re.findall(r'#(\S+)', raw_input)
                for file_ref in file_refs:
                    try:
                        if os.path.exists(file_ref):
                            with open(file_ref, 'r') as f:
                                content = f.read()
                            processed_prompt = processed_prompt.replace(f'#{file_ref}', f'\n--- FILE: {file_ref} ---\n{content}\n--- END FILE ---')
                            print(f"📎 Attached file: {file_ref}")
                        else:
                            print(f"⚠️ File not found: {file_ref}")
                    except Exception as e:
                        print(f"❌ Error reading {file_ref}: {str(e)}")

                # Submit Message
                print("\n🤖 Assistant: ", end="", flush=True)
                for chunk in engine.stream_submit_message(processed_prompt):
                    if chunk['type'] == 'message_delta':
                        print(chunk['text'], end="", flush=True)
                print("\n")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
        return 0

    manifest = build_port_manifest()
    if args.command == 'summary':
        print(QueryEnginePort(manifest).render_summary())
        return 0
    if args.command == 'manifest':
        print(manifest.to_markdown())
        return 0
    if args.command == 'models':
        models = [
            "llama-3.3-70b-versatile (Production, Versatile, 128k context)",
            "llama-3.1-8b-instant (Production, Fast, 128k context)",
            "mixtral-8x7b-32768 (Production, Sparse MoE, 32k context)",
            "gemma2-9b-it (Production, Google model, 8k context)",
            "deepseek-r1-distill-llama-70b (Reasoning)",
            "llama-3.3-70b-specdec (Speculative Decoding)",
            "qwen-2.5-32b (Fast, Versatile)"
        ]
        print("Available Groq Models:")
        for m in models:
            print(f"- {m}")
        return 0
    if args.command == 'set-model':
        with open(".groq_model", "w") as f:
            f.write(args.model_id.strip())
        print(f"Groq model set to: {args.model_id}")
        return 0
    if args.command == 'parity-audit':
        print(run_parity_audit().to_markdown())
        return 0
    if args.command == 'setup-report':
        print(run_setup().as_markdown())
        return 0
    if args.command == 'command-graph':
        print(build_command_graph().as_markdown())
        return 0
    if args.command == 'tool-pool':
        print(assemble_tool_pool().as_markdown())
        return 0
    if args.command == 'bootstrap-graph':
        print(build_bootstrap_graph().as_markdown())
        return 0
    if args.command == 'subsystems':
        for subsystem in manifest.top_level_modules[: args.limit]:
            print(f'{subsystem.name}\t{subsystem.file_count}\t{subsystem.notes}')
        return 0
    if args.command == 'commands':
        if args.query:
            print(render_command_index(limit=args.limit, query=args.query))
        else:
            commands = get_commands(include_plugin_commands=not args.no_plugin_commands, include_skill_commands=not args.no_skill_commands)
            output_lines = [f'Command entries: {len(commands)}', '']
            output_lines.extend(f'- {module.name} — {module.source_hint}' for module in commands[: args.limit])
            print('\n'.join(output_lines))
        return 0
    if args.command == 'tools':
        if args.query:
            print(render_tool_index(limit=args.limit, query=args.query))
        else:
            permission_context = ToolPermissionContext.from_iterables(args.deny_tool, args.deny_prefix)
            tools = get_tools(simple_mode=args.simple_mode, include_mcp=not args.no_mcp, permission_context=permission_context)
            output_lines = [f'Tool entries: {len(tools)}', '']
            output_lines.extend(f'- {module.name} — {module.source_hint}' for module in tools[: args.limit])
            print('\n'.join(output_lines))
        return 0
    if args.command == 'route':
        matches = PortRuntime().route_prompt(args.prompt, limit=args.limit)
        if not matches:
            print('No mirrored command/tool matches found.')
            return 0
        for match in matches:
            print(f'{match.kind}\t{match.name}\t{match.score}\t{match.source_hint}')
        return 0
    if args.command == 'bootstrap':
        print(PortRuntime().bootstrap_session(args.prompt, limit=args.limit).as_markdown())
        return 0
    if args.command == 'turn-loop':
        results = PortRuntime().run_turn_loop(args.prompt, limit=args.limit, max_turns=args.max_turns, structured_output=args.structured_output)
        for idx, result in enumerate(results, start=1):
            print(f'## Turn {idx}')
            print(result.output)
            print(f'stop_reason={result.stop_reason}')
        return 0
    if args.command == 'flush-transcript':
        engine = QueryEnginePort.from_workspace()
        engine.submit_message(args.prompt)
        path = engine.persist_session()
        print(path)
        print(f'flushed={engine.transcript_store.flushed}')
        return 0
    if args.command == 'load-session':
        session = load_session(args.session_id)
        print(f'{session.session_id}\n{len(session.messages)} messages\nin={session.input_tokens} out={session.output_tokens}')
        return 0
    if args.command == 'remote-mode':
        print(run_remote_mode(args.target).as_text())
        return 0
    if args.command == 'ssh-mode':
        print(run_ssh_mode(args.target).as_text())
        return 0
    if args.command == 'teleport-mode':
        print(run_teleport_mode(args.target).as_text())
        return 0
    if args.command == 'direct-connect-mode':
        print(run_direct_connect(args.target).as_text())
        return 0
    if args.command == 'deep-link-mode':
        print(run_deep_link(args.target).as_text())
        return 0
    if args.command == 'show-command':
        module = get_command(args.name)
        if module is None:
            print(f'Command not found: {args.name}')
            return 1
        print('\n'.join([module.name, module.source_hint, module.responsibility]))
        return 0
    if args.command == 'show-tool':
        module = get_tool(args.name)
        if module is None:
            print(f'Tool not found: {args.name}')
            return 1
        print('\n'.join([module.name, module.source_hint, module.responsibility]))
        return 0
    if args.command == 'exec-command':
        result = execute_command(args.name, args.prompt)
        print(result.message)
        return 0 if result.handled else 1
    if args.command == 'exec-tool':
        result = execute_tool(args.name, args.payload)
        print(result.message)
        return 0 if result.handled else 1
    parser.error(f'unknown command: {args.command}')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
