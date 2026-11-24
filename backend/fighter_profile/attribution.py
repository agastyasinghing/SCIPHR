"""
Fight attribution policy (FTR-01B1-R3) — ONE policy for GET /fighter/{name}/history
and the profile ``coverage`` calculation.

Problem: two distinct ``fighters`` rows can share a normalised name
("Same Name" / "Same  Name").  Normalised matching alone would hand both
fighters the union of both fighters' bouts.

Policy
------
1. Resolve the candidate identities first: every ``fighters.name`` whose
   normalised form equals the requested name's normalised form.
2. Unique identity (0 or 1 candidate): tolerant matching, as before — bouts
   whose stored corner name equals the request after trim / case / whitespace
   normalisation are attributed.
3. Colliding identity (>1 candidates): a bout is attributed to the requested
   fighter ONLY when the stored corner name equals the requested name exactly.
     * stored name exactly equals ANOTHER candidate  -> belongs to them: excluded
     * stored name matches the key but equals NO candidate exactly (or the
       requested name is not itself an exact candidate) -> cannot be attributed
       reliably: WITHHELD and reported.
   Bouts are never assigned solely because a normalised key matches.
4. Coverage is "verified" only when nothing was withheld (and, for a collision,
   the requested name is an exact candidate).  When nothing could be
   attributed but something was withheld, the result is
   ``ambiguous_unattributable``: callers must not present a zero count as
   verified coverage.

No fuzzy / substring matching; no writes; no new identity system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text

from . import history as hist


def _norm_sql(col: str) -> str:
    """Portable (SQLite + PostgreSQL) name normalisation: trim, lower-case, and
    collapse runs of up to 8 spaces.  Tabs, newlines, NBSP and non-ASCII case
    folding are NOT handled in SQL (documented limitation); candidates are
    re-checked in Python with ``history.norm_name`` (full whitespace + casefold)."""
    return f"LOWER(TRIM(REPLACE(REPLACE(REPLACE({col}, '  ', ' '), '  ', ' '), '  ', ' ')))"


_FIGHTS_SQL = text(
    "SELECT r_name, b_name, date, winner, method, weight_class FROM fights "
    f"WHERE {_norm_sql('r_name')} = :key OR {_norm_sql('b_name')} = :key ORDER BY date DESC"
)
_CANDIDATES_SQL = text(f"SELECT name FROM fighters WHERE {_norm_sql('name')} = :key")


def participant_key(name: str) -> str:
    """SQL-side comparison key: whitespace-collapsed, lower-case (ASCII-safe)."""
    return " ".join((name or "").split()).lower()


@dataclass
class Attribution:
    rows: list                                   # bouts safely attributed (newest first)
    status: str                                  # unique | collision_resolved | collision_partial | ambiguous_unattributable
    candidates: list = field(default_factory=list)
    requested_exact: bool = False
    withheld_ambiguous: int = 0
    excluded_other_identity: int = 0
    stored_spellings: list = field(default_factory=list)

    @property
    def collision(self) -> bool:
        return len(self.candidates) > 1

    @property
    def exact_mode(self) -> bool:
        """Winner/opponent resolution must use exact names (not normalised) in a collision."""
        return self.collision

    @property
    def coverage_verified(self) -> bool:
        if self.withheld_ambiguous:
            return False
        return (not self.collision) or self.requested_exact

    def identity_meta(self) -> dict:
        return {
            "stored_spellings": self.stored_spellings,
            "fighter_rows_matching_name": len(self.candidates),
            "ambiguous_identity": self.collision,
            "status": self.status,
            "candidates": list(self.candidates) if self.collision else [],
            "requested_exact_match": self.requested_exact,
            "withheld_ambiguous_bouts": self.withheld_ambiguous,
            "excluded_other_identity_bouts": self.excluded_other_identity,
            "coverage_verified": self.coverage_verified,
        }


def attribute_fights(conn, name: str) -> Attribution:
    """SELECT-only.  See module docstring for the policy."""
    target = hist.norm_name(name)
    key = participant_key(name)
    candidates = sorted({n for (n,) in conn.execute(_CANDIDATES_SQL, {"key": key}).fetchall()
                         if hist.norm_name(n) == target})
    candidate_set = set(candidates)
    matched = [r for r in conn.execute(_FIGHTS_SQL, {"key": key}).fetchall()
               if hist.norm_name(r.r_name) == target or hist.norm_name(r.b_name) == target]

    def spelled(rows):
        return sorted({c for r in rows for c in (r.r_name, r.b_name) if hist.norm_name(c) == target})

    if len(candidates) <= 1:
        return Attribution(rows=matched, status="unique", candidates=candidates,
                           requested_exact=name in candidate_set, stored_spellings=spelled(matched))

    requested_exact = name in candidate_set
    others = candidate_set - {name}
    mine, withheld, excluded = [], [], []
    for r in matched:
        corners = [c for c in (r.r_name, r.b_name) if hist.norm_name(c) == target]
        if requested_exact and name in corners:
            mine.append(r)
        elif requested_exact and all(c in others for c in corners):
            excluded.append(r)                   # clearly belongs to a different candidate
        else:
            withheld.append(r)                   # matches the key, belongs to no one reliably
    if not withheld:
        status = "collision_resolved"
    elif mine:
        status = "collision_partial"
    else:
        status = "ambiguous_unattributable"
    return Attribution(
        rows=mine, status=status, candidates=candidates, requested_exact=requested_exact,
        withheld_ambiguous=len(withheld), excluded_other_identity=len(excluded),
        stored_spellings=spelled(mine + withheld),
    )
