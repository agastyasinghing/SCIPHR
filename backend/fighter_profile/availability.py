"""
Profile field availability rules (FTR-01B1, corrected in FTR-01B1-R1).

Pure functions: given the raw ``fighters`` display columns, decide for every
profile field whether the value is usable, and why.  No DB access, no model
imports, no dependency on ``intelligence.*``.

Evidence base: docs/FTR-01_SOURCE_RECOVERY.md
  * height / reach / age: NaN in the original CSV, coerced to 0.0 by
    convert_golden_FULL.py:86 (`fillna(0)`).  A stored 0/NULL therefore means
    "missing in the source".                                   (source_nan)
  * The seven career combat stats are scraped, scrape-time values.  181
    fighters have all seven == 0 *in the original file itself*; that pattern
    is a placeholder, not a measurement.                (source_placeholder_zero)
  * Isolated zeros inside an otherwise populated block cannot be classified
    from the data (no attempt counts are stored).  The ONLY isolated zero
    accepted as a measurement is ``sub_avg`` (a plausible "no submission
    attempts" rate).  Zeros in td_avg, td_acc, slpm, str_acc, str_def and
    td_def are ``ambiguous``: the literal 0.0 is returned with a flag and is
    never usable as a score input.                    (ambiguous_source_zero)
  * Career knockdowns are not stored as a career aggregate.     (not_stored)

Invalid values (malformed, non-finite, negative counts, fractional counts,
implausible magnitudes) are NOT source-missing values: they carry basis
``invalid_value`` / ``invalid_range`` and are never ``measured``.
"""

from __future__ import annotations

import math
import numbers
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    MEASURED = "measured"            # usable, non-zero value
    MEASURED_ZERO = "measured_zero"  # a zero accepted as a real measurement (sub_avg only)
    AMBIGUOUS = "ambiguous"          # source zero we cannot classify; not usable as evidence
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
    INVALID_VALUE = "invalid_value"  # malformed or non-finite (NaN/inf/non-numeric)
    INVALID_RANGE = "invalid_range"  # finite number that is impossible for the field
    HEURISTIC = "heuristic"          # used by scores.py


# The seven career combat statistics (fighters table column names).
CORE_BLOCK = ("slpm", "str_acc", "str_def", "td_avg", "td_acc", "td_def", "sub_avg")
PHYSICAL_ZERO_MISSING = ("height_cm", "reach_cm", "age")

_FRACTION_FIELDS = ("str_acc", "str_def", "td_acc", "td_def")

# Sanity bounds: reject only clearly impossible values.  These are NOT
# data-derived limits (observed: age 18-51, height 152-211, reach 147-213).
SANITY_BOUNDS = {
    "age": (16.0, 80.0),
    "height_cm": (100.0, 260.0),
    "reach_cm": (100.0, 260.0),
    "weight_lbs": (70.0, 800.0),
}
_RATE_MAX = 60.0   # slpm / td_avg / sub_avg upper sanity bound (observed max 24.3)

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


def _classify(v: Any) -> tuple[str, Optional[float]]:
    """('null'|'invalid'|'num', float).  Strings, bools, NaN and +/-inf are invalid."""
    if v is None:
        return "null", None
    if isinstance(v, bool) or not isinstance(v, (numbers.Real, Decimal)):
        return "invalid", None
    try:
        f = float(v)
    except (TypeError, ValueError, OverflowError):
        return "invalid", None
    if not math.isfinite(f):
        return "invalid", None
    return "num", f


def _invalid(field: str, kind_or_range: Basis, note: str) -> dict:
    return _field(None, Status.UNAVAILABLE, kind_or_range, field, note)


def is_usable(field: Optional[dict]) -> bool:
    """True when a field may feed a score: measured (incl. accepted zero) and non-null."""
    return bool(field) and field["value"] is not None and field["status"] in (
        Status.MEASURED.value, Status.MEASURED_ZERO.value,
    )


