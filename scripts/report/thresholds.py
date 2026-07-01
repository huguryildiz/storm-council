"""Single source of truth for status/score thresholds.

Both the renderer (``report/layers/document.py`` — status banner color + the
four review-score chips) and the quality gate (``scripts/verify.py`` — which
status levels count as "positive" and the weak-recommendation cut point) read
these constants, so the score-color thresholds can't drift between the two.
"""

from __future__ import annotations

# Status levels the quality gate treats as positive and the report renders green.
POSITIVE_LEVELS = ("pass", "verified", "source_checked")
# Status levels the report renders red.
NEGATIVE_LEVELS = ("revise", "blocked")
# Status levels the report renders neutral (no color class).
NEUTRAL_LEVELS = ("pass_with_caveats", "caveats", "illustrative")

# Level -> CSS color class for the status banner.
STATUS_CLASS = {
    **{lvl: "green" for lvl in POSITIVE_LEVELS},
    **{lvl: "" for lvl in NEUTRAL_LEVELS},
    **{lvl: "red" for lvl in NEGATIVE_LEVELS},
}

# Review-score cut points (0-100). At/above OK -> "ok"; at/above WARN -> "warn";
# below WARN -> "bad". verify.py flags a recommendation-support score < WARN.
SCORE_OK_MIN = 80
SCORE_WARN_MIN = 50


def score_class(value) -> str:
    """Map a 0-100 review score to its color class ("ok"/"warn"/"bad", or "")."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return ""
    if n >= SCORE_OK_MIN:
        return "ok"
    if n >= SCORE_WARN_MIN:
        return "warn"
    return "bad"
