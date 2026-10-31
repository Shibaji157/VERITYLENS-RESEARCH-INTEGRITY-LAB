"""Launch from project root: streamlit run app.py"""
from dataclasses import replace
from datetime import date
import os
from urllib.parse import urlsplit

import streamlit as st

from veritylens.analysis import analyze_with_llm, deterministic_fallback, llm_is_configured
from veritylens.collector import CollectionError, collect_url, manual_source, search_wikipedia
from veritylens.demo import DEMO_GOAL, sample_sources
from veritylens.engine import run_research, summarize_findings, validate_evidence
from veritylens.models import AIInsight, Claim, CollectionFailure, Result, Source
from veritylens.report import export_json, export_markdown

st.set_page_config(page_title="VerityLens AI | Research Integrity", page_icon="🔎", layout="wide")
URL_FETCH_ENABLED = os.environ.get("VERITYLENS_ENABLE_URL_FETCH", "").strip().lower() in {"1", "true", "yes"}
st.markdown("""
<style>
.stApp {background: #0b1220; color: #e7edf7;}
[data-testid="stSidebar"] {background: #111c30; border-right: 1px solid #2b405d;}
h1,h2,h3 {letter-spacing:-0.035em;}
h1 {font-weight:750;}
p {line-height:1.6;}
[data-testid="stMetric"] {background:#142239; padding:18px; border:1px solid #2e4260; border-radius:14px;}
[data-testid="stMetricLabel"] {color:#a8bad1;}
.stButton > button[kind="primary"] {background:#326ae6; border:0;}
[data-testid="stTabs"] button {font-weight:600;}
.stAlert {border-radius:12px;}
</style>
""", unsafe_allow_html=True)


def load_demo() -> None:
    st.session_state.goal = DEMO_GOAL
    st.session_state.urls = ""
    st.session_state.source_count = 3
    st.session_state.demo_mode = True
    st.session_state.ai_consent = False
    st.session_state.search_wikipedia = False
    st.session_state.collection_failures = []
    for i, source in enumerate(sample_sources(), 1):
        st.session_state[f"source_title_{i}"] = source.title
        st.session_state[f"source_text_{i}"] = source.text
        st.session_state[f"source_date_{i}"] = source.published_at or ""
    st.session_state.pop("result", None)


def _render_claim(claim: Claim, source_lookup: dict[str, Source]) -> None:
    source = source_lookup[claim.source_id]
    st.caption(f"[{claim.source_id}] {source.title} · {claim.cycle or 'cycle not identified'}")
    st.code(claim.quote, language=None, wrap_lines=True)
    if source.url:
        st.link_button(f"Open original [{source.id}] ↗", source.url)


def _render_ai_insight(insight: AIInsight, source_lookup: dict[str, Source]) -> None:
    st.markdown(f"**{insight.category.replace('_', ' ').title()} · {insight.evidence_type}**")
    st.write(insight.statement)
    if insight.explanation:
        st.caption(insight.explanation)
    if not insight.citations:
        st.caption("No direct source passage cited; treat this as an unknown or research prompt.")
    for citation in insight.citations:
        source = source_lookup[citation.source_id]
        st.caption(f"[{source.id}] {source.title}")
        st.code(citation.quote, language=None, wrap_lines=True)
        if source.url:
            st.link_button(f"Open original [{source.id}] ↗", source.url)


