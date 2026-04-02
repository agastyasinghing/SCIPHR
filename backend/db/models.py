"""
SQLAlchemy models for SCIPHR.

Schema layout:
  fighters          — one row per fighter; latest profile stats + pre-normalized
                      XGBoost feature vector (latest_features JSON)
  fights            — one row per historical fight; metadata only (no feature
                      columns — see TODOS.md TODO-02 re PRD §11 divergence)
  events            — upcoming/recent UFC events; manually curated for v1
  event_fights      — individual fights on an event card; narrative-tagged
  predictions_log   — every /predict call logged here; INSERT is try/except
                      wrapped in main.py so a log failure never fails the response
  odds_history      — per-fighter odds snapshots from The Odds API (Phase 2/3)
  narrative_outcomes— tracks Narrative Trap prediction outcomes over time (Phase 2)

Relationships:
  fighters.name       ←──── fights.r_name / fights.b_name
  fighters.name       ←──── predictions_log.fighter1 / predictions_log.fighter2
  events.id           ←──── event_fights.event_id
  events.id           ←──── predictions_log.event_id
  event_fights.id     ←──── predictions_log.fight_id
  event_fights.id     ←──── odds_history.fight_id
  predictions_log.id  ←──── narrative_outcomes.prediction_id

Notes:
  - JSON type is used (not JSONB dialect type) for SQLite test compatibility.
    On PostgreSQL, SQLAlchemy maps JSON → jsonb when using the pg dialect with
    native_enum=False. For explicit JSONB indices add them in the Alembic
    migration (Phase 6, see TODOS.md TODO-01).
  - Schema is created via Base.metadata.create_all(engine) in migrate_csv.py.
    Alembic versioning deferred to Phase 6 before production deploy.
  - PRD §11 specifies 5,401 feature columns in the fights table; actual design
    stores features as JSONB on fighters.latest_features (Supabase free-tier
    size constraint). See TODOS.md TODO-02.
  - PRD §15 specifies asyncpg; implementation uses sync psycopg2 because the
    prediction pipeline is sync Python. See TODOS.md TODO-02.
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float,
    ForeignKey, Integer, Numeric, Text, UniqueConstraint, func,
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

    style
        Fighting style: STRIKER | WRESTLER | GRAPPLER | BRAWLER | COUNTER.
        Used by nightmare_matchup.py and win_path.py in Phase 2.
        NULL until Phase 2 populates it (not derivable from CSV alone).

    Computed fields (aura_score, chaos_contribution, mirage_meter, composite_score)
        Populated by Phase 2 intelligence modules, refreshed weekly.
        Columns defined here so Phase 2 can UPDATE without a schema migration.
    """
    __tablename__ = "fighters"

    id              = Column(_BigIntPK, primary_key=True, autoincrement=True)
    name            = Column(Text, unique=True, nullable=False, index=True)
    nickname        = Column(Text)
    weight_class    = Column(Text)
    style           = Column(Text)           # STRIKER | WRESTLER | GRAPPLER | BRAWLER | COUNTER
    is_active       = Column(Boolean, default=True)
    photo_path      = Column(Text)           # relative path or URL; populated post-launch

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

    # Phase 2 computed intelligence scores — NULL until intelligence modules run
    aura_score          = Column(Numeric(5, 2))  # Perception Gap engine
    chaos_contribution  = Column(Numeric(5, 2))  # how much does this fighter raise fight chaos?
    mirage_meter        = Column(Numeric(5, 2))  # resume inflation index
    composite_score     = Column(Numeric(5, 2))  # overall SCIPHR quality rating
    last_computed_at    = Column(DateTime(timezone=True))

    # XGBoost feature storage
    latest_features = Column(JSON)    # ~1,800 pre-calc features in r_* canonical form
    was_red         = Column(Boolean) # True if fighter was r_name in their last fight
    last_fight_date = Column(Date)
    last_fight_opp  = Column(Text)    # mutual-exclusion edge-case guard

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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


