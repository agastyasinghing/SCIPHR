"""
Response-boundary sanitisation for GET /fighter/{name} (FTR-01B1-R1).

Legacy code paths (``get_latest_fighter_stats`` -> main.py profile formulas)
cast database values with ``float(x or 0)`` and cannot be changed here.  A
non-finite stored value (NaN / +-inf) then reaches the JSON encoder, which
rejects it (HTTP 500).  Two small, boundary-only helpers:

* ``sanitize_raw_stats`` - before the legacy formulas run: a non-finite or
  non-numeric value is replaced by ``None`` so the legacy code treats it as
  its existing missing-value placeholder (legacy ``None or 0`` -> 0).  This
  is exceptional legacy behaviour for corrupted fields ONLY: the legacy 0 is
  not a measurement, and ``data_quality.fields[*]`` (read independently from
  the database) marks the field ``invalid_value``.  Valid values pass through
  untouched (same object, same type).
* ``json_safe`` - after the response is built: any remaining non-finite float
  becomes ``null``.  Valid values and types are unchanged.

Neither helper writes anything, and neither touches the predictor.
"""

from __future__ import annotations

import math
import numbers
from typing import Any


def _is_finite_number(v: Any) -> bool:
    if isinstance(v, bool):
        return False
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError, OverflowError):
        return False


def sanitize_raw_stats(raw: dict) -> tuple[dict, list[str]]:
    """Return (clean copy, sorted list of corrupted keys).  None stays None."""
    clean: dict = {}
    corrupted: list[str] = []
    for k, v in raw.items():
        if v is None or _is_finite_number(v):
            clean[k] = v
        else:
            clean[k] = None
            corrupted.append(k)
    return clean, sorted(corrupted)


def json_safe(obj: Any) -> Any:
    """Recursively replace non-finite floats with None; everything else is returned as-is."""
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, numbers.Real) and not isinstance(obj, int):
        return obj if math.isfinite(float(obj)) else None
    return obj
