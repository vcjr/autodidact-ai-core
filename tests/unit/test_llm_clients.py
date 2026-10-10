"""Adapter tests against fake SDK clients (no network)."""

from types import SimpleNamespace as NS

import pytest
from pydantic import BaseModel

from src.llm.anthropic_client import AnthropicLLM
from src.llm.gemini_client import GeminiLLM
from src.llm.types import LLMError, LLMRefusal, Tool, ToolError


def text(t):
    return NS(type="text", text=t)


def tool_use(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def resp(content, stop="end_turn", **kw):
    return NS(content=content, stop_reason=stop, stop_details=kw.get("details"), parsed_output=kw.get("parsed"))


class FakeAnthropic:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = NS(create=self._create, parse=self._create)

    def _create(self, **kwargs):
        # snapshot messages: the loop mutates the list after the call
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def echo_tool(terminal=False):
    def handler(args):
        if args.get("bad"):
            raise ToolError("nope")
        return {"echo": args}
    return Tool("echo", "echo", {"type": "object", "properties": {}}, handler, terminal=terminal)


def test_anthropic_complete_sends_effort_and_system():
    fake = FakeAnthropic([resp([text("hi")])])
    llm = AnthropicLLM(client=fake, model="claude-opus-5-5")
    assert llm.complete("q", system="sys") == "hi"
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["system"] == "sys"
    assert call["output_config"] == {"effort": "medium"}


def test_anthropic_refusal_and_truncation_raise():
    with pytest.raises(LLMRefusal):
        AnthropicLLM(client=FakeAnthropic([resp([], "refusal", details=NS(category="cyber"))])).complete("x")
    with pytest.raises(LLMError, match="max_tokens"):
        AnthropicLLM(client=FakeAnthropic([resp([text("cut")], "max_tokens")])).complete("x")


def test_anthropic_structured_uses_parse_output():
    class Out(BaseModel):
        n: int

    fake = FakeAnthropic([resp([text("{}")], parsed=Out(n=3))])
    assert AnthropicLLM(client=fake).structured("x", Out).n == 3
    assert fake.calls[0]["output_format"] is Out
    with pytest.raises(LLMError):
        AnthropicLLM(client=FakeAnthropic([resp([text("{}")], parsed=None)])).structured("x", Out)


def test_anthropic_agent_loop_batches_results_and_reports_errors():
    fake = FakeAnthropic([
        resp([text("thinking"), tool_use("t1", "echo", {"a": 1}), tool_use("t2", "echo", {"bad": True})], "tool_use"),
        resp([text("done")], "end_turn"),
    ])
    events = []
    run = AnthropicLLM(client=fake).run_agent("go", [echo_tool()], on_event=events.append)

    assert run.stopped_by == "end_turn" and run.text == "done" and run.steps == 2
    second = fake.calls[1]["messages"]
    assert second[1]["role"] == "assistant"
    results = second[2]["content"]
    assert second[2]["role"] == "user" and len(results) == 2          # ONE user message, both results
    assert results[0]["tool_use_id"] == "t1" and "is_error" not in results[0]
    assert results[1]["is_error"] is True and results[1]["content"] == "nope"
    assert [e["type"] for e in events].count("tool_call") == 2
    assert "tools" in fake.calls[0] and fake.calls[0]["tools"][0]["input_schema"]


def test_anthropic_terminal_tool_stops_loop_but_error_does_not():
    fake = FakeAnthropic([
        resp([tool_use("t1", "echo", {"bad": True})], "tool_use"),
        resp([tool_use("t2", "echo", {})], "tool_use"),
        resp([text("never reached")], "end_turn"),
    ])
    run = AnthropicLLM(client=fake).run_agent("go", [echo_tool(terminal=True)])
    assert run.stopped_by == "terminal_tool" and run.steps == 2 and len(fake.responses) == 1


def test_anthropic_unknown_tool_and_max_steps():
    fake = FakeAnthropic([resp([tool_use("t1", "ghost", {})], "tool_use")] * 2)
    run = AnthropicLLM(client=fake).run_agent("go", [echo_tool()], max_steps=2)
    assert run.stopped_by == "max_steps"
    assert run.tool_calls[0].is_error and "Unknown tool" in run.tool_calls[0].output


# ---- Gemini -----------------------------------------------------------------

class FakeGemini:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.models = NS(generate_content=self._gen)

    def _gen(self, model, contents, config):
        self.calls.append({"model": model, "contents": list(contents) if isinstance(contents, list) else contents, "config": config})
        return self.responses.pop(0)


def gresp(text_=None, calls=None, parsed=None):
    content = NS(role="model", parts=[])
    return NS(
        text=text_, function_calls=calls or [], parsed=parsed, prompt_feedback=None,
        candidates=[NS(content=content)],
    )


def test_gemini_agent_loop_and_function_response():
    fake = FakeGemini([
        gresp(calls=[NS(name="echo", args={"a": 1})]),
        gresp(text_="all done"),
    ])
    run = GeminiLLM(client=fake, model="m").run_agent("go", [echo_tool()])
    assert run.text == "all done" and run.stopped_by == "end_turn" and len(run.tool_calls) == 1
    cfg = fake.calls[0]["config"]
    assert cfg.automatic_function_calling.disable is True
    assert cfg.tools[0].function_declarations[0].name == "echo"
    reply = fake.calls[1]["contents"][-1]
    assert reply.role == "user" and reply.parts[0].function_response.name == "echo"


def test_gemini_terminal_tool_and_error_key():
    fake = FakeGemini([gresp(calls=[NS(name="echo", args={"bad": True})]), gresp(calls=[NS(name="echo", args={})])])
    run = GeminiLLM(client=fake, model="m").run_agent("go", [echo_tool(terminal=True)])
    assert run.stopped_by == "terminal_tool"
    first_reply = fake.calls[1]["contents"][-1].parts[0].function_response.response
    assert "error" in first_reply


def test_gemini_structured_falls_back_to_text_json():
    class Out(BaseModel):
        n: int

    fake = FakeGemini([gresp(text_='{"n": 7}', parsed=None)])
    assert GeminiLLM(client=fake, model="m").structured("x", Out).n == 7
