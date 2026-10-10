"""Gemini implementation of LLMClient (``google-genai`` SDK, not the deprecated one)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type

from google import genai
from google.genai import types

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

DEFAULT_MODEL = "gemini-2.5-flash"


def _guard(response: Any) -> None:
    feedback = getattr(response, "prompt_feedback", None)
    if feedback is not None and getattr(feedback, "block_reason", None):
        raise LLMRefusal(f"Gemini blocked the prompt: {feedback.block_reason}")


class GeminiLLM(LLMClient):
    provider = "gemini"

    def __init__(self, model: Optional[str] = None, client: Optional[genai.Client] = None):
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.client = client or genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def complete(self, prompt: str, *, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens),
        )
        _guard(response)
        return response.text or ""

    def structured(
        self,
        prompt: str,
        schema: Type[T],
        *,
        system: Optional[str] = None,
        max_tokens: int = 8192,
    ) -> T:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        _guard(response)
        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        if response.text:
            return schema.model_validate_json(response.text)
        raise LLMError("Gemini returned no structured output")

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
        declarations = [
            types.FunctionDeclaration(
                name=t.name, description=t.description, parameters_json_schema=t.input_schema
            )
            for t in tools
        ]
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            tools=[types.Tool(function_declarations=declarations)],
            # We run the loop ourselves so we can validate, stream and stop on terminal tools.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        contents: List[Any] = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        run = AgentRun()

        for step in range(1, max_steps + 1):
            run.steps = step
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
            _guard(response)

            calls = response.function_calls or []
            try:
                text = response.text or ""
            except Exception:
                text = ""
            if text:
                run.text = text
                emit(on_event, {"type": "text", "text": text})
            if not calls:
                run.stopped_by = "end_turn"
                return run

            contents.append(response.candidates[0].content)

            parts: List[Any] = []
            terminal_ok = False
            for call in calls:
                tool = by_name.get(call.name)
                arguments: Dict[str, Any] = dict(call.args or {})
                emit(on_event, {"type": "tool_call", "name": call.name, "input": arguments})
                if tool is None:
                    output, is_error = f"Unknown tool '{call.name}'", True
                else:
                    output, is_error = tool.execute(arguments)
                run.tool_calls.append(ToolCall(call.name, arguments, output, is_error))
                emit(
                    on_event,
                    {"type": "tool_result", "name": call.name, "is_error": is_error, "preview": output[:300]},
                )
                key = "error" if is_error else "result"
                parts.append(types.Part.from_function_response(name=call.name, response={key: output}))
                if tool is not None and tool.terminal and not is_error:
                    terminal_ok = True

            contents.append(types.Content(role="user", parts=parts))
            if terminal_ok:
                run.stopped_by = "terminal_tool"
                return run

        run.stopped_by = "max_steps"
        return run
