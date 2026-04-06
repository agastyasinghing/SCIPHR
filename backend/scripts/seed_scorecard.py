"""
seed_scorecard.py — Seed predictions_log with post-dataset-cutoff fight outcomes.

Only seeds fights on or after --after-date (default: 2025-07-01).
These are genuinely out-of-sample predictions — the model never saw them during
training, making them the only credible track record to show users.

Idempotent: skips rows where (fighter1, fighter2, created_at::date) already exist.
Use --dry-run to preview rows without inserting.

Usage:
    cd backend
    python scripts/seed_scorecard.py --after-date 2025-07-01
    python scripts/seed_scorecard.py --after-date 2025-07-01 --dry-run
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Running from backend/ → repo root is one level up.
# Running from repo root (python backend/scripts/seed_scorecard.py) → two levels up.
_script_dir = Path(__file__).parent
_backend_dir = _script_dir.parent
_repo_root = _backend_dir.parent

sys.path.insert(0, str(_backend_dir))       # backend/ imports (db.models, etc.)
sys.path.insert(0, str(_repo_root / "src"))  # predictor_golden

from dotenv import load_dotenv
load_dotenv(_backend_dir / ".env")

from sqlalchemy import create_engine, text
from db.models import PredictionLog

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Seed predictions_log with post-cutoff fight outcomes.")
    p.add_argument(
        "--after-date",
        default="2025-07-01",
        help="Only seed fights on or after this date (YYYY-MM-DD). Default: 2025-07-01",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows that would be inserted without writing to the DB.",
    )
    return p.parse_args()


def seed(engine, after_date: date, dry_run: bool = False, _predictor=None):
    """
    Data flow:
      1. Query fights table for rows where date >= after_date
      2. For each fight, run predictor.predict_fight(r_name, b_name)
      3. Check if already seeded (idempotent — skips duplicates)
      4. INSERT into predictions_log with actual_winner + was_correct populated

    Fight date is stored in created_at so the scorecard shows temporal ordering.

    _predictor: inject a predictor instance for testing; None loads the real model.
    """
    if _predictor is not None:
        predictor = _predictor
    else:
        from predictor_golden import UFCFightPredictorGolden
        model_path = str(_repo_root / "models" / "golden_model.pkl")
        log.info(f"Loading predictor from {model_path}")
        predictor = UFCFightPredictorGolden(model_path=model_path, engine=engine)
        log.info("Predictor loaded")

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT r_name, b_name, date, winner
                FROM fights
                WHERE date >= :cutoff
                  AND winner IS NOT NULL
                ORDER BY date ASC
            """),
            {"cutoff": after_date},
        ).fetchall()

    log.info(f"Found {len(rows)} fights on/after {after_date}")

    inserted = 0
    skipped_no_prediction = 0
    skipped_already_seeded = 0

    for row in rows:
        r_name, b_name, fight_date, actual_winner = row

        # ── Idempotency check ─────────────────────────────────────────────
        if not dry_run:
            with engine.connect() as conn:
                existing = conn.execute(
                    text("""
                        SELECT id FROM predictions_log
                        WHERE fighter1 = :f1
                          AND fighter2 = :f2
                          AND DATE(created_at) = :dt
                    """),
                    {"f1": r_name, "f2": b_name, "dt": str(fight_date)},
                ).fetchone()
            if existing:
                skipped_already_seeded += 1
                continue

        # ── Run model prediction ──────────────────────────────────────────
        try:
            result = predictor.predict_fight(r_name, b_name, verbose=False)
        except Exception as e:
            log.debug(f"Skipping {r_name} vs {b_name}: predict_fight raised {e}")
            skipped_no_prediction += 1
            continue

        if result is None:
            log.debug(f"Skipping {r_name} vs {b_name}: predictor returned None")
            skipped_no_prediction += 1
            continue

        predicted_winner = result["winner"]
        was_correct = (predicted_winner == actual_winner)
        confidence = float(result["confidence"])
        prob_f1 = float(result["prob_fighter1"])
        prob_f2 = float(result["prob_fighter2"])

        if dry_run:
            print(
                f"[DRY RUN] {fight_date} | {r_name} vs {b_name} | "
                f"predicted={predicted_winner} actual={actual_winner} "
                f"correct={'✓' if was_correct else '✗'} conf={confidence:.2f}"
            )
            inserted += 1
            continue

        # ── Insert row ────────────────────────────────────────────────────
        # created_at is set to fight_date so scorecard sorts by fight date.
        # SQLite returns dates as strings; PostgreSQL returns date objects.
        if isinstance(fight_date, str):
            fight_date = date.fromisoformat(fight_date)
        fight_datetime = datetime.combine(fight_date, datetime.min.time())
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO predictions_log
                            (fighter1, fighter2, winner, confidence,
                             prob_f1, prob_f2, actual_winner, was_correct, created_at)
                        VALUES
                            (:f1, :f2, :winner, :conf,
                             :pf1, :pf2, :actual, :correct, :created_at)
                    """),
                    {
                        "f1": r_name,
                        "f2": b_name,
                        "winner": predicted_winner,
                        "conf": confidence,
                        "pf1": prob_f1,
                        "pf2": prob_f2,
                        "actual": actual_winner,
                        "correct": was_correct,
                        "created_at": fight_datetime,
                    },
                )
            inserted += 1
        except Exception as e:
            log.error(f"INSERT failed for {r_name} vs {b_name}: {e}")

    log.info(
        f"Done. inserted={inserted} skipped_already_seeded={skipped_already_seeded} "
        f"skipped_no_prediction={skipped_no_prediction}"
    )
    return inserted


def main():
    args = parse_args()

    try:
        cutoff = date.fromisoformat(args.after_date)
    except ValueError:
        print(f"Invalid --after-date: {args.after_date!r}. Use YYYY-MM-DD format.")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set. Add it to backend/.env or the environment.")
        sys.exit(1)

    if args.dry_run:
        log.info(f"DRY RUN — no rows will be written. Cutoff: {cutoff}")
    else:
        log.info(f"Seeding fights from {cutoff} onwards")

    engine = create_engine(database_url, pool_pre_ping=True)
    seed(engine, cutoff, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
