"""Deterministic baseline: inspectable signals, not semantic AI or fact verification."""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime
from itertools import combinations
import re

from .models import CollectionFailure, Source, Claim, Coverage, Conflict, Freshness, Action, Result

SCHOLARSHIP_ASPECTS = {
    "Eligibility": r"\beligib|\bqualif|\benrolled\b",
    "Application deadline": r"\bdeadline\b|\bcloses?\s+on\b|\bapply\s+by\b",
    "Required documents": r"\bdocuments?\s+required\b|\brequired\s+documents?\b|\bdocuments?\s+include\b",
    "Renewal conditions": r"\brenewal\b|\bcontinuation\s+conditions?\b",
    "Application process": r"\bapplication\s+process\b|\bapply\s+(?:online|through|at)\b|\bsubmit\s+online\b",
    "Award amount": r"\baward\s+amount\b|\bscholarship\s+amount\b|\bfinancial\s+benefit\b",
    "Selection criteria": r"\bselection\s+criteria\b|\bselection\s+is\b|\bmerit\b",
    "Official contact": r"\bhelpdesk\b|\bcontact\b|\bsupport\s+email\b",
}
GENERIC_ASPECTS = {
    "Requirements": r"\brequirements?\b|\bqualifications?\b|\beligibility\b",
    "Deadlines": r"\bdeadline\b|\bdate\b|\bcloses\b",
    "Costs and benefits": r"\bcost\b|\bfees?\b|\bprice\b|\bbenefits?\b",
    "How to proceed": r"\bprocedure\b|\bsteps?\b|\bapply\b|\bprocess\b",
    "Supporting documents": r"\bdocuments?\b|\bcertificates?\b|\bforms?\b",
    "Contact information": r"\bcontacts?\b|\bsupport\b|\bhelpdesk\b",
}
CYCLE_RE = re.compile(r"\b(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})\b")
DATE_RE = re.compile(r"\b(\d{1,2}\s+[A-Za-z]{3,10}\s+20\d{2})\b")
AMOUNT_RE = re.compile(r"\b(?:INR|Rs\.?|₹)\s*([\d,]+)\b", re.IGNORECASE)


def _cycle(text: str) -> str | None:
    match = CYCLE_RE.search(text)
    if not match:
        return None
    end = match.group(2)[-2:]
    return f"{match.group(1)}-{end}"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if len(part.strip()) >= 9]


def _value(aspect: str, quote: str) -> str:
    if aspect in {"Application deadline", "Deadlines"}:
        match = DATE_RE.search(quote)
        if match:
            for pattern in ("%d %B %Y", "%d %b %Y"):
                try:
                    return datetime.strptime(match.group(1), pattern).date().isoformat()
                except ValueError:
                    pass
    if aspect == "Required documents":
        match = re.search(r"\b(?:documents?\s+required|documents?\s+include|required\s+documents?)\s*:?\s*(.+)", quote, re.I)
        if match:
            items = re.split(r",\s*|\s+and\s+", match.group(1).strip(" ."))
            return " | ".join(sorted({item.strip(" .").lower() for item in items if item.strip()}))
    if aspect == "Award amount":
        match = AMOUNT_RE.search(quote)
        if match:
            return match.group(1).replace(",", "")
    return re.sub(r"\s+", " ", quote).casefold()


def extract_claims(sources: list[Source], aspects: dict[str, str]) -> list[Claim]:
    claims: list[Claim] = []
    for source in sources:
        cycle = _cycle(source.title + "\n" + source.text[:450])
        for quote in _sentences(source.text):
            for aspect, pattern in aspects.items():
                if re.search(pattern, quote, flags=re.IGNORECASE):
                    claims.append(Claim(source_id=source.id, aspect=aspect, quote=quote,
                                        value=_value(aspect, quote), cycle=cycle))
    return claims


