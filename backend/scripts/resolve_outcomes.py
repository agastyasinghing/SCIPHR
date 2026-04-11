"""
resolve_outcomes.py — Resolve fight outcomes in predictions_log after an event.

Updates actual_winner, was_correct, actual_method, actual_round, and resolved_at
for every predictions_log row that matches the supplied results.

Idempotent: re-running with the same --results produces the same DB state.
Rows that do not match any result entry are left untouched.

Matching logic:
  A predictions_log row is matched when fighter1 and fighter2 both appear in the
  result entry (order-insensitive, case-insensitive).  If --event-id is supplied,
  only rows with that event_id (or NULL event_id) are candidates — this prevents
  name collisions across events when the same fighters meet multiple times.

Usage:
    cd backend
    python scripts/resolve_outcomes.py \\
        --event-id 3 \\
        --results '[{"fighter1": "Jon Jones", "fighter2": "Stipe Miocic", "actual_winner": "Jon Jones", "actual_method": "KO", "actual_round": 1}]'

    # Dry-run (preview without writing):
    python scripts/resolve_outcomes.py --event-id 3 --dry-run \\
        --results '[{"fighter1": "Islam Makhachev", "fighter2": "Charles Oliveira", "actual_winner": "Islam Makhachev"}]'

Result entry fields:
    fighter1        str  — one of the two fighters (order does not matter)
    fighter2        str  — the other fighter
    actual_winner   str  — name of the winner (must match fighter1 or fighter2)
    actual_method   str? — optional: KO | TKO | SUB | DEC | NC
    actual_round    int? — optional: round the fight ended in
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent
sys.path.insert(0, str(_backend_dir))

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(
        description="Resolve fight outcomes in predictions_log after an event."
    )
    p.add_argument(
        "--event-id",
        type=int,
        default=None,
        help="Restrict resolution to rows with this event_id (recommended to avoid cross-event name collisions).",
    )
    p.add_argument(
        "--results",
        required=True,
        help=(
            'JSON array of fight results. Each entry: '
            '{"fighter1": "...", "fighter2": "...", "actual_winner": "...", '
            '"actual_method": "KO|TKO|SUB|DEC|NC", "actual_round": 1}'
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matched rows and proposed updates without writing to the DB.",
    )
    return p.parse_args()


def _normalise(name: str) -> str:
    return name.strip().lower()


def resolve(engine, results: list[dict], event_id: int | None, dry_run: bool) -> None:
    """
    For each result entry, find matching predictions_log rows and update them.

    Matching: both fighter names (case-insensitive, order-insensitive) match
    the row's fighter1/fighter2 columns.  If event_id is supplied, further
    restricts to rows where predictions_log.event_id = :event_id OR is NULL.
    """
    now = datetime.now(timezone.utc)
    total_updated = 0

    with engine.begin() as conn:
        for entry in results:
            # Validate required fields
            required = ("fighter1", "fighter2", "actual_winner")
            missing = [k for k in required if not entry.get(k)]
            if missing:
                log.error("skipping_entry_missing_fields", extra={"missing": missing, "entry": entry})
                continue

            f1_raw = entry["fighter1"].strip()
            f2_raw = entry["fighter2"].strip()
            winner_raw = entry["actual_winner"].strip()
            method = entry.get("actual_method")
            round_ = entry.get("actual_round")

            f1_norm = _normalise(f1_raw)
            f2_norm = _normalise(f2_raw)
            winner_norm = _normalise(winner_raw)

            # winner must be one of the two fighters
            if winner_norm not in (f1_norm, f2_norm):
                log.error(
                    "winner_not_in_fight",
                    extra={"winner": winner_raw, "fighter1": f1_raw, "fighter2": f2_raw},
                )
                continue

            # Canonical winner name: use whichever fighter name it matched
            actual_winner = f1_raw if winner_norm == f1_norm else f2_raw

            # Build SELECT to find matching predictions_log rows
            # Using LOWER() for case-insensitive matching on PostgreSQL.
            base_where = """
                (
                    (LOWER(fighter1) = :f1 AND LOWER(fighter2) = :f2)
                    OR
                    (LOWER(fighter1) = :f2 AND LOWER(fighter2) = :f1)
                )
            """
            params: dict = {"f1": f1_norm, "f2": f2_norm}

            if event_id is not None:
                base_where += " AND (event_id = :event_id OR event_id IS NULL)"
                params["event_id"] = event_id

            select_sql = text(
                f"SELECT id, fighter1, fighter2, winner, actual_winner, was_correct "
                f"FROM predictions_log WHERE {base_where}"
            )
            rows = conn.execute(select_sql, params).fetchall()

            if not rows:
                log.warning(
                    "no_matching_rows",
                    extra={"fighter1": f1_raw, "fighter2": f2_raw, "event_id": event_id},
                )
                continue

            for row in rows:
                predicted_winner = (row.winner or "").strip()
                was_correct = _normalise(predicted_winner) == winner_norm

                if dry_run:
                    log.info(
                        "dry_run_would_update",
                        extra={
                            "id": row.id,
                            "fighter1": row.fighter1,
                            "fighter2": row.fighter2,
                            "predicted": predicted_winner,
                            "actual_winner": actual_winner,
                            "was_correct": was_correct,
                            "actual_method": method,
                            "actual_round": round_,
                        },
                    )
                    total_updated += 1
                    continue

                update_sql = text("""
                    UPDATE predictions_log
                    SET
                        actual_winner = :actual_winner,
                        was_correct   = :was_correct,
                        actual_method = :actual_method,
                        actual_round  = :actual_round,
                        resolved_at   = :resolved_at
                    WHERE id = :id
                """)
                conn.execute(
                    update_sql,
                    {
                        "actual_winner": actual_winner,
                        "was_correct": was_correct,
                        "actual_method": method,
                        "actual_round": round_,
                        "resolved_at": now,
                        "id": row.id,
                    },
                )
                log.info(
                    "resolved",
                    extra={
                        "id": row.id,
                        "fighter1": row.fighter1,
                        "fighter2": row.fighter2,
                        "actual_winner": actual_winner,
                        "was_correct": was_correct,
                    },
                )
                total_updated += 1

    action = "would update" if dry_run else "updated"
    log.info(f"done — {action} {total_updated} prediction(s)")


def main():
    args = parse_args()

    try:
        results = json.loads(args.results)
    except json.JSONDecodeError as e:
        log.error(f"--results is not valid JSON: {e}")
        sys.exit(1)

    if not isinstance(results, list):
        log.error("--results must be a JSON array")
        sys.exit(1)

    if not results:
        log.error("--results array is empty")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        log.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    engine = create_engine(database_url)

    resolve(engine, results, args.event_id, args.dry_run)


if __name__ == "__main__":
    main()
