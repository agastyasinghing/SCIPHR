"""
DB-backed feature calculator for SCIPHR (Phase 1+).

Replaces the CSV/pandas data-loading approach with two indexed DB queries
per prediction.  The public interface is unchanged — predictor_golden.py
calls the same get_latest_fighter_stats() and build_full_feature_vector()
methods it always did.

Data flow for build_full_feature_vector():
  ┌──────────────────────────────────────────────────────────────────┐
  │  fighters table (DB)                                             │
  │    fighter1 row → latest_features  (canonical r_* form)         │
  │    fighter2 row → latest_features  (canonical r_* form)         │
  └─────────────────────┬────────────────────────┬───────────────────┘
                        │                        │
                 used directly               remapped:
                 as r_* in all_stats         r_* → b_*, *_r → *_b
                        │                        │
                        └──────────┬─────────────┘
                                   ▼
                         _calculate_differences()
                         adds diff_STAT = r_STAT - b_STAT
                                   ▼
                         assemble 5,401-feature vector
                         in model-expected order
                                   ▼
                         XGBoost.predict()

Feature pre-normalization (done at migration time in migrate_csv.py):
  All features in latest_features use canonical r_* / *_r keys regardless
  of which corner the fighter was actually in.  was_red is stored in the
  DB for debugging and mutual-exclusion edge-case detection only.
"""

import json
import logging
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


def _parse_json(val) -> dict:
    """
    Ensure a value from a JSON/JSONB column is a Python dict.
    PostgreSQL returns dicts directly; SQLite returns raw JSON strings.
    """
    if val is None:
        return {}
    if isinstance(val, str):
        return json.loads(val)
    return val


