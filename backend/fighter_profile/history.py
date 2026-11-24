"""
Fight-history result semantics (FTR-01B1).

Pure function.  Never maps "not a win" to a loss.

    W        the fighter is the recorded winner
    L        the *opponent* is the recorded winner
    D        the bout is recorded as a draw
    NC       the bout is recorded as a no contest
    UNKNOWN  winner missing, or not attributable to either corner

The database currently contains no draw rows and one No Contest row
(winner == "No Contest"); methods are all NULL until FTR-01B2.
"""

from __future__ import annotations

from typing import Optional

RESULT_W, RESULT_L, RESULT_D, RESULT_NC, RESULT_UNKNOWN = "W", "L", "D", "NC", "UNKNOWN"
RESULT_CODES = (RESULT_W, RESULT_L, RESULT_D, RESULT_NC, RESULT_UNKNOWN)

_DRAW = {"draw", "d", "majority draw", "split draw", "technical draw"}
_NC = {"no contest", "nc", "n/c", "no-contest"}


def classify_result(fighter: str, r_name: str, b_name: str, winner: Optional[str]) -> str:
    w = (winner or "").strip()
    if not w:
        return RESULT_UNKNOWN
    if w.lower() in _DRAW:
        return RESULT_D
    if w.lower() in _NC:
        return RESULT_NC
    if w == fighter:
        return RESULT_W
    opponent = b_name if r_name == fighter else r_name
    if w == opponent:
        return RESULT_L
    return RESULT_UNKNOWN


def summarize(results: list[str]) -> dict:
    return {code: sum(1 for r in results if r == code) for code in RESULT_CODES}
