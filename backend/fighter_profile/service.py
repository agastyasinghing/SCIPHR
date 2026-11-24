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
from .attribution import Attribution, attribute_fights, participant_key, _FIGHTS_SQL  # noqa: F401

HISTORY_LIMIT = 20  # must match the LIMIT in main.get_fighter_history

DATA_QUALITY_SCHEMA = "fighter_profile_quality_v1"

_FIGHTER_SQL = text(
    "SELECT name, wins, losses, draws, age, height_cm, reach_cm, weight_lbs, "
    "slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg, last_fight_date "
    "FROM fighters WHERE name = :name"
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


def fetch_fight_rows(conn, name: str, limit: Optional[int] = None) -> list:
    """Bouts safely attributed to ``name`` (see attribution.py), newest first."""
    rows = attribute_fights(conn, name).rows
    return rows[:limit] if limit else rows


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
        attribution = attribute_fights(conn, name)
        dataset_end = conn.execute(_DATASET_END_SQL).scalar()
    return {
        "row": dict(row._mapping),
        "fights": [dict(f._mapping) for f in attribution.rows],
        "attribution": attribution,
        "dataset_end": _to_date(dataset_end),
    }


def build_coverage(name: str, inputs: dict) -> dict:
    fights = inputs["fights"]
    att = inputs.get("attribution")
    unattributable = att is not None and att.status == "ambiguous_unattributable"
    dates = sorted(d for d in (_to_date(f["date"]) for f in fights) if d)
    with_method = sum(1 for f in fights if (f.get("method") or "").strip())
    return {
        # None (never 0) when bouts exist but none can be attributed reliably.
        "ufc_fights_in_dataset": None if unattributable else len(fights),
        "coverage_verified": True if att is None else att.coverage_verified,
        "identity_status": "unique" if att is None else att.status,
        "withheld_ambiguous_bouts": 0 if att is None else att.withheld_ambiguous,
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


def build_history(fighter_name: str, rows, attribution: Optional[Attribution] = None) -> dict:
    """
    Fight history rows -> additive history payload.  ``rows`` need r_name,
    b_name, date, winner, method, weight_class.  Never infers a method.
    ``result_counts`` and ``methods_available_fraction`` describe the rows
    returned (the latest HISTORY_LIMIT bouts), not necessarily the whole career.
    """
    history, codes = [], []
    exact = bool(attribution and attribution.exact_mode)
    classify = hist.classify_result_exact if exact else hist.classify_result
    for row in rows:
        r_name, b_name = row.r_name, row.b_name
        result = classify(fighter_name, r_name, b_name, row.winner)
        codes.append(result)
        method = (row.method or "").strip()      # whitespace-only -> ""
        is_red = (r_name == fighter_name) if exact else (hist.norm_name(r_name) == hist.norm_name(fighter_name))
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
            "coverage_verified": True if attribution is None else attribution.coverage_verified,
            "withheld_ambiguous_bouts": 0 if attribution is None else attribution.withheld_ambiguous,
        },
        "history_note": "Methods are unavailable until the source repair (FTR-01B2); empty means unknown, not decision.",
    }
    if attribution is not None:
        out["name_match"] = attribution.identity_meta()
    return out


# ── Extension validation + guard ────────────────────────────────────────────
class ExtensionValidationError(ValueError):
    """The extension payload violates the documented contract (=> INVALID_SHAPE).
    Distinct from any exception raised by the builder itself (=> ERROR).

    ``code`` is a fixed reason string and ``where`` an allowlisted identifier
    (taken only from this module's constants, never from the payload), so both
    are safe to log.  The exception message never contains payload contents."""

    def __init__(self, code: str, where: str = ""):
        super().__init__(code)
        self.code = code
        self.where = where


_REQUIRED_FIELDS = (
    "wins", "losses", "draws", "age", "height_cm", "reach_cm", "weight_lbs", "slpm", "str_acc",
    "str_def", "td_avg", "td_acc", "td_def", "sub_avg", "career_knockdowns",
)
_STATUSES = frozenset(s_.value for s_ in availability.Status)
_BASES = frozenset(b_.value for b_ in availability.Basis)
_SCORE_NAMES = ("composite", "aura", "chaos_contribution", "mirage")
_SCORE_STATUSES = frozenset({"provisional", "unavailable"})
_BLOCK_STATUSES = frozenset({"complete", "partial", "unavailable"})
_COVERAGE_KEYS = (
    "ufc_fights_in_dataset", "first_dataset_fight", "last_dataset_fight", "snapshot_date",
    "dataset_end", "methods_available_fraction", "record_scope", "record_as_of",
    "coverage_verified", "identity_status",
)


def _bad(code: str, where: str = ""):
    raise ExtensionValidationError(code, where)


def _is_num(v) -> bool:
    import math
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _enum_ok(v, allowed) -> bool:
    """Type-check BEFORE membership: unhashable / non-string values are simply invalid."""
    return isinstance(v, str) and v in allowed


def _no_nonfinite(obj):
    """Reject NaN/inf anywhere.  Never reports the path (payload keys are untrusted)."""
    import math
    if isinstance(obj, dict):
        for v in obj.values():
            _no_nonfinite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _no_nonfinite(v)
    elif isinstance(obj, float) and not math.isfinite(obj):
        _bad("NON_FINITE_NUMBER")


