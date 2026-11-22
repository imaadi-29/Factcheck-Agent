# Test results: expected vs. actual (live app)

All "Actual" results come from the deployed app (https://factcheck-agent-web.streamlit.app/),
which uses Gemini and live Tavily web search. Nothing here is mocked. The test PDFs are in `tests/pdfs/`.

**Pass rule:** a true claim must be Verified. A wrong, outdated or fabricated claim must be flagged
(Inaccurate or False), and the correct real fact must be given where one exists. The label we
expected is shown; a flagged claim with the other label is a "label mismatch", not a miss.

## Summary (live runs, 22 Nov 2026)

| Test PDF | Claims found | Handled correctly | Notes |
|---|---|---|---|
| 1_accurate_facts.pdf | 5 | 5 of 5 Verified | |
| 2_outdated_stats.pdf | 6 | 6 of 6 flagged, with current figures | Taipei 101 labelled False instead of Inaccurate |
| 3_fabricated_claims.pdf | 6 | 6 of 6 flagged | The Zentrava sentence was split into two claims |
| 4_trap_mixed.pdf (run 1) | 9 | 8 of 8 planted claims, exact labels | |
| 4_trap_mixed.pdf (run 2, after source filter) | 9 | 7 of 8 | Python claim "Not checked" (model skipped it); Eiffel 1925 labelled False |

**Fixes made after these runs:**
- A claim the model skips in a batch is now re-checked on its own, with a test.
- The judging rules now say exactly when to use Inaccurate (a real subject with a wrong or outdated
  detail) and when to use False (fabricated, never true).
- YouTube was added to the excluded low-quality sources. Social media, Q&A sites, document dumps and
  search-result pages were already excluded.

## 1_accurate_facts.pdf
| Claim | Expected | Actual |
|---|---|---|
| Eiffel Tower completed 1889 for the Exposition Universelle | Verified | Verified ✅ |
| Apple founded 1976 by Jobs, Wozniak, Wayne | Verified | Verified ✅ |
| Everest 8,848.86 m (2020 China–Nepal announcement) | Verified | Verified ✅ |
| Python first released by Guido van Rossum in 1991 | Verified | Verified ✅ |
| Earth–Moon average distance ~384,400 km | Verified | Verified ✅ |

## 2_outdated_stats.pdf
| Claim | Expected | Actual | Correct fact given by the app |
|---|---|---|---|
| World population 7 billion | Inaccurate | Inaccurate ✅ | ~8.26–8.3 billion (2026) |
| ChatGPT 100M weekly users | Inaccurate | Inaccurate ✅ | 900M+ weekly users (TechCrunch, Feb 2026) |
| Tallest building is Taipei 101 | Inaccurate | False ⚠️ label mismatch | Burj Khalifa, 828 m |
| India 1.21B, second most populous | Inaccurate | Inaccurate ✅ | Most populous, 1.47B+ (2026) |
| Netflix 200M subscribers | Inaccurate | Inaccurate ✅ | 325M+ paid subscribers (end of 2025) |
| Marathon record 2:03:59 (Gebrselassie) | Inaccurate | Inaccurate ✅ | 1:59:30, Sabastian Sawe, London, 26 Apr 2026 |

The marathon and Netflix corrections were checked by hand: World Athletics confirms Sawe's 1:59:30
world record (26 Apr 2026), and Netflix's Q4 2025 shareholder letter reported 325M+ paid memberships.

## 3_fabricated_claims.pdf
| Claim | Expected | Actual | Correct fact given by the app |
|---|---|---|---|
| 2023 Stanford study: 97% trust chatbots over doctors | False | False ✅ | No such study; surveys show under 40% trust AI medical advice |
| Zentrava Labs reached a $9T valuation in 2024 | False | False ✅ | No company reached $9T; the largest were ~$3T |
| Zentrava Labs founded in Oslo in 2017 | False | False ✅ | No record found |
| Einstein Nobel 1935 for relativity | Inaccurate/False | Inaccurate ✅ | 1921 prize (awarded 1922), photoelectric effect |
| Human body has 412 bones | Inaccurate/False | Inaccurate ✅ | 206 bones |
| Water boils at 150 °C at sea level | Inaccurate/False | Inaccurate ✅ | 100 °C |

## 4_trap_mixed.pdf (closest to the company's "Trap Document")
| Claim | Page | Expected | Run 1 | Run 2 |
|---|---|---|---|---|
| Apple founded 1976 | 1 | Verified | Verified ✅ | Verified ✅ |
| Amazon founded by Bezos in 1994 | 1 | Verified | Verified ✅ | Verified ✅ |
| ChatGPT 100M weekly users (today) | 1 | Inaccurate | Inaccurate ✅ | Inaccurate ✅ |
| World population 7 billion | 1 | Inaccurate | Inaccurate ✅ | Inaccurate ✅ |
| 2024 Harvard study, 92% buy only AI-recommended | 1 | False | False ✅ | False ✅ |
| Eiffel Tower completed 1925 | 2 | Inaccurate | Inaccurate ✅ | False ⚠️ label mismatch |
| Nexora Retail +870% revenue | 2 | False | False ✅ | False ✅ |
| Python first released 1991 | 2 | Verified | Verified ✅ | Not checked ❌ (fixed) |

Both runs also found an extra true claim, "Eiffel Tower is the most visited paid monument", and
Verified it with a Guinness World Records source.
