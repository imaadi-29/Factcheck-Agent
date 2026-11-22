"""Steps 2 + 4 - EXTRACT claims and JUDGE them. This file ties the whole pipeline together."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from .prompts import EXTRACT_PROMPT, JUDGE_PROMPT

VERDICTS = ("Verified", "Inaccurate", "False")
JUDGE_BATCH_SIZE = 4     # claims judged per AI call
JUDGE_WORKERS = 3        # batches judged at the same time (kept low for free-tier rate limits)
MAX_DOCUMENT_CHARS = 90_000


def today() -> str:
    return date.today().strftime("%d %B %Y")


def extract_claims(llm, pages: list[dict], max_claims: int) -> list[dict]:
    document = ""
    for p in pages:
        block = f"\n<<<PAGE {p['page']}>>>\n{p['text']}\n"
        if len(document) + len(block) > MAX_DOCUMENT_CHARS:
            break
        document += block

    data = llm.generate_json(EXTRACT_PROMPT.format(
        today=today(), max_claims=max_claims, document=document), thinking="low")

    valid_pages = {p["page"] for p in pages}
    claims = []
    for raw in data.get("claims", [])[:max_claims]:
        text = str(raw.get("claim", "")).strip()
        if not text:
            continue
        try:
            page = int(raw.get("page"))
        except (TypeError, ValueError):
            page = None
        queries = [str(q).strip() for q in raw.get("search_queries", []) if str(q).strip()]
        claims.append({
            "id": len(claims) + 1,
            "claim": text,
            "original_text": str(raw.get("original_text", "")).strip() or text,
            "page": page if page in valid_pages else None,
            "category": str(raw.get("category", "other")).lower(),
            "search_queries": queries or [text],
        })
    return claims


def _claims_block(batch: list[dict]) -> str:
    parts = []
    for item in batch:
        lines = [f"### CLAIM id={item['id']}: {item['claim']}"]
        if not item["evidence"]:
            lines.append("(No search results were found.)")
        for n, ev in enumerate(item["evidence"], start=1):
            dated = f" | published {ev['published_date']}" if ev.get("published_date") else ""
            lines.append(f"[{n}] {ev['title']} | {ev['url']}{dated}\n{ev['content']}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def judge_claims(llm, claims: list[dict], search_results: list[dict], on_progress=None) -> list[dict]:
    """Attach a verdict, explanation, corrected fact and sources to every claim."""
    items = []
    for claim, found in zip(claims, search_results):
        items.append({**claim, "evidence": found["evidence"], "search_error": found["error"]})

    to_judge = [i for i in items if not i["search_error"]]
    batches = [to_judge[k:k + JUDGE_BATCH_SIZE] for k in range(0, len(to_judge), JUDGE_BATCH_SIZE)]
    missing, done = [], 0
    # Judge all batches at the same time; progress is reported from this (main) thread.
    with ThreadPoolExecutor(max_workers=JUDGE_WORKERS) as pool:
        futures = {pool.submit(_judge_batch, llm, batch): batch for batch in batches}
        for future in as_completed(futures):
            batch, results = futures[future], future.result()
            for item in batch:
                if item["id"] in results:
                    _apply_verdict(item, results[item["id"]])
                else:
                    missing.append(item)
            done += len(batch)
            if on_progress:
                on_progress(done, len(to_judge))

    # The model sometimes skips a claim in a batch: ask again, one claim per call.
    for item in missing:
        results = _judge_batch(llm, [item])
        _apply_verdict(item, results.get(item["id"]))

    for item in items:
        if item["search_error"]:
            item.update(verdict="Not checked", confidence="", correct_fact="", sources=[],
                        explanation=f"The web search failed for this claim: {item['search_error']}")
    return items


def _judge_batch(llm, batch: list[dict]) -> dict:
    data = llm.generate_json(JUDGE_PROMPT.format(today=today(), claims_block=_claims_block(batch)),
                             thinking="medium")
    results = {}
    for r in data.get("results", []):
        try:
            results[int(r.get("id"))] = r
        except (TypeError, ValueError):
            continue
    return results


def _apply_verdict(item: dict, result: dict | None) -> None:
    if not result:
        item.update(verdict="Not checked", confidence="", correct_fact="", sources=[],
                    explanation="The AI model did not return a verdict for this claim.")
        return
    verdict = str(result.get("verdict", "")).strip().capitalize()
    if verdict not in VERDICTS:
        verdict = "False" if not item["evidence"] else "Inaccurate"
    # Sources are built from the real search results only, so links can never be invented.
    sources = []
    for sid in result.get("source_ids", []) or []:
        try:
            ev = item["evidence"][int(sid) - 1]
        except (ValueError, TypeError, IndexError):
            continue
        if ev["url"] not in [s["url"] for s in sources]:
            sources.append({"title": ev["title"], "url": ev["url"]})
    item.update(
        verdict=verdict,
        confidence=str(result.get("confidence", "")).capitalize(),
        explanation=str(result.get("explanation", "")).strip(),
        correct_fact="" if verdict == "Verified" else str(result.get("correct_fact", "")).strip(),
        sources=sources,
    )


def run_pipeline(llm, searcher, pages, max_claims, status=None):
    """Full run used by the app. `status` is an optional callback(str) for progress messages."""
    say = status or (lambda _msg: None)
    say("Extracting factual claims from the document...")
    claims = extract_claims(llm, pages, max_claims)
    if not claims:
        return []
    say(f"Found {len(claims)} claims. Searching the live web for evidence...")
    search_results = searcher.evidence_for_all(claims)
    say("Comparing each claim against the evidence...")
    return judge_claims(llm, claims, search_results,
                        on_progress=lambda done, total: say(f"Judged {done} of {total} claims..."))