def find_conflicts(claims: list[Claim]) -> list[Conflict]:
    """Only compare explicit normalized fields within matching known periods."""
    comparable = {"Application deadline", "Required documents", "Award amount", "Deadlines"}
    grouped: dict[str, list[Claim]] = defaultdict(list)
    for claim in claims:
        if claim.aspect in comparable:
            grouped[claim.aspect].append(claim)
    output: list[Conflict] = []
    for aspect, items in grouped.items():
        for first, second in combinations(items, 2):
            if first.source_id == second.source_id or first.value == second.value:
                continue
            if first.cycle and second.cycle and first.cycle != second.cycle:
                continue  # A prior cycle is not necessarily a contradictory claim.
            if aspect in {"Application deadline", "Deadlines"}:
                if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", first.value)
                        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", second.value)):
                    continue
                explanation = "Different explicit deadline dates; confirm applicability and latest official notice."
            elif aspect == "Award amount":
                if not (first.value.isdigit() and second.value.isdigit()):
                    continue
                explanation = "Different stated amount values; confirm eligibility category and period."
            else:
                if " | " not in first.value and " | " not in second.value:
                    continue
                explanation = "The stated required-document lists differ; these could be alternatives or incomplete lists."
            if first.cycle != second.cycle:
                explanation += " One source lacks an identifiable cycle, so period matching is uncertain."
            output.append(Conflict(aspect=aspect, first=first, second=second,
                                   explanation=explanation))
    return output


def _parse_metadata_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_date(source: Source) -> date | None:
    return _parse_metadata_date(source.published_at) or _parse_metadata_date(source.modified_at)


def check_freshness(sources: list[Source], target_cycle: str | None, today: date) -> list[Freshness]:
    warnings = []
    for source in sources:
        cycle = _cycle(source.title + "\n" + source.text[:450])
        if target_cycle and cycle and cycle != target_cycle:
            warnings.append(Freshness(source.id, "Previous or different cycle",
                                      f"Visible {cycle}; research target is {target_cycle}. Applicability is unverified."))
        visible_date = _parse_date(source)
        publication_date = _parse_metadata_date(source.published_at)
        if visible_date is None:
            warnings.append(Freshness(source.id, "Date not verifiable",
                                      "No machine-readable publication or last-modified date is available. This does not prove the source is old."))
        elif visible_date > today:
            warnings.append(Freshness(source.id, "Future-dated metadata",
                                      f"Visible date metadata {visible_date.isoformat()} is after the reference date; verify source metadata."))
        elif (today - visible_date).days > 365:
            if source.modified_at and publication_date is None:
                warnings.append(Freshness(
                    source.id, "Older last-modified metadata",
                    f"Visible last-modified metadata {visible_date.isoformat()} is over one year old. "
                    "This does not prove that the page's information is outdated.",
                ))
            else:
                warnings.append(Freshness(
                    source.id, "Older publication metadata",
                    f"Visible publication metadata {visible_date.isoformat()} may be unsuitable for current deadlines; verify it.",
                ))
    return warnings


def _aspects(goal: str, manual_aspects: list[str] | None) -> dict[str, str]:
    if manual_aspects:
        custom = {}
        for item in manual_aspects[:12]:
            label = item.strip()[:65]
            if not label:
                continue
            meaningful = [part for part in re.findall(r"[\w-]+", label.lower()) if len(part) >= 3]
            if meaningful:
                custom[label] = r"\b(?:" + "|".join(re.escape(x) for x in meaningful) + r")\b"
        if custom:
            return custom
    if re.search(r"scholarship|grant|fellowship", goal, re.I):
        return SCHOLARSHIP_ASPECTS
    return GENERIC_ASPECTS


def validate_evidence(result: Result) -> None:
    """Hard failure if a displayed direct quote or source identifier is invented."""
    available = {source.id: source for source in result.sources}
    if len(available) != len(result.sources):
        raise ValueError("Duplicate source identifiers.")
    claim_lists: list[Claim] = [claim for row in result.coverage for claim in row.claims]
    claim_lists += [claim for conflict in result.conflicts for claim in (conflict.first, conflict.second)]
    for claim in claim_lists:
        if claim.source_id not in available or claim.quote not in available[claim.source_id].text:
            raise ValueError("Evidence validation failed: quote or source identifier not found.")
    for item in result.freshness:
        if item.source_id not in available:
            raise ValueError("Freshness warning references an unknown source.")
    for action in result.actions:
        if any(source_id not in available for source_id in action.source_ids):
            raise ValueError("Checklist references an unknown source.")
    if result.ai_analysis:
        for insight in result.ai_analysis.insights:
            for citation in insight.citations:
                if (citation.source_id not in available
                        or citation.quote not in available[citation.source_id].text):
                    raise ValueError("Evidence validation failed: AI citation does not match collected source text.")


