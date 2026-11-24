"""
Fight-history result semantics (FTR-01B1, corrected in FTR-01B1-R1).

Pure function.  Never maps "not a win" to a loss.  Names are compared after
whitespace/case normalisation; display names are never altered.

    W        the fighter is the recorded winner
    L        the *opponent* is the recorded winner
    D        the bout is recorded as a draw
    NC       the bout is recorded as a no contest
    UNKNOWN  winner missing, not attributable to either corner, or the
             fighter does not match either corner

The database currently contains no draw rows and one No Contest row
(winner == "No Contest"); methods are all NULL until FTR-01B2.
"""

from __future__ import annotations

from typing import Optional

RESULT_W, RESULT_L, RESULT_D, RESULT_NC, RESULT_UNKNOWN = "W", "L", "D", "NC", "UNKNOWN"
RESULT_CODES = (RESULT_W, RESULT_L, RESULT_D, RESULT_NC, RESULT_UNKNOWN)

_DRAW = {"draw", "d", "majority draw", "split draw", "technical draw"}
_NC = {"no contest", "nc", "n/c", "no-contest"}


def norm_name(s: Optional[str]) -> str:
    """Collapse internal whitespace, strip, casefold.  For comparison only."""
    return " ".join((s or "").split()).casefold()


def classify_result(fighter: str, r_name: str, b_name: str, winner: Optional[str]) -> str:
    w = norm_name(winner)
    if not w:
        return RESULT_UNKNOWN
    if w in _DRAW:
        return RESULT_D
    if w in _NC:
        return RESULT_NC
    f, r, b = norm_name(fighter), norm_name(r_name), norm_name(b_name)
    if f == r:
        opponent = b
    elif f == b:
        opponent = r
    else:
        return RESULT_UNKNOWN
    if w == f:
        return RESULT_W
    if w == opponent:
        return RESULT_L
    return RESULT_UNKNOWN


def summarize(results: list[str]) -> dict:
    return {code: sum(1 for r in results if r == code) for code in RESULT_CODES}
