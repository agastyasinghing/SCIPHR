"""
One-time CSV → PostgreSQL migration for SCIPHR.

Usage:
    python migrate_csv.py --csv /path/to/golden_full_converted.csv
    python migrate_csv.py --csv /path/to/golden_full_converted.csv --database-url postgresql+psycopg2://...

DATABASE_URL defaults to the DATABASE_URL environment variable.

Algorithm:
    1.  Load the golden CSV with pandas (380 MB, ~8,000 rows, ~5,401 columns).
    2.  Sort fights by date ascending so the last write for any fighter is
        always their most recent fight.
    3.  For each fight row:
          a. Collect fight metadata (r_name, b_name, date, winner, method,
             weight_class) for bulk insert into the fights table.
          b. Update the in-memory fighter_latest dict for both r_name and
             b_name, storing the fight row and which corner they were in.
    4.  Build the fighters list from fighter_latest:
          - Extract base profile stats (wins, losses, height, reach, …).
          - Extract pre-normalized feature vector (canonical r_* form) via
            _extract_features().
    5.  Bulk-upsert fighters (ON CONFLICT name DO UPDATE).
    6.  Bulk-insert fights  (ON CONFLICT r_name, b_name, date DO NOTHING).

Feature pre-normalization (_extract_features):
    All features are stored in canonical 'red corner' form regardless of
    which corner the fighter occupied:
      - was_red=True:  r_* → r_*,  *_r → *_r   (no change)
      - was_red=False: b_* → r_*,  *_b → *_r   (prefix/suffix remapped)
    This lets GoldenFeatureCalculator.build_full_feature_vector() load
    fighter1 directly (already r_*) and remap fighter2 with a simple
    r_* → b_* swap — no was_red branch at prediction time.

NaN / Inf handling:
    Numeric NaN and Inf values are stored as 0.0 (matching the model's
    own fallback on line 181 of golden_feature_calculator.py).
    String values are kept as-is for later pd.Categorical encoding.

Idempotency:
    Safe to run multiple times.  fighters uses ON CONFLICT DO UPDATE so
    re-running with the same CSV produces the same result.  fights uses
    ON CONFLICT DO NOTHING.
"""

import argparse
import os
import sys
import logging
from datetime import date as date_type
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Allow running as: python backend/scripts/migrate_csv.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.models import Base, Fight, Fighter

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Weight-class helper (mirrors main.py determine_weight_class)
# ---------------------------------------------------------------------------

def _weight_class(weight_lbs: float) -> str:
    # mirrors main.py determine_weight_class — keep thresholds in sync if changed
    if weight_lbs <= 115:
        return "Strawweight"
    elif weight_lbs <= 125:
        return "Flyweight"
    elif weight_lbs <= 135:
        return "Bantamweight"
    elif weight_lbs <= 145:
        return "Featherweight"
    elif weight_lbs <= 155:
        return "Lightweight"
    elif weight_lbs <= 170:
        return "Welterweight"
    elif weight_lbs <= 185:
        return "Middleweight"
    elif weight_lbs <= 205:
        return "Light Heavyweight"
    else:
        return "Heavyweight"


# ---------------------------------------------------------------------------
# Value cleaning
# ---------------------------------------------------------------------------

def _clean(val):
    """
    Convert a CSV cell to a JSON-safe Python type.
    - numpy scalars → Python int / float
    - NaN / Inf      → 0.0
    - strings        → str (kept for categorical encoding at prediction time)
    """
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else f
    try:
        if pd.isna(val):
            return 0.0
    except (TypeError, ValueError):
        pass
    return val


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _extract_features(row: pd.Series, was_red: bool) -> dict:
    """
    Extract this fighter's stats from a fight row and normalize to canonical
    r_* / *_r form (as if they were always in the red corner).

    was_red=True  → r_* columns kept as r_*;  *_r columns kept as *_r
    was_red=False → b_* columns remapped to r_*; *_b columns remapped to *_r
    """
    prefix = "r_" if was_red else "b_"
    suffix = "_r" if was_red else "_b"
    features: dict = {}

    for col, val in row.items():
        cleaned = _clean(val)
        if col.startswith(prefix):
            # e.g. r_fighter_w  →  r_fighter_w   (was_red)
            # e.g. b_fighter_w  →  r_fighter_w   (was_blue)
            features["r_" + col[len(prefix):]] = cleaned
        elif col.endswith(suffix) and not col.startswith(("r_", "b_")):
            # e.g. wins_3_r → wins_3_r   (was_red)
            # e.g. wins_3_b → wins_3_r   (was_blue)
            features[col[: -len(suffix)] + "_r"] = cleaned

    return features


def _extract_base_stats(row: pd.Series, was_red: bool) -> dict:
    """Extract the ~15 profile stats stored as direct fighters table columns."""
    pfx = "r_" if was_red else "b_"

    def g(key, default=0.0):
        val = row.get(pfx + key, default)
        cleaned = _clean(val)
        return cleaned if cleaned is not None else default

    weight_lbs = float(g("fighter_weight_lbs", 185) or 185)
    return {
        "weight_class": _weight_class(weight_lbs),
        "weight_lbs":   weight_lbs,
        "height_cm":    float(g("fighter_height_cm") or 0),
        "reach_cm":     float(g("fighter_reach_cm") or 0),
        "wins":         int(float(g("fighter_w") or 0)),
        "losses":       int(float(g("fighter_l") or 0)),
        "draws":        int(float(g("fighter_d") or 0)),
        "age":          float(g("age") or 0),
        "slpm":         float(g("fighter_SlpM") or 0),
        "str_acc":      float(g("fighter_Str_Acc") or 0),
        "str_def":      float(g("fighter_Str_Def") or 0),
        "td_avg":       float(g("fighter_TD_Avg") or 0),
        "td_acc":       float(g("fighter_TD_Acc") or 0),
        "td_def":       float(g("fighter_TD_Def") or 0),
        "sub_avg":      float(g("fighter_Sub_Avg") or 0),
    }


