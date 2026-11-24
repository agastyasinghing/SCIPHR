"""
Legacy-profile integrity helpers (FTR-01B1-R2).

The legacy profile path (``get_latest_fighter_stats`` -> main.py formulas)
trusts stored numbers.  This module lets the profile endpoint:

* read raw stats through a **profile-only fallback** when the shared calculator
  raises while coercing a malformed value (``read_legacy_raw_stats``) - the
  shared calculator itself is never modified;
* validate raw inputs and stored scores, and describe exactly what was
  corrupted (``assess_raw_inputs`` / ``assess_stored_scores``);
* report which legacy *derived* scores depended on corrupted inputs
  (``build_legacy_integrity``).

Three kinds of corruption are kept distinct:
  raw_input_corruption     a raw fighter number is malformed/non-finite/impossible
  stored_score_corruption  a stored aura/composite/chaos/mirage value is invalid
  derived_scores_affected  a heuristically computed legacy score used corrupted input

Nothing here writes to the database.  Database/connection errors are NOT
caught: a failing database must surface as a failure, never as fabricated data.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from sqlalchemy import text

from .availability import RATE_MAX, SANITY_BOUNDS

_RAW_SQL = text(
    "SELECT wins, losses, draws, age, height_cm, reach_cm, weight_lbs, "
    "slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg "
    "FROM fighters WHERE name = :name"
)

# column -> legacy raw key (same mapping as GoldenFeatureCalculator.get_latest_fighter_stats)
_COLUMN_TO_RAW = {
    "wins": "fighter_w", "losses": "fighter_l", "draws": "fighter_d", "age": "age",
    "height_cm": "fighter_height_cm", "reach_cm": "fighter_reach_cm",
    "weight_lbs": "fighter_weight_lbs", "slpm": "fighter_SlpM",
    "str_acc": "fighter_Str_Acc", "str_def": "fighter_Str_Def",
    "td_avg": "fighter_TD_Avg", "td_acc": "fighter_TD_Acc",
    "td_def": "fighter_TD_Def", "sub_avg": "fighter_Sub_Avg",
}

_COUNTS = ("fighter_w", "fighter_l", "fighter_d")
_FRACTIONS = ("fighter_Str_Acc", "fighter_Str_Def", "fighter_TD_Acc", "fighter_TD_Def")
_RATES = ("fighter_SlpM", "fighter_TD_Avg", "fighter_Sub_Avg")
_PHYSICAL_BOUNDS = {
    "age": SANITY_BOUNDS["age"],
    "fighter_height_cm": SANITY_BOUNDS["height_cm"],
    "fighter_reach_cm": SANITY_BOUNDS["reach_cm"],
    "fighter_weight_lbs": SANITY_BOUNDS["weight_lbs"],
}

# Legacy derived scores -> the raw inputs their formulas read (main.py).
DERIVED_DEPENDENCIES = {
    "aura_score": ("fighter_w", "fighter_l", "fighter_SlpM", "fighter_TD_Avg"),
    "composite_score": ("fighter_w", "fighter_l", "fighter_Str_Acc", "fighter_Str_Def"),
    "chaos_contribution": ("fighter_SlpM", "fighter_Str_Def"),
    "mirage_meter": ("fighter_w", "fighter_l", "fighter_Str_Def"),
}
STORED_SCORE_FIELDS = tuple(DERIVED_DEPENDENCIES)


def _finite(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError, OverflowError):
        return None
    return f if math.isfinite(f) else None


def read_legacy_raw_stats(engine, name: str) -> tuple[dict, list[str]]:
    """
    Profile-only equivalent of ``get_latest_fighter_stats`` that cannot raise on
    malformed numbers.  Returns (raw, malformed_keys); ``({}, [])`` when the
    fighter row does not exist.  Valid values are coerced exactly as the shared
    calculator does (``float(x or 0)``; weight default 185); a malformed or
    non-finite value becomes ``None`` and its legacy key is reported.

    Only database errors can raise here (and they must propagate).
    """
    with engine.connect() as conn:
        row = conn.execute(_RAW_SQL, {"name": name}).fetchone()
    if row is None:
        return {}, []
    m = row._mapping
    raw: dict = {}
    malformed: list[str] = []
    for col, key in _COLUMN_TO_RAW.items():
        v = m.get(col)
        default = 185.0 if col == "weight_lbs" else 0.0
        if not v:                       # None / 0 / '' -> legacy `x or default`
            raw[key] = default
            continue
        f = _finite(v)
        if f is None:
            raw[key] = None
            malformed.append(key)
        else:
            raw[key] = f
    raw["knockdowns"] = 0.0             # not stored (same hard-coded legacy value)
    return raw, sorted(malformed)


def assess_raw_inputs(raw: dict) -> tuple[dict, list[dict]]:
    """
    Validate finite raw numbers for impossible values (negative/fractional
    counts, out-of-range fractions, rates or physicals).  Returns
    (clean raw with impossible values replaced by None, corruption entries).
    A zero physical is "missing in the source", not corruption.
    """
    clean = dict(raw)
    found: list[dict] = []

    def bad(key, reason="invalid_range"):
        clean[key] = None
        found.append({"field": key, "reason": reason})

    for k in _COUNTS:
        f = _finite(raw.get(k))
        if f is not None and (f < 0 or f != int(f)):
            bad(k)
    for k in _FRACTIONS:
        f = _finite(raw.get(k))
        if f is not None and not 0.0 <= f <= 1.0:
            bad(k)
    for k in _RATES:
        f = _finite(raw.get(k))
        if f is not None and not 0.0 <= f <= RATE_MAX:
            bad(k)
    for k, (lo, hi) in _PHYSICAL_BOUNDS.items():
        f = _finite(raw.get(k))
        if f is not None and f != 0 and not lo <= f <= hi:
            bad(k)
    return clean, sorted(found, key=lambda e: e["field"])


def assess_stored_scores(stored) -> tuple[dict, list[dict]]:
    """
    Validate the stored aura/composite/chaos/mirage columns (0-100, finite).
    Returns ({score: float | None}, corruption entries).  If ANY stored score
    is corrupted, every stored score is ignored (all None) so the legacy
    response falls back to its documented heuristics rather than mixing
    sources; ``scores_source`` then reports "heuristic".
    """
    values: dict = {k: None for k in STORED_SCORE_FIELDS}
    corruption: list[dict] = []
    if stored is None:
        return values, corruption
    for k in STORED_SCORE_FIELDS:
        v = getattr(stored, k, None)
        if v is None:
            continue
        f = _finite(v)
        if f is None:
            corruption.append({"field": k, "reason": "invalid_value"})
        elif not 0.0 <= f <= 100.0:
            corruption.append({"field": k, "reason": "invalid_range"})
        else:
            values[k] = f
    if corruption:
        return {k: None for k in STORED_SCORE_FIELDS}, corruption
    return values, corruption


def build_legacy_integrity(
    malformed_keys: list[str],
    range_corruption: list[dict],
    stored_corruption: list[dict],
    heuristic_scores: set[str],
) -> tuple[dict, set[str]]:
    """
    Assemble the top-level ``legacy_integrity`` object.

    Returns (object, names of legacy scores that must be withheld (null)
    because they were computed from corrupted inputs).
    """
    raw_entries = [{"field": k, "reason": "invalid_value"} for k in malformed_keys] + list(range_corruption)
    raw_entries.sort(key=lambda e: e["field"])
    for e in raw_entries:
        e["legacy_placeholder"] = 185.0 if e["field"] == "fighter_weight_lbs" else 0.0
    corrupted_keys = {e["field"] for e in raw_entries}

    affected = []
    for score, deps in DERIVED_DEPENDENCIES.items():
        if score not in heuristic_scores:
            continue
        hit = [d for d in deps if d in corrupted_keys]
        if hit:
            affected.append({
                "score": score, "depends_on": hit, "legacy_value": None,
                "reason": "derived_from_corrupted_inputs",
            })
    obj = {
        "schema": "legacy_integrity_v1",
        "corrupted": bool(raw_entries or stored_corruption),
        "raw_input_corruption": raw_entries,
        "stored_score_corruption": list(stored_corruption),
        "derived_scores_affected": affected,
        "note": ("Corrupted raw inputs appear in legacy `stats` as the legacy placeholder "
                 "(0, or 185 for weight): a placeholder, not a measurement. Legacy scores "
                 "derived from them are withheld (null). Corrupted stored scores are ignored."),
    }
    return obj, {a["score"] for a in affected}
