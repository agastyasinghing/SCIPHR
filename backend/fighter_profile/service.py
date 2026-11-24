"""
Read-only profile read-model (FTR-01B1).

``read_profile_inputs`` issues SELECT statements only against ``fighters`` and
``fights`` (display columns + fight metadata).  It never reads
``latest_features``, never imports the predictor / feature calculator /
XGBoost, and never touches ``backend/intelligence``.

``build_profile_extension`` returns the additive ``data_quality`` and
``scores`` objects for GET /fighter/{name}.
"""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from sqlalchemy import text

from . import availability, history as hist, scores as scores_mod

HISTORY_LIMIT = 20  # must match the LIMIT in main.get_fighter_history

DATA_QUALITY_SCHEMA = "fighter_profile_quality_v1"

_FIGHTER_SQL = text(
    "SELECT name, wins, losses, draws, age, height_cm, reach_cm, weight_lbs, "
    "slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg, last_fight_date "
    "FROM fighters WHERE name = :name"
)
_FIGHTS_SQL = text(
    "SELECT r_name, b_name, date, winner, method FROM fights "
    "WHERE r_name = :name OR b_name = :name ORDER BY date DESC"
)
_DATASET_END_SQL = text("SELECT MAX(date) FROM fights")

# Documented compatibility problems in the legacy `intelligence` object,
# which this ticket intentionally leaves unchanged.
LEGACY_COMPAT = {
    "intelligence.composite_score": "Known incorrect: saturates at 100 for nearly every fighter (extra x100). Use scores.composite.",
    "intelligence.chaos_contribution": "Known incorrect: missing striking defence is counted as 'no defence'. Use scores.chaos_contribution.",
    "intelligence.mirage_meter": "Known incorrect: missing striking defence can trigger a Mirage value. scores.mirage is intentionally withheld (UNVALIDATED_HEURISTIC).",
    "intelligence.aura_score": "Legacy win rate ignores draws; not a public-sentiment measure. Use scores.aura.",
    "intelligence.style": "Defaults to 'STRIKER' when data is missing. Style profiling is out of scope here (FTR-01B3).",
    "intelligence.is_active": "Constant true in the database; not an activity measure.",
    "legacy.corrupt_values": "Non-finite/malformed legacy numeric inputs are coerced to the legacy placeholder 0 (not a measurement); any remaining non-finite output becomes null. See legacy_corrupted_fields and fields[*].basis = invalid_value.",
    "stats": "Legacy zeros are not availability-aware (0 may mean missing); total_knockdowns is always 0. Use data_quality.fields.",
}


def _to_date(v) -> Optional[_dt.date]:
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    try:
        return _dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _iso(d: Optional[_dt.date]) -> Optional[str]:
    return d.isoformat() if d else None


def read_profile_inputs(engine, name: str) -> Optional[dict]:
    """SELECT-only read of one fighter's display columns and fight metadata."""
    with engine.connect() as conn:
        row = conn.execute(_FIGHTER_SQL, {"name": name}).fetchone()
        if row is None:
            return None
        fights = conn.execute(_FIGHTS_SQL, {"name": name}).fetchall()
        dataset_end = conn.execute(_DATASET_END_SQL).scalar()
    return {
        "row": dict(row._mapping),
        "fights": [dict(f._mapping) for f in fights],
        "dataset_end": _to_date(dataset_end),
    }


def build_coverage(name: str, inputs: dict) -> dict:
    fights = inputs["fights"]
    dates = sorted(d for d in (_to_date(f["date"]) for f in fights) if d)
    with_method = sum(1 for f in fights if (f.get("method") or "").strip())
    return {
        "ufc_fights_in_dataset": len(fights),
        "first_dataset_fight": _iso(dates[0]) if dates else None,
        "last_dataset_fight": _iso(dates[-1]) if dates else None,
        "snapshot_date": _iso(_to_date(inputs["row"].get("last_fight_date"))),
        "dataset_end": _iso(inputs["dataset_end"]),
        "methods_available_fraction": (with_method / len(fights)) if fights else None,
        "record_scope": "scraped_career_record",
        "record_as_of": None,
        "record_note": ("Career record as scraped; the exact scrape date is unknown. "
                        "It is not verified to include or exclude the most recent bout."),
        "stats_basis": "scraped_current_career",
        "age_basis": "age_at_last_recorded_bout",
    }


