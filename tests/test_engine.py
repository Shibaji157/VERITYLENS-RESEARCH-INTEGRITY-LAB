from datetime import date
from dataclasses import replace
import pytest
from veritylens.demo import DEMO_GOAL, sample_sources
from veritylens.engine import (
    run_research, validate_evidence, find_conflicts, extract_claims, SCHOLARSHIP_ASPECTS,
)
from veritylens.models import Source
from veritylens.report import export_markdown, export_json


def demo():
    return run_research(DEMO_GOAL, sample_sources(), today=date(2026, 10, 31))


def test_full_demo_flow_has_conflicts_gap_freshness_and_actions():
    result = demo()
    aspects = {item.aspect: item.status for item in result.coverage}
    assert aspects["Application deadline"] == "Possible conflict"
    assert aspects["Required documents"] == "Possible conflict"
    assert aspects["Renewal conditions"] == "Previous-cycle evidence only"
    assert aspects["Official contact"] == "Not found in reviewed sources"
    assert len(result.conflicts) == 2
    assert any(x.source_id == "S3" and "cycle" in x.label.lower() for x in result.freshness)
    assert any(x.priority == "High" for x in result.actions)
    validate_evidence(result)


def test_different_application_cycles_are_not_automatically_contradictions():
    one = Source("S1", "Programme 2026-27", "Application deadline is 15 November 2026.")
    two = Source("S2", "Programme 2024-25", "Application deadline is 12 October 2024.")
    assert not find_conflicts(extract_claims([one, two], SCHOLARSHIP_ASPECTS))


def test_one_source_and_missing_aspect_not_proof_of_universal_absence():
    result = run_research(DEMO_GOAL, [sample_sources()[0]], today=date(2026, 10, 31))
    renewal = next(x for x in result.coverage if x.aspect == "Renewal conditions")
    assert renewal.status == "Not found in reviewed sources"
    assert "does not prove" in renewal.explanation
    assert not result.conflicts


def test_invalid_citation_is_rejected():
    result = demo()
    result.coverage[0].claims[0] = replace(result.coverage[0].claims[0], quote="FABRICATED QUOTE")
    with pytest.raises(ValueError, match="Evidence validation failed"):
        validate_evidence(result)


def test_claim_extraction_returns_atomic_source_linked_passage():
    source = Source("S1", "Current notice", "Application deadline is 15 November 2026.")
    claims = extract_claims([source], SCHOLARSHIP_ASPECTS)
    deadline = next(claim for claim in claims if claim.aspect == "Application deadline")
    assert deadline.source_id == source.id
    assert deadline.quote == "Application deadline is 15 November 2026."
    assert deadline.value == "2026-11-15"


def test_ai_citation_is_also_checked_against_source_text():
    from veritylens.analysis import AIAnalysis
    from veritylens.models import AIInsight, EvidenceLink

    result = demo()
    result.ai_analysis = AIAnalysis(
        "ai_assisted", "Summary",
        [AIInsight("key_claim", "Claim", "direct evidence", "", [EvidenceLink("S1", "invented quote")])],
    )
    with pytest.raises(ValueError, match="AI citation"):
        validate_evidence(result)


def test_missing_sources_or_research_goal_raises():
    with pytest.raises(ValueError, match="research question"):
        run_research("", sample_sources())
    with pytest.raises(ValueError, match="at least one"):
        run_research(DEMO_GOAL, [])


def test_exports_include_traceable_material():
    result = demo()
    markdown = export_markdown(result)
    structured = export_json(result)
    assert "[S1]" in markdown and "verification checklist" in markdown.lower()
    assert "Traceable findings summary" in markdown
    assert "Possible application deadline discrepancy" in markdown
    assert '"conflicts"' in structured and '"source_id": "S2"' in structured


def test_undated_sources_flag_unknown_without_guessing_date():
    result = run_research("Scholarship eligibility", [Source("S1", "Unknown", "Eligibility: undergraduate students only.")],
                          today=date(2026, 10, 31))
    assert result.freshness[0].label == "Date not verifiable"
    assert "does not prove" in result.freshness[0].explanation


def test_last_modified_metadata_is_not_mislabeled_as_publication_date():
    source = Source(
        "S1", "Editable page", "Scholarship requirements are listed here.",
        modified_at="2024-01-01T00:00:00Z", collection_method="wikipedia_search",
    )
    result = run_research("Scholarship requirements", [source], today=date(2026, 10, 31))
    warning = next(item for item in result.freshness if item.source_id == "S1")
    assert warning.label == "Older last-modified metadata"
    assert "does not prove" in warning.explanation


def test_invalid_publication_date_falls_back_to_last_modified_metadata():
    source = Source(
        "S1", "Editable page", "Scholarship requirements are listed here.",
        published_at="not-a-date", modified_at="2024-01-01T00:00:00Z",
    )
    result = run_research("Scholarship requirements", [source], today=date(2026, 10, 31))
    warning = next(item for item in result.freshness if item.source_id == "S1")
    assert warning.label == "Older last-modified metadata"


def test_unknown_cycle_does_not_silently_invent_date():
    source = Source("S1", "Notice", "Required documents: ID and marksheet.")
    result = run_research("Scholarship?", [source], today=date(2026, 10, 31))
    assert result.cycle is None