def show_results(result: Result) -> None:
    source_lookup = {item.id: item for item in result.sources}
    found = sum(row.status == "Evidence located" for row in result.coverage)
    missing = sum(row.status in {"Not found in reviewed sources", "Previous-cycle evidence only"}
                  for row in result.coverage)
    a, b, c, d = st.columns(4)
    a.metric("Sources reviewed", len(result.sources))
    b.metric("Aspects with evidence", found)
    c.metric("Potential gaps", missing)
    d.metric("Possible discrepancies", len(result.conflicts))
    st.caption("Indicators are evidence-screening signals — not scores of factual completeness or AI confidence.")

    tabs = st.tabs(["Research overview", "Key claims & AI", "Coverage matrix", "Conflict explorer",
                    "Freshness", "Source evidence", "Verification plan", "Export"])
    with tabs[0]:
        st.subheader("What does the reviewed material establish?")
        st.write(f"**Research question:** {result.goal}")
        st.write(f"**Analysis period:** {result.cycle or 'Not identifiable from the question or sources'}")
        st.info("Direct quotations are source evidence. Coverage labels and priorities are automated interpretations; verify them.")
        st.subheader("Traceable findings summary")
        for finding in summarize_findings(result):
            st.write(f"- {finding}")
        st.write(f"**Sources retrieved/entered:** {len(result.sources)} · **Sources that failed:** {len(result.collection_failures)}")
        if result.collection_failures:
            with st.expander("Review sources that could not be collected", expanded=True):
                for failure in result.collection_failures:
                    st.warning(f"{failure.source}: {failure.message}")
        for row in result.coverage:
            if row.claims:
                claim = next((x for x in row.claims if not result.cycle or not x.cycle or x.cycle == result.cycle), row.claims[0])
                with st.expander(f"{row.aspect} · {row.status}"):
                    st.write(row.explanation)
                    _render_claim(claim, source_lookup)
        if len(result.sources) < 2:
            st.warning("Only one source is available; cross-source contradiction detection is limited.")
    with tabs[1]:
        st.subheader("Distinct evidence-backed claims")
        st.caption("Claims are candidate statements extracted from passages, not verified facts. Each citation is checked against collected text.")
        seen_claims = set()
        for row in result.coverage:
            for claim in row.claims:
                marker = (claim.source_id, claim.quote)
                if marker in seen_claims:
                    continue
                seen_claims.add(marker)
                with st.container(border=True):
                    st.markdown(f"**{row.aspect}** · {claim.cycle or 'cycle not identified'}")
                    _render_claim(claim, source_lookup)
        analysis = result.ai_analysis
        if not analysis or analysis.mode != "ai_assisted":
            st.info("AI-assisted analysis is not active. The deterministic evidence screen remains available; no AI claims are implied.")
            if analysis and analysis.error_message:
                st.warning(analysis.error_message)
        else:
            st.divider()
            st.subheader("Optional AI-assisted research signals")
            st.caption("Source text was sent to the configured provider only after explicit consent. AI interpretations are not verified facts.")
            st.markdown(f"**AI-generated overview (unverified):** {analysis.summary}")
            if analysis.truncated_sources:
                st.warning("Some source text exceeded the AI context limit; this AI review may be incomplete.")
            for insight in analysis.insights:
                with st.container(border=True):
                    _render_ai_insight(insight, source_lookup)
    with tabs[2]:
        st.subheader("Information coverage matrix")
        st.caption("'Not found' means not found in this specific reviewed set, never universally absent.")
        st.dataframe([{"Research aspect": row.aspect, "Finding": row.status,
                       "Cited passages": len(row.claims), "Interpretation": row.explanation}
                      for row in result.coverage], width="stretch", hide_index=True)
        for row in result.coverage:
            with st.expander(f"Evidence: {row.aspect} — {row.status}"):
                st.write(row.explanation)
                if not row.claims:
                    st.warning("No matching passage was found in reviewed text. Try additional official sources.")
                for claim in row.claims[:12]:
                    _render_claim(claim, source_lookup)
    with tabs[3]:
        st.subheader("Potential claim discrepancies")
        if not result.conflicts:
            st.info("No differing comparable values detected. This is not proof all sources agree.")
        for number, item in enumerate(result.conflicts, 1):
            with st.container(border=True):
                st.markdown(f"**{number}. {item.aspect}** · {item.label}")
                st.write(item.explanation)
                left, right = st.columns(2)
                with left:
                    _render_claim(item.first, source_lookup)
                with right:
                    _render_claim(item.second, source_lookup)
    with tabs[4]:
        st.subheader("Date and application-cycle signals")
        if not result.freshness:
            st.success("No date/cycle warnings under the current rules. Freshness is not guaranteed.")
        for item in result.freshness:
            with st.container(border=True):
                st.markdown(f"**{item.label}** · [{item.source_id}] {source_lookup[item.source_id].title}")
                st.write(item.explanation)
    with tabs[5]:
        st.subheader("Evidence provenance and source library")
        for source in result.sources:
            origin = "SYNTHETIC" if source.synthetic else ("LIVE-RETRIEVED" if source.url else "MANUALLY ENTERED")
            with st.expander(f"[{source.id}] {source.title} · {origin}"):
                st.write(f"**Published / updated metadata:** {source.published_at or 'Unknown'}")
                st.write(f"**Last-modified metadata:** {source.modified_at or 'Unknown'}")
                st.write(f"**Retrieved/source URL:** {source.url or 'Not provided'}")
                st.write(f"**Canonical URL:** {source.canonical_url or 'Not provided by page'}")
                st.write(f"**Collected at (UTC):** {source.collected_at or 'Not recorded for synthetic fixture'}")
                st.write(f"**Collection method:** {source.collection_method}")
                if source.collection_method == "manual":
                    st.write("**Origin:** User-provided text; original external source is not authenticated.")
                if source.extraction_note:
                    st.caption(source.extraction_note)
                if source.url:
                    st.link_button("Open original page ↗", source.url)
                st.text_area("Collected readable text", source.text, height=220, disabled=True, key=f"collected_{source.id}")
    with tabs[6]:
        st.subheader("Prioritized verification plan")
        st.caption("Tick items during your own review. These checkmarks are local to the current app session.")
        for number, action in enumerate(result.actions):
            with st.container(border=True):
                st.checkbox(f"[{action.priority.upper()}] {action.task}", key=f"verify_{number}_{action.aspect}")
                st.caption(action.reason)
                if action.source_ids:
                    st.write("Relevant reviewed source IDs: " + ", ".join(action.source_ids))
        st.warning("Use the latest authoritative source to resolve high-impact uncertainties. The app does not independently certify facts.")
    with tabs[7]:
        st.subheader("Take your evidence with you")
        st.download_button("Download full research report (.md)", export_markdown(result),
                           "veritylens_research_report.md", "text/markdown", width="stretch")
        st.download_button("Download structured evidence (.json)", export_json(result),
                           "veritylens_evidence.json", "application/json", width="stretch")
        st.caption(result.method_note)