def build_profile_extension(engine, name: str) -> Optional[dict]:
    """
    Returns {"data_quality": {...}, "scores": {...}} or None when the fighter
    row cannot be found.  Raises on DB errors (caller decides how to degrade).
    """
    inputs = read_profile_inputs(engine, name)
    if inputs is None:
        return None
    fields = availability.build_fields(inputs["row"])
    data_quality = {
        "schema": DATA_QUALITY_SCHEMA,
        "fields": fields,
        "core_stat_block": availability.core_block_summary(inputs["row"], fields),
        "coverage": build_coverage(name, inputs),
        "legacy_compat": LEGACY_COMPAT,
    }
    return {"data_quality": data_quality, "scores": scores_mod.build_scores(fields)}


def build_history(fighter_name: str, rows) -> dict:
    """
    Fight history rows -> additive history payload.  ``rows`` need r_name,
    b_name, date, winner, method, weight_class.  Never infers a method.
    ``result_counts`` and ``methods_available_fraction`` describe the rows
    returned (the latest HISTORY_LIMIT bouts), not necessarily the whole career.
    """
    history, codes = [], []
    for row in rows:
        r_name, b_name = row.r_name, row.b_name
        result = hist.classify_result(fighter_name, r_name, b_name, row.winner)
        codes.append(result)
        method = (row.method or "").strip()      # whitespace-only -> ""
        is_red = hist.norm_name(r_name) == hist.norm_name(fighter_name)
        history.append({
            "opponent": b_name if is_red else r_name,
            "date": str(row.date),
            "result": result,
            "method": method,
            "method_available": bool(method),
            "weight_class": row.weight_class or "",
        })
    with_method = sum(1 for h in history if h["method_available"])
    return {
        "fights": history,
        "result_counts": hist.summarize(codes),
        "methods_available_fraction": (with_method / len(history)) if history else None,
        "history_scope": {
            "window": f"latest_{HISTORY_LIMIT}_fights",
            "rows_returned": len(history),
            "may_be_truncated": len(history) >= HISTORY_LIMIT,
            "applies_to": ["result_counts", "methods_available_fraction"],
        },
        "history_note": "Methods are unavailable until the source repair (FTR-01B2); empty means unknown, not decision.",
    }


# ── Extension guard ─────────────────────────────────────────────────────────
_REQUIRED_DQ = ("schema", "fields", "core_stat_block", "coverage", "legacy_compat")
_REQUIRED_SCORES = ("meta", "composite", "aura", "chaos_contribution", "mirage")


def validate_extension(ext) -> None:
    """Raise ValueError unless ext has the complete data_quality/scores shape."""
    if not isinstance(ext, dict):
        raise ValueError("extension is not an object")
    dq, sc = ext.get("data_quality"), ext.get("scores")
    if not isinstance(dq, dict) or any(k not in dq for k in _REQUIRED_DQ):
        raise ValueError("data_quality incomplete")
    if not isinstance(dq["fields"], dict) or "slpm" not in dq["fields"]:
        raise ValueError("data_quality.fields incomplete")
    if not isinstance(sc, dict) or any(k not in sc for k in _REQUIRED_SCORES):
        raise ValueError("scores incomplete")
    for k in _REQUIRED_SCORES[1:]:
        if not isinstance(sc[k], dict) or "available" not in sc[k] or "value" not in sc[k]:
            raise ValueError(f"scores.{k} incomplete")


def guard_extension(builder, engine, name: str, logger) -> dict:
    """
    Run ``builder(engine, name)`` and validate its shape; never raises.

    Returns {"data_quality", "scores", "extension_status"}.  On any failure the
    objects are null and ``extension_status`` says why (NOT_FOUND | ERROR |
    INVALID_SHAPE).  Legacy scores are never substituted.  Logs carry the
    fighter name and the exception *type* only (no message, no traceback, no DSN).
    """
    try:
        if engine is None:
            raise LookupError("no database engine")
        ext = builder(engine, name)
        if ext is None:
            logger.warning("profile_extension_not_found fighter=%r", name)
            return {"data_quality": None, "scores": None,
                    "extension_status": {"available": False, "reason": "NOT_FOUND"}}
        validate_extension(ext)
        return {"data_quality": ext["data_quality"], "scores": ext["scores"],
                "extension_status": {"available": True, "reason": None}}
    except ValueError as exc:
        logger.warning("profile_extension_invalid_shape fighter=%r error=%s", name, type(exc).__name__)
        return {"data_quality": None, "scores": None,
                "extension_status": {"available": False, "reason": "INVALID_SHAPE"}}
    except Exception as exc:  # noqa: BLE001 - degrade, never fail the legacy response
        logger.warning("profile_extension_failed fighter=%r error=%s", name, type(exc).__name__)
        return {"data_quality": None, "scores": None,
                "extension_status": {"available": False, "reason": "ERROR"}}
