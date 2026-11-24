"""
Profile-level heuristic scores (FTR-01B1).

Pure functions.  These are *profile heuristics* for a single fighter.  They
are NOT model predictions and NOT the matchup intelligence signals in
``backend/intelligence/*`` (different code, different semantics).

Record definition (documented choice, used by every score here)
---------------------------------------------------------------
    record_total = wins + losses + draws
    win_rate     = wins / record_total          (draws count as non-wins)
No-contests / DQs are not stored in the database and are therefore not in the
denominator.  The legacy endpoint used wins / (wins + losses) and ignored
draws; the two definitions differ only for fighters with draws.

Every score returns an object with: value (nullable), available, status
("provisional" | "unavailable"), reason, inputs_required, inputs_missing,
provenance ("heuristic"), validated (False), label, description and, where
relevant, claims the formula does not support.
"""

from __future__ import annotations

from typing import Optional

from .availability import Basis, is_usable

SCHEMA = "fighter_profile_scores_v1"
MIN_RECORD_FOR_MIRAGE = 5   # provisional small-sample guard (documented, unvalidated)

RECORD_DEFINITION = (
    "win_rate = wins / (wins + losses + draws); draws count as non-wins; "
    "no-contests are not stored and not counted. Scraped career record."
)


def _unavailable(label, description, reason, required, missing, unsupported=()):
    return {
        "value": None, "available": False, "status": "unavailable",
        "reason": reason, "inputs_required": list(required),
        "inputs_missing": sorted(missing), "provenance": Basis.HEURISTIC.value,
        "validated": False, "label": label, "description": description,
        "unsupported_claims": list(unsupported),
    }


def _provisional(value, label, description, required, unsupported=()):
    if not (0.0 <= value <= 100.0):  # defensive range validation
        raise ValueError(f"score out of range [0,100]: {value}")
    return {
        "value": round(value, 1), "available": True, "status": "provisional",
        "reason": None, "inputs_required": list(required), "inputs_missing": [],
        "provenance": Basis.HEURISTIC.value, "validated": False,
        "label": label, "description": description,
        "unsupported_claims": list(unsupported),
    }


def _record(fields: dict) -> tuple[Optional[float], list[str]]:
    """(win_rate, missing_inputs).  win_rate is None when the record is unusable."""
    missing = [k for k in ("wins", "losses", "draws") if not is_usable(fields.get(k))]
    if missing:
        return None, missing
    w, l, d = (fields[k]["value"] for k in ("wins", "losses", "draws"))
    if min(w, l, d) < 0:
        return None, ["wins", "losses", "draws"]
    total = w + l + d
    if total == 0:
        return None, ["record_total"]
    return w / total, []


def _missing(fields: dict, names) -> list[str]:
    return [n for n in names if not is_usable(fields.get(n))]


def record_total(fields: dict) -> int:
    return int(sum((fields[k]["value"] or 0) for k in ("wins", "losses", "draws")
                   if is_usable(fields.get(k))))


# ── Composite ──────────────────────────────────────────────────────────────
def composite(fields: dict) -> dict:
    """
    0.40·win_rate + 0.30·str_acc + 0.30·str_def, scaled to 0–100.
    (Legacy bug: the sum was multiplied by an extra 100, saturating at 100.)
    """
    label = "Composite (record + striking-percentage heuristic)"
    desc = ("Weighted blend of career win rate, striking accuracy and striking "
            "defence. A heuristic over scraped profile numbers; not a model "
            "output and not validated against outcomes.")
    req = ["wins", "losses", "draws", "str_acc", "str_def"]
    win_rate, miss = _record(fields)
    miss = miss + _missing(fields, ["str_acc", "str_def"])
    if miss:
        return _unavailable(label, desc, "MISSING_OR_UNCONFIRMED_INPUTS", req, miss)
    acc, dfn = fields["str_acc"]["value"], fields["str_def"]["value"]
    if not (0 <= acc <= 1 and 0 <= dfn <= 1):
        return _unavailable(label, desc, "INPUT_OUT_OF_RANGE", req, ["str_acc", "str_def"])
    return _provisional((win_rate * 40.0) + (acc * 30.0) + (dfn * 30.0), label, desc, req)