st.markdown("##### VERITYLENS / RESEARCH INTEGRITY LAB")
st.title("See what the sources don't tell you.")
st.write("Compare evidence across sources, locate unanswered questions, and create a responsible verification plan.")

with st.sidebar:
    st.markdown("### Research workspace")
    st.caption("Digital Dark Spot · Hackathon prototype")
    st.button("🧪 Load fictional scholarship demo", on_click=load_demo, width="stretch")
    st.info("The demo is entirely synthetic. It is a transparent functional test, not a real scholarship.")
    st.divider()
    st.markdown("**Research method**")
    if llm_is_configured():
        st.write("Transparent rule-based baseline plus optional AI analysis; AI use requires explicit consent. Neither independently verifies facts.")
    else:
        st.write("Transparent rule-based baseline. No API key needed; optional AI analysis is inactive.")
    if URL_FETCH_ENABLED:
        st.caption("Direct URL retrieval is enabled: public HTML/text only; source-access policies apply.")
    else:
        st.caption("Direct URL retrieval is disabled by default for public-deployment safety. Paste source text or use Wikipedia search.")

if st.session_state.get("demo_mode"):
    st.warning("SYNTHETIC DEMONSTRATION LOADED · Fixture text is marked synthetic; edited passages are treated as user-entered text.")

st.session_state.setdefault("source_count", 2)
with st.form("research_form"):
    goal = st.text_input("1 · Research goal or decision question", key="goal",
                         placeholder="What should I verify before applying for this scholarship?", max_chars=500)
    urls = st.text_area("2 · Optional public source URLs — one per line", key="urls", height=85,
                        placeholder="https://example.org/current-guidance\nhttps://example.org/archived-guidance",
                        max_chars=2500, disabled=not URL_FETCH_ENABLED)
    if not URL_FETCH_ENABLED:
        st.caption("URL fetching is disabled in this deployment. To enable it in a trusted local environment, set VERITYLENS_ENABLE_URL_FETCH=1 before starting Streamlit.")
    search_requested = st.checkbox(
        "Search English Wikipedia for pages related to this question (third-party, collaboratively edited sources)",
        key="search_wikipedia",
    )
    source_count = st.number_input("3 · Number of pasted source documents", min_value=1, max_value=4,
                                   step=1, key="source_count")
    st.caption("Paste readable excerpts from permitted documents. Preserve wording and identify the original externally when possible.")
    for i in range(1, int(source_count) + 1):
        with st.expander(f"Pasted source {i}", expanded=(i == 1)):
            st.text_input("Document name / origin", key=f"source_title_{i}", placeholder="Official notice / page title")
            st.text_area("Direct source text", key=f"source_text_{i}", height=135,
                         placeholder="Paste the actual document text here, not your summary.", max_chars=20000)
            st.text_input("Visible publication date (optional YYYY-MM-DD)", key=f"source_date_{i}",
                          placeholder="2026-10-01")
    custom = st.text_input("Optional research aspects (comma-separated)", key="aspects",
                           placeholder="Leave blank for the scholarship or generic starter template", max_chars=500)
    if llm_is_configured():
        llm_consent = st.checkbox(
            "I consent to send the collected source text and research question to the configured AI provider.",
            key="ai_consent",
        )
    else:
        llm_consent = False
        st.caption("Optional AI analysis is not configured. No source text is sent to an AI provider.")
    submitted = st.form_submit_button("Analyze evidence →", type="primary", width="stretch")

