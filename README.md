# 🔎 Fact-Check Agent

A web app that acts as a **truth layer for marketing content**. Upload a PDF and the app:

1. **Extracts** specific factual claims (statistics, dates, financial and technical figures), keeping the page number of each claim
2. **Verifies** each claim by searching the **live web** (Tavily Search API)
3. **Reports** each claim as **Verified**, **Inaccurate** (wrong or outdated) or **False** (no evidence / fabricated), with an explanation, the **correct real fact** and **source links**

**Live app:** https://factcheck-agent-web.streamlit.app/
**Demo video:** `<add link here>`

---

## How it works

```
PDF ─► PyMuPDF (text + page numbers)
    ─► Gemini: extract checkable claims + search queries        (1 AI call)
    ─► Tavily: live web search per claim, run in parallel       (1–2 searches per claim)
    ─► Gemini: judge claims in batches of 5 using ONLY the evidence
    ─► Streamlit report: verdicts, corrected facts, sources, CSV/JSON download
```

Design choices that make results trustworthy:

- **Evidence-only judging.** The model is told to judge only from the search results, not its own memory, and it is given today's date so it can tell when a figure is outdated.
- **No invented links.** The model cites evidence by number, and the app turns those numbers into the real URLs Tavily returned. A source link can't be made up.
- **Honest failures.** If a search fails, the claim is shown as *Not checked* rather than guessed.
- **Credit protection.** At most 25 claims per run (12 by default). The same PDF with the same settings is served from an in-memory cache, and the app automatically retries when it hits rate limits.

| Verdict | Meaning |
|---|---|
| 🟢 Verified | Credible evidence supports the claim (allowing small rounding differences) |
| 🟠 Inaccurate | The subject is real, but a figure or date is wrong, or an old figure is presented as current |
| 🔴 False | No credible evidence, a fabricated entity or statistic, or the evidence flatly contradicts the claim |

## Tech stack

| Part | Tool |
|---|---|
| Interface and hosting | [Streamlit](https://streamlit.io) on Streamlit Community Cloud |
| PDF text extraction | [PyMuPDF](https://pymupdf.readthedocs.io) |
| Live web search | [Tavily Search API](https://docs.tavily.com) |
| Claim extraction and judging | [Google Gemini API](https://ai.google.dev) (`google-genai` SDK; uses the newest available Flash model unless `GEMINI_MODEL` is set) |

## Project structure

```
app.py                      Streamlit interface
factcheck/
  pdf_utils.py              Read PDF text page by page
  prompts.py                Instructions for claim extraction and judging
  llm.py                    Gemini wrapper (JSON output, retries, model fallback)
  search.py                 Tavily live web search
  checker.py                Pipeline: extract -> search -> judge
tests/
  make_test_pdfs.py         Builds test PDFs (accurate / outdated / fabricated / mixed)
  pdfs/                     The generated test PDFs
  EXPECTED_RESULTS.md       Expected verdicts and actual results from the live app
  test_plumbing.py          Offline tests of the pipeline logic, using stand-ins for the APIs
.streamlit/
  config.toml               Theme and upload limit
  secrets.toml.example      Template for API keys (the real secrets.toml is git-ignored)
```

## Run locally

```bash
git clone <your-repo-url>
cd factcheck-agent
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then paste your keys into it
streamlit run app.py
```

Free API keys:
- Gemini: [Google AI Studio](https://aistudio.google.com/apikey)
- Tavily: [app.tavily.com](https://app.tavily.com) (1,000 free credits a month)

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub. Do **not** commit `secrets.toml`.
2. Go to [share.streamlit.io](https://share.streamlit.io), click **Create app**, choose the repo, branch `main` and main file `app.py`.
3. Under **Advanced settings → Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "..."
   TAVILY_API_KEY = "..."
   ```
4. Click **Deploy**.

## Limitations

- Scanned (image-only) PDFs are not supported, because there's no text to read. The first 40 pages are processed.
- Verdicts are only as good as the search results. For important decisions, open the cited sources.
- Free-tier API quotas can run out. Visitors can paste their own keys in the sidebar; they are kept only for that browser session.
