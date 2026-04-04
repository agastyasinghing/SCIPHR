"""
Shared pytest fixtures for SCIPHR backend tests.

Phase 1 fixtures:  engine (SQLite in-memory with all tables)
Phase 2 fixtures:  FighterContext variants for intelligence module tests

Uses SQLite in-memory so tests run without a real PostgreSQL instance.
SQLAlchemy's JSON type maps to TEXT in SQLite — read/write behaviour is
identical to PostgreSQL for our use cases (dict serialization).
"""

import sys
import os

# Ensure backend/ is on the path (for db.models, intelligence.*)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Ensure src/ is on the path (for golden_feature_calculator)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from db.models import Base


# ---------------------------------------------------------------------------
# Phase 1: DB engine fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """
    Fresh SQLite in-memory engine with all tables created.

    StaticPool: forces all connections to share the same underlying SQLite
    connection so tables created by create_all() are visible to every
    subsequent call (including calls from FastAPI's request-handler threads).

    check_same_thread=False: SQLite's default single-thread guard would reject
    connections re-used across FastAPI's threadpool — disable it since we own
    the engine and control its lifecycle within a single test.
    """
    e = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    yield e
    e.dispose()


# ---------------------------------------------------------------------------
# Phase 2: FighterContext fixtures for intelligence module tests
#
# These fixtures cover the key test branches defined in the Phase 2
# test review diagram (items [8]–[12], [22], [24]–[29]).
#
# Stat keys match fighters table column names:
#   slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg,
#   wins, losses, draws, age, weight_lbs, height_cm, reach_cm, weight_class
#
# Fight dicts match fights table columns:
#   r_name, b_name, date, winner, method, weight_class
# ---------------------------------------------------------------------------

from intelligence.models import FighterContext


def _make_fight(r_name, b_name, winner, method, date="2023-01-01"):
    return {
        "r_name": r_name,
        "b_name": b_name,
        "date": date,
        "winner": winner,
        "method": method,
        "weight_class": "Lightweight",
    }


@pytest.fixture
def striker_stats():
    """Profile stats for a high-output striker (STRIKER style)."""
    return {
        "wins": 18, "losses": 3, "draws": 0, "age": 30.0,
        "weight_lbs": 155.0, "height_cm": 175.0, "reach_cm": 178.0,
        "weight_class": "Lightweight",
        "slpm": 5.8, "str_acc": 0.47, "str_def": 0.58,
        "td_avg": 0.8, "td_acc": 0.35, "td_def": 0.72,
        "sub_avg": 0.3,
    }


@pytest.fixture
def grappler_stats():
    """Profile stats for a submission grappler (GRAPPLER style)."""
    return {
        "wins": 14, "losses": 4, "draws": 0, "age": 28.0,
        "weight_lbs": 155.0, "height_cm": 172.0, "reach_cm": 174.0,
        "weight_class": "Lightweight",
        "slpm": 2.1, "str_acc": 0.38, "str_def": 0.52,
        "td_avg": 4.2, "td_acc": 0.62, "td_def": 0.55,
        "sub_avg": 2.1,
    }


@pytest.fixture
def wrestler_stats():
    """Profile stats for a pure wrestler (WRESTLER style)."""
    return {
        "wins": 20, "losses": 5, "draws": 1, "age": 32.0,
        "weight_lbs": 170.0, "height_cm": 178.0, "reach_cm": 180.0,
        "weight_class": "Welterweight",
        "slpm": 2.8, "str_acc": 0.41, "str_def": 0.60,
        "td_avg": 4.5, "td_acc": 0.58, "td_def": 0.68,
        "sub_avg": 0.6,
    }


@pytest.fixture
def counter_stats():
    """Profile stats for a counter-striker (COUNTER style)."""
    return {
        "wins": 12, "losses": 2, "draws": 0, "age": 27.0,
        "weight_lbs": 145.0, "height_cm": 170.0, "reach_cm": 177.0,
        "weight_class": "Featherweight",
        "slpm": 2.4, "str_acc": 0.55, "str_def": 0.70,
        "td_avg": 1.0, "td_acc": 0.40, "td_def": 0.65,
        "sub_avg": 0.5,
    }


@pytest.fixture
def zero_stats():
    """All-zero stats (edge case: new fighter or data gap)."""
    return {
        "wins": 0, "losses": 0, "draws": 0, "age": 0.0,
        "weight_lbs": 185.0, "height_cm": 0.0, "reach_cm": 0.0,
        "weight_class": "Unknown",
        "slpm": 0.0, "str_acc": 0.0, "str_def": 0.0,
        "td_avg": 0.0, "td_acc": 0.0, "td_def": 0.0,
        "sub_avg": 0.0,
    }


# ── FighterContext fixtures ───────────────────────────────────────────────

@pytest.fixture
def f1_ctx(striker_stats):
    """Fighter 1: high-output striker, 5 KO/TKO wins in last 6 fights."""
    fights = [
        _make_fight("F1", "Opp1", "F1", "KO/TKO", "2024-03-01"),
        _make_fight("F1", "Opp2", "F1", "KO/TKO", "2023-09-01"),
        _make_fight("Opp3", "F1", "Opp3", "Decision - Unanimous", "2023-01-01"),
        _make_fight("F1", "Opp4", "F1", "KO/TKO", "2022-06-01"),
        _make_fight("F1", "Opp5", "F1", "KO/TKO", "2021-11-01"),
        _make_fight("Opp6", "F1", "F1", "Submission", "2021-03-01"),
    ]
    return FighterContext(
        name="F1",
        stats=striker_stats,
        fights=fights,
        wins=striker_stats["wins"],
        losses=striker_stats["losses"],
        draws=striker_stats["draws"],
    )


@pytest.fixture
def f2_ctx(grappler_stats):
    """Fighter 2: submission grappler, 4 submission wins in last 5 fights."""
    fights = [
        _make_fight("F2", "Opp7", "F2", "Submission", "2024-02-01"),
        _make_fight("Opp8", "F2", "F2", "Submission", "2023-08-01"),
        _make_fight("F2", "Opp9", "F2", "Decision - Unanimous", "2023-02-01"),
        _make_fight("F2", "Opp10", "F2", "Submission", "2022-07-01"),
        _make_fight("Opp11", "F2", "Opp11", "KO/TKO", "2021-12-01"),
    ]
    return FighterContext(
        name="F2",
        stats=grappler_stats,
        fights=fights,
        wins=grappler_stats["wins"],
        losses=grappler_stats["losses"],
        draws=grappler_stats["draws"],
    )


@pytest.fixture
def high_finish_ctx_f1(striker_stats):
    """Fighter with very high finish rate: 8/8 fights end in KO/TKO."""
    fights = [
        _make_fight("HF1", f"Opp{i}", "HF1" if i % 4 != 0 else f"Opp{i}", "KO/TKO", f"202{3-i//4}-01-01")
        for i in range(8)
    ]
    return FighterContext(
        name="HF1", stats=striker_stats, fights=fights, wins=6, losses=2, draws=0
    )


@pytest.fixture
def high_finish_ctx_f2(striker_stats):
    """Opponent: also high finish rate — all 7 fights ended in finish."""
    fights = [
        _make_fight("HF2", f"Opp{i+10}", "HF2", "KO/TKO" if i < 4 else "Submission", f"202{3-i//3}-06-01")
        for i in range(7)
    ]
    return FighterContext(
        name="HF2", stats=striker_stats, fights=fights, wins=7, losses=0, draws=0
    )


@pytest.fixture
def dec_ctx_f1(counter_stats):
    """Decision specialist: all 10 fights went to decision."""
    fights = [
        _make_fight("DC1", f"Opp{i}", "DC1" if i % 3 != 0 else f"Opp{i}", "Decision - Unanimous", f"202{3-i//4}-01-01")
        for i in range(10)
    ]
    return FighterContext(
        name="DC1", stats=counter_stats, fights=fights, wins=7, losses=3, draws=0
    )


@pytest.fixture
def dec_ctx_f2(counter_stats):
    """Opponent decision specialist: 9/9 fights went to decision."""
    fights = [
        _make_fight("DC2", f"Opp{i+20}", "DC2", "Decision - Split" if i % 2 else "Decision - Unanimous", f"202{3-i//4}-06-01")
        for i in range(9)
    ]
    return FighterContext(
        name="DC2", stats=counter_stats, fights=fights, wins=9, losses=0, draws=0
    )


@pytest.fixture
def zero_fight_ctx(zero_stats):
    """New fighter with zero fight history (edge case)."""
    return FighterContext(
        name="NewFighter",
        stats=zero_stats,
        fights=[],
        wins=0,
        losses=0,
        draws=0,
    )
