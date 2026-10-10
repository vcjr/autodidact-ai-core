from src.llm.types import LLMError
from src.retrieval import BM25Index, HybridRetriever, LLMReranker, best_excerpt, build_where
from src.retrieval.hybrid import rrf, tokenize
from tests.fakes import ScriptedLLM, make_corpus


def test_tokenize_drops_stopwords_keeps_tech_terms():
    assert tokenize("How to learn C# and Node.js") == ["learn", "c#", "node.js"]


def test_bm25_prefers_exact_rare_term():
    idx = BM25Index(["a", "b", "c"], ["python basics tutorial", "rust ownership borrow checker", "tutorial tutorial tutorial"])
    assert idx.search("borrow checker")[0][0] == "b"
    assert idx.search("zzzz") == []


def test_rrf_rewards_agreement():
    fused = rrf([["a", "b", "c"], ["c", "a", "d"]])
    assert fused["a"] > fused["b"] and fused["a"] > fused["d"]


def test_build_where_shapes():
    assert build_where() is None
    assert build_where(domain_id="music") == {"domain_id": "MUSIC"}
    w = build_where("music", "piano", "Beginner", 0.5)
    assert w == {"$and": [
        {"domain_id": "MUSIC"}, {"subdomain_id": "PIANO"}, {"difficulty": "beginner"},
        {"helpfulness_score": {"$gte": 0.5}},
    ]}


def test_best_excerpt_centres_on_query_terms():
    text = "filler " * 300 + "the sweep picking technique is explained here" + " filler" * 300
    out = best_excerpt(text, "sweep picking", max_chars=200)
    assert "sweep picking" in out and len(out) < 220


def test_hybrid_search_respects_filters_and_records_ranks():
    r = HybridRetriever(make_corpus())
    hits = r.search("piano scales", where=build_where(domain_id="MUSIC", subdomain_id="PIANO"), k=3)
    assert hits and all(h.metadata["subdomain_id"] == "PIANO" for h in hits)
    assert hits[0].id == "v3"
    assert "vector" in hits[0].ranks or "bm25" in hits[0].ranks


def test_hybrid_exact_term_query_finds_rare_doc():
    r = HybridRetriever(make_corpus())
    hits = r.search("altered dominant", k=2, pool=1)
    assert hits[0].id == "v4"


def test_reranker_reorders_and_falls_back():
    corpus = make_corpus()
    base = HybridRetriever(corpus).search("piano", k=4)
    ids = [h.id for h in base]
    llm = ScriptedLLM(structured_queue=[
        {"ranked": [{"id": i, "relevance": 10 if i == ids[-1] else 1, "reason": "x"} for i in ids]},
    ])
    out = LLMReranker(llm).rerank("piano", base, top_n=2)
    assert out[0].id == ids[-1] and len(out) == 2

    broken = ScriptedLLM(structured_queue=[LLMError("boom")])
    assert [h.id for h in LLMReranker(broken).rerank("piano", base, top_n=2)] == ids[:2]


def test_retriever_uses_reranker_when_present():
    corpus = make_corpus()
    base_ids = [h.id for h in HybridRetriever(corpus).search("piano", k=4)]
    llm = ScriptedLLM(structured_queue=[
        {"ranked": [{"id": i, "relevance": 10 if i == base_ids[-1] else 0, "reason": ""} for i in base_ids]},
    ])
    hits = HybridRetriever(corpus, reranker=LLMReranker(llm)).search("piano", k=1, pool=4)
    assert hits[0].id == base_ids[-1]
