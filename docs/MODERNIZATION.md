# Modernization notes

This branch (`modernize/agentic-rag`) moves the project from a 2024-era fixed RAG
pipeline to an agentic design that uses what current models are good at.

## What changed and why

| Before | After | Why |
| --- | --- | --- |
| Intake → Scope → Retrieve → Generate; one retrieval, filters guessed up front | `CurriculumAgent`: model calls tools (search, prerequisites, submit) and iterates | The model can notice an empty/weak result, loosen filters, search from another angle |
| Free-text curriculum; URLs trusted | Structured `Curriculum` + validator: every URL must come from a search result in the same session; prerequisites must name earlier modules; ≤1 difficulty step | Hallucinated links and out-of-order paths are rejected *inside the loop*, so the model fixes them |
| Gemini SDK calls scattered in agents | `src/llm` interface with Claude + Gemini adapters, native structured output | Swap providers by env var; agents and tests don't import vendor SDKs |
| Vector-only retrieval, `all-mpnet-base-v2` | BM25 + vector with RRF, LLM rerank, pluggable embeddings (`local` / `gemini`) | Exact terms (names, jargon) and meaning both matter; rerank is the biggest precision gain |
| Heuristic quality (views, subscribers) | Optional `PedagogyJudge` blended in (`LLM_QUALITY_JUDGE=1`) | Popularity ≠ teaches well |
| No eval | `scripts/run_evals.py`, 12 cases, deterministic metrics + optional judge, baseline gate | Any model/prompt change can now be measured |
| Static output | `/v3/tutor`, diagnostic quiz, flashcards, FSRS review, `/v3/study/replan` | Adaptive, interactive learning |
| 20 requirements, ~11 unused (torch/transformers/langchain/...) | Trimmed; admin/dev split out | Smaller image, fewer CVEs |

## Design decisions

- **Why Claude *and* Gemini?** The project started on Gemini and keeps working on it. The
  default Anthropic model is `claude-opus-5-5`; override with `ANTHROPIC_MODEL`.
- **Why no forced `tool_choice`?** Newer Claude models reject forced tool choice. The
  agent instead ends via a *terminal* `submit_curriculum` tool whose handler validates
  and returns errors, which is also what gives the self-correction loop.
- **Tutor citations are verified.** The model must quote verbatim; quotes not found in
  the source text are dropped and the reply is marked `grounded: false`.
- **Scoring and level inference are plain Python**, not LLM calls: reproducible and testable.
- **Embedding collections are provider-specific.** Switching `EMBEDDING_PROVIDER` selects a
  different collection; copy data with `scripts/migrate_embeddings.py`.

## Not verified here (needs your keys / services)

The offline suite (80 tests) uses scripted LLMs and fake SDK clients. It verifies logic and
message shapes, **not** live provider behaviour or retrieval quality. Before relying on this:

1. `python scripts/run_evals.py --save-baseline` against your real library, then `--compare`
   after each change. Starter cases assume your library covers music/Python/ML.
2. Smoke-test both providers (`LLM_PROVIDER=anthropic`, then `gemini`) - the Gemini tool-loop
   and embedding calls follow the `google-genai` docs but were not run against the live API.
3. Try `EMBEDDING_PROVIDER=gemini` on a copy of the data and compare eval scores.

## Known limitations / follow-ups

- Transcripts are stored without timestamps, so tutor citations are quote-level, not
  "jump to 4:12". Preserving segment timestamps at ingestion would enable that.
- Each video is one document; long transcripts would benefit from chunking.
- The BM25 index is in-memory (rebuilt when the collection size changes). Fine for tens of
  thousands of documents; use a search engine beyond that.
- Streaming endpoint keeps running server-side if the client disconnects.
- No refusal fallback is configured for Claude; a policy decline surfaces as HTTP 422.
- Legacy v1/v2 agents, `api.py`, and `google-generativeai` remain for compatibility and
  can be deleted once clients move to `/v3`.
