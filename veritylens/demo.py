"""Entirely fictional controlled fixture: not a real scholarship or official notice."""
from .models import Source

DEMO_GOAL = "What must I verify for the fictional 2026-27 Meridian Scholars Grant?"


def sample_sources() -> list[Source]:
    return [
        Source(
            id="S1", title="FICTIONAL programme announcement — 2026-27",
            synthetic=True, published_at="2026-09-20",
            extraction_note="Controlled synthetic demonstration; not a real official source.",
            text=(
                "Meridian Scholars Grant — 2026-27 (FICTIONAL DEMO).\n"
                "Eligibility: Applicants must be enrolled full-time in an undergraduate programme.\n"
                "Application deadline is 15 November 2026.\n"
                "Documents required: identity proof, marksheet, and household income certificate.\n"
                "Application process: Apply online through the fictional programme portal.\n"
                "Award amount: INR 30000 per academic year.\n"
                "Selection criteria: Selection is based on academic merit."
            ),
        ),
        Source(
            id="S2", title="FICTIONAL student guidance — 2026-27",
            synthetic=True, published_at="2026-10-05",
            extraction_note="Controlled synthetic demonstration; not a real college website.",
            text=(
                "Meridian Scholars Grant — 2026-27 (FICTIONAL DEMO).\n"
                "Application deadline is 20 November 2026.\n"
                "Documents required: identity proof, marksheet, and self-declared income statement.\n"
                "Application process: Applicants must submit online."
            ),
        ),
        Source(
            id="S3", title="FICTIONAL archived notice — 2024-25",
            synthetic=True, published_at="2024-08-10",
            extraction_note="Controlled synthetic demonstration; previous-cycle fixture.",
            text=(
                "Meridian Scholars Grant — 2024-25 (FICTIONAL ARCHIVE).\n"
                "Application deadline is 12 October 2024.\n"
                "Renewal conditions: Award holders needed 75% attendance for renewal in 2024-25."
            ),
        ),
    ]
