"""
SQLAlchemy models for SCIPHR.

Schema layout:
  fighters        — one row per fighter; latest profile stats + pre-normalized
                    XGBoost feature vector (latest_features JSON)
  fights          — one row per historical fight; metadata only (no feature
                    columns — PostgreSQL's ~1,600 col limit makes storing all
                    5,401 features as columns infeasible; see CLAUDE.md §Phase 1)
  predictions_log — every /predict call logged here; INSERT is try/except
                    wrapped in main.py so a log failure never fails the response
  events          — upcoming/recent UFC events; stub for Phase 3
  odds_history    — historical odds from The Odds API; stub for Phase 2/3

Relationships:
  fighters.name  ←──── fights.r_name / fights.b_name
  fighters.name  ←──── predictions_log.fighter1 / predictions_log.fighter2
  events.id      ←──── odds_history.event_id  (Phase 3)

Notes:
  - JSON type is used (not JSONB dialect type) for SQLite test compatibility.
    On PostgreSQL, SQLAlchemy maps JSON → jsonb when using the pg dialect with
    native_enum=False. For explicit JSONB indices add them in the Alembic
    migration (Phase 6, see TODOS.md).
  - Schema is created via Base.metadata.create_all(engine) in migrate_csv.py.
    Alembic versioning deferred to Phase 6 before production deploy.
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float,
    Integer, Text, UniqueConstraint, func,
)
from sqlalchemy import JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# BigInteger primary key that degrades to Integer on SQLite (for tests).
# PostgreSQL uses BIGSERIAL; SQLite uses its ROWID autoincrement.
_BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Fighter(Base):
    """
    One row per fighter.  Populated once by migrate_csv.py; static for v1
    (no live fight-ingestion pipeline until v3+).

    latest_features
        Pre-computed XGBoost input features stored in canonical 'red corner'
        form — all keys use r_* prefix or *_r suffix regardless of which
        corner the fighter occupied in their most recent fight.  This lets
        build_full_feature_vector() load fighter1 directly and remap fighter2
        by a simple r_* → b_* key swap, with no was_red branch needed at
        query time.

    was_red / last_fight_opp
        Stored for transparency and mutual-exclusion edge-case detection.
        If last_fight_opp == the predicted opponent, a warning is logged
        (the pre-computed features include context from that matchup).
    """
    __tablename__ = "fighters"

    id              = Column(_BigIntPK, primary_key=True, autoincrement=True)
    name            = Column(Text, unique=True, nullable=False, index=True)
    weight_class    = Column(Text)

    # Base profile stats (match original CSV key names via get_latest_fighter_stats mapping)
    weight_lbs      = Column(Float)
    height_cm       = Column(Float)
    reach_cm        = Column(Float)
    wins            = Column(Integer, default=0)
    losses          = Column(Integer, default=0)
    draws           = Column(Integer, default=0)
    age             = Column(Float)
    slpm            = Column(Float)
    str_acc         = Column(Float)
    str_def         = Column(Float)
    td_avg          = Column(Float)
    td_acc          = Column(Float)
    td_def          = Column(Float)
    sub_avg         = Column(Float)

    # XGBoost feature storage
    latest_features = Column(JSON)    # ~1,800 pre-calc features in r_* canonical form
    was_red         = Column(Boolean) # True if fighter was r_name in their last fight
    last_fight_date = Column(Date)
    last_fight_opp  = Column(Text)    # mutual-exclusion edge-case guard


class Fight(Base):
    """
    One row per historical fight.  Metadata only — no feature columns.
    Used by Phase 2 intelligence modules that need fight history
    (chaos scorer, win-path heuristics, etc.).
    """
    __tablename__ = "fights"
    __table_args__ = (
        UniqueConstraint("r_name", "b_name", "date", name="uq_fight"),
    )

    id           = Column(_BigIntPK, primary_key=True, autoincrement=True)
    r_name       = Column(Text, nullable=False, index=True)
    b_name       = Column(Text, nullable=False, index=True)
    date         = Column(Date, nullable=False, index=True)
    winner       = Column(Text)
    method       = Column(Text)
    weight_class = Column(Text)


class PredictionLog(Base):
    """
    Logged on every successful POST /predict call.
    The INSERT is wrapped in try/except in main.py — a DB failure here must
    never surface to the user or fail the prediction response.
    """
    __tablename__ = "predictions_log"

    id         = Column(_BigIntPK, primary_key=True, autoincrement=True)
    fighter1   = Column(Text, nullable=False)
    fighter2   = Column(Text, nullable=False)
    winner     = Column(Text)
    confidence = Column(Float)
    prob_f1    = Column(Float)
    prob_f2    = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    """
    Upcoming and recent UFC events.  Stub for Phase 3.
    Data populated manually via JSON curation (not from CSV).
    """
    __tablename__ = "events"

    id        = Column(_BigIntPK, primary_key=True, autoincrement=True)
    name      = Column(Text, nullable=False)
    date      = Column(Date, index=True)
    location  = Column(Text)
    main_card = Column(JSON)
    prelims   = Column(JSON)


class OddsHistory(Base):
    """
    Historical and current odds data.  Stub for Phase 2 (value_bet.py /
    The Odds API integration).
    """
    __tablename__ = "odds_history"

    id          = Column(_BigIntPK, primary_key=True, autoincrement=True)
    event_id    = Column(_BigIntPK)
    fighter1    = Column(Text)
    fighter2    = Column(Text)
    odds_f1     = Column(Float)
    odds_f2     = Column(Float)
    bookmaker   = Column(Text)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