# ── Aura ───────────────────────────────────────────────────────────────────
def aura(fields: dict) -> dict:
    label = "Aura (record-and-volume proxy)"
    desc = ("Proxy built from win rate, career length and offensive volume "
            "(strikes and takedowns). It is NOT a measure of public sentiment "
            "or hype and has not been validated as one.")
    unsupported = ["public_sentiment", "betting_market_perception"]
    req = ["wins", "losses", "draws", "slpm", "td_avg"]
    win_rate, miss = _record(fields)
    miss = miss + _missing(fields, ["slpm", "td_avg"])
    if miss:
        return _unavailable(label, desc, "MISSING_OR_UNCONFIRMED_INPUTS", req, miss, unsupported)
    volume = min(1.0, (fields["slpm"]["value"] / 6.0) * 0.5 + (fields["td_avg"]["value"] / 5.0) * 0.5)
    total = record_total(fields)
    value = min(100.0, win_rate * 40.0 + volume * 35.0 + min(total, 20) / 20.0 * 25.0)
    return _provisional(value, label, desc, req, unsupported)


# ── Chaos contribution ─────────────────────────────────────────────────────
def chaos_contribution(fields: dict) -> dict:
    label = "Chaos Contribution (volume-and-defence heuristic)"
    desc = ("Half striking volume, half striking-defence gap. A missing or "
            "unconfirmed defence figure makes the score unavailable instead of "
            "counting as 'no defence'.")
    req = ["slpm", "str_def"]
    miss = _missing(fields, req)
    if miss:
        return _unavailable(label, desc, "MISSING_OR_UNCONFIRMED_INPUTS", req, miss)
    sd = fields["str_def"]["value"]
    if not 0 <= sd <= 1:
        return _unavailable(label, desc, "INPUT_OUT_OF_RANGE", req, ["str_def"])
    volume = min(1.0, fields["slpm"]["value"] / 7.0)
    return _provisional((volume * 0.5 + (1.0 - sd) * 0.5) * 100.0, label, desc, req)


# ── Mirage ─────────────────────────────────────────────────────────────────
def mirage(fields: dict) -> dict:
    label = "Mirage (record vs striking-defence gap)"
    desc = ("Flags a strong win rate paired with weak striking defence. It does "
            "NOT measure opposition quality or resume inflation: no opponent "
            "data is used.")
    unsupported = ["opposition_quality", "resume_inflation"]
    req = ["wins", "losses", "draws", "str_def"]
    win_rate, miss = _record(fields)
    miss = miss + _missing(fields, ["str_def"])
    if miss:
        return _unavailable(label, desc, "MISSING_OR_UNCONFIRMED_INPUTS", req, miss, unsupported)
    if record_total(fields) < MIN_RECORD_FOR_MIRAGE:
        return _unavailable(label, desc, "INSUFFICIENT_RECORD", req, ["record_total>=%d" % MIN_RECORD_FOR_MIRAGE], unsupported)
    sd = fields["str_def"]["value"]
    if not 0 <= sd <= 1:
        return _unavailable(label, desc, "INPUT_OUT_OF_RANGE", req, ["str_def"], unsupported)
    value = min(100.0, max(0.0, (win_rate - 0.65) * 200.0)) if (win_rate > 0.65 and sd < 0.55) else 0.0
    return _provisional(value, label, desc, req, unsupported)


def build_scores(fields: dict) -> dict:
    """``scores`` object for GET /fighter/{name}."""
    return {
        "meta": {
            "schema": SCHEMA,
            "kind": "profile_heuristics",
            "not_model_output": True,
            "validated": False,
            "record_definition": RECORD_DEFINITION,
            "note": ("Profile-level heuristics. Distinct from the matchup "
                     "intelligence signals returned by /predict."),
        },
        "composite": composite(fields),
        "aura": aura(fields),
        "chaos_contribution": chaos_contribution(fields),
        "mirage": mirage(fields),
    }
