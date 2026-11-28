# FTR-01A — Fighter Data Integrity Audit & Multi-Label Style Architecture

**Ticket:** FTR-01A (investigation + documentation only)
**Repo state audited:** branch `main`, HEAD `53b7c1c7ac72646e6bf1cf7a41d3c3c376a5fd43` (merge of PR #21, v0.1.16.1)
**Worktree:** one pre-existing uncommitted change (`backend/requirements-prod.txt`, `anyio 3.7.1 → 4.9.0`) — untouched.
**Audit date:** 2026-11-23 (environment date)
**Application code / schema / DB data / model changed by this ticket:** none (see §8).

**Status labels used throughout**

| Label | Meaning |
|---|---|
| **CONFIRMED** | Reproduced by running code, a read-only SQL query, or read directly from source in this session |
| **INFERRED** | Strongly implied by confirmed facts, but not directly observed |
| **PROPOSED** | A design recommendation of this audit; not a fact |
| **UNKNOWN** | Could not be established from the evidence available; needs a human or missing artifact |

**Defect class tags:** **[SRC]** = source-data / data-pipeline defect, **[APP]** = application-logic defect, **[SRC+APP]** = source gap made user-visible by application logic.

---

## 1. Executive summary

1. **The "zeros" are real gaps made to look like measurements.** Nullability is destroyed twice before it reaches the DB: `src/convert_golden_FULL.py:86` runs `converted.fillna(0)` on the whole dataset, then `backend/scripts/migrate_csv.py:132-149` (`_clean`) and `:182-208` (`_extract_base_stats`) coerce anything non-numeric to `0.0`. The `fighters` table has **no NULLs in any stat column** (CONFIRMED), so *the database cannot tell "measured 0" from "missing" for any field.* Availability must therefore be **inferred by rule** (§4) until the original source file is recovered.
2. **Read-only re-verification matches the earlier audit exactly** (§2.2): 2,615 fighters; 8,231 fights; 181 fighters with all seven core stats zero; 672 with zero height or reach; 158 with zero age; 0 fights with a method; 0 fighters with a style or any intelligence score; 2,615/2,615 `is_active = true`; latest fight 2025-10-04.
3. **Eight of the nine suspected logic bugs are confirmed and reproduced** (§3); the ninth (Composite saturation) is worse than suspected — it is a ×100 unit error that makes Composite = 100 for **9,260 of 9,261** points on a uniform input grid. Additional directly-related defects were found, most importantly: **`perception_gap` raises `TypeError` on every real DB row** (date object vs string comparison, masked by string-date test fixtures), **`win_path` counts every win with a NULL method as a decision**, and **finish-dependent signals are identically zero for every fighter** because no fight has a method.
4. **Style should not be derived from `classify_style()`.** It is a single-label, first-match ladder that returns `STRIKER` as an unconditional default (`backend/intelligence/utils.py:65`), and a test asserts that default (`backend/tests/test_utils.py:49-54`). §5 proposes a transparent, division-relative, multi-label classifier with an explicit *unclassified* outcome and **no numeric confidence** (there is no ground truth to calibrate one against).
5. **The prediction engine can be fully isolated.** The XGBoost path reads only `fighters.latest_features` (JSONB) via `build_full_feature_vector()`. Every defect above lives in the *display* columns (`slpm`, `str_def`, …), the profile endpoint, or the heuristic intelligence modules. §7 proposes a read-model layer that touches none of the model inputs, and a hash-based isolation test.
6. **Two findings the ticket did not anticipate** change the style design:
   - **Women's divisions are not represented in `fighters.weight_class`.** 256 fighters have Women's fights (864 fight rows), but `fighters.weight_class` contains only men's division names, derived from `weight_lbs`. The entire "Strawweight" bucket (102) is women. A naive per-`fighters.weight_class` percentile would rank women against a mixed pool and men against nobody comparable. Division must come from the `fights` table (§5.3).
   - **The original source CSV is not in the repo** (`data/` does not exist locally; `.gitignore` excludes it). Everything about *why* a value is zero upstream is inferred from the conversion/migration scripts. Recovering `data/UFC_full_data_golden.csv` is the single highest-leverage unblock (Decision D1).

---

## 2. Verified current state and source provenance

### 2.1 Pipeline trace

```
data/UFC_full_data_golden.csv   (NOT in repo — UNKNOWN content)
   │  src/convert_golden_FULL.py
   │    :26-37  f_1_* → r_*, f_2_* → b_*
   │    :76-82  copies 'weight_class','gender','result','result_details',
   │            'finish_round','finish_time', … *only if present in source*
   │    :86     converted = converted.fillna(0)          ← NULLABILITY LOST (1)
   ▼
data/golden_full_converted.csv  (NOT in repo)
   │  backend/scripts/migrate_csv.py
   │    :132-149 _clean(): NaN/Inf → 0.0, non-parsable → 0.0   ← NULLABILITY LOST (2)
   │    :182-208 _extract_base_stats(): float(g(k) or 0)       ← "or 0" coerces None/NaN
   │    :346     method = row.get("finish")   ← column name 'finish' is not copied by
   │                                           convert_golden_FULL.py:76-78 → always NaN
   │    :347     weight_class = row.get("weight_class")  (raw, uncleaned → '0' string)
   │    :191     weight_lbs default 185 → fighters.weight_class via _weight_class()
   ▼
PostgreSQL (Supabase)
   fighters: base stat columns (Float, no NULLs)  +  latest_features JSONB (model input)
   fights:   r_name,b_name,date,winner,method,weight_class
   │
   ├─ MODEL PATH:  fighters.latest_features → build_full_feature_vector()
   │               (src/golden_feature_calculator.py:115-238) → XGBoost
   │
   └─ DISPLAY PATH: fighters base columns → get_latest_fighter_stats()
                    (golden_feature_calculator.py:73-113; `or 0` on every field,
                     `knockdowns` hard-coded 0.0 at :112)
                    → GET /fighter/{name} (backend/main.py:478-609)
                    → FighterProfile.jsx (frontend/src/pages/FighterProfile.jsx:99-123)
```

All of the above lines are CONFIRMED by reading the files. That `finish` is never populated is CONFIRMED by DB (`fights.method IS NOT NULL` → 0 rows) and by static reading; that the *source* CSV lacks a `finish` column (vs. having one that is all-NaN) is **INFERRED** (the conversion script never copies one; `result` / `result_details` / `finish_round` / `finish_time` are copied if present — whether they hold method information is **UNKNOWN** until the CSV is inspected).

### 2.2 Database facts (read-only SELECTs, session `default_transaction_read_only=on`, 2026-11-23)

All counts below are **CONFIRMED** and match the earlier investigation.

| Fact | Value |
|---|---|
| `fighters` rows | 2,615 |
| `fights` rows | 8,231 (1994-03-11 → 2025-10-04) |
| Fighters, all 7 core stats = 0 (`slpm,str_acc,str_def,td_avg,td_acc,td_def,sub_avg`) | **181** |
| …of which have exactly 1 UFC fight in `fights` | 121 (67%); 2 fights: 33; ≥3 fights: 27; max 13 |
| …of which have ≥2 fights but all-zero career block | **60** (50 of these have non-zero rolling-window features, so the gap is specific to the `fighter_*` career block) |
| Zero height or zero reach | 672 (height 0: 41; reach 0: 671; both: 40) |
| Zero reach among fighters whose last fight ≥ 2015 | 123 (older fighters: 548) |
| Zero age | 158 (123 of them also all-zero stats) |
| Any NULL in `slpm`/`td_avg`/`height_cm` | **0** |
| `fights.method` non-NULL | **0 of 8,231** |
| `fights.winner` not equal to either corner name | 1 (`'No Contest'`: Zachary Reese vs Sedriques Dumas, 2025-09-13) |
| `fighters.style` non-NULL | 0 |
| Any of `aura_score/composite_score/mirage_meter/chaos_contribution` non-NULL | 0 |
| `is_active` | `true` for 2,615 / 2,615 |
| Fighters with `draws > 0` | 436 |
| `fights.weight_class` anomalies | 10 rows `'0'`; 1 `'Nieznana'`; 3 `'UFC … Title'`; 3 `'UFC n Tournament Title'`; `Open Weight` 101; `Catch Weight` 72 |
| Women's fight rows / distinct women fighters | 864 / 256 |
| `fighters.weight_class` values | men's names only (9 values); women appear as Strawweight 102, Flyweight 79, Bantamweight 68, Featherweight 7 |
| Fighters whose last-fight division ≠ `fighters.weight_class` (excl. women/open/catch) | 174 |
| Fighters who fought in >1 distinct `fights.weight_class` | 882 |
| `weight_lbs = 185` | 333 (indistinguishable from the migration default; UNKNOWN how many are defaults) |
| Fighters with ≥3 UFC fights in dataset | 1,785 (68%); 1 fight: 399; 2 fights: 431 |
| Fighters whose last fight ≥ 2024-10-04 (12 mo. before dataset end) | 633 |
| Fighters not fought since 2022-10-04 | 1,737 |
| `fighters.slpm == latest_features->>'r_fighter_SlpM'` mismatches | 0 (display columns are a copy of the same CSV cell as the model feature — **no independent source**) |

Value ranges (CONFIRMED): height 152.4–210.8 cm; reach 147.3–213.4 cm (no values in 1–119 → no unit sentinels); age 18–51; `str_acc`, `str_def`, `td_acc`, `td_def` all within [0,1]; extreme outliers `slpm` max 20.55, `td_avg` max 24.32, `sub_avg` max 24.3 (8 fighters with `slpm>10`, 13 with `td_avg>8`, 20 with `sub_avg>5` — small-sample artifacts, **INFERRED**).

### 2.3 Field-by-field provenance table

| Profile field (API key) | Source → storage | Nullability lost where | Zero semantics | Status |
|---|---|---|---|---|
| `wins_total/losses_total/draw` | CSV `r_/b_fighter_w/l/d` → `wins/losses/draws` (Integer, default 0) | `migrate_csv.py:197-199` `int(float(x or 0))` | Record is *career* (includes pre-UFC: every fighter has `w+l+d ≥ n_ufc_fights`; 0 fighters have `w+l+d=0`) | Whether the record includes the fighter's **last** dataset fight: **UNKNOWN** |
| `age` | `r_age` → `age` | `:200` | 0 = missing (no real age < 18; min non-zero is 18) | **CONFIRMED** sentinel |
| `height`, `reach` | `fighter_height_cm/reach_cm` (cm, already) | `:195-196` | 0 = missing (no real value < 147) | **CONFIRMED** sentinel; no unit conversion occurs in repo code |
| `weight`, `weight_class` | `fighter_weight_lbs` (default 185) → `_weight_class()` (`:106-125`) | `:191`: NaN→0.0→falsy→185 | Missing weight silently becomes 185 → "Middleweight"; women bucketed to men's names; 174 disagree with last fight | **CONFIRMED** defects [SRC+APP] |
| `SLpM_total`, `sig_str_acc_total`, `sig_str_def_total` | `fighter_SlpM/Str_Acc/Str_Def` → `slpm/str_acc/str_def` (fractions 0–1) → ×100 in `main.py:520-521` | `:201-203` | Jointly-zero block = missing (inferred rule §4); `slpm=0 ∧ str_acc=0` with other stats non-zero: 19 fighters (ambiguous) | **INFERRED** |
| `td_avg_total`, `td_acc_total`, `td_def_total` | `fighter_TD_*` | `:204-206` | `td_avg=0 ⇒ td_acc=0` always (structural: no attempts). `td_acc=0 ∧ td_avg>0`: 0 fighters. `td_def=0` among non-all-zero: 290 (ambiguous; small-sample 0% and 100% (153 fighters) are both legitimate extremes) | **INFERRED** |
| `sub_avg_total` | `fighter_Sub_Avg` | `:207` | 0 for 1,100 fighters; legitimately common outside the all-zero block | **INFERRED** |
| `total_knockdowns` | **not stored**; `golden_feature_calculator.py:112` hard-codes `0.0` | n/a — never persisted | Always 0 → *not-stored*, not zero. `latest_features['r_knockdowns']` is a **last-bout** in-fight value (nonzero for 221 fighters), not a career total | **CONFIRMED** |
| `fights.method` | CSV `finish` (absent) | `migrate_csv.py:346` | Always NULL | **CONFIRMED** source/pipeline gap |
| `fights.winner` | CSV `winner` | n/a | Always a corner name except one `'No Contest'`; **no draw is representable** (436 fighters have draws; 0 fight rows say Draw) | Draw encoding: **UNKNOWN** |
| `is_active` | not in CSV; model default `True` (`db/models.py:87`) | n/a | Constant `true` | **CONFIRMED** |
| `style`, `aura/composite/mirage/chaos_contribution` | never written | n/a | Always NULL → endpoint computes on the fly | **CONFIRMED** |

### 2.4 Historical-snapshot limitations

- **CONFIRMED:** `fighters` holds exactly one snapshot per fighter: the stats from the row of their *most recent* fight (`migrate_csv.py:359-361`, ascending date sort). Stats are never refreshed after the dataset's last fight (2025-10-04); the dataset is ~13 months stale relative to the environment date; the model file records `trained_date 2025-11-18`.
- **INFERRED (partially contradicted by data — treat as UNKNOWN):** `fighter_*` columns are *pre-fight* snapshots. Evidence for: Aaron Pico's career `SlpM`=0 while his last bout's in-fight `r_sig_strikes_succ`=13 and `r_ctrl_time_sec`=121 (debut → no prior UFC stats). Evidence against: 278 single-fight fighters have non-zero career stats, and 60 fighters with ≥2 fights are all-zero. Provenance is therefore *mixed*; a debut-zero and a source-gap-zero are indistinguishable in the DB.
- **CONFIRMED:** `latest_features` contains last-bout in-fight columns (`r_sig_strikes_succ`, `r_knockdowns`, `r_ctrl_time_sec`, …) next to career/rolling columns (2,124 keys for Pico, 54 non-zero). Whether training rows contained same-fight in-fight values is **UNKNOWN** and is a model-owner concern, explicitly **out of scope** (§8) — noted only because it affects how safe it is to reuse these columns for display evidence (§5.2 does **not** rely on them).
- `fights` contains only fights present in the dataset, not each fighter's full UFC career necessarily: Aaron Pico has **1** fight row (Lerone Murphy, 2025-08-16, `winner = Lerone Murphy`) yet record 13-4. Fight-history counts are "UFC fights *in dataset*", never "career fights".

### 2.5 Aaron Pico — verified end-to-end (CONFIRMED)

DB row: `wins 13, losses 4, draws 0, age 28.0, height 0.0, reach 0.0, weight_lbs 145.0, weight_class Featherweight, slpm/str_acc/str_def/td_avg/td_acc/td_def/sub_avg all 0.0, style NULL`. Single fight row. Rolling-window features (`slpm_3_r`, `td_avg_3_r`, `wins_3_r`, `ctrl_ratio_3_r`) all `0.0`.
Rendered today: STRIKER, Composite 100, Aura 51.8, Chaos Contribution 50.0, Mirage 22.9 (reproduced in §3, B1–B4).

---

## 3. Confirmed bugs with reproduction evidence

Reproduction method: pure functions imported from `backend/intelligence/*` and run with the project's own `.venv`; `main.py` profile formulas (not importable without app startup/DB) were re-typed **verbatim** from `main.py:551-594` into a throw-away script. Scripts live only in the session scratchpad; condensed copies are in Appendix B. No DB writes, no app startup.

### B1. Composite Score saturates at 100 — **CONFIRMED [APP]**
- **Where:** `backend/main.py:578-581`
  ```python
  min(100.0, max(0.0, (win_rate * 40.0 + str_acc * 30.0 + str_def * 30.0) * 100.0))
  ```
- **Cause:** `win_rate`, `str_acc`, `str_def` are already 0–1 fractions, so the weighted sum is already on a 0–100 scale; the extra `* 100.0` makes any sum ≥ 1.0 clamp to 100.
- **Evidence:** on a 21×21×21 grid of (win_rate, str_acc, str_def) ∈ [0,1], **9,260 / 9,261** points return 100.0 (all but the origin). Pico (13-4, zeros): `(0.765·40 + 0 + 0)·100 = 3,059` → 100.0. A 6-5 fighter with 30%/30% → 100.0; a 1-1 fighter with 1%/1% → 100.0. `1 win in 100 fights`, zero accuracy → 40.0.
- **Compounded by:** missing `str_acc/str_def` contribute 0 (not excluded), so the score is simultaneously saturated *and* penalising missingness; also ignores draws (`total_fights = wins + losses or 1`, `main.py:553`).
- **Spec divergence:** PRD §10.4 (lines 562-566) calls it an "overall model-based quality rating"; the implementation is a record+striking-percentage heuristic that does not touch the model. UI copy (`FighterProfile.jsx:200`) repeats the PRD wording.

### B2. Missing striking defence inflates Chaos — **CONFIRMED [SRC+APP]**
- **Where (profile):** `main.py:583-588` — `chin_risk = max(0, 1 - str_def)`; `str_def=0` (missing) ⇒ `chin_risk = 1.0` ⇒ Chaos Contribution ≥ 50 for any fighter with missing stats (Pico: **50.0**; a 1-1 fighter with 1%/1%: 49.5).
- **Where (matchup):** `backend/intelligence/chaos_scorer.py:128-138` — `vuln = max(0, opp_str_acc − own_str_def)`; with `str_def=0` the full opponent accuracy counts as vulnerability and the `chin_issues` driver fires (`> 0.05`).
- **Evidence:** `chaos_scorer.compute(Pico[zero stats], opponent[acc .48])` → score **13.55**, drivers `['chin_issues','loss_streak']`; the same fighter with illustrative plausible values (def .55, acc .45, slpm 3.5) → **7.8**, no `chin_issues`. (Comparator is synthetic; it demonstrates the mechanism, not a "true" Pico value.)

### B3. Missing data triggers Mirage — **CONFIRMED [SRC+APP]**
- **Where:** `main.py:592-594` — `mirage = (win_rate − 0.65)·200 if win_rate > 0.65 and str_def < 0.55 else 0`.
- **Evidence:** Pico: win_rate 13/17 = 0.765 and `str_def=0 < 0.55` → **22.9**. Any >65% record with missing `str_def` produces a non-zero Mirage by construction. The signal literally means "good record + bad defence", and "missing" is read as "bad".
- **Spec divergence:** PRD §10.4 (lines 571-585) defines Mirage as a 0–10 opposition-quality index (opponent win rate, finish share, streak vs. quality, recency). None of those inputs are used; scale is 0–100.

### B4. STRIKER assigned by default — **CONFIRMED [APP]**
- **Where:** `backend/intelligence/utils.py:46-65` (`return "STRIKER"` when no rule fires or on exception), re-defaulted in `frontend/src/pages/FighterProfile.jsx:119` (`intel.style || 'STRIKER'`). `backend/tests/test_utils.py:49-54` asserts "all-zero → STRIKER" and "{} → STRIKER" as *expected* behaviour.
- **Evidence:** `classify_style(<Pico zeros>) == 'STRIKER'`, `classify_style({}) == 'STRIKER'`. 203 fighters satisfy the literal STRIKER rule (`slpm>5 ∧ td_avg<1.5`); every other fighter that fails all five rules is also labelled STRIKER.
- **Also:** the ladder is order-dependent first-match (a fighter with `sub_avg > 1.5` is GRAPPLER regardless of striking); thresholds are absolute, era-blind, and unrelated to division (Strawweights vs Heavyweights).

### B5. Fights missing finish method — **CONFIRMED [SRC/pipeline] with downstream [APP] damage**
- **Root cause:** `migrate_csv.py:346` reads column `finish`, which `convert_golden_FULL.py` never copies (`:76-78` list). 8,231/8,231 methods are NULL.
- **Downstream, all CONFIRMED by repro:**
  - `utils.finish_rate()` (`utils.py:78-99`) = **0.0 for every fighter** → Chaos "finish rate" component (0–55 of 100) is identically 0. Max reachable raw chaos is therefore ≈ 63 (× division multiplier ≤ 1.30); `EXTREME` (≥75) is reachable only with Heavyweight multiplier plus short-notice *and* weight-miss. **INFERRED** arithmetic from `chaos_scorer.py:103-109, 169-179`.
  - `perception_gap._aura_score` finish component (0–0.25) = 0 for all (`perception_gap.py:45-47`).
  - `win_path._method_counts` (`win_path.py:55-61`): `else: dec += 1` — **every win with a NULL method is counted as a decision**, so `dec_rate = 1.0`, `ko_rate = sub_rate = 0` for all fighters with ≥1 win. Pico's top Kill Chain path is `TAKEDOWN_CONTROL` (0.2137) purely because `sub_norm = 0` ⇒ `(1 − sub_norm)·0.3` (`win_path.py:108`).
  - `fight_dna._compute_dna` (`fight_dna.py:73-82`): `cardio = dec_rate = 0.0` for every fighter with fights (NULL ≠ "DECISION"); `chin` ignores KO losses (`:61-71`). Fighters with *no* fights get a neutral 0.5 — so a fighter with history scores *worse* on cardio than one with none.
  - `/fighter/{name}/history` returns `method: ""` for every row (`main.py:654`).
- **Substring fragility** (latent, UNKNOWN until real method strings exist): `_is_finish` uses `"SUB" in m` and `"KO" in m` (`utils.py:72-75`); e.g. `_is_finish("Substitution") → True`; `"DQ"`/`"Overturned"` → False (reasonable) but untested against real strings.

### B6. Draws and no-contests classified as losses — **CONFIRMED [APP]** (draw *data* UNKNOWN)
- `main.py:653`: `"result": "W" if row.winner == fighter_name else "L"` — the only NC row in the DB (Reese vs Dumas) is rendered **L for both fighters**; any future `Draw` is also L.
- Win-rate denominators are inconsistent: profile `wins/(wins+losses)` ignoring draws (`main.py:553`, `FighterProfile.jsx:252`); `perception_gap.py:58-59` includes draws; `chaos_scorer._record_volatility` skips draws/NC (`:68-73`); `utils.win_streak` breaks the streak on draw/NC (`utils.py:127-134`) — itself fine, and test `test_utils.py:160` covers it.
- **Data side:** 0 draw rows exist among 8,231 fights while 436 fighters carry `draws > 0` (likely pre-UFC or non-UFC, **INFERRED**). Whether the source encoded draws as a named winner is **UNKNOWN**; the only real non-win sample in the DB is the single NC.

### B7. "Activity filtering" despite all fighters active — **CONFIRMED [SRC+APP]**
- `is_active` is constant `true` (DB), treated as active when NULL (`main.py:456, 460, 570`). `FighterSearch.jsx:84-89` and `FighterProfile.jsx:147` implement filters/badges that can never trigger: the **"Inactive" filter returns an empty list** and no profile shows the Inactive badge.
- Real recency exists (`fighters.last_fight_date`): 633 fighters fought within 12 months of dataset end, 1,737 have not fought since 2022-10-04. Because the dataset ends 2025-10-04, "active" must be measured relative to **dataset end**, not wall clock, and the data cannot establish retirement (only *recency*).

### B8. Misleading score-provenance metadata — **CONFIRMED [APP]**
- `main.py:596,607`: `scores_source = "computed" if (stored and stored.aura_score is not None) else "heuristic"`. Stored values never exist, so it is always `"heuristic"` — correct but (a) keyed only on `aura_score` (if one column were populated the label would say "computed" for the other three heuristics); (b) never read by the frontend (grep: no consumer outside `main.py`); (c) the UI presents these as "SCIPHR Intelligence" with PRD-style definitions ("Overall SCIPHR quality rating", "Resume inflation") that the heuristics do not implement. No per-score input list, no availability flag, and `null`s are impossible (all four fall back to numbers, and `FighterProfile.jsx:120-123` additionally `?? 0`).

### B9. Knockdown totals default to zero — **CONFIRMED [SRC+APP]**
- `golden_feature_calculator.py:112` hard-codes `"knockdowns": 0.0  # not stored in Phase 1; Phase 2 adds it` (Phase 2 never did); `main.py:522` serialises it as `total_knockdowns`; `FighterProfile.jsx:232` renders "Total Knockdowns 0" for **every** fighter. `ai_analyst._ko_rate` (`ai_analyst.py:42-49`) consumes the same key (always 0).
- `latest_features['r_knockdowns']` exists but is a last-bout value (221 fighters non-zero) — not a career total, not safe to relabel as one.

### Related defects found while tracing

| ID | Finding | File:lines | Status |
|---|---|---|---|
| R1 | `perception_gap` compares `f.get("date")` (a `datetime.date` from the DB) to the string `"2022-07-01"` → **`TypeError`** on real data; `_safe_compute` swallows it, so `perception_gap`/`aura` badges silently never fire in production. The shared test fixture builds fights with **string** dates (`backend/tests/conftest.py:65-75`, `_make_fight(..., date="2023-01-01")`), hiding it. Reproduced: `TypeError: '>=' not supported between instances of 'datetime.date' and 'str'`. (Whether prod `/predict` has been returning `perception_gap: null` is **INFERRED**; a live call was not made.) | `perception_gap.py:50`; `orchestrator.py:324-336` | **CONFIRMED** |
| R2 | **Unit mismatch between endpoints for the same keys:** `/fighter/{name}` returns `sig_str_acc_total` etc. as **0–100** (`main.py:520-527`), while `/predict` `fighter*_stats` returns `sig_str_acc_total`/`td_acc_total` as **0–1** (`src/predictor_golden.py:193-194`) and omits `sig_str_def_total`, `td_avg_total`, `sub_avg_total`, `draw`, `weight_class`. | as cited | **CONFIRMED** |
| R3 | `ai_analyst._remap_for_style` divides accuracy by 100 and reads `td_avg_total/sub_avg_total/sig_str_def_total` — keys absent from `/predict` stats (R2) — so analyst style input is `{sub_avg:0, td_avg:0, slpm, str_acc≈0.005, str_def:0}` ⇒ effectively always `STRIKER` (BRAWLER/COUNTER/WRESTLER/GRAPPLER unreachable). | `ai_analyst.py:24-39, 104-105, 156-157` | **CONFIRMED** (static) |
| R4 | `/detailed-stats` fabricates `*_recent_fights` with `random.seed(hash(name))` from win rate; it is not real history (and `hash()` of a `str` is per-process randomised, so it is not even stable across restarts). | `main.py:1154-1174, 1134-1135` | **CONFIRMED** (static); out of scope but trust-relevant |
| R5 | Stat-derived signals treat missing as 0 across the engine: `fight_dna` (`fight_dna.py:42-47` → all dimensions 0 for Pico, `chin`=0.5), `win_path` (`:92-99`), `nightmare_matchup` / `chaos_scorer` style ladders. Nightmare/Clash outputs for any pairing involving an incomplete fighter are artifacts of the STRIKER default (B4). | as cited | **CONFIRMED** (Pico repro) |
| R6 | Division keys diverge across code: `fights.weight_class` has Women's divisions, `fighters.weight_class` does not; `_WEIGHT_CLASS_MULTIPLIER` in `chaos_scorer.py:31-45` has Women's keys that `FighterContext.stats["weight_class"]` (from `fighters`) can never match, so the women's multipliers are dead code and women are scored with men's multipliers. | `chaos_scorer.py:172-177`; `orchestrator.py:314` | **CONFIRMED** (DB + static) |
| R7 | `FighterProfile` defaults `wc = stats.weight_class \|\| 'Welterweight'` (`FighterProfile.jsx:101`), inventing a division when absent. | | **CONFIRMED** (static) |
| R8 | Profile displays `"0 years"` (`FighterProfile.jsx:262`), `0.00`/`0.0%` for unavailable stats (`:111-117, 229-243`), "Win Rate 0%" when wins=0 (`:252`) — rendering of absence as zero is UI-side too. | | **CONFIRMED** (static) |

---

## 4. Data-quality and nullability rules

**Principle (PROPOSED):** *never emit a number the data cannot support.* Replace "zero vs. missing" with an explicit per-field availability status. **Do not** convert all zeros to NULL.

### 4.1 Field availability statuses (PROPOSED)

| Status | Meaning | Value emitted |
|---|---|---|
| `measured` | Non-zero value, or plausible measured value | number |
| `measured_zero` | Zero that the rules consider legitimate | `0` |
| `undefined_no_attempts` | Ratio undefined because its denominator is zero (e.g. `td_acc` when `td_avg = 0`) | `null` |
| `unavailable` | Zero that the rules consider missing | `null` |
| `not_stored` | Field is not in the DB at all (e.g. career knockdowns) | `null` |

Each field also carries `basis`: `"inferred_zero_pattern"` today (rules below) → `"source_flag"` if/when a true NaN mask is recovered from the original CSV. **The API must never claim `"verified"` missingness while `basis` is inferred.**

### 4.2 Rules (PROPOSED; thresholds from §2 evidence)

| Field(s) | Rule | Rationale / evidence |
|---|---|---|
| **Core stat block** `{slpm,str_acc,str_def,td_avg,td_acc,td_def,sub_avg}` | If **all seven** are 0 → whole block `unavailable` (`core_block_available = false`) | A fighter with ≥1 fight who landed no strikes, attempted no takedowns, no subs, and has 0% accuracy *and* 0% defence *and* 0% TD defence is not credible; 181 fighters; 50/60 of the ≥2-fight cases have non-zero rolling windows, proving a block-specific gap |
| `slpm`, `str_acc` | Block available and value 0 → `measured_zero` flagged `low_sample` if `n_ufc_fights < 3` (19 fighters have `slpm=0 ∧ str_acc=0` outside the all-zero block) | Plausible only for very short fights; cannot confirm |
| `str_def` | Block available and `str_def = 0` → `unavailable` (5 fighters) | Absorbing 100% of strikes is not credible; 0% defence also drives B2/B3 |
| `td_avg`, `sub_avg` | Block available and 0 → `measured_zero` | Strikers who never shoot; 1,100 fighters have `sub_avg = 0` |
| `td_acc` | `td_avg = 0` → `undefined_no_attempts`; else `measured` | Structural: `td_avg=0 ⇒ td_acc=0`, never `td_acc=0 ∧ td_avg>0` |
| `td_def` | Block available → `measured` (incl. 0 and 1.0); mark `low_sample` when `n_ufc_fights < 3` | 0% (136+154) and 100% (153) are both legitimate small-sample extremes; cannot be disambiguated without attempts counts (not stored) |
| `height`, `reach` | 0 → `unavailable` | No real value < 147 cm; 41/671 zeros; **do not** impute from weight class |
| `age` | 0 → `unavailable` | Min real age 18; also **stale** by construction (age at last fight, not today) → label `age_at_last_fight` |
| `weight_lbs` / `weight_class` | Display `division` from the `fights` table (§5.3), not from `weight_lbs`; keep `weight_lbs` only as an informational field; 185 is indistinguishable from the default → `basis: "possible_default"` when exactly 185 and the fights-derived division disagrees | 333 at exactly 185; 174 division disagreements; Women's absent |
| `wins/losses/draws` | Always `measured` (every fighter has `w+l+d ≥ n_ufc_fights ≥ 1`); expose as `record_scope: "career_as_of_last_dataset_fight"` | Whether it includes the last fight is UNKNOWN → phrase accordingly |
| `knockdowns` | `not_stored`, `null` | B9 |
| `fight method` | `unavailable` per fight; coverage `method_coverage = 0.0` exposed at profile level | B5 |
| Fight result | Enumerate `W / L / D / NC / UNKNOWN` (never default to L) | B6 |
| Activity | `activity_status ∈ {RECENT, NOT_RECENT, UNKNOWN}` from `last_fight_date` vs **dataset max date** (default window 24 mo. — **D8**), never `retired` | B7 |

### 4.3 Historical-coverage object (PROPOSED)

Per fighter: `ufc_fights_in_dataset`, `first_dataset_fight`, `last_dataset_fight`, `snapshot_date` (= `last_fight_date`), `dataset_end` (= global max date, not wall clock), `methods_available_fraction`, `core_block_available`, `n_fields_available / n_fields_total`.

### 4.4 What this ticket can and cannot do about the source
- **Can (read-time, no writes):** infer availability by the rules above.
- **Cannot:** recover true NaN masks, finish methods, `gender`, or real weight classes without `UFC_full_data_golden.csv` (or the converted CSV). Re-running `migrate_csv.py` is **out of scope** and, importantly, **must not** be applied to `latest_features` (model inputs) in any future remediation without a separate model-owner sign-off (§7).

---

## 5. Proposed multi-label fighting-style algorithm

**All of §5 is PROPOSED.** Nothing here is implemented. Style labels describe *tendencies in what a fighter does*, not skill or effectiveness.

### 5.1 Dimensions and evidence fields

| Dimension | Tendency metric (primary) | Supporting metric | Explicitly excluded |
|---|---|---|---|
| `STRIKING` | `slpm` (sig. strikes landed / min) | `str_acc` as a *quality gate only* (see 5.4), not a score | `str_def` (defensive skill), knockdowns (not stored), last-bout in-fight columns |
| `WRESTLING` | `td_avg` (takedowns landed / 15 min) | `td_acc` as a quality gate only | `td_def` (defensive skill) |
| `SUBMISSION_GRAPPLING` | `sub_avg` (submission attempts / 15 min) | method-based sub-win share **only once** `fights.method` is restored (§8 D1) | `sub_wins_*_r` rolling windows until their definition is verified (**UNKNOWN**) |

Rationale: attempts/volume per unit time measure *propensity*; accuracy and defence measure *effectiveness*. Keeping them out of the score avoids the skill/tendency conflation the ticket warns about. Do **not** invent sub-types (pressure, counter, etc.): no field identifies range, pace-of-approach, or counter-timing (no distance/position/strike-target data in the display columns). The `COUNTER`/`BRAWLER` legacy labels are **dropped**, not remapped, for that reason.

### 5.2 Evidence source and isolation
Inputs are the `fighters` display columns + the `fights` table (division, fight count, dates) — **read-only**. The classifier must not read `latest_features` (model input, unknown in-fight contamination, §2.4) or import the predictor.

### 5.3 Peer group (division-relative normalisation)

1. **Division key:** most recent `fights.weight_class` among *standard* divisions (Men's 8 + Women's 4; map `Women's X` as its own key), falling back to the modal standard division across the fighter's fights, then to `fighters.weight_class` flagged `basis: "weight_derived"`. Exclude `Open Weight`, `Catch Weight`, `'0'`, `Nieznana`, and `UFC … Title` strings from the key. Women's fighters currently carry men's `fighters.weight_class` — the fights-derived key is **required** for correctness (CONFIRMED need, §2.2).
2. **Reference population (who is ranked against):** fighters in the same division key who pass the §5.4 evidence gate. Ineligible fighters are *excluded from the reference set* (so zeros never drag percentiles down) and receive no classification.
3. **Percentile:** mid-rank percentile `100·(n_less + 0.5·n_equal)/N` on the tendency metric. Rank-based (not z-score) because the distributions are heavy-tailed (`td_avg` up to 24, `slpm` up to 20).
4. **Small / sparse divisions:** current eligible counts (≥3 fights, non-all-zero) — men: Strawweight(\*)83, Light Heavyweight 142, Heavyweight 144, Flyweight 172, Featherweight 195, Middleweight 220, Bantamweight 232, Lightweight 284, Welterweight 286 (\*these are *mixed-sex* under the current column; the real Women's divisions are materially smaller, e.g. Women's Featherweight has only 30 fight rows total). Proposed `MIN_PEERS = 40` (**D5**): below it, pool with the adjacent same-sex division and set `peer_group.pooled = true`; if still below, `unclassified (PEER_GROUP_TOO_SMALL)`.
5. **Era:** stats span 1994–2025 (1,465 fighters last fought before 2020). Start with one all-era reference per division; the sensitivity study (5.7) must also report an era-banded variant before **D6** is decided.

### 5.4 Evidence gate (eligibility) — rule-based tiers, **not** probabilities

A fighter is **eligible** iff all hold:
- `core_block_available` (§4.2),
- the dimension's metric field is `measured`/`measured_zero` (not `unavailable`),
- `ufc_fights_in_dataset ≥ MIN_FIGHTS` (proposed **3**; 1,785 fighters pass, 399 have 1 fight, 431 have 2).

`evidence_level` (descriptive, deterministic): `INSUFFICIENT` (fails gate) · `LIMITED` (3–4 fights) · `ADEQUATE` (≥5 fights). Fight-minutes are not stored, so fight count is only a coarse proxy for denominator size (**INFERRED weakness**; state in API docs).

A high percentile on a metric from an ineligible fighter never qualifies a dimension. Accuracy gates (proposed, **D5**): STRIKING additionally requires `str_acc` available; WRESTLING requires `td_acc` not `undefined_no_attempts` unless `td_avg>0`. (Gates, not score terms.)

### 5.5 Qualification rules (`division_relative_v1`)

Given percentiles `pS, pW, pG` for an eligible fighter:
1. A dimension is **present** if `p ≥ T_PRESENT` (inclusive; proposed **65**).
2. If no dimension is present → `classification_status: "unclassified"`, `reason: "NO_DISTINCT_TENDENCY"`.
3. `primary_style` = present dimension with highest `p` (ties broken by the fixed order `STRIKING, WRESTLING, SUBMISSION_GRAPPLING` and reported as `tie: true`).
4. `secondary_styles` = other present dimensions with `p ≥ primary_p − MARGIN` (proposed **MARGIN = 20**), ordered by `p`.
5. `is_versatile = true` iff all three are present (all three then listed; `primary_style` is still the max).
6. Unmet gate → `unclassified`, `reason ∈ {INSUFFICIENT_DATA, PEER_GROUP_TOO_SMALL}`.

Interpretations: *striking-oriented* = `{primary: STRIKING, secondary: []}`; *striking + wrestling* = `{STRIKING, [WRESTLING]}`; *wrestling + submission grappling* = `{WRESTLING, [SUBMISSION_GRAPPLING]}`; *versatile* = `is_versatile`.

### 5.6 Missing-data behaviour (non-negotiable)
Missing is never a value of 0 anywhere in this path. A dimension whose metric is `unavailable` is **absent from `dimensions`** (not zero-filled). Pico → `unclassified / INSUFFICIENT_DATA`, no dimensions, no label. There is **no default label**.

### 5.7 Confidence — assessment
**A calibrated numeric confidence cannot be meaningfully computed today** (CONFIRMED reasoning): there are no ground-truth style labels to calibrate against; fight minutes and attempt counts (denominators) are not stored; peer distributions are era-mixed; thresholds are conventions, not estimated parameters. **Do not ship a `confidence` number.** Ship only verifiable descriptives: `evidence_level`, `fights_used`, `peer_group.size`, `margin_to_threshold` (distance of each percentile from `T_PRESENT`), and `lead_over_next` (primary vs. next percentile). Revisit only if labelled data is supplied (**D5**).

### 5.8 Threshold sensitivity & validation plan (to run in 01B, offline, read-only)

1. **Grid:** `T_PRESENT ∈ {55,60,65,70,75}` × `MARGIN ∈ {10,15,20,25}` × `MIN_FIGHTS ∈ {2,3,5}`. Report per cell: share `unclassified` by reason; label-set distribution (single / dual / versatile); mean labels per fighter.
2. **Stability:** (a) *threshold flip rate* — fraction of fighters whose `primary_style` changes between adjacent cells; (b) *peer bootstrap* — resample each division's reference set 200× and report fraction of fighters whose label *set* changes; (c) *era-banded vs all-era* reference comparison.
3. **Small division report:** per-division eligible N, pooled flag, bootstrap flip rate; divisions with N < 40 listed explicitly.
4. **Representative-fighter review (human, not an oracle):** a stratified sample (10 per division across label outcomes, plus all boundary cases within ±3 percentile of a threshold) is shown to a domain reviewer as a *sanity check*; disagreement is logged, not auto-tuned. Test oracles remain **synthetic** (§10).
5. **Acceptance proposal (needs approval, D5):** no fighter flips primary label under ±5-point threshold shifts unless within that band of a threshold by construction; report (not bound) bootstrap flip rate.

### 5.9 Response shape (illustrative only; fields refined by evidence)

```jsonc
"style_profile": {
  "method": "division_relative_v1",
  "classification_status": "classified",          // | "unclassified"
  "reason": null,                                  // INSUFFICIENT_DATA | NO_DISTINCT_TENDENCY | PEER_GROUP_TOO_SMALL
  "primary_style": "WRESTLING",
  "secondary_styles": ["STRIKING"],
  "is_versatile": false,
  "dimensions": [
    {"id":"WRESTLING","present":true,"percentile":88.2,"metric":"td_avg","value":4.1},
    {"id":"STRIKING","present":true,"percentile":71.0,"metric":"slpm","value":4.6},
    {"id":"SUBMISSION_GRAPPLING","present":false,"percentile":31.5,"metric":"sub_avg","value":0.2}
  ],
  "evidence": {"evidence_level":"ADEQUATE","fights_used":9,"core_block_available":true,
               "fields_used":["slpm","td_avg","sub_avg","str_acc","td_acc"],"fields_missing":[]},
  "peer_group": {"key":"Lightweight","size":284,"pooled":false,"basis":"fights_table"},
  "thresholds": {"present":65,"secondary_margin":20,"min_fights":3},
  "tendency_note": "Describes tendencies, not skill or effectiveness."
}
```
(Values above are placeholders for the schema, not real fighters.)

---

## 6. Proposed backward-compatible API contract — `GET /fighter/{fighter_name}`

### 6.1 Current contract (CONFIRMED, `main.py:597-609`)
```jsonc
{ "name": "...",
  "stats": { "wins_total","losses_total","draw","age","height","reach","weight","weight_class",
             "SLpM_total","sig_str_acc_total","sig_str_def_total","total_knockdowns",
             "td_avg_total","td_acc_total","td_def_total","sub_avg_total" },   // all numbers, 0 = absent
  "intelligence": { "style","is_active","aura_score","composite_score",
                    "chaos_contribution","mirage_meter","scores_source" } }     // all non-null
```

### 6.2 Additive extension (PROPOSED)
Keep `name`, `stats`, `intelligence` unchanged in shape **for one release** (deprecation window — **D3**); add siblings:

```jsonc
{
  "name": "...",
  "stats": { /* unchanged keys; unchanged semantics in release N */ },
  "intelligence": { /* unchanged keys; see 6.4 for the two semantic changes */ },

  "data_quality": {                       // NEW
    "schema": "fighter_profile_v2",
    "fields": {                           // per display field
      "slpm":   {"value": null, "status": "unavailable", "basis": "inferred_zero_pattern"},
      "td_acc": {"value": null, "status": "undefined_no_attempts", "basis": "structural"},
      "sub_avg":{"value": 0.0,  "status": "measured_zero", "basis": "inferred_zero_pattern"},
      "height": {"value": null, "status": "unavailable", "basis": "inferred_zero_pattern"},
      "knockdowns": {"value": null, "status": "not_stored", "basis": "not_in_schema"}
      /* … one entry per field in stats */
    },
    "coverage": {
      "ufc_fights_in_dataset": 1, "first_dataset_fight": "2025-08-16", "last_dataset_fight": "2025-08-16",
      "snapshot_date": "2025-08-16", "dataset_end": "2025-10-04",
      "record_scope": "career_as_of_last_dataset_fight",
      "methods_available_fraction": 0.0, "core_block_available": false,
      "fields_available": 3, "fields_total": 15
    },
    "activity": {"status": "RECENT", "basis": "last_fight_vs_dataset_end", "window_months": 24}
  },

  "scores": {                             // NEW — nullable, provenance-labelled
    "composite": {"value": null, "available": false, "reason": "INSUFFICIENT_INPUTS",
                  "inputs_required": ["str_acc","str_def","record"], "inputs_missing": ["str_acc","str_def"],
                  "provenance": "heuristic_v2", "label": "Composite (heuristic)"},
    "aura": {…}, "chaos_contribution": {…}, "mirage": {…}
  },

  "style_profile": { /* §5.9 */ },       // NEW

  "history_summary": {"results": {"W":0,"L":1,"D":0,"NC":0,"UNKNOWN":0}}   // optional, from fights
}
```

### 6.3 Compatibility rules
- **Existing keys are never removed or retyped in release N.** Null-ification of `stats.*` (replacing zeros with `null`) is deferred to release N+1 **or** gated by a query flag (`?schema=v2`) — chosen under **D3**. The only in-repo consumer of `/fighter/{name}` is `FighterProfile.jsx` (CONFIRMED by grep: `api.js` → `FighterProfile.jsx`; `FighterProfile.jsx` already tolerates `null`/`undefined` via `||`/`??` but would silently render them as 0 — which is why 01C must change it). External consumers of the public API are **UNKNOWN**.
- `/predict` keeps its own `fighter*_stats` shape (R2) — **not** changed by FTR-01; the unit mismatch is documented and handled in the profile layer only.
- `/fighters` (list) keeps `{name, weight_class, is_active}`; `is_active` semantics change is **D8**; `division` added as a new additive key.
- `/fighter/{name}/history` rows: keep `result: "W"|"L"`, add `"D"`, `"NC"`, `"UNKNOWN"` as new enum values (consumers rendering `result.toLowerCase()` CSS classes degrade gracefully: `FighterProfile.jsx:300-301`); add `method_available: false`.

### 6.4 `intelligence` object — two deliberate semantic changes (need approval, **D4/D9**)
1. `intelligence.style`: today always a string. **PROPOSED:** keep the key and legacy vocabulary for one release but return `null` instead of `"STRIKER"` when `core_block_available` is false; add `intelligence.style_deprecated: true` and point to `style_profile`. Do **not** map new labels into the legacy five (different semantics, silently misleading).
2. `composite_score/aura_score/chaos_contribution/mirage_meter`: today always numeric. **PROPOSED:** fix B1 (remove the extra `×100`), return `null` when required inputs are `unavailable`; mirror the same values under `scores.*` with availability metadata. `scores_source` becomes per-score `provenance`.

### 6.5 Consumers inventory (CONFIRMED by grep, whole repo)

| Consumer | Uses | Impact of FTR-01 | Compatibility action |
|---|---|---|---|
| `main.py:564` `/fighter/{name}` | `classify_style` | primary change site | additive `style_profile`; legacy `style` null-guard |
| `intelligence/chaos_scorer.py:112-113` | `classify_style(f_ctx.stats)` → clash matrix (15 pts) | no change in 01B; **recommended separate ticket** (D4) | keep unchanged → `/predict` intelligence output and `predictions_log.chaos_score` stay stable |
| `intelligence/fight_dna.py:108-110` | `collision_type = "{S1}_VS_{S2}"` | unchanged | `AnalystMode.jsx:666` renders `collision_type`; `AnalystMode.test.jsx` fixtures use legacy strings |
| `intelligence/nightmare_matchup.py:44-45` | style pairs → `_NIGHTMARE_PATTERNS` | unchanged | `NightmareResult.style_f1/f2` surfaced to UI/cinematic title |
| `intelligence/win_path.py:101` | `style == "COUNTER"` boost | unchanged | |
| `ai_analyst.py:104-105,156-157` | `classify_style(_remap_for_style(...))` | unchanged | R3 fix is separate |
| `FighterProfile.jsx:119,161` | `intel.style || 'STRIKER'` | **must change in 01C** | render `style_profile` chips; no fallback label |
| `utils.classify_style` tests | `tests/test_utils.py:28-64` (6 tests incl. 2 that assert the STRIKER default) | **update in 01B only if `classify_style` itself changes** | prefer: leave `classify_style` untouched; add a new function/module; legacy tests stay green |
| Raw stats: `get_latest_fighter_stats` | `main.py:495,970-971`, `predictor_golden.py:174-175` | unchanged | profile layer reads `fighters` columns itself (so `knockdowns: 0.0` coercion is bypassed) |
| Intelligence scores | `FighterProfile.jsx:120-123` (`?? 0`); `PerceptionGap.aura_score_f1/f2` (separate, matchup-level; **not** the profile `aura_score`) in `badge_engine.py:167,218,235`, `cinematic_title.py:186` | profile fix must not touch matchup-level `aura_score_f*` | note: two different "aura" computations (profile `main.py:573-576` vs `perception_gap.py:34-63`) share a name |

**Recommended compatibility strategy:** *leave `classify_style()` and every intelligence module byte-identical in 01B.* Introduce a new, separately-named module for the multi-label classifier. Migrate intelligence modules to it (or add missing-data guards to them) only under an explicit follow-up ticket, because doing so changes `/predict` intelligence payloads, logged `predictions_log` values and the Historical Scorecard semantics.

---

## 7. Prediction-engine isolation architecture

### 7.1 Boundaries (CONFIRMED from code)

```
L0  Source snapshot (frozen)         fighters.latest_features (JSONB, 2,124+ keys), models/golden_model.pkl
 │                                   (sha256 a465a75aebaafe3659232aeb83fdbafe04461dad139ebcf186baadc683274a44; 5,401 feature_names, order-hash 94ec2d88365fc070a9c117925b8f02e7121d1c6271c3528837791377b8a9f321,
 │                                    test_accuracy 0.857143, trained_date 2025-11-18)
L1  ML feature vector                src/golden_feature_calculator.py: build_full_feature_vector(), _calculate_differences()
 │                                   src/predictor_golden.py: predict_fight()           ← MUST NOT CHANGE
L2  Display read-model  (NEW)        backend/profile/*  — reads fighters display columns + fights; emits DTO only
 │                                   availability.py · division.py · style_profile.py · scores.py
L3  Intelligence heuristics          backend/intelligence/*  (consume FighterContext; unchanged in 01B)
L4  API serialisation                backend/main.py endpoints
L5  Presentation                     React
```

### 7.2 Rules (PROPOSED)
1. L2 **reads** `fighters.{slpm,…}`/`fights`; it never reads `latest_features`, never imports `golden_feature_calculator`, `predictor_golden`, or `models/*`. Enforced by an AST import test.
2. L2 never writes. No schema change, no backfill in 01B/01C (any column such as a persisted availability mask is a separate approved migration).
3. `_clean()`/`_extract_features()`/`latest_features` are untouched; **no re-migration** of model inputs. Zeros in `latest_features` are what the model was evaluated with; "fixing" them would silently change predictions.
4. `get_latest_fighter_stats()` stays as is (it is also used by `/generate-ai-poster` and `/predict`); the profile read-model bypasses its `knockdowns: 0.0` and `or 0` coercions by querying the columns directly.
5. Any future change to a heuristic *intelligence* signal is a **separate ticket** with its own scorecard-impact analysis (`predictions_log` stores chaos/gap/edge values).

### 7.3 Isolation tests (PROPOSED — new `backend/tests/test_prediction_isolation.py`)
- `sha256(models/golden_model.pkl) == a465a75aebaafe3659232aeb83fdbafe04461dad139ebcf186baadc683274a44` and `sha256("\n".join(feature_names)) == 94ec2d88365fc070a9c117925b8f02e7121d1c6271c3528837791377b8a9f321`, `len == 5401` (both recorded 2026-11-23 from the working tree).
- Golden-vector snapshot: for 3 fixed SQLite-seeded fighter pairs, `build_full_feature_vector(...)` equals a committed snapshot (length 5,401, exact values) before/after the change; `predict_proba` equal to 1e-12.
- Row-hash test: after the profile endpoint is invoked in tests, `fighters.latest_features` hashes unchanged (read-only guarantee).
- AST test: nothing under `backend/profile/` imports `golden_feature_calculator`, `predictor_golden`, `pickle`, `xgboost`.
- Existing: `test_feature_calculator.py` (7 tests), `test_p0.py`, `test_api_phase3.py` must pass unmodified.

---

## 8. Explicit scope exclusions

**Excluded from FTR-01A (this audit):** any application code edit, schema change, DB write, CSV re-import/migration, dependency installation, model retraining, feature-vector or model-artifact change, frontend redesign, commit/push.

**Excluded from FTR-01B/01C (proposed):** XGBoost/`latest_features` changes; fixing the finish-method gap in the DB (needs source data + write approval); changing `/predict` response shapes; changing intelligence modules (`chaos_scorer`, `fight_dna`, `nightmare_matchup`, `win_path`, `perception_gap`, `badge_engine`) except where a ticket below says so; fighter photos (OQ-09); live-activity/retirement data; fabricated recent-record (R4); model-leakage review of in-fight columns in `latest_features` (§2.4); ethnicity/nationality/sex data collection; non-UFC promotions (v1 anti-goal); pressure/counter/range sub-styles.

**Observation only (needs an owner, no action here):** `latest_features` includes last-bout in-fight statistics; whether the training set contained same-fight values (leakage) is UNKNOWN and potentially relevant to the 85.7% claim. Not investigated further because the constraint is *do not touch the model pipeline*.

---

## 9. Proposed implementation tickets

### FTR-01B — Backend: trustworthy fighter profile read-model (PROPOSED)
| # | Work item | Depends |
|---|---|---|
| B-1 | `backend/profile/availability.py`: field-status rules §4.2; coverage object §4.3; pure functions + unit tests | — |
| B-2 | `backend/profile/division.py`: fights-table division resolver (sex-aware, standard-division filter, pooled fallback) | D6 |
| B-3 | `backend/profile/style_profile.py`: percentile + `division_relative_v1` rules §5.5; no import of intelligence modules or `classify_style` | B-1, B-2, D5 |
| B-4 | `backend/profile/scores.py`: corrected, nullable heuristics (B1 unit fix; B2/B3 missing-input guards; draws in win rate; per-score provenance & `inputs_missing`); relabel copy (no "model-based") | B-1, D9 |
| B-5 | `main.py` `/fighter/{name}`: additive `data_quality`, `scores`, `style_profile`; legacy `intelligence.style` null-guard; `/fighter/{name}/history` result enum (`W/L/D/NC/UNKNOWN`) | B-1…B-4, D3, D4 |
| B-6 | Activity from `last_fight_date` vs dataset end; `/fighters` adds `division`, `activity_status` (keep `is_active` for compat) | D8 |
| B-7 | Offline sensitivity script (read-only) producing the §5.8 report as a committed Markdown/CSV artifact | B-3 |
| B-8 | `test_prediction_isolation.py` + deterministic fixtures (§10); fix test-fixture blind spot by adding `datetime.date` rows to perception/orchestrator fixtures | — |
| B-9 | Documentation: API reference for the new objects; deprecation note for `intelligence.style` | — |

### FTR-01C — Frontend: honest profile presentation (PROPOSED, no visual redesign)
| # | Work item |
|---|---|
| C-1 | `FighterProfile.jsx`: render `null` as "Not available"/"—" (replaces `||0` / `toFixed` on absent values, `:111-123, 262`); remove `'STRIKER'` fallback (`:119`) and `'Welterweight'` default (`:101`) |
| C-2 | Style chips from `style_profile` (primary/secondary/versatile; "Not enough data to classify" for `unclassified`, with reason copy); tooltip "describes tendencies, not skill" |
| C-3 | Coverage banner/inline notices from `data_quality.coverage` (e.g. "Based on 1 UFC fight in dataset; striking and grappling stats unavailable") |
| C-4 | Score cards read `scores.*`; show "Not enough data" when `available:false`; show provenance label ("heuristic") |
| C-5 | Remove "Total Knockdowns" row until a real source exists; show W/L/D/NC in history; hide Inactive filter/badge until activity status is meaningful (use `activity_status`) |
| C-6 | Tests: add `frontend/src/__tests__/FighterProfile.test.jsx` (none exists today — CONFIRMED: tests exist for AnalystMode, Dashboard, FighterSearch, FightPoster, HistoricalScorecard, PicksBuilder only) |

### Recommended *separate* tickets (not part of 01B/01C)
- **FTR-01D — Intelligence missing-data guards:** chaos (B2), fight_dna (R5, cardio default), win_path NULL-method→decision (B5), perception_gap date `TypeError` (R1), nightmare/clash on `unclassified`; with `predictions_log`/scorecard impact analysis. *Opus + ultrathink per CLAUDE.md (touches scoring).* R1 is a straightforward production bug and could be fast-tracked.
- **FTR-01E — Source remediation:** recover `UFC_full_data_golden.csv`; produce a NaN mask / `gender` / method / division table; import into **new** columns/tables only; requires write approval.
- **FTR-01F — Remove fabricated `recent_fights` (R4).**

---

## 10. Acceptance criteria and test matrix

### 10.1 Global acceptance criteria (PROPOSED)
- AC-1 Prediction outputs, feature vectors, model hash and `latest_features` are byte-identical before/after (§7.3).
- AC-2 No API response emits a numeric zero for a field whose status is `unavailable`/`not_stored`/`undefined_no_attempts` in the new objects.
- AC-3 No default style label exists; an incomplete fighter is `unclassified` with a reason.
- AC-4 Existing response keys remain present with unchanged types in release N.
- AC-5 `Composite` can take values < 100 for ordinary fighters (property test: monotonic in each input; range [0,100]; not constant over the grid).
- AC-6 Result enum includes `D`/`NC`; the NC fixture never renders as `L`.
- AC-7 All new tests deterministic (fixed fixtures; no network/DB; no reliance on real-world fighter labels as the only oracle).
- AC-8 Sensitivity report committed; flip rates reported; thresholds approved by a human (D5).

### 10.2 Test matrix (deterministic fixtures: in-memory SQLite, existing `_seed_fighter` pattern in `test_feature_calculator.py`; pure-function tests need no DB)

| ID | Scenario | Fixture (synthetic) | Expected |
|---|---|---|---|
| T01 | **Aaron-Pico-like / incomplete data** | 13-4, age 28, height 0, reach 0, all 7 stats 0, 1 fight (lost), `weight_lbs` 145 | `core_block_available=false`; stats fields `unavailable`; `style_profile.unclassified/INSUFFICIENT_DATA`; `scores.*.available=false`; `intelligence.style = null`; no `STRIKER` anywhere; history result `L` |
| T02 | Complete striking stats | 10 fights; `slpm` at 90th pct of division peers, `td_avg` and `sub_avg` at ~30th | `primary_style=STRIKING`, `secondary=[]` |
| T03 | Strong wrestling evidence | `td_avg` 95th pct, `slpm` 40th, `sub_avg` 20th | `primary=WRESTLING` |
| T04 | Mixed-style (striking + wrestling) | `slpm` 80th, `td_avg` 70th (diff 10 < margin 20) | `primary=STRIKING`, `secondary=[WRESTLING]` |
| T05 | Wrestling + submission grappling | `td_avg` 85th, `sub_avg` 75th | `primary=WRESTLING`, `secondary=[SUBMISSION_GRAPPLING]` |
| T06 | Versatile (all three) | 80/75/70th | `is_versatile=true`; three dimensions listed |
| T07 | No distinct tendency | all 3 at 40–60th, complete data | `unclassified/NO_DISTINCT_TENDENCY` |
| T08 | **Legitimately measured zero** | complete block, 8 fights, `sub_avg=0`, `td_avg=0` (pure striker) | `sub_avg`/`td_avg` status `measured_zero`, value `0` (not null); `td_acc` `undefined_no_attempts`; classification may be STRIKING; **not** treated as missing |
| T09 | Missing individual fields | block available but `height=0`, `reach=0`, `age=0`, `str_def=0` | those fields `unavailable`/null; Composite/Mirage/Chaos-contribution `available=false` (inputs missing) or computed without them per rule; no inflation (regression for B2/B3) |
| T10 | Completely missing combat stats, many fights | 6 fights, all-zero block (the "60 fighters" pattern) | `unclassified/INSUFFICIENT_DATA`; `evidence.fights_used=6`; not classified despite fight count |
| T11 | Draw history | `draws=2` on record; fights rows with `winner='Draw'` | history `D`; win rate denominator includes/excludes per documented rule; streak per `win_streak` |
| T12 | No-contest history | fight `winner='No Contest'` | `NC`; not `L`; excluded from streak; both fighters show `NC` |
| T13 | Missing finish method | all `method=NULL` (production reality) | `methods_available_fraction=0.0`; no `finish_rate`-based claim emitted; `method_available=false`; none counted as decision |
| T14 | Percentile boundary | inject percentiles `64.99/65.00/65.01` into `qualify()` (threshold logic separated from percentile maths) | `65.00` present (inclusive); `64.99` absent; margin boundary `primary−20` inclusive |
| T15 | Percentile maths & ties | 11 peers with distinct values; and 11 peers with a 5-way tie | mid-rank formula exact; ties don't produce `percentile > 100` |
| T16 | Small division | 12 eligible peers | pooled flag / `PEER_GROUP_TOO_SMALL` per `MIN_PEERS`; deterministic |
| T17 | Sparse peer set with ineligible zeros | peers include 30% all-zero fighters | zeros excluded from reference set; percentile unchanged vs. same set without them |
| T18 | Division resolution | fighter with `fighters.weight_class='Strawweight'` but fights rows `Women's Strawweight` | division key `Women's Strawweight`, `basis='fights_table'`; Open/Catch/`'0'` ignored |
| T19 | Composite property | grid over (win_rate, acc, def) | strictly increases with each input; not saturated; range [0,100] (regression B1) |
| T20 | Chaos/Mirage guard | `str_def` unavailable, 70% win rate | Mirage = unavailable (not 22.9); Chaos contribution unavailable |
| T21 | Backward compat | snapshot of existing response keys/types for a fixture fighter | all legacy keys present; types unchanged (release N) |
| T22 | `/fighters` & activity | fixture with dates around the 24-month window | `activity_status` boundary inclusive; never `retired` |
| T23 | **Prediction regression** | §7.3 hashes + vector snapshot + `test_feature_calculator.py` + `test_p0.py` + `test_api_phase3.py` unchanged | pass unmodified |
| T24 | Date-type regression (R1) | `datetime.date` rows through `perception_gap._aura_score` | no `TypeError` (this lives in FTR-01D if intelligence is out of scope; add the fixture now so the gap is visible) |
| T25 | Frontend | `FighterProfile.test.jsx`: `null` → "Not available", unclassified copy, multi-chip rendering, no STRIKER fallback, Inactive badge hidden | pass |

Baseline (could not run in this audit): `pytest` is **not installed** in `.venv` (`No module named pytest`); per the no-install constraint the existing suite was not executed here. STATUS.md claims 248/248 passing (UNVERIFIED by this audit). The 01B kickoff should record a baseline run first.

---

## 11. Open decisions requiring human approval

| ID | Decision | Recommendation |
|---|---|---|
| **D1** | Where is `data/UFC_full_data_golden.csv` / `golden_full_converted.csv`? Needed to (a) verify zero provenance, (b) recover true NaN masks, (c) find method and `gender`. | Locate it before 01B; if it cannot be found, ship rule-based inference with `basis: "inferred_zero_pattern"` |
| **D2** | Availability storage: compute at read-time (no writes) vs. persist a mask/columns (schema + data write). | Read-time for 01B; persisted mask only via FTR-01E |
| **D3** | `stats.*` nulls: in place (breaking for unknown external consumers) vs. additive only for one release vs. `?schema=v2`. | Additive for release N, null-ify in N+1 |
| **D4** | `intelligence.style` semantics, and whether intelligence modules should later adopt `style_profile` (changes `/predict` intelligence, `predictions_log`, scorecard). | Null-guard legacy field now; module migration under FTR-01D |
| **D5** | Thresholds (`T_PRESENT=65`, `MARGIN=20`, `MIN_FIGHTS=3`, `MIN_PEERS=40`), accuracy gates, and the acceptable instability bound; whether any labelled data exists to ever support a confidence number. | Approve *after* viewing the §5.8 sensitivity report, not before |
| **D6** | Peer-group policy: sex-aware fights-derived division; pooling adjacent small divisions; all-era vs era-banded; treatment of Open/Catch weight and fighters with multiple divisions (882). | Fights-derived, pooled only if N<40; decide era after sensitivity run |
| **D7** | May 3-fight (`LIMITED`) fighters be labelled, or only ≥5? Are debutants shown as "Debut — no UFC stats yet" distinct from "data missing" (indistinguishable today)? | Label LIMITED with explicit badge; no distinct debut copy until D1 resolves provenance |
| **D8** | Activity definition: recency window (24 mo.), anchor (dataset end vs wall clock), wording (`RECENT/NOT_RECENT/UNKNOWN`, never "retired"); dataset is ~13 months stale. | Dataset-end anchor; add a visible "data through 2025-10-04" |
| **D9** | Composite/Mirage/Aura redefinition vs. relabel: Composite is not "model-based" (PRD §10.4); Mirage differs from PRD's 0–10 opposition-quality spec. Vocabulary rules in CLAUDE.md. | Relabel as heuristics now; real Mirage needs opponent-quality data (separate ticket) |
| **D10** | Treat the `latest_features` in-fight-column/leakage question as a separate model-owner review? | Yes — not part of FTR-01 |
| **D11** | Model-selection for implementation (CLAUDE.md): style classifier/scoring = Opus + ultrathink; API/React = Sonnet. Per-module workflow `/plan-ceo-review → /plan-eng-review → build → /review → /ship`. | Apply as written |
| **D12** | Fast-track R1 (`perception_gap` TypeError) and R4 (fabricated recent record) outside the FTR-01 sequence? | Yes for R1 (production bug); R4 at your discretion |

---

## Appendix A — Read-only SQL used (all `SELECT`, executed with `default_transaction_read_only=on`)

Representative queries (full set was ~100 statements; results tabulated in §2.2):
```sql
-- all-zero core block
SELECT count(*) FROM fighters WHERE coalesce(slpm,0)=0 AND coalesce(str_acc,0)=0 AND coalesce(str_def,0)=0
  AND coalesce(td_avg,0)=0 AND coalesce(td_acc,0)=0 AND coalesce(td_def,0)=0 AND coalesce(sub_avg,0)=0;       -- 181
-- methods
SELECT count(*) FROM fights WHERE method IS NOT NULL;                                                         -- 0
-- women bucketed into men's names
SELECT f.weight_class, count(DISTINCT f.name) FROM fighters f
  JOIN fights x ON (x.r_name=f.name OR x.b_name=f.name) WHERE x.weight_class LIKE 'Women%' GROUP BY 1;        -- Strawweight 102, Flyweight 79, Bantamweight 68, Featherweight 7
-- display columns == model feature copies
SELECT count(*) FROM fighters WHERE abs(coalesce(slpm,0)-coalesce((latest_features->>'r_fighter_SlpM')::float,0))>1e-9;  -- 0
-- all-zero by number of UFC fights in dataset
SELECT n,count(*) FROM (SELECT (SELECT count(*) FROM fights x WHERE x.r_name=f.name OR x.b_name=f.name) n
  FROM fighters f WHERE <all-zero predicate>) t GROUP BY 1 ORDER BY 1;                                        -- 1:121, 2:33, 3:11, …
```

## Appendix B — Reproduction snippet (pure functions, no DB/app)

```python
# run with project .venv from repo root; sys.path.insert(0,'backend')
from intelligence import utils, chaos_scorer, perception_gap
from intelligence.models import FighterContext
import datetime as dt
zero = dict(wins=13,losses=4,draws=0,age=28.0,weight_lbs=145.0,height_cm=0.0,reach_cm=0.0,
            weight_class='Featherweight',slpm=0.0,str_acc=0.0,str_def=0.0,td_avg=0.0,td_acc=0.0,td_def=0.0,sub_avg=0.0)
utils.classify_style(zero)                      # 'STRIKER'          (B4)
utils.finish_rate([{'method': None}]*4, 'x')    # 0.0                (B5)
# main.py:578-581 composite, verbatim → 100.0 for Pico, 9260/9261 grid points saturated   (B1)
# chaos_scorer.compute(Pico, opp) → 13.55 ['chin_issues','loss_streak']                   (B2)
perception_gap.compute(FighterContext(name='P',stats=zero,wins=13,losses=4,
    fights=[{'date': dt.date(2025,8,16),'winner':'x','method':None}]), <ctx2>, (0.3,0.7))
# → TypeError: '>=' not supported between instances of 'datetime.date' and 'str'          (R1)
```

## Appendix C — Files inspected

`CLAUDE.md`, `STATUS.md`, `TODOS.md` (grep), `SCIPHR_PRD_v1.1.md` §10.4 (lines 551-590), `backend/main.py` (429-659, 1069-1179, greps), `backend/ai_analyst.py` (1-90), `backend/db/models.py`, `backend/scripts/migrate_csv.py`, `backend/intelligence/{utils,orchestrator,models,chaos_scorer,fight_dna,perception_gap,win_path,nightmare_matchup}.py`, `src/golden_feature_calculator.py`, `src/predictor_golden.py` (170-215), `src/convert_golden_FULL.py` (1-110), `models/golden_model.pkl` (feature names/metadata read; model not modified), `frontend/src/pages/{FighterProfile,FighterSearch}.jsx`, `frontend/src/api/api.js` (grep), `frontend/src/components/picks/AnalystMode.jsx` (grep), `backend/tests/{test_utils,test_feature_calculator,test_api_phase3,conftest}.py` (targeted), `frontend/src/__tests__/*` (listing + greps).
