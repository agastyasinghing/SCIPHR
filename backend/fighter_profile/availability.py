"""
Profile field availability rules (FTR-01B1).

Pure functions: given the raw ``fighters`` display columns, decide for every
profile field whether the value is usable, and why.  No DB access, no model
imports, no dependency on ``intelligence.*``.

Evidence base: docs/FTR-01_SOURCE_RECOVERY.md
  * height / reach / age: NaN in the original CSV, coerced to 0.0 by
    convert_golden_FULL.py:86 (`fillna(0)`).  A stored 0 therefore means
    "missing in the source".                                   (source_nan)
  * The seven career combat stats are scraped, scrape-time values.  181
    fighters have all seven == 0 *in the original file itself*; that pattern
    is a placeholder, not a measurement.                (source_placeholder_zero)
  * Isolated zeros inside an otherwise populated block cannot be classified
    from the data (no attempt counts are stored).  Offensive-rate zeros
    (td_avg, sub_avg) are plausible measurements; zeros in accuracy and
    defence fields are ambiguous.                      (ambiguous_source_zero)
  * Career knockdowns are not stored as a career aggregate.     (not_stored)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    MEASURED = "measured"            # usable, non-zero (or non-zero-capable) value
    MEASURED_ZERO = "measured_zero"  # a zero that is accepted as a real measurement
    AMBIGUOUS = "ambiguous"          # source zero we cannot classify; not strong evidence
    UNAVAILABLE = "unavailable"      # value must not be shown or used
    NOT_STORED = "not_stored"        # the quantity is not in the database at all


class Basis(str, Enum):
    MEASURED = "measured"
    SOURCE_NAN = "source_nan"
    SOURCE_PLACEHOLDER_ZERO = "source_placeholder_zero"
    AMBIGUOUS_SOURCE_ZERO = "ambiguous_source_zero"
    NOT_STORED = "not_stored"
    SCRAPED_CAREER_RECORD = "scraped_career_record"
    POSSIBLE_DEFAULT = "possible_default"
    INVALID_RANGE = "invalid_range"
    HEURISTIC = "heuristic"          # used by scores.py


# The seven career combat statistics (fighters table column names).
CORE_BLOCK = ("slpm", "str_acc", "str_def", "td_avg", "td_acc", "td_def", "sub_avg")
PHYSICAL_ZERO_MISSING = ("height_cm", "reach_cm", "age")

_FRACTION_FIELDS = ("str_acc", "str_def", "td_acc", "td_def")

UNITS = {
    "wins": "count", "losses": "count", "draws": "count",
    "age": "years_at_last_recorded_bout",
    "height_cm": "cm", "reach_cm": "cm", "weight_lbs": "lbs",
    "slpm": "strikes_per_minute",
    "str_acc": "fraction_0_1", "str_def": "fraction_0_1",
    "td_avg": "takedowns_per_15_min", "td_acc": "fraction_0_1",
    "td_def": "fraction_0_1", "sub_avg": "submission_attempts_per_15_min",
    "career_knockdowns": "count",
}


def _field(value: Optional[float], status: Status, basis: Basis, field: str,
           note: Optional[str] = None) -> dict:
    out = {
        "value": value,
        "status": status.value,
        "basis": basis.value,
        "unit": UNITS.get(field),
    }
    if note:
        out["note"] = note
    return out


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def is_usable(field: Optional[dict]) -> bool:
    """True when a field may feed a score: measured (incl. accepted zero) and non-null."""
    return bool(field) and field["value"] is not None and field["status"] in (
        Status.MEASURED.value, Status.MEASURED_ZERO.value,
    )


def core_block_unavailable(row: dict) -> tuple[bool, Optional[Basis]]:
    """
    All seven career combat stats zero/NULL => the block is a source placeholder.

    Returns (is_unavailable, basis).  ``source_placeholder_zero`` when any value
    is a literal zero (the pattern verified on 181 fighters in the original
    CSV), ``source_nan`` if every value is NULL (future repaired data).
    """
    vals = [_num(row.get(k)) for k in CORE_BLOCK]
    if all(v is None or v == 0 for v in vals):
        if any(v == 0 for v in vals):
            return True, Basis.SOURCE_PLACEHOLDER_ZERO
        return True, Basis.SOURCE_NAN
    return False, None


def build_fields(row: dict) -> dict:
    """
    Build ``data_quality.fields`` for one fighter.

    ``row`` holds the ``fighters`` display columns:
    wins, losses, draws, age, height_cm, reach_cm, weight_lbs,
    slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg.
    """
    fields: dict[str, dict] = {}

    # ── Record (scraped career record; scrape date unknown) ──────────────
    for k in ("wins", "losses", "draws"):
        v = _num(row.get(k))
        if v is None:
            fields[k] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, k)
        else:
            fields[k] = _field(
                int(v), Status.MEASURED, Basis.SCRAPED_CAREER_RECORD, k,
                note="Scraped career record; precise scrape date unknown." if k == "wins" else None,
            )

    # ── Physical: stored 0 == missing in the source ──────────────────────
    for k in PHYSICAL_ZERO_MISSING:
        v = _num(row.get(k))
        if v is None or v == 0:
            note = "Value is missing in the source dataset."
            if k == "age":
                note += " (When present, age is measured at the last recorded bout.)"
            fields[k] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, k, note)
        elif v < 0:
            fields[k] = _field(None, Status.UNAVAILABLE, Basis.INVALID_RANGE, k)
        else:
            note = "Age at the fighter's last recorded bout, not present-day age." if k == "age" else None
            fields[k] = _field(v, Status.MEASURED, Basis.MEASURED, k, note)

    # weight: 185.0 is also the migration default for missing weights
    w = _num(row.get("weight_lbs"))
    if w is None or w <= 0:
        fields["weight_lbs"] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, "weight_lbs")
    elif w == 185.0:
        fields["weight_lbs"] = _field(
            w, Status.AMBIGUOUS, Basis.POSSIBLE_DEFAULT, "weight_lbs",
            "185 lbs is also the migration default for a missing weight.",
        )
    else:
        fields["weight_lbs"] = _field(w, Status.MEASURED, Basis.MEASURED, "weight_lbs")

    # ── Career combat block ──────────────────────────────────────────────
    block_missing, block_basis = core_block_unavailable(row)
    if block_missing:
        for k in CORE_BLOCK:
            fields[k] = _field(
                None, Status.UNAVAILABLE, block_basis, k,
                "All seven career combat stats are zero in the source: placeholder, not a measurement.",
            )
    else:
        v = {k: _num(row.get(k)) for k in CORE_BLOCK}
        for k in CORE_BLOCK:
            x = v[k]
            if x is None:
                fields[k] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, k)
            elif x < 0 or (k in _FRACTION_FIELDS and x > 1):
                fields[k] = _field(None, Status.UNAVAILABLE, Basis.INVALID_RANGE, k)
            elif x > 0:
                fields[k] = _field(x, Status.MEASURED, Basis.MEASURED, k)
            elif k in ("td_avg", "sub_avg"):
                # A rate of zero is a plausible measurement (e.g. a fighter who never shoots).
                fields[k] = _field(0.0, Status.MEASURED_ZERO, Basis.MEASURED, k)
            elif k == "td_acc" and (v["td_avg"] or 0) > 0:
                fields[k] = _field(0.0, Status.MEASURED_ZERO, Basis.MEASURED, k)
            else:
                # slpm, str_acc, str_def, td_def, and td_acc when td_avg == 0:
                # cannot be classified without attempt counts.
                note = {
                    "slpm": "Zero striking volume next to populated stats is unconfirmed.",
                    "str_acc": "Zero striking accuracy next to populated stats is unconfirmed.",
                    "str_def": "Zero striking defence is implausible; not used as evidence.",
                    "td_def": "Zero takedown defence may be a small-sample extreme; not used as evidence.",
                    "td_acc": "Takedown accuracy of zero with no takedowns: attempts are not stored.",
                }[k]
                fields[k] = _field(0.0, Status.AMBIGUOUS, Basis.AMBIGUOUS_SOURCE_ZERO, k, note)

    # ── Career knockdowns: not stored as a career aggregate ──────────────
    fields["career_knockdowns"] = _field(
        None, Status.NOT_STORED, Basis.NOT_STORED, "career_knockdowns",
        "Only per-bout knockdowns exist in the source; no career total is stored.",
    )
    return fields


def core_block_summary(row: dict) -> dict:
    missing, basis = core_block_unavailable(row)
    return {
        "available": not missing,
        "basis": basis.value if basis else Basis.MEASURED.value,
        "fields": list(CORE_BLOCK),
    }
