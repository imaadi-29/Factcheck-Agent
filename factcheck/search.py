"""Step 3 - SEARCH: look each claim up on the live web with the Tavily API.

Tavily is a search engine built for AI apps: it returns the page title, URL and
the most relevant text from each page, which we pass to the AI judge as evidence.
"""

from concurrent.futures import ThreadPoolExecutor

from tavily import TavilyClient

RESULTS_PER_QUERY = 5
MAX_EVIDENCE_PER_CLAIM = 6
MAX_CHARS_PER_RESULT = 1200

# Social media, Q&A sites, document dumps and search-result pages are not reliable evidence.
EXCLUDED_DOMAINS = [
    "instagram.com", "facebook.com", "x.com", "twitter.com", "tiktok.com", "pinterest.com",
    "linkedin.com", "threads.net", "brainly.com", "quora.com", "chegg.com", "scribd.com",
    "coursehero.com", "studocu.com", "search.yahoo.com", "bing.com", "google.com", "youtube.com",
]


class SearchClient:
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)

    def _search_one(self, query: str) -> list[dict]:
        response = self.client.search(
            query=query,
            search_depth="advanced",   # better text snippets (2 credits per search)
            max_results=RESULTS_PER_QUERY,
            exclude_domains=EXCLUDED_DOMAINS,
        )
        return response.get("results", [])

    @staticmethod
    def _merge(result_lists: list[list[dict]]) -> list[dict]:
        """Combine the results of a claim's queries, dropping duplicates and excluded sites."""
        evidence, seen_urls = [], set()
        for results in result_lists:
            for item in results:
                url = item.get("url")
                if not url or url in seen_urls or _is_excluded(url):
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

    def evidence_for_all(self, claims: list[dict], workers: int = 8) -> list[dict]:
        """Run every query of every claim at the same time. Errors are recorded per claim."""
        jobs = [(i, q) for i, claim in enumerate(claims) for q in claim["search_queries"][:2]]

        def run(job):
            try:
                return job[0], self._search_one(job[1]), ""
            except Exception as exc:  # network problem, quota used up, ...
                return job[0], None, str(exc)[:300]

        per_claim = [{"results": [], "errors": []} for _ in claims]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, results, error in pool.map(run, jobs):
                if error:
                    per_claim[i]["errors"].append(error)
                else:
                    per_claim[i]["results"].append(results)

        out = []
        for found in per_claim:
            if found["results"]:          # at least one query worked
                out.append({"evidence": self._merge(found["results"]), "error": ""})
            else:
                out.append({"evidence": [], "error": (found["errors"] or ["No search was run."])[0]})
        return out


def _is_excluded(url: str) -> bool:
    """Second safety net in case the search API still returns an excluded site."""
    host = url.split("//")[-1].split("/")[0].lower()
    return any(host == d or host.endswith("." + d) for d in EXCLUDED_DOMAINS)
