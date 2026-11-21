"""The instructions we give the AI model. Keeping them in one file makes them easy to tune."""

EXTRACT_PROMPT = """You are a meticulous fact-checking analyst. Today's date is {today}.

Below is the text of a PDF. Each page starts with a marker like <<<PAGE 3>>>.

Extract up to {max_claims} specific, checkable factual claims. Prioritise, in order:
1. Statistics and percentages (users, market share, growth rates, survey results)
2. Financial figures (revenue, valuation, funding, prices, market size)
3. Dates and years (founding dates, launch dates, historic events)
4. Technical figures and specifications (speeds, sizes, capacities, benchmarks)
5. Records, rankings and other concrete facts about named people, companies or places

Rules:
- Skip opinions, slogans, vague statements and anything that cannot be checked.
- Include a forecast only if it is attributed to a named source (then the claim is that the source made that forecast).
- Make every claim self-contained: replace pronouns like "it" or "the company" with the actual name,
  and keep numbers, units and any timeframe exactly as the document states them.
- "original_text" must be a short exact quote from the document containing the claim.
- "page" is the page number from the nearest preceding <<<PAGE n>>> marker.
- "search_queries": 1-2 short web-search queries that would find the authoritative, most recent
  figure for this fact. If the figure changes over time, include words like "latest" or the current year.
- Do not invent claims that are not in the text.

Return ONLY JSON in this shape:
{{"claims": [{{"claim": "...", "original_text": "...", "page": 1,
  "category": "statistic|financial|date|technical|other", "search_queries": ["..."]}}]}}

DOCUMENT:
{document}
"""

JUDGE_PROMPT = """You are a strict, evidence-based fact checker. Today's date is {today}.

For each claim below you are given numbered evidence from a live web search.
Judge each claim using ONLY that evidence. Do not rely on your own memory for facts.

Verdicts (use exactly one):
- "Verified": credible evidence clearly supports the claim (small rounding differences of about 5% are fine).
  If the claim explicitly dates a figure (e.g. "in 2019") and it was correct for that date, it is Verified;
  mention any newer figure in the explanation.
- "Inaccurate": the subject is real but a number, date or detail is wrong, OR the figure is outdated
  (it was true in the past but is presented as current and newer data exists).
- "False": there is no credible evidence for the claim, the event/entity/statistic appears fabricated,
  or the evidence flatly contradicts it.

Rules:
- Prefer authoritative sources (official sites, government/statistical bodies, company filings,
  reputable news) over SEO blogs. When sources disagree, prefer the most recent authoritative one.
- "correct_fact": for Inaccurate or False claims, state the correct real fact with its date/timeframe,
  taken from the evidence. If the evidence does not contain the correct value, write
  "No reliable figure found in search results." For Verified claims, return "".
- "explanation": 1-3 plain-English sentences explaining the verdict.
- "source_ids": the evidence numbers that support your verdict/correction (empty list if none).
- "confidence": "High", "Medium" or "Low".

Return ONLY JSON in this shape:
{{"results": [{{"id": 1, "verdict": "Verified|Inaccurate|False", "confidence": "High|Medium|Low",
  "explanation": "...", "correct_fact": "...", "source_ids": [1, 2]}}]}}

CLAIMS AND EVIDENCE:
{claims_block}
"""
