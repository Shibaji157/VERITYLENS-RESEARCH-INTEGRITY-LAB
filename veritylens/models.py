"""Typed data exchanged between collection, analysis, and presentation."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    text: str
    url: str | None = None
    published_at: str | None = None  # Date supplied explicitly or extracted from page metadata.
    canonical_url: str | None = None
    collected_at: str | None = None
    modified_at: str | None = None
    collection_method: str = "manual"
    synthetic: bool = False
    extraction_note: str = ""


@dataclass(frozen=True)
class Claim:
    source_id: str
    aspect: str
    quote: str
    value: str
    cycle: str | None


@dataclass
class Coverage:
    aspect: str
    status: str
    claims: list[Claim] = field(default_factory=list)
    explanation: str = ""


@dataclass(frozen=True)
class Conflict:
    aspect: str
    first: Claim
    second: Claim
    explanation: str
    label: str = "Possible discrepancy — verify context"


@dataclass(frozen=True)
class Freshness:
    source_id: str
    label: str
    explanation: str


@dataclass(frozen=True)
class Action:
    aspect: str
    priority: str
    task: str
    reason: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CollectionFailure:
    source: str
    message: str


@dataclass(frozen=True)
class EvidenceLink:
    source_id: str
    quote: str


@dataclass(frozen=True)
class AIInsight:
    category: str
    statement: str
    evidence_type: str
    explanation: str
    citations: list[EvidenceLink] = field(default_factory=list)


@dataclass
class AIAnalysis:
    mode: str
    summary: str
    insights: list[AIInsight] = field(default_factory=list)
    error_message: str | None = None
    truncated_sources: bool = False


@dataclass
class Result:
    goal: str
    sources: list[Source]
    cycle: str | None
    coverage: list[Coverage]
    conflicts: list[Conflict]
    freshness: list[Freshness]
    actions: list[Action]
    method_note: str
    collection_failures: list[CollectionFailure] = field(default_factory=list)
    ai_analysis: AIAnalysis | None = None
