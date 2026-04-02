"""
Integration tests for DB-backed GoldenFeatureCalculator.

Test diagram:
  ┌──────────────────────────────────────────────────────────────┐
  │  fighters table (SQLite in-memory)                           │
  │    seed_fighter() inserts rows with known latest_features    │
  └──────────────────────────┬───────────────────────────────────┘
                             │
              GoldenFeatureCalculator(engine)
                             │
       ┌─────────────────────┴───────────────────────┐
       │                                             │
  get_latest_fighter_stats()            build_full_feature_vector()
       │                                             │
  [1] found → returns CSV-key dict     [3] f2 features r_* → b_*
  [2] not found → returns {}           [4] was_red warning logged
                                        [5] fighter not found → None
                                        [6] diff_ features computed
"""

import logging
import pytest
from sqlalchemy.orm import Session
from db.models import Fighter
from golden_feature_calculator import GoldenFeatureCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_fighter(engine, name, *, was_red=True, features=None,
                  last_fight_opp=None, wins=10, losses=2):
    """Insert one Fighter row with given attributes."""
    with Session(engine) as s:
        s.add(Fighter(
            name=name,
            was_red=was_red,
            last_fight_opp=last_fight_opp,
            wins=wins,
            losses=losses,
            draws=0,
            age=28.0,
            weight_lbs=155.0,
            height_cm=178.0,
            reach_cm=183.0,
            weight_class="Lightweight",
            slpm=5.1,
            str_acc=0.47,
            str_def=0.60,
            td_avg=1.2,
            td_acc=0.40,
            td_def=0.75,
            sub_avg=0.5,
            latest_features=features or {"r_fighter_w": float(wins), "r_fighter_l": float(losses)},
        ))
        s.commit()


# ---------------------------------------------------------------------------
# get_latest_fighter_stats tests
# ---------------------------------------------------------------------------

def test_get_latest_fighter_stats_returns_mapped_keys(engine):
    """Found fighter → dict uses original CSV key names."""
    _seed_fighter(engine, "Jon Jones", wins=27, losses=1)
    calc = GoldenFeatureCalculator(engine)
    stats = calc.get_latest_fighter_stats("Jon Jones")

    assert stats["fighter_w"] == 27.0
    assert stats["fighter_l"] == 1.0
    assert "fighter_height_cm" in stats
    assert "fighter_SlpM" in stats


def test_get_latest_fighter_stats_not_found_returns_empty(engine):
    """Unknown fighter name → empty dict, no exception."""
    calc = GoldenFeatureCalculator(engine)
    stats = calc.get_latest_fighter_stats("Nobody McUnknown")
    assert stats == {}


# ---------------------------------------------------------------------------
# build_full_feature_vector tests
# ---------------------------------------------------------------------------

def test_build_full_feature_vector_fighter1_red_direct(engine):
    """
    Fighter1's features (canonical r_* form) go straight into r_* positions.
    Fighter2's features get remapped to b_* positions.
    """
    _seed_fighter(engine, "Jon Jones",    features={"r_fighter_w": 27.0})
    _seed_fighter(engine, "Stipe Miocic", features={"r_fighter_w": 20.0})

    calc = GoldenFeatureCalculator(engine)
    feature_names = ["r_fighter_w", "b_fighter_w"]
    vector = calc.build_full_feature_vector("Jon Jones", "Stipe Miocic", feature_names)

    assert vector is not None
    assert vector[0] == 27.0   # r_fighter_w → red corner
    assert vector[1] == 20.0   # b_fighter_w ← remapped from r_ of fighter2


def test_build_full_feature_vector_suffix_remapped_to_blue(engine):
    """
    *_r suffix features in fighter2 are remapped to *_b in all_stats.
    """
    _seed_fighter(engine, "A", features={"wins_3_r": 3.0})
    _seed_fighter(engine, "B", features={"wins_3_r": 1.0})

    calc = GoldenFeatureCalculator(engine)
    vector = calc.build_full_feature_vector("A", "B", ["wins_3_r", "wins_3_b"])

    assert vector[0] == 3.0   # A's wins_3_r stays as *_r
    assert vector[1] == 1.0   # B's wins_3_r remapped to wins_3_b


def test_build_full_feature_vector_missing_fighter_returns_none(engine):
    """Either fighter absent from DB → returns None (not an exception)."""
    _seed_fighter(engine, "Known Fighter")
    calc = GoldenFeatureCalculator(engine)

    assert calc.build_full_feature_vector("Known Fighter", "Ghost", ["r_fighter_w"]) is None
    assert calc.build_full_feature_vector("Ghost", "Known Fighter", ["r_fighter_w"]) is None


def test_build_full_feature_vector_mutual_exclusion_warning(engine, caplog):
    """
    When fighter1's last_fight_opp == fighter2, a WARNING is logged.
    The vector is still returned (not None) — it's non-fatal.
    """
    _seed_fighter(engine, "A", last_fight_opp="B", features={"r_fighter_w": 5.0})
    _seed_fighter(engine, "B", features={"r_fighter_w": 4.0})

    calc = GoldenFeatureCalculator(engine)
    with caplog.at_level(logging.WARNING, logger="golden_feature_calculator"):
        vector = calc.build_full_feature_vector("A", "B", ["r_fighter_w"])

    assert vector is not None
    assert any("Mutual-exclusion" in r.message for r in caplog.records)


def test_build_full_feature_vector_diff_features_computed(engine):
    """
    diff_fighter_w = r_fighter_w − b_fighter_w must be in the feature vector
    when feature_names includes it.
    """
    _seed_fighter(engine, "A", features={"r_fighter_w": 10.0})
    _seed_fighter(engine, "B", features={"r_fighter_w": 6.0})

    calc = GoldenFeatureCalculator(engine)
    vector = calc.build_full_feature_vector(
        "A", "B", ["r_fighter_w", "b_fighter_w", "diff_fighter_w"]
    )

    assert vector is not None
    assert vector[2] == pytest.approx(4.0)   # 10.0 - 6.0
