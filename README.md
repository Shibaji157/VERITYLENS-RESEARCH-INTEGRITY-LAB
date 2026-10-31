# VerityLens AI — Evidence-to-Action Research Review

**Shinchan Online Hackathon 2026 · Digital Dark Spot**

VerityLens AI is an evidence-first research review prototype. Rather than merely summarizing information, it maps **what a selected set of sources mentions**, highlights **potential information gaps**, shows **possible conflicts with exact excerpts**, checks **visible date and cycle signals**, and generates a **prioritized verification checklist**.

> **Integrity notice:** The deterministic baseline is transparent and heuristic. Optional LLM analysis is available only when explicitly configured and consented to; it is not fact verification. No external provider has been configured or live-tested here. Source text, source titles, published dates, and synthetic examples may be unverified. Never use this as the sole basis for a high-stakes decision.

## 1. Features in this release

- Research question input, optional custom research dimensions.
- Up to four pasted source documents and up to five publicly accessible HTML or text URLs.
- Optional English Wikipedia query search, with up to three short, explicitly labeled, editable-encyclopedia extracts.
- Basic webpage text, page title, same-host canonical URL, available publication metadata, and UTC collection timestamp extraction.
- Source-by-source retrieval failures, timeout/paywall/unsupported-format messages, and honest missing-date handling.
- Scholarship-specific coverage matrix and generic fallback categories.
- A dedicated candidate-claims view with verbatim source citations.
- Evidence located / not found in reviewed sources / previous-cycle evidence only / possible conflict indicators.
- Possible differing deadlines, document lists, and amounts, with actual supporting text from each source.
- Application-cycle distinction to reduce false conflicts between previous/current cycles.
- Warnings for older publications, missing date metadata, and nonmatching cycles.
- Source provenance with exact quotes, source ID, URL (when collected), and source text.
- Wikipedia revision timestamps are labeled as last-modified information, never as publication dates; the search source itself warns users to verify against primary references.
- Checklist prioritized by potential decision impact.
- Markdown report and JSON evidence download.
- Clearly labeled **fictional** scholarship fixture for an honest, reproducible demo.
- Optional source-grounded analysis through an OpenAI-compatible Chat Completions endpoint. It is disabled unless configured and explicitly consented to; source citations are checked against collected text.
- Deterministic analysis remains available when AI is unconfigured, declined, unavailable, or returns invalid citations; its fallback status is visible.
- Basic URL safety rules, robots.txt when accessible, timeouts, request/content-size caps, and mocked network tests.

## 2. Quick start — Windows PowerShell in VS Code

Install **Python 3.10+** and use the declared dependencies (Streamlit 1.55+). In VS Code select **File → Open Folder…** and choose `D:\All Project\Hakathon Project\Shinchan 1\veritylens_phase1`.

```powershell
cd "D:\All Project\Hakathon Project\Shinchan 1\veritylens_phase1"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

In VS Code, press **Ctrl+Shift+P**, run **Python: Select Interpreter**, and choose `.venv\Scripts\python.exe` before editing or running tests.

If activation is blocked, run this in the current PowerShell process and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternative commands without activating the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the localhost address displayed by Streamlit (normally http://localhost:8501) **in your local browser**. Direct URL retrieval is disabled by default. To enable it for trusted local use only, set `$env:VERITYLENS_ENABLE_URL_FETCH = "1"` before starting Streamlit. Do not enable arbitrary URL fetching on a public deployment.

> **If the browser shows a file listing (for example `127.0.0.1:5500`)**: that is VS Code Live Server serving the project folder as static files; it is not the VerityLens app. Stop/ignore Live Server, run `python -m streamlit run app.py` from the project folder, and open the Streamlit **Local URL** printed in the terminal (normally `http://localhost:8501`). Do not use **Go Live** or open `app.py` directly in the browser.

### Optional AI-assisted analysis

The application works without an API key. To enable the optional AI layer, configure an OpenAI-compatible Chat Completions provider in the same PowerShell window before starting Streamlit:

```powershell
$env:VERITYLENS_LLM_API_KEY = "your-provider-key"
$env:VERITYLENS_LLM_MODEL = "gpt-4o-mini"
$env:VERITYLENS_LLM_BASE_URL = "https://api.openai.com/v1"
python -m streamlit run app.py
```

The model and HTTPS base URL can be changed for a compatible provider. Never put a real key in source control or screenshots. With a key configured, the form still requires explicit consent before sending the research question and source text to that provider. Do not send private or confidential material. API errors and invalid citations are shown as a deterministic fallback; no provider credentials or response body are written to application logs. `.env.example` is a reference only and is not automatically loaded by this app.

