"""Export a complete research review without pretending analyses are verified facts."""
from dataclasses import asdict
import json
from .engine import summarize_findings
from .models import Result


def export_json(result: Result) -> str:
    return json.dumps(asdict(result), indent=2, ensure_ascii=False)


def export_markdown(result: Result) -> str:
    lines = ["# VerityLens AI — Research Review", "", f"**Research goal:** {result.goal}",
             f"**Target cycle:** {result.cycle or 'Not identified'}", "",
             "> This report identifies potential gaps and possible differences in reviewed evidence. "
             "It is not an independent fact-check.", "", "## Sources inspected", ""]
    for source in result.sources:
        lines.extend([f"- **[{source.id}] {source.title}** — {source.url or 'Pasted / demonstration text'}"
                      + (" — SYNTHETIC" if source.synthetic else ""),
                      f"  - Canonical URL: {source.canonical_url or 'Not provided by page'}",
                      f"  - Visible publication metadata: {source.published_at or 'Unknown'}",
                      f"  - Visible last-modified metadata: {source.modified_at or 'Unknown'}",
                      f"  - Collection method: {source.collection_method}",
                      f"  - Collected/retrieved at: {source.collected_at or 'Not recorded'}"])
    if result.collection_failures:
        lines += ["", "## Sources that could not be collected", ""]
        for failure in result.collection_failures:
            lines.append(f"- **{failure.source}:** {failure.message}")
    lines += ["", "## Traceable findings summary", ""]
    lines.extend(f"- {finding}" for finding in summarize_findings(result))
    lines += ["", "## Evidence coverage", ""]
    for row in result.coverage:
        lines.append(f"### {row.aspect} — {row.status}")
        lines.append(row.explanation)
        for claim in row.claims:
            lines.append(f"- [{claim.source_id}] \"{claim.quote}\"")
        lines.append("")
    lines += ["## Possible conflicts", ""]
    if not result.conflicts:
        lines.append("No directly comparable differing values found by this screening method.")
    for conflict in result.conflicts:
        lines += [f"- **{conflict.aspect}: {conflict.label}**. {conflict.explanation}",
                  f"  - [{conflict.first.source_id}] \"{conflict.first.quote}\"",
                  f"  - [{conflict.second.source_id}] \"{conflict.second.quote}\""]
    lines += ["", "## Source freshness and context", ""]
    if not result.freshness:
        lines.append("No date or cycle flags from the supported checks; this does not guarantee currency.")
    for flag in result.freshness:
        lines.append(f"- [{flag.source_id}] **{flag.label}:** {flag.explanation}")
    lines += ["", "## Prioritized verification checklist", ""]
    for action in result.actions:
        lines.append(f"- [ ] **{action.priority}**: {action.task} Reason: {action.reason}")
    lines += ["", "## Method and limitations", "", result.method_note, "",
              "Verify all high-impact information with authoritative current documents. "
              "Pasted content and synthetic samples are not authenticated.", ""]
    if result.ai_analysis:
        lines += ["## Optional AI-assisted insights", "",
                  f"**Mode:** {result.ai_analysis.mode}",
                  result.ai_analysis.summary]
        if result.ai_analysis.error_message:
            lines.append(f"**AI status:** {result.ai_analysis.error_message}")
        if result.ai_analysis.truncated_sources:
            lines.append("Some source text exceeded the configured AI context limit; the AI review was partial.")
        for insight in result.ai_analysis.insights:
            lines += ["", f"### {insight.category.replace('_', ' ').title()} — {insight.evidence_type}",
                      insight.statement, insight.explanation]
            for citation in insight.citations:
                lines.append(f"- [{citation.source_id}] \"{citation.quote}\"")
        lines.append("")
    return "\n".join(lines)
