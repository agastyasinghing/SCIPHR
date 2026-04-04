"""
IntelligenceOrchestrator — coordinates all 9 intelligence modules.

Data flow per /predict call:
                                                              ┌──────────────┐
  POST /predict                                               │  fights table │
       │                                                      │  (history)    │
       ├─1─ XGBoost prediction → prob_f1, prob_f2             └──────┬────────┘
       │                                                             │
       ├─2─ _build_context(f1) ←─────────── DB: fighters + fights ──┘
       ├─3─ _build_context(f2) ←─────────── DB: fighters + fights
       │    (raises ValueError if latest_features=NULL)
       │
       ├─4─ _safe_compute(chaos_scorer)      → ChaosResult | None
       ├─5─ _safe_compute(perception_gap)    → PerceptionGapResult | None
       ├─6─ _safe_compute(narrative_trap)    → NarrativeTrapResult | None
       ├─7─ _safe_compute(value_bet)         → ValueBetResult (NO_ODDS if no fight_id)
       ├─8─ _safe_compute(fight_dna)         → FightDNAResult | None
       ├─9─ _safe_compute(false_consensus)   → FalseConsensusResult | None
       ├─10─ _safe_compute(nightmare_matchup)→ NightmareResult | None
       ├─11─ _safe_compute(win_path)         → WinPathResult | None
       ├─12─ badge_engine.compute(all above) → list[Badge]
       │
       └─► IntelligenceResult bundle

Max DB queries:
    2 × fighter profile+stats (fighters table, indexed by name)
    2 × fight history (fights table, r_name/b_name index)
    1 × odds_history (if fight_id provided)
    = 5 queries max regardless of how many modules run

Failure isolation:
    _safe_compute wraps each module call; any exception → None result + log.
    badge_engine handles None inputs gracefully (skips affected badges).
    If _build_context fails (fighter missing / latest_features=NULL),
    orchestrator.compute() logs the error and returns an empty IntelligenceResult.
    The XGBoost prediction itself is unaffected.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from .models import (
    Badge,
    FighterContext,
    IntelligenceResult,
    ValueBetResult,
)
from . import (
    badge_engine,
    chaos_scorer,
    false_consensus,
    fight_dna,
    narrative_trap,
    nightmare_matchup,
    perception_gap,
    value_bet,
    win_path,
)

log = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """
    Coordinates all 9 intelligence modules for a single /predict call.

    Usage (Phase 3 wiring in main.py):
        orchestrator = IntelligenceOrchestrator(engine)
        result = orchestrator.compute(
            f1_name="Conor McGregor",
            f2_name="Khabib Nurmagomedov",
            model_probs=(0.32, 0.68),
            fight_id=None,          # or event_fights.id when available
            event_fight=None,       # or dict from event_fights row
        )
        # result is IntelligenceResult; always returned even on partial failure
    """

    def __init__(self, engine):
        """
        Args:
            engine: SQLAlchemy Engine instance (already connected, pool_pre_ping).
                    Shared with the main FastAPI predictor — no new connections opened.
        """
        self.engine = engine

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def compute(
        self,
        f1_name: str,
        f2_name: str,
        model_probs: tuple[float, float],
        fight_id: Optional[int] = None,
        event_fight: Optional[dict] = None,
    ) -> IntelligenceResult:
        """
        Run all 9 intelligence modules and return a bundled IntelligenceResult.

        Args:
            f1_name:     Fighter 1 name (canonical, as stored in fighters table).
            f2_name:     Fighter 2 name.
            model_probs: (prob_f1, prob_f2) XGBoost model probabilities.
            fight_id:    event_fights.id if this is a scheduled card fight;
                         None for ad-hoc predictions (value_bet → NO_ODDS).
            event_fight: Full event_fights row as dict if available;
                         used by narrative_trap to read .narratives tags.

        Returns:
            IntelligenceResult — always returned, never raises.
            Modules that fail are None; value_bet is always present.
        """
        # ── Build fighter contexts (2+2 DB queries) ───────────────────────
        try:
            f1_ctx = self._build_context(f1_name)
            f2_ctx = self._build_context(f2_name)
        except Exception as exc:
            log.error(
                "IntelligenceOrchestrator: context build failed for %s vs %s: %s",
                f1_name, f2_name, exc,
            )
            return IntelligenceResult()

        # ── Run modules via _safe_compute ─────────────────────────────────
        chaos_res = self._safe_compute(
            chaos_scorer.compute, f1_ctx, f2_ctx,
            module_name="chaos_scorer",
        )
        gap_res = self._safe_compute(
            perception_gap.compute, f1_ctx, f2_ctx, model_probs,
            module_name="perception_gap",
        )
        narrative_res = self._safe_compute(
            narrative_trap.compute, f1_ctx, f2_ctx, event_fight,
            module_name="narrative_trap",
        )
        value_res = self._safe_compute(
            value_bet.compute,
            f1_ctx, f2_ctx, self.engine, fight_id,
            model_probs[0], model_probs[1],
            module_name="value_bet",
        )
        dna_res = self._safe_compute(
            fight_dna.compute, f1_ctx, f2_ctx,
            module_name="fight_dna",
        )
        consensus_res = self._safe_compute(
            false_consensus.compute, f1_ctx, f2_ctx, chaos_res, model_probs,
            module_name="false_consensus",
        )
        nightmare_res = self._safe_compute(
            nightmare_matchup.compute, f1_ctx, f2_ctx,
            module_name="nightmare_matchup",
        )
        win_res = self._safe_compute(
            win_path.compute, f1_ctx, f2_ctx, model_probs,
            module_name="win_path",
        )

        # value_bet must never be None — fall back to NO_ODDS sentinel
        if value_res is None:
            value_res = ValueBetResult()

        # ── Badge assignment ───────────────────────────────────────────────
        # badge_engine is called via _safe_compute so a NotImplementedError
        # (stub not yet filled by Opus) or any runtime error never propagates
        # to the caller — it degrades gracefully to an empty badge list.
        badges: list[Badge] = self._safe_compute(
            lambda: badge_engine.compute(
                chaos=chaos_res,
                gap=gap_res,
                narrative=narrative_res,
                value=value_res,
                dna=dna_res,
                consensus=consensus_res,
                nightmare=nightmare_res,
                win=win_res,
                f1_name=f1_name,
                f2_name=f2_name,
            ),
            module_name="badge_engine",
        ) or []

        return IntelligenceResult(
            chaos=chaos_res,
            perception_gap=gap_res,
            narrative_trap=narrative_res,
            value_bet=value_res,
            fight_dna=dna_res,
            false_consensus=consensus_res,
            nightmare=nightmare_res,
            win_path=win_res,
            badges=badges,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_context(self, fighter_name: str) -> FighterContext:
        """
        Load fighter profile stats + full career fight history from DB.

        Queries:
            1. fighters table — profile stats columns (not latest_features JSONB)
            2. fights table   — all historical fights, date DESC (no LIMIT;
                                max ~35 rows for most active fighters in dataset)

        Critical gap guard:
            If fighters.latest_features is NULL the migration has not run
            for this fighter.  We log a warning but continue — intelligence
            modules will compute with available profile stats only.

        Raises:
            ValueError if the fighter is not found in the fighters table at all.
        """
        with self.engine.connect() as conn:
            # ── Fighter profile ───────────────────────────────────────────
            row = conn.execute(
                text("""
                    SELECT wins, losses, draws, age, weight_lbs,
                           height_cm, reach_cm, weight_class,
                           slpm, str_acc, str_def,
                           td_avg, td_acc, td_def, sub_avg,
                           latest_features
                    FROM fighters
                    WHERE name = :name
                """),
                {"name": fighter_name},
            ).fetchone()

        if row is None:
            raise ValueError(
                f"Fighter '{fighter_name}' not found in fighters table. "
                "Ensure Phase 1 migration has run."
            )

        m = row._mapping

        # Warn on NULL latest_features but don't abort — modules degrade
        if m["latest_features"] is None:
            log.warning(
                "Fighter '%s' has latest_features=NULL — "
                "Phase 1 migration may not have populated this fighter. "
                "Intelligence modules will run with profile-only stats.",
                fighter_name,
            )

        stats = {
            "wins":        int(m.get("wins", 0) or 0),
            "losses":      int(m.get("losses", 0) or 0),
            "draws":       int(m.get("draws", 0) or 0),
            "age":         float(m.get("age", 0) or 0),
            "weight_lbs":  float(m.get("weight_lbs", 185) or 185),
            "height_cm":   float(m.get("height_cm", 0) or 0),
            "reach_cm":    float(m.get("reach_cm", 0) or 0),
            "weight_class": m.get("weight_class") or "Unknown",
            "slpm":        float(m.get("slpm", 0) or 0),
            "str_acc":     float(m.get("str_acc", 0) or 0),
            "str_def":     float(m.get("str_def", 0) or 0),
            "td_avg":      float(m.get("td_avg", 0) or 0),
            "td_acc":      float(m.get("td_acc", 0) or 0),
            "td_def":      float(m.get("td_def", 0) or 0),
            "sub_avg":     float(m.get("sub_avg", 0) or 0),
        }

        # ── Fight history ─────────────────────────────────────────────────
        with self.engine.connect() as conn:
            fight_rows = conn.execute(
                text("""
                    SELECT r_name, b_name, date, winner, method, weight_class
                    FROM fights
                    WHERE r_name = :name OR b_name = :name
                    ORDER BY date DESC
                """),
                {"name": fighter_name},
            ).fetchall()

        fights = [dict(r._mapping) for r in fight_rows]

        return FighterContext(
            name=fighter_name,
            stats=stats,
            fights=fights,
            wins=stats["wins"],
            losses=stats["losses"],
            draws=stats["draws"],
        )

    def _safe_compute(self, fn, *args, module_name: str):
        """
        Call fn(*args) and return its result.
        On any exception: log the error and return None.

        badge_engine and callers must handle None returns from any module.

        This is the sole error boundary for all intelligence modules.
        A failing module never propagates to the prediction response.
        """
        try:
            return fn(*args)
        except NotImplementedError:
            # Stubs raise NotImplementedError until Opus fills the formula.
            # Log at debug level — this is expected until Phase 2 is complete.
            log.debug("Intelligence module '%s' is not yet implemented.", module_name)
            return None
        except Exception as exc:
            log.error(
                "Intelligence module '%s' failed: %s: %s",
                module_name, type(exc).__name__, exc,
            )
            return None
