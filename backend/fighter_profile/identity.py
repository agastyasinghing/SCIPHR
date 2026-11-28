"""
Profile identity resolution (FTR-01B1-R4) — ONE resolver for GET /fighter/{name}
and GET /fighter/{name}/history, run BEFORE ``predictor.search_fighter``.

``search_fighter`` is a case-insensitive first-match lookup, so with two stored
fighters "Case Twin" / "CASE TWIN" it hands every request the same fighter.  The
profile routes therefore resolve identity against the ``fighters`` table first:

1. Exact stored-name match (Python string equality; case and internal spaces
   count).  Exactly one exact fighter wins, even if others share its
   normalised name.  A SQL result is never trusted as proof of exactness.
2. Otherwise the whitespace/case-normalised candidates.  Exactly one -> chosen.
   More than one -> ``AmbiguousFighterIdentity`` (HTTP 409 in the route); the
   first is never picked.
3. Otherwise the caller-supplied fuzzy search runs, and its answer is checked
   against the database identity candidates: a fuzzy result whose normalised
   name is shared by several fighters is ambiguous, never a bypass.
4. Nothing resolvable -> ``None`` (the route keeps its 404 behaviour).

SELECT-only.  Database errors propagate: an identity read failure must never
degrade into an unsafe first match.
"""

from __future__ import annotations

from typing import Callable, Optional

from sqlalchemy import text

from . import history as hist
from .attribution import _CANDIDATES_SQL, participant_key

_EXACT_SQL = text("SELECT name FROM fighters WHERE name = :name")


class AmbiguousFighterIdentity(Exception):
    """Several distinct stored fighters match; ``candidates`` are real stored names."""

    code = "AMBIGUOUS_FIGHTER_IDENTITY"

    def __init__(self, candidates: list):
        super().__init__(self.code)
        self.candidates = sorted(candidates)

    def detail(self) -> dict:
        return {"code": self.code, "candidates": list(self.candidates)}


def _candidates(conn, name: str) -> list:
    target = hist.norm_name(name)
    rows = conn.execute(_CANDIDATES_SQL, {"key": participant_key(name)}).fetchall()
    return sorted({n for (n,) in rows if hist.norm_name(n) == target})


def resolve_fighter_identity(
    conn, name: str, fuzzy_search: Optional[Callable[[str], Optional[str]]] = None
) -> Optional[str]:
    """Return the exact stored fighter name, ``None`` if unresolvable, or raise
    ``AmbiguousFighterIdentity``."""
    # 1. exact stored name (verified in Python, not by the SQL collation)
    exact = {n for (n,) in conn.execute(_EXACT_SQL, {"name": name}).fetchall() if n == name}
    if len(exact) == 1:
        return next(iter(exact))

    # 2. normalised candidates
    cands = _candidates(conn, name)
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        raise AmbiguousFighterIdentity(cands)

    # 3. fuzzy search, re-checked against database identity
    if fuzzy_search is None:
        return None
    guess = fuzzy_search(name)
    if not guess:
        return None
    guess_exact = {n for (n,) in conn.execute(_EXACT_SQL, {"name": guess}).fetchall() if n == guess}
    guess_cands = _candidates(conn, guess)
    if len(guess_cands) > 1:
        raise AmbiguousFighterIdentity(guess_cands)       # never bypass a collision
    if len(guess_cands) == 1:
        return guess_cands[0]
    if len(guess_exact) == 1:
        return next(iter(guess_exact))
    return None