class Event(Base):
    """
    Upcoming and recent UFC events.  Manually curated for v1.
    Data populated via JSON curation (not from CSV).

    card_temperature  CHALK | MIXED | CHAOS | DOG — set by intelligence engine
                      or manually overridden for Phase 3 Dashboard.
    is_published      FALSE until the event is ready to show on the Dashboard.
    """
    __tablename__ = "events"

    id              = Column(_BigIntPK, primary_key=True, autoincrement=True)
    event_name      = Column(Text, nullable=False)
    event_date      = Column(Date, index=True)
    location        = Column(Text)
    card_temperature    = Column(Text)           # CHALK | MIXED | CHAOS | DOG
    avg_chaos_score     = Column(Numeric(4, 2))
    is_published        = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EventFight(Base):
    """
    Individual fights on an event card.

    narratives  — manually tagged narrative signals for Narrative Trap detector.
                  JSONB list of strings, e.g. ["HYPE_TRAIN", "REVENGE_FIGHT"].
                  Phase 2 narrative_trap.py reads these at prediction time.
    notes       — fight-week intel: injuries, camp news, weight miss, etc.
    """
    __tablename__ = "event_fights"

    id              = Column(_BigIntPK, primary_key=True, autoincrement=True)
    event_id        = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    fighter1_name   = Column(Text, nullable=False)
    fighter2_name   = Column(Text, nullable=False)
    card_position   = Column(Text)  # MAIN_EVENT | CO_MAIN | MAIN_CARD | PRELIM | EARLY_PRELIM
    weight_class    = Column(Text)
    is_title_fight  = Column(Boolean, default=False)
    narratives      = Column(JSON)           # list[str] — narrative signal tags
    short_notice    = Column(Boolean, default=False)
    weight_miss     = Column(Boolean, default=False)
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


class PredictionLog(Base):
    """
    Logged on every successful POST /predict call.
    The INSERT is wrapped in try/except in main.py — a DB failure here must
    never surface to the user or fail the prediction response.

    Intelligence signal columns (chaos_score through odds_at_prediction) are
    NULL in Phase 1 — populated starting Phase 2 when intelligence modules
    are wired into /predict.

    Post-fight resolution columns (actual_winner through resolved_at) are
    NULL until the fight happens and an admin resolves the prediction.
    These feed the Historical Scorecard (Phase 4).
    """
    __tablename__ = "predictions_log"

    id              = Column(_BigIntPK, primary_key=True, autoincrement=True)
    fighter1        = Column(Text, nullable=False)
    fighter2        = Column(Text, nullable=False)
    winner          = Column(Text)
    confidence      = Column(Float)
    prob_f1         = Column(Float)
    prob_f2         = Column(Float)

    # Intelligence signals — NULL until Phase 2 wires these into /predict
    chaos_score     = Column(Numeric(4, 2))
    perception_gap  = Column(Numeric(6, 2))  # fighter1_gap - fighter2_gap
    narrative_risk  = Column(Text)           # LOW | MODERATE | HIGH
    value_signal    = Column(Text)           # STRONG_EDGE | EDGE_DETECTED | NO_EDGE | FADE_OPPORTUNITY
    edge_pct        = Column(Numeric(5, 4))  # Kelly edge fraction
    odds_at_prediction = Column(JSON)        # {fighter1: {american: -185, implied: 0.649}, ...}

    # Event / fight linkage — NULL until event_fights are populated (Phase 3)
    event_id        = Column(Integer, ForeignKey("events.id"))
    fight_id        = Column(Integer, ForeignKey("event_fights.id"))

    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Post-fight resolution — NULL until fight resolves; populated by admin tool (Phase 4)
    actual_winner   = Column(Text)
    was_correct     = Column(Boolean)
    actual_method   = Column(Text)           # KO | TKO | SUB | DEC | NC
    actual_round    = Column(Integer)
    resolved_at     = Column(DateTime(timezone=True))


class OddsHistory(Base):
    """
    Per-fighter odds snapshots from The Odds API.
    One row per fighter per recording — matches the Sharp Money Indicator's
    need to detect line movement between opening and closing lines.

    fight_id FK points to event_fights (not events) for fight-level granularity.
    is_opening_line TRUE for the first snapshot recorded for this fight.
    """
    __tablename__ = "odds_history"

    id                  = Column(_BigIntPK, primary_key=True, autoincrement=True)
    fight_id            = Column(Integer, ForeignKey("event_fights.id"), index=True)
    fighter_name        = Column(Text, nullable=False)
    american_odds       = Column(Integer, nullable=False)
    implied_probability = Column(Numeric(5, 4), nullable=False)
    is_opening_line     = Column(Boolean, default=False)
    recorded_at         = Column(DateTime(timezone=True), server_default=func.now())


class NarrativeOutcome(Base):
    """
    Tracks Narrative Trap prediction outcomes over time.
    Populated after each fight resolves — validates whether flagged narrative
    traps actually correlated with upsets.  Feeds the /scorecard/narrative-traps
    endpoint (Phase 4).
    """
    __tablename__ = "narrative_outcomes"

    id                  = Column(_BigIntPK, primary_key=True, autoincrement=True)
    prediction_id       = Column(Integer, ForeignKey("predictions_log.id"), nullable=False, index=True)
    narrative_type      = Column(Text, nullable=False)  # e.g. "HYPE_TRAIN", "REVENGE_FIGHT"
    was_trap_flagged    = Column(Boolean, nullable=False)
    hyped_fighter_won   = Column(Boolean)               # NULL until fight resolves
    resolved_at         = Column(DateTime(timezone=True))
