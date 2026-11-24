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
_FIGHTER_NAME_COUNT_SQL = text(
    f"SELECT COUNT(*) FROM fighters WHERE {_norm_sql('name')} = :key"
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


def participant_key(name: str) -> str:
    """SQL-side comparison key: whitespace-collapsed, lower-case (ASCII-safe)."""
    return " ".join((name or "").split()).lower()


def fetch_fight_rows(conn, name: str, limit: Optional[int] = None) -> list:
    """
    Fights in which ``name`` took part, newest first.

    SQL narrows candidates with a portable normalised equality (never LIKE /
    substring / fuzzy matching); Python then confirms with the full
    ``norm_name`` comparison.  Original stored names are preserved in the rows.
    """
    target = hist.norm_name(name)
    rows = [r for r in conn.execute(_FIGHTS_SQL, {"key": participant_key(name)}).fetchall()
            if hist.norm_name(r.r_name) == target or hist.norm_name(r.b_name) == target]
    return rows[:limit] if limit else rows


def participant_identity(conn, name: str, rows: list) -> dict:
    """How the name matched: stored spellings, and whether the key is ambiguous."""
    target = hist.norm_name(name)
    spellings = sorted({n for r in rows for n in (r.r_name, r.b_name)
                        if hist.norm_name(n) == target})
    matching = conn.execute(_FIGHTER_NAME_COUNT_SQL, {"key": participant_key(name)}).scalar() or 0
    return {
        "stored_spellings": spellings,
        "fighter_rows_matching_name": int(matching),
        "ambiguous_identity": int(matching) > 1,
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
        fights = fetch_fight_rows(conn, name)
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


def build_history(fighter_name: str, rows, identity: Optional[dict] = None) -> dict:
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
    out = {
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
    if identity is not None:
        out["name_match"] = identity
    return out


# ── Extension validation + guard ────────────────────────────────────────────
class ExtensionValidationError(ValueError):
    """The extension payload violates the documented contract (=> INVALID_SHAPE).
    Distinct from any exception raised by the builder itself (=> ERROR)."""


_REQUIRED_FIELDS = (
    "wins", "losses", "draws", "age", "height_cm", "reach_cm", "weight_lbs", "slpm", "str_acc",
    "str_def", "td_avg", "td_acc", "td_def", "sub_avg", "career_knockdowns",
)
_STATUSES = {s_.value for s_ in availability.Status}
_BASES = {b_.value for b_ in availability.Basis}
_SCORE_NAMES = ("composite", "aura", "chaos_contribution", "mirage")
_SCORE_STATUSES = {"provisional", "unavailable"}
_BLOCK_STATUSES = {"complete", "partial", "unavailable"}
_COVERAGE_KEYS = (
    "ufc_fights_in_dataset", "first_dataset_fight", "last_dataset_fight", "snapshot_date",
    "dataset_end", "methods_available_fraction", "record_scope", "record_as_of",
)


def _bad(msg: str):
    raise ExtensionValidationError(msg)


def _is_num(v) -> bool:
    import math
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _no_nonfinite(obj, path="ext"):
    import math
    if isinstance(obj, dict):
        for k, v in obj.items():
            _no_nonfinite(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _no_nonfinite(v, f"{path}[{i}]")
    elif isinstance(obj, float) and not math.isfinite(obj):
        _bad(f"non-finite number at {path}")


def validate_extension(ext) -> None:
    """
    Validate the documented ``data_quality`` / ``scores`` contract.  Bounded:
    required keys, enum values, types, and value/availability consistency.
    Raises ExtensionValidationError.
    """
    if not isinstance(ext, dict):
        _bad("extension is not an object")
    _no_nonfinite(ext)
    dq, sc = ext.get("data_quality"), ext.get("scores")

    # data_quality
    if not isinstance(dq, dict):
        _bad("data_quality missing")
    for k in ("schema", "fields", "core_stat_block", "coverage", "legacy_compat"):
        if k not in dq:
            _bad(f"data_quality.{k} missing")
    if not isinstance(dq["schema"], str) or not isinstance(dq["legacy_compat"], dict):
        _bad("data_quality.schema/legacy_compat malformed")
    fields = dq["fields"]
    if not isinstance(fields, dict):
        _bad("data_quality.fields malformed")
    for name in _REQUIRED_FIELDS:
        f = fields.get(name)
        if not isinstance(f, dict) or any(k not in f for k in ("value", "status", "basis", "unit")):
            _bad(f"data_quality.fields.{name} malformed")
        if f["status"] not in _STATUSES or f["basis"] not in _BASES:
            _bad(f"data_quality.fields.{name} has unknown status/basis")
        v, usable = f["value"], f["status"] in ("measured", "measured_zero")
        if usable and not _is_num(v):
            _bad(f"data_quality.fields.{name} is {f['status']} without a finite value")
        if f["status"] in ("unavailable", "not_stored") and v is not None:
            _bad(f"data_quality.fields.{name} is {f['status']} but has a value")
        if f["status"] == "ambiguous" and v is not None and not _is_num(v):
            _bad(f"data_quality.fields.{name} ambiguous value not finite")
    blk = dq["core_stat_block"]
    if (not isinstance(blk, dict) or blk.get("status") not in _BLOCK_STATUSES
            or not isinstance(blk.get("available"), bool)
            or blk["available"] != (blk["status"] == "complete")
            or not isinstance(blk.get("usable_fields"), list)
            or not isinstance(blk.get("unconfirmed_fields"), list)
            or not isinstance(blk.get("invalid_fields"), list)):
        _bad("data_quality.core_stat_block malformed")
    cov = dq["coverage"]
    if not isinstance(cov, dict) or any(k not in cov for k in _COVERAGE_KEYS):
        _bad("data_quality.coverage malformed")
    n = cov["ufc_fights_in_dataset"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        _bad("data_quality.coverage.ufc_fights_in_dataset invalid")
    frac = cov["methods_available_fraction"]
    if frac is not None and not (_is_num(frac) and 0.0 <= frac <= 1.0):
        _bad("data_quality.coverage.methods_available_fraction invalid")
    for k in ("first_dataset_fight", "last_dataset_fight", "snapshot_date", "dataset_end"):
        if cov[k] is not None and not isinstance(cov[k], str):
            _bad(f"data_quality.coverage.{k} invalid")

    # scores
    if not isinstance(sc, dict) or not isinstance(sc.get("meta"), dict):
        _bad("scores.meta missing")
    for name in _SCORE_NAMES:
        o = sc.get(name)
        if not isinstance(o, dict) or any(k not in o for k in ("value", "available", "status", "reason")):
            _bad(f"scores.{name} malformed")
        if not isinstance(o["available"], bool) or o["status"] not in _SCORE_STATUSES:
            _bad(f"scores.{name}.available/status invalid")
        if o["available"]:
            if not _is_num(o["value"]) or not 0.0 <= o["value"] <= 100.0:
                _bad(f"scores.{name} is available without a finite 0-100 value")
            if o["status"] != "provisional":
                _bad(f"scores.{name} available but status != provisional")
        else:
            if o["value"] is not None:
                _bad(f"scores.{name} is unavailable but has a value")
            if o["status"] != "unavailable" or not isinstance(o["reason"], str) or not o["reason"]:
                _bad(f"scores.{name} unavailable without status/reason")


def guard_extension(builder, engine, name: str, logger) -> dict:
    """
    Run ``builder(engine, name)`` and validate its payload; never raises.

    Returns {"data_quality", "scores", "extension_status"}.  Failures give null
    objects and ``extension_status.reason``:
        NOT_FOUND      the builder reported no such fighter row
        INVALID_SHAPE  the payload violated the contract (validator rejected it)
        ERROR          the builder (or engine access) raised, including ValueError
    Legacy scores are never substituted.  Logs carry the fighter name and the
    exception *type* only (no message, no traceback, no connection string).
    """
    try:
        if engine is None:
            raise LookupError("no database engine")
        ext = builder(engine, name)
    except Exception as exc:  # noqa: BLE001 - builder failure => ERROR (legacy response still served)
        logger.warning("profile_extension_failed fighter=%r error=%s", name, type(exc).__name__)
        return {"data_quality": None, "scores": None,
                "extension_status": {"available": False, "reason": "ERROR"}}
    if ext is None:
        logger.warning("profile_extension_not_found fighter=%r", name)
        return {"data_quality": None, "scores": None,
                "extension_status": {"available": False, "reason": "NOT_FOUND"}}
    try:
        validate_extension(ext)
    except ExtensionValidationError as exc:
        logger.warning("profile_extension_invalid_shape fighter=%r detail=%s", name, str(exc)[:120])
        return {"data_quality": None, "scores": None,
                "extension_status": {"available": False, "reason": "INVALID_SHAPE"}}
    return {"data_quality": ext["data_quality"], "scores": ext["scores"],
            "extension_status": {"available": True, "reason": None}}