def summarize_findings(result: Result) -> list[str]:
    """Create a concise local summary whose source-backed statements carry IDs and excerpts."""
    findings = [f"Reviewed {len(result.sources)} source(s) for the stated research question."]
    for conflict in result.conflicts:
        findings.append(
            f"Possible {conflict.aspect.lower()} discrepancy: "
            f"[{conflict.first.source_id}] “{conflict.first.quote}” versus "
            f"[{conflict.second.source_id}] “{conflict.second.quote}”."
        )
    for row in result.coverage:
        if row.status == "Not found in reviewed sources":
            findings.append(f"No {row.aspect.lower()} passage was located in the reviewed source set.")
        elif row.status == "Previous-cycle evidence only":
            citations = "; ".join(f"[{claim.source_id}] “{claim.quote}”" for claim in row.claims[:2])
            findings.append(
                f"Only previous/different-cycle evidence was located for {row.aspect.lower()}: {citations} "
                "Current applicability is unknown."
            )
    if not result.conflicts and not any(
        row.status in {"Not found in reviewed sources", "Previous-cycle evidence only"}
        for row in result.coverage
    ):
        findings.append("No supported conflict or explicit evidence gap was detected by these screening rules.")
    if result.freshness:
        findings.append(f"{len(result.freshness)} source date/cycle warning(s) need review.")
    return findings


def run_research(goal: str, sources: list[Source], *, custom_aspects: list[str] | None = None,
                 today: date | None = None,
                 collection_failures: list[CollectionFailure] | None = None) -> Result:
    if not goal.strip():
        raise ValueError("Enter a research question first.")
    if not sources or not any(item.text.strip() for item in sources):
        raise ValueError("Add at least one readable source. Multiple sources are recommended.")
    aspects = _aspects(goal, custom_aspects)
    available = [item for item in sources if item.text.strip()]
    goal_cycle = _cycle(goal)
    observed_cycles = [_cycle(src.title + "\n" + src.text[:450]) for src in available]
    target_cycle = goal_cycle or max((cycle for cycle in observed_cycles if cycle), default=None)
    all_claims = extract_claims(available, aspects)
    conflicts = find_conflicts(all_claims)
    conflict_aspects = {item.aspect for item in conflicts}
    coverage: list[Coverage] = []
    for aspect in aspects:
        matches = [claim for claim in all_claims if claim.aspect == aspect]
        applicable = [claim for claim in matches if not (target_cycle and claim.cycle and claim.cycle != target_cycle)]
        if aspect in conflict_aspects:
            status = "Possible conflict"
            explanation = "Comparable source statements differ. See the Conflict Explorer; context may explain them."
        elif applicable:
            status = "Evidence located"
            explanation = "Relevant passages were located; keyword-based screening does not establish completeness or truth."
        elif matches:
            status = "Previous-cycle evidence only"
            explanation = "Only non-target-cycle passages were found; current applicability is not established."
        else:
            status = "Not found in reviewed sources"
            explanation = "No relevant passage was located in the inspected text. This does not prove it does not exist."
        coverage.append(Coverage(aspect, status, matches, explanation))
    freshness = check_freshness(available, target_cycle, today or date.today())
    actions: list[Action] = []
    high_impact = {"Application deadline", "Required documents", "Renewal conditions", "Deadlines", "Requirements"}
    for row in coverage:
        if row.status == "Evidence located":
            continue
        priority = "High" if row.status == "Possible conflict" or row.aspect in high_impact else "Medium"
        action_verb = "Resolve the differing source statements" if row.status == "Possible conflict" else "Verify the current requirements"
        task = f"{action_verb} for {row.aspect.lower()} using a current authoritative source."
        actions.append(Action(row.aspect, priority, task,
                              row.explanation, tuple(sorted({claim.source_id for claim in row.claims}))))
    if not actions:
        actions.append(Action("Final validation", "Medium", "Verify key details from the current official notice.",
                              "Located text is not independently fact-checked.", tuple(item.id for item in available)))
    actions.sort(key=lambda action: (action.priority != "High", action.aspect))
    method_note = (
        "The deterministic baseline uses keyword-based aspect screening and compares explicitly parsed deadlines, "
        "amounts, and document lists. Optional AI analysis is separate, consent-gated, and citation-validated when "
        "configured. Neither layer independently verifies source truth."
    )
    result = Result(
        goal, available, target_cycle, coverage, conflicts, freshness, actions, method_note,
        collection_failures=collection_failures or [],
    )
    validate_evidence(result)
    return result
