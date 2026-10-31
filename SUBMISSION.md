# Submission-ready project details (accurate for this Phase 1 prototype)

## Project name
**VerityLens AI — Evidence-to-Action Intelligence Platform**

## Project description

Finding information is easier than deciding whether that information is complete, current, and consistent. Scholarship applicants, researchers, and other decision-makers can miss important policies because relevant details are spread across different documents. Conventional search and summarization experiences often tell people what a document contains, but do not systematically reveal what the reviewed material fails to establish.

**VerityLens AI** is a web-based evidence review platform built for the **Digital Dark Spot** challenge. A user enters a research question, pastes selected source documents or provides publicly accessible HTML/text URLs, and runs a structured source comparison. The prototype produces a research coverage matrix indicating where relevant passages were located, where information was not found in the reviewed material, where only older-cycle passages were located, and where comparable fields suggest a possible conflict.

The claim discrepancy explorer presents actual excerpts, associated source identifiers, and available source links. The baseline detects differences between explicit deadline dates, required-document lists, and award amounts and avoids treating different application cycles as automatically contradictory. A separate freshness panel highlights visibly older material, prior application cycles, and unavailable publication metadata without claiming that age automatically makes information false. A prioritized verification checklist turns these issues into practical questions to resolve against current authoritative sources. The result can be exported as a Markdown research report or structured JSON evidence file.

The main differentiator is its **evidence-to-action workflow**: a user can move from source excerpts to a structured candidate-claims dashboard, research-aspect coverage, possible discrepancies, visible uncertainty, and the next verification steps. A citation validator checks that cited passages occur verbatim in their declared collected sources, reducing the risk of unsupported citations in both the deterministic and optional AI-assisted analysis. Users can also opt into a limited English Wikipedia query search; these collaborative articles are labeled as non-authoritative and should be checked against their primary references. The included scholarship demonstration is prominently labeled as fictional synthetic test material.

**Technology stack:** Python 3.10+, Streamlit for the browser interface, Requests and BeautifulSoup for public HTML/text extraction, the Wikimedia API for opt-in English Wikipedia query search, typed Python dataclasses for structured evidence, and Pytest for analysis/security unit tests. The deterministic baseline is transparent and heuristic. An optional OpenAI-compatible LLM analysis can be configured through environment variables; the user must explicitly consent before source text is sent. Its output is citation-validated but not fact-verified, and a deterministic fallback is shown when the provider is unavailable or its citations are invalid. No provider has been configured or live-tested as part of this project. Future scope includes general web search, richer PDF/document ingestion, source authority assessment, and stronger public-deployment URL-fetch security.

The design prioritizes a testable, auditable core, honest limitations, and explainable findings over an unverified chatbot or unsupported confidence scores.

## Required repository link
**Add your genuine, accessible GitHub repository URL here after uploading the code.** Do not invent a URL.

## Optional links
Only include a live deployment or demo video once the actual destination has been verified. Both are optional in the official PDF.

## 3-minute judge demo

**0:00–0:20** Describe scholarship information scattered across conflicting, incomplete and dated sources. **0:20–0:45** Enter the question and load the **fictional labeled dataset**. **0:45–1:20** Show the dedicated key-claims view and coverage matrix: current-cycle renewal not established. **1:20–2:05** Show the two 2026-27 deadline and required-document discrepancies, with exact source passages and source IDs. **2:05–2:30** Point out the archived 2024-25 notice and its separate freshness warning. **2:30–3:00** Show the verification checklist and downloadable report; explain that optional AI requires provider configuration and explicit consent, while deterministic analysis works without it.

## Likely judge questions — accurate answers

**How is it different from search?** It organizes inspected information into research requirements, possible gaps, comparable claims, and actionable follow-ups. It does not replace search.

**How are gaps identified?** The initial scholarship template screens the selected source text for relevant passages; absence is always scoped to the reviewed material. This method is heuristic and can miss paraphrases.

**How do you prevent citation hallucinations?** The validator rejects references to nonexistent source IDs and excerpts not appearing in a collected source. It does not authenticate the source itself.

**Can the system distinguish real contradictions?** It flags explicit differing comparable values for review, excludes known different-cycle comparisons, and labels the finding as *possible*, not final proof.

**How are stale sources handled?** It warns about visible older dates, nonmatching application cycles, and missing metadata; it never declares every old document false.

**What if a source is inaccessible?** The application shows a source-specific warning, continues analyzing successfully collected sources, and allows pasted permitted source text as a fallback.

**What is AI-assisted here?** The core works deterministically without a key. With an explicitly configured provider and user consent, the optional LLM extracts source-grounded claims, possible conflicts, gaps, and questions. It is not independently verified; every citation must match an exact collected passage, and users must review the output.

**What are the limitations?** The current scope is HTML/text and heuristic screening, with only limited English Wikipedia search, no validated source authority, no live-verified LLM provider, and no hardened public fetch deployment. Real-world decisions still need authoritative verification.
