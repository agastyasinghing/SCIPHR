"""
Integration tests for scripts/migrate_csv.py.

Tests use a tiny synthetic CSV written to a temp file.
All DB assertions run against SQLite in-memory (from conftest.py engine fixture).

Test diagram (new codepaths):
  CSV file (tmp)
       │
  migrate(csv_path, db_url)
       │
       ├── [1] NaN feature values stored as 0.0 (not NaN/null/inf)
       ├── [2] Latest fight wins: fighter with 2 rows uses stats from newer date
       ├── [3] Idempotent: running migrate() twice gives same row count
       └── [4] was_red=False when fighter only appears as b_name
"""

import io
import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sqlalchemy import text
from migrate_csv import migrate


# ---------------------------------------------------------------------------
# CSV factory
# ---------------------------------------------------------------------------

def _make_csv(tmp_path, rows: list[dict]) -> str:
    """Write a list of fight-row dicts to a temp CSV and return the path."""
    df = pd.DataFrame(rows)
    path = str(tmp_path / "test_fights.csv")
    df.to_csv(path, index=False)
    return path


def _base_row(**kwargs) -> dict:
    """Minimal valid fight row with sensible defaults."""
    defaults = {
        "r_name": "Fighter A",
        "b_name": "Fighter B",
        "date": "2023-01-15",
        "winner": "Fighter A",
        "finish": "KO",
        "weight_class": "Lightweight",
        "r_fighter_w": 10.0,
        "r_fighter_l": 2.0,
        "r_fighter_d": 0.0,
        "r_fighter_weight_lbs": 155.0,
        "r_fighter_height_cm": 178.0,
        "r_fighter_reach_cm": 183.0,
        "r_age": 28.0,
        "r_fighter_SlpM": 5.1,
        "r_fighter_Str_Acc": 0.47,
        "r_fighter_Str_Def": 0.60,
        "r_fighter_TD_Avg": 1.2,
        "r_fighter_TD_Acc": 0.40,
        "r_fighter_TD_Def": 0.75,
        "r_fighter_Sub_Avg": 0.5,
        "b_fighter_w": 8.0,
        "b_fighter_l": 3.0,
        "b_fighter_d": 0.0,
        "b_fighter_weight_lbs": 155.0,
        "b_fighter_height_cm": 175.0,
        "b_fighter_reach_cm": 180.0,
        "b_age": 30.0,
        "b_fighter_SlpM": 4.5,
        "b_fighter_Str_Acc": 0.43,
        "b_fighter_Str_Def": 0.55,
        "b_fighter_TD_Avg": 0.9,
        "b_fighter_TD_Acc": 0.35,
        "b_fighter_TD_Def": 0.70,
        "b_fighter_Sub_Avg": 0.3,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_nan_values_normalized_to_zero(engine, tmp_path):
    """NaN in a feature column → stored as 0.0 in latest_features."""
    import math
    row = _base_row(r_fighter_SlpM=float("nan"))
    csv = _make_csv(tmp_path, [row])
    migrate(csv, engine=engine)

    with engine.connect() as conn:
        features = conn.execute(
            text("SELECT latest_features FROM fighters WHERE name = 'Fighter A'")
        ).scalar()

    # latest_features is a JSON string in SQLite; parse if needed
    import json
    if isinstance(features, str):
        features = json.loads(features)

    assert features is not None
    slpm_val = features.get("r_fighter_SlpM")
    assert slpm_val is not None
    assert not math.isnan(float(slpm_val)), "NaN should have been stored as 0.0"
    assert float(slpm_val) == 0.0


def test_latest_fight_wins_over_earlier_fight(engine, tmp_path):
    """
    Fighter A appears in two rows.  After migration, was_red and
    last_fight_date must reflect the 2023 fight (more recent), not 2020.
    """
    rows = [
        _base_row(date="2020-06-01", r_fighter_w=5.0),   # older
        _base_row(date="2023-01-15", r_fighter_w=10.0),  # newer
    ]
    csv = _make_csv(tmp_path, rows)
    migrate(csv, engine=engine)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT wins, last_fight_date FROM fighters WHERE name = 'Fighter A'")
        ).fetchone()

    assert row is not None
    assert row[0] == 10       # wins from the 2023 row
    assert str(row[1]).startswith("2023")


def test_idempotent_on_second_run(engine, tmp_path):
    """Running migrate() twice yields the same fighter and fight counts."""
    rows = [_base_row()]
    csv = _make_csv(tmp_path, rows)

    migrate(csv, engine=engine)
    with engine.connect() as conn:
        fighters_1 = conn.execute(text("SELECT COUNT(*) FROM fighters")).scalar()
        fights_1   = conn.execute(text("SELECT COUNT(*) FROM fights")).scalar()

    migrate(csv, engine=engine)
    with engine.connect() as conn:
        fighters_2 = conn.execute(text("SELECT COUNT(*) FROM fighters")).scalar()
        fights_2   = conn.execute(text("SELECT COUNT(*) FROM fights")).scalar()

    assert fighters_1 == fighters_2
    assert fights_1   == fights_2


def test_fighters_only_skips_fights(engine, tmp_path):
    """fighters_only=True must populate fighters but leave fights table empty."""
    csv = _make_csv(tmp_path, [_base_row()])
    migrate(csv, engine=engine, fighters_only=True)

    with engine.connect() as conn:
        n_fights   = conn.execute(text("SELECT COUNT(*) FROM fights")).scalar()
        n_fighters = conn.execute(text("SELECT COUNT(*) FROM fighters")).scalar()

    assert n_fights == 0, "fighters_only must not insert any fights"
    assert n_fighters > 0, "fighters_only must still upsert fighters"


def test_was_red_false_when_fighter_only_in_blue(engine, tmp_path):
    """
    Fighter B only ever appears as b_name → was_red must be False,
    and latest_features keys must be in canonical r_* form (remapped from b_*).
    """
    import json
    csv = _make_csv(tmp_path, [_base_row()])
    migrate(csv, engine=engine)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT was_red, latest_features FROM fighters WHERE name = 'Fighter B'")
        ).fetchone()

    assert row is not None
    was_red   = row[0]
    features  = row[1]

    if isinstance(features, str):
        features = json.loads(features)

    assert was_red is False or was_red == 0, "Fighter B was blue — was_red should be False"
    # b_fighter_w should have been remapped to r_fighter_w
    assert "r_fighter_w" in features, "b_* features must be remapped to r_* canonical form"
    assert "b_fighter_w" not in features, "raw b_* keys must not appear in latest_features"
