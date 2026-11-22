"""Offline tests of the app's internal logic, using stand-ins for the AI and search APIs.

These do NOT test fact-checking quality (that needs the real APIs). They check that
pages, verdicts and source links are wired together correctly and errors are handled.
Run:  python -m pytest tests/test_plumbing.py -q
"""
from pathlib import Path

from factcheck.checker import run_pipeline
from factcheck.pdf_utils import extract_pages

PDF = Path(__file__).parent / "pdfs" / "4_trap_mixed.pdf"


class StubLLM:
    active_model = "stub"

    def generate_json(self, prompt, thinking=None):
        if "Extract up to" in prompt:
            return {"claims": [
                {"claim": "Eiffel Tower completed in 1925", "original_text": "completed in 1925",
                 "page": 2, "category": "date", "search_queries": ["Eiffel Tower completion year"]},
                {"claim": "Python released 1991", "page": "2", "category": "date", "search_queries": []},
                {"claim": "Made-up page", "page": 99, "search_queries": ["x"]},
                {"claim": "", "page": 1},
            ]}
        return {"results": [
            {"id": 1, "verdict": "inaccurate", "confidence": "high", "explanation": "Built 1889.",
             "correct_fact": "Completed in 1889.", "source_ids": [1, 1, 7]},
            {"id": 2, "verdict": "Verified", "explanation": "ok", "correct_fact": "ignored", "source_ids": [2]},
            {"id": 3, "verdict": "nonsense", "source_ids": []},
        ]}


class StubSearch:
    def evidence_for_all(self, claims):
        ev = [{"title": "A", "url": "https://a.example", "content": "1889"},
              {"title": "B", "url": "https://b.example", "content": "1991"}]
        out = [{"evidence": ev, "error": ""} for _ in claims]
        out[-1] = {"evidence": [], "error": "quota exceeded"}
        return out


def test_pipeline_wiring():
    pages, total = extract_pages(PDF.read_bytes())
    assert total == 2 and [p["page"] for p in pages] == [1, 2]
    results = run_pipeline(StubLLM(), StubSearch(), pages, max_claims=10)
    assert len(results) == 3                       # empty claim dropped
    r1, r2, r3 = results
    assert r1["verdict"] == "Inaccurate" and r1["page"] == 2
    assert [s["url"] for s in r1["sources"]] == ["https://a.example"]   # dedup + bad id ignored
    assert r2["verdict"] == "Verified" and r2["correct_fact"] == "" and r2["page"] == 2
    assert r2["search_queries"] == ["Python released 1991"]             # falls back to claim text
    assert r3["page"] is None                      # page 99 does not exist
    assert r3["verdict"] == "Not checked"          # search error is reported, not guessed


def test_bad_pdf():
    import pytest
    from factcheck.pdf_utils import PDFError
    with pytest.raises(PDFError):
        extract_pages(b"not a pdf")


def test_skipped_claim_is_retried():
    """If the model leaves a claim out of a batch, it is asked again on its own."""
    from factcheck.checker import judge_claims

    class SkippingLLM:
        calls = 0

        def generate_json(self, prompt, thinking=None):
            SkippingLLM.calls += 1
            if "### CLAIM id=1" in prompt:   # batch call: answer claim 1, skip claim 2
                return {"results": [{"id": 1, "verdict": "Verified", "source_ids": [1]}]}
            return {"results": [{"id": 2, "verdict": "False", "source_ids": []}]}

    claims = [{"id": 1, "claim": "a", "search_queries": ["a"]}, {"id": 2, "claim": "b", "search_queries": ["b"]}]
    found = [{"evidence": [{"title": "T", "url": "https://t.example", "content": "x"}], "error": ""}] * 2
    out = judge_claims(SkippingLLM(), claims, found)
    assert [r["verdict"] for r in out] == ["Verified", "False"]
    assert SkippingLLM.calls == 2


def test_parallel_search_keeps_partial_results():
    """One failed query should not throw away the other query's evidence."""
    from factcheck.search import SearchClient

    sc = SearchClient.__new__(SearchClient)

    def fake_search(query):
        if query.startswith("bad"):
            raise RuntimeError("quota exceeded")
        return [{"url": f"https://{query}.example", "title": query, "content": "text"},
                {"url": "https://www.instagram.com/p/1", "title": "ig", "content": "x"}]

    sc._search_one = fake_search
    claims = [{"search_queries": ["bad-a", "good-a"]}, {"search_queries": ["bad-b"]}]
    out = sc.evidence_for_all(claims)
    assert [e["url"] for e in out[0]["evidence"]] == ["https://good-a.example"]  # Instagram dropped
    assert out[0]["error"] == ""
    assert out[1]["evidence"] == [] and "quota" in out[1]["error"]


def test_thinking_setting_falls_back_when_unsupported():
    from types import SimpleNamespace
    from factcheck.llm import GeminiLLM

    configs = []

    def generate_content(model, contents, config):
        configs.append(config.thinking_config)
        if config.thinking_config is not None:
            raise RuntimeError("400 INVALID_ARGUMENT: thinking_level is not supported for this model")
        return SimpleNamespace(text='{"ok": true}')

    llm = GeminiLLM.__new__(GeminiLLM)
    llm.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    llm.models, llm.active_model, llm.thinking_supported = ["m"], "m", True
    assert llm.generate_json("hi", thinking="low") == {"ok": True}
    assert configs[0] is not None and configs[1] is None
