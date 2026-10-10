"""
Provider-neutral LLM interface.

Every agent in the project talks to an ``LLMClient`` rather than a vendor SDK, so
the provider (Claude, Gemini, or a scripted fake in tests) is a config choice.

Three primitives cover everything the app needs:
- ``complete``   free-form text
- ``structured`` text -> validated Pydantic model (native structured output)
- ``run_agent``  tool-use loop; the model decides what to call and when to stop
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

EventCallback = Callable[[Dict[str, Any]], None]


class LLMError(RuntimeError):
    """Provider call failed or returned something unusable."""


class LLMRefusal(LLMError):
    """The model declined the request (safety classifier / policy)."""


class ToolError(Exception):
    """
    Raised by a tool handler for a *recoverable* problem (bad arguments, failed
    validation). The message is sent back to the model as an error tool result so
    it can correct itself and retry.
    """


@dataclass
class Tool:
    """
    A function the model may call.

    ``terminal`` tools end the agent loop when their handler succeeds - used for
    ``submit_*`` tools whose handler validates the final answer.
    """

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Any]
    terminal: bool = False

    def execute(self, arguments: Dict[str, Any]) -> tuple[str, bool]:
        """Run the handler. Returns (serialized_result, is_error)."""
        try:
            result = self.handler(arguments)
        except ToolError as exc:
            return str(exc), True
        except Exception as exc:  # tool bugs must not kill the loop
            return f"{type(exc).__name__}: {exc}", True
        if isinstance(result, str):
            return result, False
        return json.dumps(result, default=str, ensure_ascii=False), False


@dataclass
class ToolCall:
    name: str
    input: Dict[str, Any]
    output: str
    is_error: bool = False


@dataclass
class AgentRun:
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    steps: int = 0
    # "end_turn" | "terminal_tool" | "max_steps"
    stopped_by: str = "end_turn"


class LLMClient(ABC):
    """Interface implemented by each provider."""

    provider: str = "abstract"
    model: str = ""

    @abstractmethod
    def complete(self, prompt: str, *, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        ...

    @abstractmethod
    def structured(
        self,
        prompt: str,
        schema: Type[T],
        *,
        system: Optional[str] = None,
        max_tokens: int = 8192,
    ) -> T:
        ...

    @abstractmethod
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
        ...


def emit(on_event: Optional[EventCallback], event: Dict[str, Any]) -> None:
    """Fire an event callback, never letting a UI bug break the agent loop."""
    if on_event is None:
        return
    try:
        on_event(event)
    except Exception:
        pass