if submitted:
    items: list[Source] = []
    failures: list[CollectionFailure] = []
    metadata_warnings: list[str] = []
    for i in range(1, int(source_count) + 1):
        source_text = st.session_state.get(f"source_text_{i}", "")
        if not source_text.strip():
            continue
        try:
            date_value = st.session_state.get(f"source_date_{i}", "").strip()
            if date_value:
                try:
                    valid_date = date.fromisoformat(date_value)
                except ValueError:
                    valid_date = None
                if valid_date is None or valid_date.isoformat() != date_value:
                    metadata_warnings.append(f"Pasted source {i}: date must be a real YYYY-MM-DD date; metadata omitted.")
                    date_value = ""
            source = manual_source(f"S{len(items)+1}", st.session_state.get(f"source_title_{i}", ""),
                                   source_text, date_value)
            if st.session_state.get("demo_mode") and any(source_text == sample.text for sample in sample_sources()):
                source = replace(
                    source, synthetic=True,
                    extraction_note="Synthetic demo text; metadata may have been edited. Not an authentic notice.",
                )
            items.append(source)
        except CollectionError as exc:
            failures.append(CollectionFailure(f"Pasted source {i}", str(exc)))
    url_list = [value.strip() for value in urls.splitlines() if value.strip()]
    if len(url_list) > 5:
        failures.append(CollectionFailure("Additional URLs", "Only the first five URLs were attempted to bound response time."))
    if url_list and not URL_FETCH_ENABLED:
        failures.append(CollectionFailure(
            "Submitted URLs",
            "Direct URL retrieval is disabled for this deployment. Paste permitted source text or use English Wikipedia search.",
        ))
    elif url_list:
        with st.spinner("Reading public pages with access and safety checks…"):
            for index, url in enumerate(url_list[:5], 1):
                try:
                    items.append(collect_url(url, f"S{len(items)+1}"))
                except CollectionError as exc:
                    try:
                        parts = urlsplit(url)
                        safe_label = f"{parts.scheme}://{parts.hostname or 'unresolved host'}/…"
                    except ValueError:
                        safe_label = "Submitted URL"
                    failures.append(CollectionFailure(f"URL {index} ({safe_label})", str(exc)))
    if search_requested:
        with st.spinner("Searching English Wikipedia and retrieving short article extracts…"):
            try:
                discovered, search_failures = search_wikipedia(goal)
                items.extend(discovered)
                failures.extend(CollectionFailure("Wikipedia query", item) for item in search_failures)
            except CollectionError as exc:
                failures.append(CollectionFailure("Wikipedia query", str(exc)))
    if st.session_state.get("demo_mode") and not any(source.synthetic for source in items):
        st.session_state.demo_mode = False
    st.session_state.collection_failures = failures
    for warning in metadata_warnings:
        st.warning(warning)
    try:
        st.session_state.result = run_research(
            goal, items, custom_aspects=[x.strip() for x in custom.split(",") if x.strip()] or None,
            collection_failures=failures)
        if llm_consent:
            with st.spinner("Analyzing the collected source text with the configured AI provider…"):
                st.session_state.result.ai_analysis = analyze_with_llm(goal, items)
        else:
            fallback_message = (
                "AI analysis was not requested; source text was not sent to an AI provider."
                if llm_is_configured() else
                "No AI API key is configured; source text was not sent to an AI provider."
            )
            st.session_state.result.ai_analysis = deterministic_fallback(fallback_message)
        validate_evidence(st.session_state.result)
        st.success(f"Screened {len(items)} readable sources. Review each automated signal against the cited passages.")
    except ValueError as exc:
        st.session_state.pop("result", None)
        st.error(str(exc))

if "result" in st.session_state:
    st.divider()
    show_results(st.session_state.result)
else:
    st.divider()
    if st.session_state.get("collection_failures"):
        st.subheader("Source collection status")
        st.error("No analysis is available until at least one source is readable.")
        for failure in st.session_state.collection_failures:
            st.warning(f"{failure.source}: {failure.message}")
    st.markdown("### From scattered text to an actionable research review")
    st.write("Start with a research question and two or more source documents, or load the clearly labeled fictional demonstration.")
    st.caption("Core workflow: sources → cited passages → coverage → possible discrepancies → freshness → next steps.")