class GoldenFeatureCalculator:
    """
    Extracts fighter features from PostgreSQL instead of CSV.
    Initialized with a SQLAlchemy Engine (sync, psycopg2).
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        log.info("GoldenFeatureCalculator initialised (DB-backed)")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_latest_fighter_stats(self, fighter_name: str) -> dict:
        """
        Return base profile stats for a fighter as a dict with the original
        CSV key names expected by main.py and predictor_golden.py callers.
        Returns {} if the fighter is not found.

        Key mapping (DB column → CSV key):
          wins     → fighter_w       slpm    → fighter_SlpM
          losses   → fighter_l       str_acc → fighter_Str_Acc
          draws    → fighter_d       str_def → fighter_Str_Def
          age      → age             td_avg  → fighter_TD_Avg
          height_cm→ fighter_height_cm  ...
        """
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM fighters WHERE name = :name"),
                {"name": fighter_name},
            ).fetchone()

        if row is None:
            log.debug("get_latest_fighter_stats: '%s' not found", fighter_name)
            return {}

        m = row._mapping
        return {
            "fighter_w":          float(m.get("wins", 0) or 0),
            "fighter_l":          float(m.get("losses", 0) or 0),
            "fighter_d":          float(m.get("draws", 0) or 0),
            "age":                float(m.get("age", 0) or 0),
            "fighter_height_cm":  float(m.get("height_cm", 0) or 0),
            "fighter_reach_cm":   float(m.get("reach_cm", 0) or 0),
            "fighter_weight_lbs": float(m.get("weight_lbs", 185) or 185),
            "fighter_SlpM":       float(m.get("slpm", 0) or 0),
            "fighter_Str_Acc":    float(m.get("str_acc", 0) or 0),
            "fighter_Str_Def":    float(m.get("str_def", 0) or 0),
            "fighter_TD_Avg":     float(m.get("td_avg", 0) or 0),
            "fighter_TD_Acc":     float(m.get("td_acc", 0) or 0),
            "fighter_TD_Def":     float(m.get("td_def", 0) or 0),
            "fighter_Sub_Avg":    float(m.get("sub_avg", 0) or 0),
            "knockdowns":         0.0,  # not stored in Phase 1; Phase 2 adds it
        }

    def build_full_feature_vector(
        self,
        fighter1_name: str,
        fighter2_name: str,
        feature_names: list,
    ) -> Optional[list]:
        """
        Build the 5,401-element feature vector expected by the XGBoost model.

        fighter1 is placed in the red corner; fighter2 in the blue corner.
        Returns None if either fighter is missing from the DB.

        Steps:
          1. Fetch latest_features for both fighters (2 indexed PK queries).
          2. Warn if mutual-exclusion edge case is detected.
          3. Load fighter1's features directly into all_stats (r_* keys).
          4. Remap fighter2's features from r_* → b_* into all_stats.
          5. Compute diff_STAT = r_STAT − b_STAT via _calculate_differences().
          6. Build ordered vector from feature_names (0.0 for missing).
        """
        with self.engine.connect() as conn:
            f1_row = conn.execute(
                text(
                    "SELECT latest_features, last_fight_opp, name "
                    "FROM fighters WHERE name = :name"
                ),
                {"name": fighter1_name},
            ).fetchone()
            f2_row = conn.execute(
                text(
                    "SELECT latest_features, last_fight_opp, name "
                    "FROM fighters WHERE name = :name"
                ),
                {"name": fighter2_name},
            ).fetchone()

        if f1_row is None:
            log.warning("build_full_feature_vector: fighter not found: '%s'", fighter1_name)
            return None
        if f2_row is None:
            log.warning("build_full_feature_vector: fighter not found: '%s'", fighter2_name)
            return None

        # Mutual-exclusion edge case: fighter1's last fight was against fighter2.
        # Features are pre-computed and include context from that matchup.
        if f1_row.last_fight_opp and f1_row.last_fight_opp == fighter2_name:
            log.warning(
                "Mutual-exclusion: %s's most recent fight was against %s. "
                "Pre-computed features may include context from their last matchup.",
                fighter1_name,
                fighter2_name,
            )

        f1_features: dict = _parse_json(f1_row.latest_features)
        f2_features: dict = _parse_json(f2_row.latest_features)

        all_stats: dict = {}

        # ── Fighter 1 → red corner ─────────────────────────────────────────
        # latest_features already in canonical r_* form; use directly.
        all_stats.update(f1_features)
        log.debug(
            "Fighter 1 (%s): loaded %d features into red corner",
            fighter1_name,
            len(f1_features),
        )

        # ── Fighter 2 → blue corner ────────────────────────────────────────
        # Remap r_* → b_*,  *_r → *_b
        f2_count = 0
        for key, val in f2_features.items():
            if key.startswith("r_"):
                all_stats["b_" + key[2:]] = val
                f2_count += 1
            elif key.endswith("_r") and not key.startswith("r_"):
                all_stats[key[:-2] + "_b"] = val
                f2_count += 1
        log.debug(
            "Fighter 2 (%s): remapped %d features into blue corner",
            fighter2_name,
            f2_count,
        )

        log.debug(
            "FINAL CHECK — r_fighter_w (should be %s): %s | b_fighter_w (should be %s): %s",
            fighter1_name,
            all_stats.get("r_fighter_w", "MISSING"),
            fighter2_name,
            all_stats.get("b_fighter_w", "MISSING"),
        )

        # ── Matchup-specific difference features ──────────────────────────
        self._calculate_differences(all_stats)

        # ── Assemble feature vector in model-expected order ────────────────
        temp_df = pd.DataFrame([all_stats])

        # String columns → categorical codes (same as original implementation)
        object_cols = temp_df.select_dtypes(include=["object"]).columns
        for col in object_cols:
            temp_df[col] = pd.Categorical(temp_df[col]).codes

        feature_vector = []
        missing_count = 0
        for feature_name in feature_names:
            if feature_name in temp_df.columns:
                val = temp_df[feature_name].iloc[0]
                if pd.notna(val) and np.isfinite(float(val)):
                    feature_vector.append(float(val))
                else:
                    feature_vector.append(0.0)
            else:
                feature_vector.append(0.0)
                missing_count += 1

        non_zero = sum(1 for f in feature_vector if f != 0)
        log.debug(
            "Built %d features (%d non-zero, %d missing/defaulted)",
            len(feature_vector),
            non_zero,
            missing_count,
        )

        return feature_vector

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calculate_differences(self, all_stats: dict) -> None:
        """
        Add diff_STAT = r_STAT − b_STAT for every paired r_*/b_* stat.
        Operates in-place on all_stats.  Unchanged from the original CSV
        implementation — the dict-based input is data-source agnostic.
        """
        # Prefix-based pairs  (r_fighter_w / b_fighter_w → diff_fighter_w)
        r_stats = {k: v for k, v in all_stats.items() if k.startswith("r_")}
        for r_key, r_val in r_stats.items():
            b_key = "b_" + r_key[2:]
            if b_key in all_stats:
                b_val = all_stats[b_key]
                if (
                    pd.api.types.is_numeric_dtype(type(r_val))
                    and pd.api.types.is_numeric_dtype(type(b_val))
                    and pd.notna(r_val)
                    and pd.notna(b_val)
                ):
                    all_stats["diff_" + r_key[2:]] = r_val - b_val

        # Suffix-based pairs  (wins_3_r / wins_3_b → diff_wins_3)
        r_suffix_stats = {
            k: v for k, v in all_stats.items()
            if k.endswith("_r") and not k.startswith("r_")
        }
        for r_key, r_val in r_suffix_stats.items():
            b_key = r_key[:-2] + "_b"
            if b_key in all_stats:
                b_val = all_stats[b_key]
                if (
                    pd.api.types.is_numeric_dtype(type(r_val))
                    and pd.api.types.is_numeric_dtype(type(b_val))
                    and pd.notna(r_val)
                    and pd.notna(b_val)
                ):
                    all_stats["diff_" + r_key[:-2]] = r_val - b_val
