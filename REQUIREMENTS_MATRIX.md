# Official requirement traceability — Digital Dark Spot

The official two-page **Shinchan Online Hackathon 2026** statement is the source of truth; this matrix separates its expected outcomes from our product inventions. Test IDs identify implemented automated tests where available; otherwise they state the required manual verification.

| Official expectation / caution | Implemented or planned behavior | Module | Test / verification | Status |
|---|---|---|---|---|
| Working web application; topic/question/research goal | Streamlit research form, results tabs, synthetic demo | `app.py` | Public browser test: synthetic demo analyzed 3 sources; findings dashboard rendered | Verified locally and on public Streamlit Community Cloud |
| Add/collect source material including user URLs or permitted search results | User-provided text, local opt-in public HTML/text URLs, and opt-in English Wikipedia query search; URL fetch is off on public deployment | `app.py`, `collector.py` | Mocked URL/API tests; live Wikimedia API returned three Mars articles | Limited Wikipedia search verified; public HTML URL retrieval/general web search absent |
| Source provenance and retrieval status | Titles, retrieved/canonical URLs, publication metadata, collection timestamps, and per-source failures | `collector.py`, `models.py`, `app.py`, `report.py` | Mocked metadata, timeout, and paywall tests | Implemented for readable public HTML/text; canonical/date fields may be absent |
| Structured summary of reviewed information | Candidate claims and categorized evidence passages in dedicated dashboard | `engine.py`, `app.py` | `test_claim_extraction_returns_atomic_source_linked_passage` | Implemented as heuristic evidence screening, not verified semantic synthesis |
| Clear potential gaps / unanswered questions | Coverage matrix with missing, old-only, and conflict statuses | `engine.py`, `app.py` | `test_one_source_and_missing_aspect_not_proof_of_universal_absence` | Implemented, heuristic |
| Possible source contradictions, with references | Comparable deadline/document/amount discrepancies | `engine.py`, `app.py` | `test_different_application_cycles_are_not_automatically_contradictions` | Implemented, limited field types |
| Warnings when information may be outdated/undated | Cycle, publication-date, or last-modified flags distinguished | `engine.py`, `app.py` | Missing-date and last-modified tests | Implemented; source date metadata is not authenticated |
| Prioritized next-step verification checklist | Impact-based checkboxes and actionable prompts | `engine.py`, `app.py` | `test_full_demo_flow_has_conflicts_gap_freshness_and_actions` | Implemented |
| Dashboard separates sourced evidence and AI suggestion / uncertainty | Exact direct quotations; optional consent-gated AI insights labeled by evidence type; deterministic fallback | `app.py`, `analysis.py`, `models.py` | AI citation-validation and fallback tests; browser tab smoke test | Implemented; live provider integration not configured or verified |
| Original source references accessible | Article URL when collected; source ID / full text for pasted sources | `collector.py`, `app.py` | Verbatim citation tests; live Wikipedia article link obtained | Implemented; a source URL does not itself authenticate its content |
| Demonstrate at least one gap and possible conflict | Clearly labeled fictional scholarship fixture | `demo.py`, `engine.py` | `test_full_demo_flow_has_conflicts_gap_freshness_and_actions` | Implemented, SYNTHETIC ONLY |
| AI-generated findings described as possible, not fact | AI suggestions are separate from source evidence, citations must match exact source text | `analysis.py`, `app.py`, `engine.py` | AI citation-validation and fallback tests | Implemented; AI correctness still requires human review |
| Generic chatbot alone insufficient | End-to-end gap and verification workflow | `app.py`, `engine.py` | Synthetic end-to-end test and browser demo | Implemented |
| Working polished core > incomplete feature count | No authentication or multi-service infrastructure | Entire project | Public deployment reviewed; arbitrary URL fetch disabled there | Design choice |

**Additional innovations proposed by participant (not organizer mandates):** research coverage matrix; cycle-aware conflict matching; source provenance/quote validation; discrepancy explorer; decision-oriented checklist; exportable evidence ledger; optional consent-gated source-grounded analysis. The specific status taxonomy, heuristics, Python stack, dark theme, and fictional sample scholarship are participant design choices, not official requirements.

## Original official rubric (total 10.0 marks)

| Criterion | Weight | Max marks | Evidence judges should see | Risk / validation |
|---|---:|---:|---|---|
| Problem understanding and relevance | 15% | 1.5 | Student decision demo identifies missing renewal information | Explain restricted reviewed-sources scope |
| Innovation and originality | 20% | 2.0 | Coverage + conflicts + verification, not just summary | Rules-only analysis may appear insufficiently semantic |
| Working prototype and functionality | 25% | 2.5 | Input → evidence → gap/conflict → checklist → export | Verify Streamlit tabs and URL fetching on target PC |
| Technical implementation | 15% | 1.5 | Separate collector, engine, schemas, tests | Harden URL fetching before public deployment |
| Evidence, accuracy and transparency | 15% | 1.5 | Inspect source IDs and exact quotes; uncertainty shown | Pasted docs and dates are not authenticated |
| Presentation and demo | 10% | 1.0 | ~3-minute faithful walkthrough, clearly marked synthetic data | No live provider configured; AI layer must be described as optional |

No marks are guaranteed by merely having a feature. Judges will score observable quality.

## Official submission logistics

The PDF states: individual participation; submission via **Unista** using the registered account under **Rounds**; opens **31 October 2026, 10:00 AM**; closes **1 November 2026, 5:00 PM**. Mandatory fields: **project name**, **detailed project description** (problem, solution, workflow, major features, innovation, stack, future scope), and **judge-accessible GitHub repository**. **Live demo, demo video, slides** are optional. Confirm portal time zone; the PDF does not specify one.

## Most important open validation items

1. Complete manual checks of every results tab and download; public-browser smoke test confirmed the dashboard and traceable demo findings.
2. Test genuinely accessible permissible public sources; automated retrieval tests use mocked responses.
3. Configure and test an AI provider only with a real key and explicit consent; automated tests mock provider calls.
4. Explicitly label fiction; do not present synthetic conflict as an externally verified fact.
5. Submit the public GitHub repository and live demo URLs through Unista before closing time.
