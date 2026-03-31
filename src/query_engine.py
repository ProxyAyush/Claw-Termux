from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from uuid import uuid4

from .commands import build_command_backlog
from .models import PermissionDenial, UsageSummary
from .port_manifest import PortManifest, build_port_manifest
from .session_store import StoredSession, load_session, save_session
from .tools import build_tool_backlog
from .transcript import TranscriptStore
from .groq_client import GroqClient


@dataclass(frozen=True)
class QueryEngineConfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False
    structured_retry_limit: int = 2


@dataclass(frozen=True)
class TurnResult:
    prompt: str
    output: str
    matched_commands: tuple[str, ...]
    matched_tools: tuple[str, ...]
    permission_denials: tuple[PermissionDenial, ...]
    usage: UsageSummary
    stop_reason: str


@dataclass
class QueryEnginePort:
    manifest: PortManifest
    config: QueryEngineConfig = field(default_factory=QueryEngineConfig)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    mutable_messages: list[dict[str, str]] = field(default_factory=list)
    permission_denials: list[PermissionDenial] = field(default_factory=list)
    total_usage: UsageSummary = field(default_factory=UsageSummary)
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)
    client: GroqClient = field(default_factory=GroqClient)

    @classmethod
    def from_workspace(cls) -> 'QueryEnginePort':
        return cls(manifest=build_port_manifest())

    @classmethod
    def from_saved_session(cls, session_id: str) -> 'QueryEnginePort':
        stored = load_session(session_id)
        # Assuming stored messages are strings, but we need to convert them to dicts
        # For simplicity, we'll treat them as a list of user/assistant turns
        messages = []
        for i, msg in enumerate(stored.messages):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})
        
        transcript = TranscriptStore(entries=list(stored.messages), flushed=True)
        return cls(
            manifest=build_port_manifest(),
            session_id=stored.session_id,
            mutable_messages=messages,
            total_usage=UsageSummary(stored.input_tokens, stored.output_tokens),
            transcript_store=transcript,
        )

    def submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ) -> TurnResult:
        if len(self.mutable_messages) >= self.config.max_turns * 2:
            output = f'Max turns reached before processing prompt: {prompt}'
            return TurnResult(
                prompt=prompt,
                output=output,
                matched_commands=matched_commands,
                matched_tools=matched_tools,
                permission_denials=denied_tools,
                usage=self.total_usage,
                stop_reason='max_turns_reached',
            )

        self.mutable_messages.append({"role": "user", "content": prompt})
        
        try:
            response_json = self.client.chat(self.mutable_messages)
            output = response_json["choices"][0]["message"]["content"]
            input_tokens = response_json["usage"]["prompt_tokens"]
            output_tokens = response_json["usage"]["completion_tokens"]
            
            # Update usage based on actual tokens from API
            self.total_usage = UsageSummary(
                input_tokens=self.total_usage.input_tokens + input_tokens,
                output_tokens=self.total_usage.output_tokens + output_tokens
            )
        except Exception as e:
            output = f"Error calling Groq API: {str(e)}"
            input_tokens = 0
            output_tokens = 0

        self.mutable_messages.append({"role": "assistant", "content": output})
        
        projected_usage = self.total_usage
        stop_reason = 'completed'
        if projected_usage.input_tokens + projected_usage.output_tokens > self.config.max_budget_tokens:
            stop_reason = 'max_budget_reached'
            
        self.transcript_store.append(prompt)
        self.transcript_store.append(output)
        self.permission_denials.extend(denied_tools)
        self.compact_messages_if_needed()
        
        return TurnResult(
            prompt=prompt,
            output=output,
            matched_commands=matched_commands,
            matched_tools=matched_tools,
            permission_denials=denied_tools,
            usage=self.total_usage,
            stop_reason=stop_reason,
        )

    def stream_submit_message(
        self,
        prompt: str,
        matched_commands: tuple[str, ...] = (),
        matched_tools: tuple[str, ...] = (),
        denied_tools: tuple[PermissionDenial, ...] = (),
    ):
        yield {'type': 'message_start', 'session_id': self.session_id, 'prompt': prompt}
        if matched_commands:
            yield {'type': 'command_match', 'commands': matched_commands}
        if matched_tools:
            yield {'type': 'tool_match', 'tools': matched_tools}
        if denied_tools:
            yield {'type': 'permission_denial', 'denials': [denial.tool_name for denial in denied_tools]}
        
        self.mutable_messages.append({"role": "user", "content": prompt})
        self.transcript_store.append(prompt)
        
        full_output = []
        try:
            for chunk in self.client.stream_chat(self.mutable_messages):
                full_output.append(chunk)
                yield {'type': 'message_delta', 'text': chunk}
        except Exception as e:
            error_msg = f"Error calling Groq API: {str(e)}"
            yield {'type': 'message_delta', 'text': error_msg}
            full_output.append(error_msg)

        output = "".join(full_output)
        self.mutable_messages.append({"role": "assistant", "content": output})
        self.transcript_store.append(output)
        
        # In streaming mode we don't get usage info as easily without extra work,
        # but for now we'll just estimate or ignore it for the summary.
        # Groq stream chunks don't always include usage until the final chunk.
        
        yield {
            'type': 'message_stop',
            'usage': {'input_tokens': self.total_usage.input_tokens, 'output_tokens': self.total_usage.output_tokens},
            'stop_reason': 'completed',
            'transcript_size': len(self.transcript_store.entries),
        }

    def compact_messages_if_needed(self) -> None:
        if len(self.mutable_messages) > self.config.compact_after_turns * 2:
            self.mutable_messages[:] = self.mutable_messages[-(self.config.compact_after_turns * 2) :]
        self.transcript_store.compact(self.config.compact_after_turns * 2)

    def replay_user_messages(self) -> tuple[str, ...]:
        return self.transcript_store.replay()

    def flush_transcript(self) -> None:
        self.transcript_store.flush()

    def persist_session(self) -> str:
        self.flush_transcript()
        path = save_session(
            StoredSession(
                session_id=self.session_id,
                messages=tuple(msg["content"] for msg in self.mutable_messages),
                input_tokens=self.total_usage.input_tokens,
                output_tokens=self.total_usage.output_tokens,
            )
        )
        return str(path)

    def _format_output(self, summary_lines: list[str]) -> str:
        if self.config.structured_output:
            payload = {
                'summary': summary_lines,
                'session_id': self.session_id,
            }
            return self._render_structured_output(payload)
        return '\n'.join(summary_lines)

    def _render_structured_output(self, payload: dict[str, object]) -> str:
        last_error: Exception | None = None
        for _ in range(self.config.structured_retry_limit):
            try:
                return json.dumps(payload, indent=2)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
                last_error = exc
                payload = {'summary': ['structured output retry'], 'session_id': self.session_id}
        raise RuntimeError('structured output rendering failed') from last_error

    def render_summary(self) -> str:
        command_backlog = build_command_backlog()
        tool_backlog = build_tool_backlog()
        sections = [
            '# Python Porting Workspace Summary',
            '',
            self.manifest.to_markdown(),
            '',
            f'Command surface: {len(command_backlog.modules)} mirrored entries',
            *command_backlog.summary_lines()[:10],
            '',
            f'Tool surface: {len(tool_backlog.modules)} mirrored entries',
            *tool_backlog.summary_lines()[:10],
            '',
            f'Session id: {self.session_id}',
            f'Conversation turns stored: {len(self.mutable_messages)}',
            f'Permission denials tracked: {len(self.permission_denials)}',
            f'Usage totals: in={self.total_usage.input_tokens} out={self.total_usage.output_tokens}',
            f'Max turns: {self.config.max_turns}',
            f'Max budget tokens: {self.config.max_budget_tokens}',
            f'Transcript flushed: {self.transcript_store.flushed}',
        ]
        return '\n'.join(sections)
