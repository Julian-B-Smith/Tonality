"""Constraint search — exact, exhaustive queries over the identity universe.

The *inverse* of analysis: instead of "what is this set?", ask "which sets
satisfy these constraints?" and let the engine enumerate them exactly over the
4096-mask universe (Phase 4, the marquee agent-facing tool). This is
**generative-side** (ROADMAP cardinal rule): a search constraint and a
checkable rule are the same predicate pointed in opposite directions, so the
scalar predicate machinery is the ruleset engine's ``Condition`` (eq/in/gte/lte)
reused over an *identity* field vocabulary.

``search_identities`` (pitch-class-set identities over the 4096-mask universe — the 4,095 non-empty masks)
and ``search_voicings`` (register enumeration — a bounded generative space whose
register window is required, never defaulted) share one predicate contract.
``repair_sequence`` is the third member: conformance repair, imposing a ruleset
on an existing piece with minimal re-pitch edits.
"""

from __future__ import annotations

from .fields import IDENTITY_FIELDS
from .identities import search_identities
from .results import (
    IdentityMatch,
    IdentitySearchResult,
    Repair,
    RepairEdit,
    RepairResult,
    VoicingMatch,
    VoicingSearchResult,
)
from .repair import repair_sequence
from .voicings import VOICING_FIELDS, search_voicings

__all__ = [
    "IDENTITY_FIELDS",
    "IdentityMatch",
    "IdentitySearchResult",
    "VOICING_FIELDS",
    "VoicingMatch",
    "VoicingSearchResult",
    "search_identities",
    "search_voicings",
    "Repair",
    "RepairEdit",
    "RepairResult",
    "repair_sequence",
]
