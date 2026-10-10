"""Claude implementation of LLMClient (official ``anthropic`` SDK)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type

import anthropic

from src.llm.types import (
    AgentRun,
    EventCallback,
    LLMClient,
    LLMError,
    LLMRefusal,
    T,
    Tool,
    ToolCall,
    emit,
)

DEFAULT_MODEL = "claude-opus-5-5"


def _check_stop(response: Any) -> None:
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None)
        raise LLMRefusal(f"Claude declined the request (category={category})")
    if response.stop_reason == "max_tokens":
        raise LLMError("Response truncated at max_tokens; raise max_tokens")


def _text_of(response: Any) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


class AnthropicLLM(LLMClient):
    provider = "anthropic"

    def __init__(
        self,
        model: Optional[str] = None,
        effort: str = "medium",
        client: Optional[anthropic.Anthropic] = None,
    ):
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.effort = effort
        # Zero-arg client resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = client or anthropic.Anthropic()

    def _base(self, system: Optional[str], max_tokens: int) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "output_config": {"effort": self.effort},
        }
        if system:
            kwargs["system"] = system
        return kwargs

    def complete(self, prompt: str, *, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        response = self.client.messages.create(
            messages=[{"role": "user", "content": prompt}],
            **self._base(system, max_tokens),
        )
        _check_stop(response)
        return _text_of(response)

    def structured(
        self,
        prompt: str,
        schema: Type[T],
        *,
        system: Optional[str] = None,
        max_tokens: int = 8192,
    ) -> T:
        response = self.client.messages.parse(
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            **self._base(system, max_tokens),
        )
        _check_stop(response)
        if response.parsed_output is None:
            raise LLMError("Claude returned no parseable structured output")
        return response.parsed_output

    def run_agent(
        self,
        prompt: str,
        tools: List[Tool],
        *,
        system: Optional[str] = None,
        max_steps: int = 12,
        max_tokens: int = 8192,
        on_event: Optional[EventCallback] = None,
    ) -> AgentRun:
        by_name = {t.name: t for t in tools}
        tool_defs = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]
        messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        run = AgentRun()

        for step in range(1, max_steps + 1):
            run.steps = step
            response = self.client.messages.create(
                messages=messages, tools=tool_defs, **self._base(system, max_tokens)
            )
            _check_stop(response)

            text = _text_of(response)
            if text:
                run.text = text
                emit(on_event, {"type": "text", "text": text})

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                run.stopped_by = "end_turn"
                return run

            # Keep the full content (incl. thinking blocks) so the model's reasoning
            # stays valid across turns.
            messages.append({"role": "assistant", "content": response.content})

            results: List[Dict[str, Any]] = []
            terminal_ok = False
            for block in tool_uses:
                tool = by_name.get(block.name)
                arguments = dict(block.input or {})
                emit(on_event, {"type": "tool_call", "name": block.name, "input": arguments})
                if tool is None:
                    output, is_error = f"Unknown tool '{block.name}'", True
                else:
                    output, is_error = tool.execute(arguments)
                run.tool_calls.append(ToolCall(block.name, arguments, output, is_error))
                emit(
                    on_event,
                    {"type": "tool_result", "name": block.name, "is_error": is_error, "preview": output[:300]},
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                        **({"is_error": True} if is_error else {}),
                    }
                )
                if tool is not None and tool.terminal and not is_error:
                    terminal_ok = True

            # All results for one assistant turn go back in a single user message.
            messages.append({"role": "user", "content": results})
            if terminal_ok:
                run.stopped_by = "terminal_tool"
                return run

        run.stopped_by = "max_steps"
        return run