def core_block_placeholder_basis(row: dict) -> Optional[Basis]:
    """
    All seven career stats NULL/zero (and none malformed) => placeholder block.
    Returns the basis, or None when the block is not a placeholder.  A block that
    contains any malformed/non-finite value is never classed as the placeholder
    pattern; its fields are judged individually.
    """
    kinds = [_classify(row.get(k)) for k in CORE_BLOCK]
    if any(k == "invalid" for k, _ in kinds):
        return None
    if all(k == "null" or v == 0 for k, v in kinds):
        if any(k == "num" for k, _ in kinds):
            return Basis.SOURCE_PLACEHOLDER_ZERO
        return Basis.SOURCE_NAN
    return None


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
        kind, v = _classify(row.get(k))
        if kind == "null":
            fields[k] = _invalid(k, Basis.SOURCE_NAN, "Record count is missing in the source.")
        elif kind == "invalid":
            fields[k] = _invalid(k, Basis.INVALID_VALUE, "Malformed or non-finite record count.")
        elif v < 0 or v != int(v):
            fields[k] = _invalid(k, Basis.INVALID_RANGE, "Record counts must be non-negative whole numbers.")
        else:
            fields[k] = _field(
                int(v), Status.MEASURED, Basis.SCRAPED_CAREER_RECORD, k,
                note="Scraped career record; precise scrape date unknown." if k == "wins" else None,
            )

    # ── Physical: stored 0/NULL == missing in the source ─────────────────
    for k in PHYSICAL_ZERO_MISSING:
        kind, v = _classify(row.get(k))
        lo, hi = SANITY_BOUNDS[k]
        if kind == "invalid":
            fields[k] = _invalid(k, Basis.INVALID_VALUE, "Malformed or non-finite value.")
        elif kind == "null" or v == 0:
            note = "Value is missing in the source dataset."
            if k == "age":
                note += " (When present, age is measured at the last recorded bout.)"
            fields[k] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, k, note)
        elif not (lo <= v <= hi):
            fields[k] = _invalid(k, Basis.INVALID_RANGE, f"Outside the plausible range {lo:g}-{hi:g}.")
        else:
            note = "Age at the fighter's last recorded bout, not present-day age." if k == "age" else None
            fields[k] = _field(v, Status.MEASURED, Basis.MEASURED, k, note)

    # weight: 185.0 is also the migration default for missing weights
    kind, w = _classify(row.get("weight_lbs"))
    lo, hi = SANITY_BOUNDS["weight_lbs"]
    if kind == "invalid":
        fields["weight_lbs"] = _invalid("weight_lbs", Basis.INVALID_VALUE, "Malformed or non-finite value.")
    elif kind == "null" or w == 0:
        fields["weight_lbs"] = _field(None, Status.UNAVAILABLE, Basis.SOURCE_NAN, "weight_lbs")
    elif not (lo <= w <= hi):
        fields["weight_lbs"] = _invalid("weight_lbs", Basis.INVALID_RANGE, f"Outside the plausible range {lo:g}-{hi:g}.")
    elif w == 185.0:
        fields["weight_lbs"] = _field(
            w, Status.AMBIGUOUS, Basis.POSSIBLE_DEFAULT, "weight_lbs",
            "185 lbs is also the migration default for a missing weight.",
        )
    else:
        fields["weight_lbs"] = _field(w, Status.MEASURED, Basis.MEASURED, "weight_lbs")

    # ── Career combat block ──────────────────────────────────────────────
    placeholder = core_block_placeholder_basis(row)
    if placeholder is not None:
        for k in CORE_BLOCK:
            fields[k] = _field(
                None, Status.UNAVAILABLE, placeholder, k,
                "All seven career combat stats are zero in the source: placeholder, not a measurement.",
            )
    else:
        cls = {k: _classify(row.get(k)) for k in CORE_BLOCK}
        td_avg_val = cls["td_avg"][1]
        for k in CORE_BLOCK:
            kind, x = cls[k]
            upper = 1.0 if k in _FRACTION_FIELDS else _RATE_MAX
            if kind == "null":
                fields[k] = _invalid(k, Basis.SOURCE_NAN, "Value is missing in the source dataset.")
            elif kind == "invalid":
                fields[k] = _invalid(k, Basis.INVALID_VALUE, "Malformed or non-finite value.")
            elif x < 0 or x > upper:
                fields[k] = _invalid(k, Basis.INVALID_RANGE, f"Outside the possible range 0-{upper:g}.")
            elif x > 0:
                fields[k] = _field(x, Status.MEASURED, Basis.MEASURED, k)
            elif k == "sub_avg":
                # The only isolated zero accepted as a measurement: "no submission attempts".
                fields[k] = _field(0.0, Status.MEASURED_ZERO, Basis.MEASURED, k)
            else:
                note = {
                    "slpm": "Zero striking volume next to populated stats is unconfirmed.",
                    "str_acc": "Zero striking accuracy next to populated stats is unconfirmed.",
                    "str_def": "Zero striking defence is implausible; not used as evidence.",
                    "td_avg": "Zero takedown rate next to populated stats is unconfirmed (attempts are not stored).",
                    "td_def": "Zero takedown defence may be a small-sample extreme; not used as evidence.",
                    "td_acc": ("Zero takedown accuracy is unconfirmed: takedown attempts are not stored."
                               if (td_avg_val or 0) > 0 else
                               "Takedown accuracy of zero with no takedowns: attempts are not stored."),
                }[k]
                fields[k] = _field(0.0, Status.AMBIGUOUS, Basis.AMBIGUOUS_SOURCE_ZERO, k, note)

    # ── Career knockdowns: not stored as a career aggregate ──────────────
    fields["career_knockdowns"] = _field(
        None, Status.NOT_STORED, Basis.NOT_STORED, "career_knockdowns",
        "Only per-bout knockdowns exist in the source; no career total is stored.",
    )
    return fields


def core_block_summary(row: dict, fields: Optional[dict] = None) -> dict:
    """
    Coverage of the seven career stats.

    status: "complete"    every field usable,
            "partial"     some fields usable, others ambiguous/invalid/missing,
            "unavailable" no usable field (e.g. the placeholder pattern).
    ``available`` is True only for "complete": an invalid or unconfirmed field
    means the block must not claim complete measured coverage.
    """
    fields = fields if fields is not None else build_fields(row)
    placeholder = core_block_placeholder_basis(row)
    usable = [k for k in CORE_BLOCK if is_usable(fields[k])]
    unconfirmed = [k for k in CORE_BLOCK if fields[k]["status"] == Status.AMBIGUOUS.value]
    invalid = [k for k in CORE_BLOCK if fields[k]["basis"] in
               (Basis.INVALID_VALUE.value, Basis.INVALID_RANGE.value)]
    if placeholder is not None:
        status, basis = "unavailable", placeholder.value
    elif len(usable) == len(CORE_BLOCK):
        status, basis = "complete", Basis.MEASURED.value
    elif usable:
        status, basis = "partial", "mixed"
    else:
        status, basis = "unavailable", "mixed"
    return {
        "available": status == "complete",
        "status": status,
        "basis": basis,
        "fields": list(CORE_BLOCK),
        "usable_fields": usable,
        "unconfirmed_fields": unconfirmed,
        "invalid_fields": invalid,
    }