# ---------------------------------------------------------------------------
# Core migration function (importable for tests)
# ---------------------------------------------------------------------------

def migrate(
    csv_path: str,
    database_url: Optional[str] = None,
    *,
    engine: Optional[Engine] = None,
) -> None:
    """
    Load *csv_path* and migrate fighters + fights into the database.
    Safe to call more than once (idempotent).

    Pass either *database_url* (a SQLAlchemy URL string) or an already-created
    *engine*.  Passing *engine* directly is required when using SQLite
    in-memory databases in tests, since each new create_engine() call opens
    a fresh isolated DB.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if engine is None:
        if not database_url:
            raise ValueError("database_url must be provided (or set DATABASE_URL env var)")
        engine = create_engine(database_url, pool_pre_ping=True)

    Base.metadata.create_all(engine)

    log.info("Loading CSV: %s", csv_path)
    df = pd.read_csv(csv_path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date", ascending=True).reset_index(drop=True)
    log.info("Loaded %d fights, %d columns", len(df), len(df.columns))

    # -----------------------------------------------------------------------
    # Pass 1: collect fights metadata + build per-fighter latest-fight state
    # -----------------------------------------------------------------------
    fight_rows: list[dict] = []
    fighter_latest: dict[str, dict] = {}  # name → {row, was_red, date, opp}

    for _, row in df.iterrows():
        r_name = row.get("r_name")
        b_name = row.get("b_name")

        if pd.isna(r_name) or pd.isna(b_name):
            continue

        fight_date = row["date"].date() if not pd.isna(row["date"]) else None
        winner = _clean(row.get("winner")) if not pd.isna(row.get("winner", float("nan"))) else None
        method = _clean(row.get("finish")) if not pd.isna(row.get("finish", float("nan"))) else None
        wc_col = row.get("weight_class") if not pd.isna(row.get("weight_class", float("nan"))) else None

        fight_rows.append({
            "r_name":       str(r_name),
            "b_name":       str(b_name),
            "date":         fight_date,
            "winner":       str(winner) if winner is not None else None,
            "method":       str(method) if method is not None else None,
            "weight_class": str(wc_col) if wc_col is not None else None,
        })

        # Overwrite with more recent fight (ascending sort guarantees this)
        fighter_latest[str(r_name)] = {"row": row, "was_red": True,  "date": fight_date, "opp": str(b_name)}
        fighter_latest[str(b_name)] = {"row": row, "was_red": False, "date": fight_date, "opp": str(r_name)}

    log.info("Processed %d valid fight rows, %d unique fighters",
             len(fight_rows), len(fighter_latest))

    # -----------------------------------------------------------------------
    # Pass 2: build fighter upsert dicts
    # -----------------------------------------------------------------------
    fighter_rows: list[dict] = []
    for name, state in fighter_latest.items():
        row      = state["row"]
        was_red  = state["was_red"]
        base     = _extract_base_stats(row, was_red)
        features = _extract_features(row, was_red)
        fighter_rows.append({
            "name":             name,
            "was_red":          was_red,
            "last_fight_date":  state["date"],
            "last_fight_opp":   state["opp"],
            "latest_features":  features,
            **base,
        })

    # -----------------------------------------------------------------------
    # DB writes — dialect-specific upsert (PostgreSQL or SQLite)
    # -----------------------------------------------------------------------
    dialect = engine.dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as _insert
    else:
        from sqlalchemy.dialects.postgresql import insert as _insert

    with engine.begin() as conn:
        # Fights — ON CONFLICT DO NOTHING (idempotent)
        if fight_rows:
            stmt = (
                _insert(Fight)
                .values(fight_rows)
                .on_conflict_do_nothing(index_elements=["r_name", "b_name", "date"])
            )
            result = conn.execute(stmt)
            log.info("Fights inserted: %d (skipped duplicates)", result.rowcount)

        # Fighters — ON CONFLICT DO UPDATE (re-running updates to latest state)
        if fighter_rows:
            _ins = _insert(Fighter).values(fighter_rows)
            stmt = _ins.on_conflict_do_update(
                index_elements=["name"],
                set_={
                    col: getattr(_ins.excluded, col)
                    for col in fighter_rows[0]
                    if col != "name"
                },
            )
            result = conn.execute(stmt)
            log.info("Fighters upserted: %d", result.rowcount)

    # Verify
    with engine.connect() as conn:
        n_fighters = conn.execute(text("SELECT COUNT(*) FROM fighters")).scalar()
        n_fights   = conn.execute(text("SELECT COUNT(*) FROM fights")).scalar()
    log.info("Migration complete — fighters: %d, fights: %d", n_fighters, n_fights)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SCIPHR CSV → PostgreSQL")
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to golden_full_converted.csv",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy database URL (defaults to DATABASE_URL env var)",
    )
    args = parser.parse_args()
    migrate(args.csv, args.database_url)