## Live demo

**Live app:** [Open VerityLens AI on Streamlit Community Cloud](https://veritylens-research-integrity-lab-3kawsjsxqxj29xsrn8tpnj.streamlit.app/)

The public app was deployed from the `main` branch and verified in a browser: the synthetic scholarship demo loaded, analyzed three labeled sources, and rendered its findings dashboard. Arbitrary URL fetching is disabled in this public deployment; pasted text and opt-in English Wikipedia query search remain available.

### Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with an account that can access the repository.
3. Create an app from `Shibaji157/VERITYLENS-RESEARCH-INTEGRITY-LAB`, branch `main`, entry point `app.py`.
4. Leave `VERITYLENS_ENABLE_URL_FETCH` unset. Direct arbitrary URL fetching is disabled by default for public deployments; pasted text and the opt-in Wikipedia search remain available.
5. Add AI provider secrets only in the Community Cloud app settings if you choose to enable that feature; never commit them.
6. Wait for the app health check, open its generated `*.streamlit.app` URL, and verify the synthetic demo and query workflow.

DNS-rebinding/SSRF risks mean direct URL fetching must remain disabled on public hosting unless a hardened, network-isolated fetch service is added.

## 3. Demonstration (3 minutes)

1. Click **Load fictional scholarship demo** in the sidebar.
2. Read the conspicuous synthetic-material warning. Click **Analyze evidence**.
3. Show the **Research overview** and **Coverage matrix**. Point out that the 2024-25 renewal clause is **not valid evidence for the 2026-27 renewal policy**.
4. Open **Conflict explorer**. Compare the differing **2026-27 deadlines** and **required-document lists**, with source IDs and exact text.
5. Open **Freshness** and explain why the old 2024-25 document must not automatically contradict the 2026-27 documents.
6. Open **Source evidence** to show each passage in its original collected text.
7. Open **Verification plan** and **Export**.

All three sample documents are **synthetic** and must not be represented as a real scholarship or external official notice.

For a real demonstration, replace sample text with passages from genuinely accessible, permitted public source pages; preserve the original URL or explain the origin of pasted text. Do not invent a real-source conflict.

### Optional reproducible real-source scenario

1. Enter a research question such as `What should I know about Mars?`.
2. Select **Search English Wikipedia** to retrieve up to three short public article extracts through the Wikimedia API. The query goes to Wikimedia; the retrieved articles are collaboratively edited, secondary sources, not authoritative evidence.
3. Run the analysis and inspect the article links, exact extracts, last-modified metadata, and the warning to verify important claims against primary references.

The Wikimedia API search endpoint was reachable during development. Network/API availability is not guaranteed; automated tests mock requests.

## 4. Project structure

```text
veritylens_phase1/
├── app.py                  Streamlit interface
├── veritylens/
│   ├── __init__.py
│   ├── models.py           Data contracts for source/claim/report
│   ├── collector.py        Safe-ish public HTML/text access and extraction
│   ├── analysis.py         Optional consent-gated AI and citation validation
│   ├── engine.py           Coverage, conflicts, freshness, verification plan
│   ├── demo.py             Fictional controlled scholarship fixture
│   └── report.py           Markdown and JSON exports
├── demo_output/           Pre-generated SYNTHETIC demo report / JSON
├── tests/
│   ├── test_engine.py
│   ├── test_collector.py
│   └── test_analysis.py
├── requirements.txt
├── pytest.ini
├── .gitignore
├── .env.example
├── .streamlit/config.toml  Dark-mode color theme
├── REQUIREMENTS_MATRIX.md
├── SUBMISSION.md
└── README.md
```

## 5. Architecture

```text
Research question + opt-in Wikimedia search / public URLs / pasted documents
                 |
          Collector + parser
                 |
  Immutable source IDs + exact readable text
                 |
       Deterministic claim extraction
                 |
      Research-aspect coverage analysis
            /             \
     Cycle-aware       Comparable-field
       freshness       conflict screening
            \             /
          Citation validator
                 |
      Optional consent-gated AI analysis
                 |
      Prioritized action checklist
                 |
    Dashboard + Markdown / JSON report
```

This architecture deliberately isolates collection and analysis from the UI. Deterministic and optional AI-generated citations are validated as literal substrings of collected source text. The AI layer supplements rather than replaces the deterministic baseline.

## 6. Security and reliability

`collector.py` rejects non-HTTP(S) URLs, credentials inside links, nonstandard ports, loopback/localhost, private/reserved IP ranges, and redirects to those destinations. It sets request timeouts and limits readable page size. It checks an accessible robots.txt policy and refuses paths disallowed by that file. When robots.txt is unreachable, the app warns that the policy could not be confirmed; you are responsible for site terms and permissions. It does not bypass login or paywalls.

Source text is only sent to a configured AI service when the user checks the consent box. The default AI endpoint must use HTTPS. The app does not persist collected source text beyond its Streamlit session, but the selected provider may process submitted text under its own policies. Do not submit secrets or private documents.

**Security limitation:** DNS is resolved during URL validation and again when making the request; DNS rebinding between those stages remains possible. This starter app must **not** be exposed as an unrestricted public URL-fetching service without stronger network egress protection (e.g., a hardened fetch proxy, pinned IP connections, and server network allow/block rules).

## 7. Known analytical limitations

- No general live web-search integration. Optional query-based retrieval is limited to English Wikipedia; users may also paste text or provide permitted public URLs.
- Optional OpenAI-compatible LLM analysis is not enabled by default and has not been live-tested in this workspace. The deterministic baseline remains the guaranteed local path.
- Keyword screening can miss paraphrases or misclassify mentions as coverage; AI interpretations can also be wrong even when their quoted passages are genuine.
- Document lists that differ are only **possible discrepancies**: one list may be partial or category-specific.
- A nonmatching application cycle is a freshness/context warning, **not** proof of outdated or inaccurate content.
- Inferred target cycle defaults to the latest clearly visible source cycle when the question does not specify one; confirm this with the user.
- Publication/update metadata may be absent or incorrect and is not independently authenticated.
- PDF, JavaScript-rendered pages, dynamic login-only sites, and very large pages are not collected from URLs in this version. Truncation at the text-size limit is disclosed.
- Pasted text cannot be independently authenticated; the app labels its origin accordingly.
- No persistent storage of sessions. Verification checkboxes are local to the app session.
- Generic custom-topic analysis is shallow; high-impact uses require manual evidence review.
- Live network behavior depends on the target site's availability and policies. Automated retrieval tests mock network calls.

## 8. Automated verification

```powershell
python -m pytest -q
python -m compileall -q .
```

The tests cover the end-to-end synthetic workflow, conflicts and cross-cycle handling, missing/modified dates, exact deterministic and AI citation validation, AI fallback and provider timeouts/size limits, URL validation, mocked retrieval and search responses, canonical metadata, paywall/timeout errors, source truncation, and report export. Unit tests mock network calls; a separate manual development check retrieved three live English Wikipedia article extracts for the query `Mars planet`.

## 9. Deployment guidance

For local use, follow the Quick start. The verified Streamlit Community Cloud deployment uses the repository root, `app.py` as the entry point, and `requirements.txt` for dependencies. Direct URL retrieval is disabled by default, including on the public app; do not enable it publicly until the documented DNS-rebinding/SSRF limitation is mitigated with network-level egress controls. Configure any AI key only through the host's secret/environment-variable facility. The live app is linked above.

## 10. Troubleshooting

- `py` not found: install Python 3.10+ with the **Add Python to PATH** option, or use `python -m venv .venv`.
- `No module named streamlit`: select your `.venv` interpreter and reinstall from `requirements.txt`.
- PowerShell script execution blocked: use the per-process bypass instruction above, or use `.venv\Scripts\python.exe` directly.
- A URL fails: confirm public access, `robots.txt`, HTTP response, correct HTML content, and that the site does not require JavaScript. Paste permitted plain text instead.
- No conflict found: not every differing sentence is comparable; the baseline only compares parsed dates, amounts, and lists.
- Uncertain coverage: read supporting passages and supply more authoritative/current source material.

## 11. Submission checklist

- [ ] Test start-up and all tabs in your own Windows browser.
- [ ] Run tests with passing output on your machine.
- [ ] Demonstrate the fictional data honestly or gather reliable real examples.
- [ ] Create a **public or otherwise judge-accessible** GitHub repository and push this full directory (without `.venv` / secrets).
- [ ] Paste the project name, accurate description, and real repository URL into **Unista → Rounds**.
- [ ] Submit by **1 November 2026, 5:00 PM**, per the official PDF (verify which local time zone the portal uses).
- [ ] Add deployed demo, video, and slides only if ready; the official PDF says they are optional.

The GitHub repository and live Streamlit app are linked above. No live AI provider integration has been configured or verified.
