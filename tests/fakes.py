"""Test doubles: a scripted LLM and an in-memory Chroma-like collection."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type

from src.llm.types import AgentRun, LLMClient, Tool, ToolCall, T, emit
from src.retrieval.hybrid import tokenize


class ScriptedLLM(LLMClient):
    """
    ``run_agent`` replays a script of tool calls through the REAL tool handlers, so
    agent wiring (tools, validation, terminal handling) is exercised without a model.

    script items: (tool_name, args) or a callable(state) -> (tool_name, args)
    """

    provider = "scripted"
    model = "scripted"

    def __init__(self, script=None, structured_queue: Optional[List[Any]] = None, completions: Optional[List[str]] = None):
        self.script = list(script or [])
        self.structured_queue = list(structured_queue or [])
        self.completions = list(completions or [])
        self.prompts: List[str] = []

    def complete(self, prompt, *, system=None, max_tokens=4096):
        self.prompts.append(prompt)
        return self.completions.pop(0) if self.completions else ""

    def structured(self, prompt, schema: Type[T], *, system=None, max_tokens=8192) -> T:
        self.prompts.append(prompt)
        item = self.structured_queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, schema) else schema.model_validate(item)

    def run_agent(self, prompt, tools: List[Tool], *, system=None, max_steps=12, max_tokens=8192, on_event=None):
        self.prompts.append(prompt)
        by_name = {t.name: t for t in tools}
        run = AgentRun()
        history: List[ToolCall] = []
        for step, item in enumerate(self.script, 1):
            if step > max_steps:
                run.stopped_by = "max_steps"
                return run
            name, args = item(history) if callable(item) else item
            run.steps = step
            emit(on_event, {"type": "tool_call", "name": name, "input": args})
            tool = by_name.get(name)
            output, is_error = tool.execute(args) if tool else (f"Unknown tool {name}", True)
            call = ToolCall(name, args, output, is_error)
            run.tool_calls.append(call)
            history.append(call)
            emit(on_event, {"type": "tool_result", "name": name, "is_error": is_error, "preview": output[:200]})
            if tool and tool.terminal and not is_error:
                run.stopped_by = "terminal_tool"
                return run
        run.stopped_by = "end_turn"
        return run


class FakeCollection:
    """Minimal Chroma collection: vector 'similarity' is token overlap."""

    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs  # each: id, text, metadata

    def count(self):
        return len(self.docs)

    @staticmethod
    def _match(meta: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
        if not where:
            return True
        if "$and" in where:
            return all(FakeCollection._match(meta, w) for w in where["$and"])
        (key, cond), = where.items()
        val = meta.get(key)
        if isinstance(cond, dict):
            return all(val is not None and val >= v for op, v in cond.items() if op == "$gte")
        return val == cond

    def get(self, where=None, include=None, limit=None):
        rows = [d for d in self.docs if self._match(d["metadata"], where)]
        return {
            "ids": [d["id"] for d in rows],
            "documents": [d["text"] for d in rows],
            "metadatas": [d["metadata"] for d in rows],
        }

    def query(self, query_texts, n_results=10, where=None, include=None):
        q = set(tokenize(query_texts[0]))
        rows = [d for d in self.docs if self._match(d["metadata"], where)]
        rows.sort(key=lambda d: len(q & set(tokenize(d["text"]))), reverse=True)
        rows = rows[:n_results]
        return {
            "ids": [[d["id"] for d in rows]],
            "documents": [[d["text"] for d in rows]],
            "metadatas": [[d["metadata"] for d in rows]],
            "distances": [[0.1 * i for i in range(len(rows))]],
        }


def make_corpus() -> FakeCollection:
    def doc(i, title, text, diff, sub="PIANO", q=0.9):
        return {
            "id": i,
            "text": text,
            "metadata": {
                "source": f"https://youtube.com/watch?v={i}",
                "title": title,
                "domain_id": "MUSIC",
                "subdomain_id": sub,
                "difficulty": diff,
                "helpfulness_score": q,
                "platform": "youtube",
            },
        }

    return FakeCollection(
        [
            doc("v1", "Piano from zero", "learn piano basics keys notes middle c hand position beginner", "beginner"),
            doc("v2", "Reading sheet music", "read sheet music staff clef notes rhythm piano", "beginner"),
            doc("v3", "Major scales and chords", "major scales chords triads piano theory", "intermediate"),
            doc("v4", "Advanced jazz voicings", "jazz voicings extensions altered dominant piano advanced", "advanced"),
            doc("g1", "Guitar basics", "guitar strings frets open chords beginner", "beginner", sub="GUITAR"),
        ]
    )
