"""Step 3 - SEARCH: look each claim up on the live web with the Tavily API.

Tavily is a search engine built for AI apps: it returns the page title, URL and
the most relevant text from each page, which we pass to the AI judge as evidence.
"""

from concurrent.futures import ThreadPoolExecutor

from tavily import TavilyClient

RESULTS_PER_QUERY = 5
MAX_EVIDENCE_PER_CLAIM = 6
MAX_CHARS_PER_RESULT = 1200


class SearchClient:
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)

    def _search_one(self, query: str) -> list[dict]:
        response = self.client.search(
            query=query,
            search_depth="advanced",   # better text snippets (2 credits per search)
            max_results=RESULTS_PER_QUERY,
        )
        return response.get("results", [])

    def evidence_for(self, queries: list[str]) -> list[dict]:
        """Run up to two queries for one claim and return de-duplicated evidence."""
        evidence, seen_urls = [], set()
        for query in queries[:2]:
            for item in self._search_one(query):
                url = item.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                evidence.append({
                    "title": (item.get("title") or url)[:200],
                    "url": url,
                    "content": (item.get("content") or "")[:MAX_CHARS_PER_RESULT],
                    "published_date": item.get("published_date", ""),
                })
        evidence.sort(key=lambda e: len(e["content"]), reverse=True)
        return evidence[:MAX_EVIDENCE_PER_CLAIM]

    def evidence_for_all(self, claims: list[dict], workers: int = 4) -> list[dict]:
        """Search for every claim in parallel. Errors are recorded per claim."""

        def run(claim):
            try:
                return {"evidence": self.evidence_for(claim["search_queries"]), "error": ""}
            except Exception as exc:  # network problem, quota used up, ...
                return {"evidence": [], "error": str(exc)[:300]}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(run, claims))