def validate_extension(ext) -> None:
    """
    Validate the documented ``data_quality`` / ``scores`` contract.  Bounded:
    required keys, enum values (type-checked first), types, and value /
    availability consistency.  Raises ExtensionValidationError only.
    """
    if not isinstance(ext, dict):
        _bad("EXTENSION_NOT_OBJECT")
    _no_nonfinite(ext)
    dq, sc = ext.get("data_quality"), ext.get("scores")

    # data_quality
    if not isinstance(dq, dict):
        _bad("DATA_QUALITY_MISSING")
    for k in ("schema", "fields", "core_stat_block", "coverage", "legacy_compat"):
        if k not in dq:
            _bad("DATA_QUALITY_KEY_MISSING", k)
    if not isinstance(dq["schema"], str) or not isinstance(dq["legacy_compat"], dict):
        _bad("DATA_QUALITY_SCHEMA_MALFORMED")
    fields = dq["fields"]
    if not isinstance(fields, dict):
        _bad("FIELDS_MALFORMED")
    for name in _REQUIRED_FIELDS:
        f = fields.get(name)
        if not isinstance(f, dict) or any(k not in f for k in ("value", "status", "basis", "unit")):
            _bad("FIELD_MALFORMED", name)
        if not _enum_ok(f["status"], _STATUSES):
            _bad("FIELD_STATUS_INVALID", name)
        if not _enum_ok(f["basis"], _BASES):
            _bad("FIELD_BASIS_INVALID", name)
        v, status = f["value"], f["status"]
        if status in ("measured", "measured_zero") and not _is_num(v):
            _bad("FIELD_MEASURED_WITHOUT_VALUE", name)
        if status in ("unavailable", "not_stored") and v is not None:
            _bad("FIELD_UNAVAILABLE_WITH_VALUE", name)
        if status == "ambiguous" and v is not None and not _is_num(v):
            _bad("FIELD_AMBIGUOUS_VALUE_INVALID", name)
    blk = dq["core_stat_block"]
    if (not isinstance(blk, dict) or not _enum_ok(blk.get("status"), _BLOCK_STATUSES)
            or not isinstance(blk.get("available"), bool)
            or blk["available"] != (blk["status"] == "complete")
            or not isinstance(blk.get("usable_fields"), list)
            or not isinstance(blk.get("unconfirmed_fields"), list)
            or not isinstance(blk.get("invalid_fields"), list)):
        _bad("CORE_BLOCK_MALFORMED")
    cov = dq["coverage"]
    if not isinstance(cov, dict) or any(k not in cov for k in _COVERAGE_KEYS):
        _bad("COVERAGE_MALFORMED")
    n = cov["ufc_fights_in_dataset"]
    if not isinstance(cov["coverage_verified"], bool):
        _bad("COVERAGE_VERIFIED_INVALID")
    if n is None:
        if cov["coverage_verified"]:
            _bad("COVERAGE_NULL_COUNT_VERIFIED")      # a missing count can never be "verified"
    elif not isinstance(n, int) or isinstance(n, bool) or n < 0:
        _bad("COVERAGE_COUNT_INVALID")
    frac = cov["methods_available_fraction"]
    if frac is not None and not (_is_num(frac) and 0.0 <= frac <= 1.0):
        _bad("COVERAGE_FRACTION_INVALID")
    for k in ("first_dataset_fight", "last_dataset_fight", "snapshot_date", "dataset_end"):
        if cov[k] is not None and not isinstance(cov[k], str):
            _bad("COVERAGE_DATE_INVALID", k)

    # scores
    if not isinstance(sc, dict) or not isinstance(sc.get("meta"), dict):
        _bad("SCORES_META_MISSING")
    for name in _SCORE_NAMES:
        o = sc.get(name)
        if not isinstance(o, dict) or any(k not in o for k in ("value", "available", "status", "reason")):
            _bad("SCORE_MALFORMED", name)
        if not isinstance(o["available"], bool):
            _bad("SCORE_AVAILABLE_INVALID", name)
        if not _enum_ok(o["status"], _SCORE_STATUSES):
            _bad("SCORE_STATUS_INVALID", name)
        if o["available"]:
            if not _is_num(o["value"]) or not 0.0 <= o["value"] <= 100.0:
                _bad("SCORE_AVAILABLE_WITHOUT_VALID_VALUE", name)
            if o["status"] != "provisional":
                _bad("SCORE_AVAILABLE_STATUS_MISMATCH", name)
        else:
            if o["value"] is not None:
                _bad("SCORE_UNAVAILABLE_WITH_VALUE", name)
            if o["status"] != "unavailable" or not isinstance(o["reason"], str) or not o["reason"]:
                _bad("SCORE_UNAVAILABLE_WITHOUT_REASON", name)


def _invalid_shape():
    return {"data_quality": None, "scores": None,
            "extension_status": {"available": False, "reason": "INVALID_SHAPE"}}


def guard_extension(builder, engine, name: str, logger) -> dict:
    """
    Run ``builder(engine, name)`` and validate its payload; never raises.

    Returns {"data_quality", "scores", "extension_status"}.  Failures give null
    objects and ``extension_status.reason``:
        NOT_FOUND      the builder reported no such fighter row
        INVALID_SHAPE  the payload violated the contract (validator rejected it,
                       including any malformed-data exception inside validation)
        ERROR          the builder (or engine access) raised, including ValueError
    Legacy scores are never substituted.  Logs contain only the fighter name,
    fixed reason codes, allowlisted identifiers and exception *type names* -
    never payload contents, payload keys, exception messages or SQL/URLs.
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
        logger.warning("profile_extension_invalid_shape fighter=%r code=%s where=%s",
                       name, exc.code, exc.where or "-")
        return _invalid_shape()
    except Exception as exc:  # noqa: BLE001 - malformed data must never escape the validation boundary
        logger.warning("profile_extension_invalid_shape fighter=%r code=VALIDATION_FAULT error=%s",
                       name, type(exc).__name__)
        return _invalid_shape()
    return {"data_quality": ext["data_quality"], "scores": ext["scores"],
            "extension_status": {"available": True, "reason": None}}
