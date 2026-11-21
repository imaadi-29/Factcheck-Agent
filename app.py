"""Fact-Check Agent - a Streamlit web app.

Upload a PDF -> the app extracts factual claims, searches the live web for each one,
and reports whether each claim is Verified, Inaccurate or False, with sources.

Run locally with:  streamlit run app.py
"""

import hashlib
import html
import json
import os

import pandas as pd
import streamlit as st

from factcheck.checker import run_pipeline
from factcheck.llm import GeminiLLM, LLMError
from factcheck.pdf_utils import PDFError, extract_pages
from factcheck.search import SearchClient

st.set_page_config(page_title="Fact-Check Agent", page_icon="🔎", layout="wide")

VERDICT_STYLE = {
    "Verified":    {"color": "green",  "icon": ":material/check_circle:", "help": "Matches current, credible data."},
    "Inaccurate":  {"color": "orange", "icon": ":material/warning:",      "help": "Real topic, but the figure is wrong or outdated."},
    "False":       {"color": "red",    "icon": ":material/cancel:",       "help": "No credible evidence, or fabricated."},
    "Not checked": {"color": "gray",   "icon": ":material/help:",         "help": "Could not be checked (search or AI error)."},
}

st.markdown("""
<style>
  .block-container {max-width: 1100px; padding-top: 2rem;}
  .claim-quote {border-left: 3px solid #d0d5dd; padding: .25rem .75rem; color: #475467;
                font-style: italic; margin: .25rem 0 .5rem 0;}
  .correct-fact {background: #ecfdf3; border: 1px solid #abefc6; border-radius: 8px;
                 padding: .6rem .8rem; margin: .4rem 0;}
  [data-testid="stMetricValue"] {font-size: 1.8rem;}
</style>
""", unsafe_allow_html=True)


# ---------- API keys: read from Streamlit secrets or environment, never from code ----------
def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:          # no secrets file present
        value = ""
    return str(value or os.environ.get(name, "")).strip()


with st.sidebar:
    st.header("Settings")
    max_claims = st.slider("Maximum claims to check", 5, 25, 12,
                           help="More claims = longer run and more API credits used.")
    with st.expander("Use your own API keys (optional)"):
        st.caption("Only needed if the app's own credits run out. "
                   "Keys stay in this browser session and are never stored.")
        user_gemini = st.text_input("Gemini API key", type="password")
        user_tavily = st.text_input("Tavily API key", type="password")
    st.divider()
    st.subheader("How it works")
    st.markdown(
        "1. **Read** the PDF page by page\n"
        "2. **Extract** stats, dates, financial and technical claims with Gemini\n"
        "3. **Search** the live web for each claim with Tavily\n"
        "4. **Judge** each claim against the search results only\n"
        "5. **Report** verdicts, corrected facts and source links"
    )
    st.caption("AI can make mistakes. Always open the sources for important decisions.")

gemini_key = user_gemini or get_secret("GEMINI_API_KEY")
tavily_key = user_tavily or get_secret("TAVILY_API_KEY")
gemini_model = get_secret("GEMINI_MODEL")


@st.cache_resource
def report_cache() -> dict:
    """Shared in-memory store: re-checking the same PDF with the same settings costs no API credits."""
    return {}


def check_document(pdf_bytes: bytes, max_claims: int, say) -> dict:
    cache_key = (hashlib.sha256(pdf_bytes).hexdigest(), max_claims)
    cache = report_cache()
    if cache_key in cache:
        say("This document was checked recently, so the saved report is shown.")
        return cache[cache_key]
    pages, total_pages = extract_pages(pdf_bytes)
    say(f"Read {len(pages)} page(s) with text.")
    llm = GeminiLLM(gemini_key, gemini_model)
    searcher = SearchClient(tavily_key)
    results = run_pipeline(llm, searcher, pages, max_claims, status=say)
    report = {"results": results, "pages_read": len(pages), "total_pages": total_pages,
              "model": llm.active_model}
    if results and all(r["verdict"] != "Not checked" for r in results):
        if len(cache) > 50:
            cache.clear()
        cache[cache_key] = report
    return report


# ---------- Header and upload ----------
st.title("🔎 Fact-Check Agent")
st.markdown("A truth layer for marketing content: upload a PDF and every stat, date and figure "
            "is checked against **live web data**.")

c1, c2, c3 = st.columns(3)
c1.markdown("🟢 **Verified**: matches current data")
c2.markdown("🟠 **Inaccurate**: wrong or outdated figure")
c3.markdown("🔴 **False**: no evidence / fabricated")

uploaded = st.file_uploader("Upload a PDF", type=["pdf"], help="Text-based PDFs up to 20 MB.")

