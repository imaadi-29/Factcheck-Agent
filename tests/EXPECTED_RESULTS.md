# Test plan: expected verdicts

These are the verdicts a correct fact-checker **should** give. The "Actual" column is
filled in only after running the deployed app with real API keys. Nothing here is a
recorded result until that column is filled.

"Inaccurate" vs "False" can legitimately differ for a claim about a real subject with a badly
wrong number (e.g. Einstein's Nobel year). Either one counts as a pass, as long as the claim
is flagged and the correct fact is given.

## 1_accurate_facts.pdf (all should be Verified)
| Claim | Expected | Actual |
|---|---|---|
| Eiffel Tower completed 1889 | Verified | |
| Apple founded 1976 by Jobs, Wozniak, Wayne | Verified | |
| Everest 8,848.86 m (2020 announcement) | Verified | |
| Python first released 1991 | Verified | |
| Earth–Moon average distance ~384,400 km | Verified | |

## 2_outdated_stats.pdf (all should be Inaccurate, with the current figure)
| Claim | Expected | Correct fact should mention | Actual |
|---|---|---|---|
| World population 7 billion | Inaccurate | 8+ billion (UN) | |
| ChatGPT 100M weekly users | Inaccurate | a much higher recent figure (e.g. OpenAI's 2025 announcements) | |
| Tallest building is Taipei 101 | Inaccurate | Burj Khalifa | |
| India 1.21B, second most populous | Inaccurate | ~1.4B+, most populous since 2023 | |
| Netflix 200M subscribers | Inaccurate | 300M+ (end of 2024) | |
| Marathon record 2:03:59 (Gebrselassie) | Inaccurate | the current record holder and time | |

## 3_fabricated_claims.pdf (flagged False or Inaccurate)
| Claim | Expected | Correct fact should mention | Actual |
|---|---|---|---|
| Zentrava Labs $9T valuation | False | no evidence the company or valuation exists | |
| 2023 Stanford study, 97% trust chatbots over doctors | False | no such study found | |
| Einstein Nobel 1935 for relativity | Inaccurate/False | 1921 prize (awarded 1922), photoelectric effect | |
| Human body 412 bones | Inaccurate/False | 206 bones | |
| Water boils at 150 °C at sea level | Inaccurate/False | 100 °C | |

## 4_trap_mixed.pdf (mixed, closest to the company's "Trap Document")
| Claim | Page | Expected | Actual (live app, 22 Nov 2026) |
|---|---|---|---|
| Apple founded 1976 | 1 | Verified | Verified ✅ |
| Amazon founded by Bezos in 1994 | 1 | Verified | Verified ✅ |
| ChatGPT 100M weekly users (today) | 1 | Inaccurate | Inaccurate ✅ (gave 900M, Feb 2026) |
| World population 7 billion | 1 | Inaccurate | Inaccurate ✅ (gave ~8.3B, 2026) |
| 2024 Harvard study, 92% buy only AI-recommended | 1 | False | False ✅ |
| Eiffel Tower completed 1925 | 2 | Inaccurate (1889) | Inaccurate ✅ (gave 31 Mar 1889) |
| Nexora Retail +870% revenue | 2 | False | False ✅ |
| Python first released 1991 | 2 | Verified | Verified ✅ |

Extra claim the app also found in 4_trap_mixed.pdf: 'Eiffel Tower is the most visited paid monument' was Verified, with a Guinness World Records source. Result: 8 of 8 planted claims classified correctly.