missing = [n for n, k in (("GEMINI_API_KEY", gemini_key), ("TAVILY_API_KEY", tavily_key)) if not k]
if missing:
    st.warning(f"API keys missing: {', '.join(missing)}. Add them to the app's secrets, "
               "or paste your own keys in the sidebar.")

run = st.button("Run fact-check", type="primary", disabled=not uploaded or bool(missing),
                use_container_width=True)

if run and uploaded:
    pdf_bytes = uploaded.getvalue()
    with st.status("Fact-checking your document...", expanded=True) as status_box:
        try:
            report = check_document(pdf_bytes, max_claims, status_box.write)
            st.session_state["report"] = report
            st.session_state["report_name"] = uploaded.name
            status_box.update(label="Fact-check complete", state="complete", expanded=False)
        except PDFError as exc:
            status_box.update(label="Could not read the PDF", state="error")
            st.error(str(exc))
        except LLMError as exc:
            status_box.update(label="AI model error", state="error")
            st.error(f"{exc} If the free quota is used up, try again later or add your own key in the sidebar.")
        except Exception as exc:
            status_box.update(label="Something went wrong", state="error")
            message = str(exc)
            if "tavily" in message.lower() or "unauthorized" in message.lower():
                message = "The Tavily search API rejected the request. Check TAVILY_API_KEY or your credits."
            st.error(f"Error: {message[:400]}")


# ---------- Results ----------
report = st.session_state.get("report")
if report:
    results = report["results"]
    st.divider()
    st.subheader(f"Report: {st.session_state.get('report_name', 'document')}")
    st.caption(f"Read {report['pages_read']} of {report['total_pages']} pages · "
               f"model: {report['model']} · search: Tavily (live web)")

    if not results:
        st.info("No checkable factual claims (stats, dates, figures) were found in this document.")
    else:
        counts = {v: sum(r["verdict"] == v for r in results) for v in VERDICT_STYLE}
        if counts["Not checked"] == len(results):
            st.error("None of the claims could be checked. The search API key may be invalid "
                     "or out of credits. See the messages below.")
        m = st.columns(4)
        m[0].metric("Claims checked", len(results))
        m[1].metric("🟢 Verified", counts["Verified"])
        m[2].metric("🟠 Inaccurate", counts["Inaccurate"])
        m[3].metric("🔴 False", counts["False"])

        options = ["All"] + [v for v in VERDICT_STYLE if counts[v]]
        choice = st.segmented_control("Filter", options, default="All", label_visibility="collapsed")
        shown = [r for r in results if choice in (None, "All") or r["verdict"] == choice]

        for r in shown:
            style = VERDICT_STYLE.get(r["verdict"], VERDICT_STYLE["Not checked"])
            with st.container(border=True):
                top = st.columns([5, 2])
                top[0].markdown(f"**{r['id']}. {r['claim']}**")
                with top[1]:
                    st.badge(r["verdict"], icon=style["icon"], color=style["color"], help=style["help"])
                meta = f"📄 Page {r['page']}" if r.get("page") else "📄 Page unknown"
                meta += f" · {r['category'].title()}"
                if r.get("confidence"):
                    meta += f" · Confidence: {r['confidence']}"
                st.caption(meta)
                if r.get("original_text") and r["original_text"] != r["claim"]:
                    st.markdown(f'<div class="claim-quote">“{html.escape(r["original_text"])}”</div>',
                                unsafe_allow_html=True)
                st.markdown(r.get("explanation", ""))
                if r.get("correct_fact"):
                    fact = html.escape(r["correct_fact"])
                    st.markdown(f'<div class="correct-fact">✅ <b>Correct fact:</b> {fact}</div>',
                                unsafe_allow_html=True)
                if r.get("sources"):
                    links = " · ".join(f"[{s['title'][:70]}]({s['url']})" for s in r["sources"])
                    st.markdown(f"**Sources:** {links}")
                elif r["verdict"] != "Not checked":
                    st.caption("No supporting sources were found in the search results.")

        table = pd.DataFrame([{
            "id": r["id"], "page": r.get("page"), "claim": r["claim"], "verdict": r["verdict"],
            "confidence": r.get("confidence", ""), "explanation": r.get("explanation", ""),
            "correct_fact": r.get("correct_fact", ""),
            "sources": " | ".join(s["url"] for s in r.get("sources", [])),
        } for r in results])
        d1, d2 = st.columns(2)
        d1.download_button("Download report (CSV)", table.to_csv(index=False).encode("utf-8"),
                           "fact_check_report.csv", "text/csv", use_container_width=True)
        slim = [{k: v for k, v in r.items() if k != "evidence"} for r in results]
        d2.download_button("Download report (JSON)", json.dumps(slim, indent=2).encode("utf-8"),
                           "fact_check_report.json", "application/json", use_container_width=True)
elif not uploaded:
    st.info("Upload a PDF to begin. Tip: marketing one-pagers, reports and pitch decks work well.")
