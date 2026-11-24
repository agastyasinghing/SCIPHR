# FTR-01A2 — Original Source Recovery and Data Provenance

**Ticket:** FTR-01A2 (strict read-only investigation; follows `docs/FTR-01_AUDIT.md`)
**Repo:** `main` @ `53b7c1c7ac72646e6bf1cf7a41d3c3c376a5fd43`; worktree = one pre-existing change (`backend/requirements-prod.txt`) + untracked `docs/`
**Date:** 2026-11-23
**Changed by this ticket:** only this document (no application code, DB rows, CSVs, model, dependencies; nothing committed or pushed; no large data copied into the repo).

Status labels (as in the audit): **CONFIRMED** (observed in this session) · **INFERRED** · **PROPOSED** · **UNKNOWN**. Audit assumptions are re-graded **CONFIRMED / REFUTED / STILL UNKNOWN** in §10.
Repair classes: **A** safe read-time/API-only · **B** recoverable from original data · **C** requires external data · **D** cannot currently be established.

---

## Headline results

| Question | Answer |
|---|---|
| Are original missing values recoverable? | **Partly.** Height (41), reach (671), age (158) and weight (18) are **true NaN in the original** and fully, deterministically restorable (**B**). The seven career stat columns (`SlpM`, `Str_Acc`, `Str_Def`, `TD_*`, `Sub_Avg`) are **already 0 in the original** — there is no NaN to restore; the 181 all-zero fighters are zero *in the source itself* (**D** for official values). But per-bout totals exist in the source for 164/181 of them, so a **dataset-derived** replacement is possible (**B**, with caveats, §3.3). |
| Are finish methods recoverable? | **Yes, 100%.** The original has a complete `result` column (0 NaN, 8 values) plus `result_details` (21 NaN, all legitimate), `finish_round`, `finish_time`. The DB shows 0 methods only because `migrate_csv.py:346` reads a column named `finish` that does not exist. (**B**) |
| Can divisions be corrected? | **Yes.** The original has `gender` (0 NaN), `weight_class` incl. all four Women's divisions (10 NaN), and a unique URL per fighter. Fight-level division and sex are deterministic (**B**). 76 fighters have no standard-division bout (Open/Catch/tournament only) and need a fallback (**C/D** for those). |
| Does the source match the imported DB? | **Yes — exactly.** `UFC_full_data_golden.csv → convert_golden_FULL.py → golden_full_converted.csv → migrate_csv.py → Supabase`. 14 fighter columns × 2,615 fighters: **0 mismatches**; 8,231/8,231 fights match on (r_name, b_name, date, winner, weight_class); `latest_features` spot-checked on 10 features: mismatches confined to the 45 tournament-era fighters with two bouts on one date (§8). |
| Biggest surprise | The career stats are **not pre-fight snapshots**. They are **constant across every row of a fighter** (99.9%), i.e. one scrape-time value copied onto all of that fighter's bouts. This **refutes** the audit's §2.4 "pre-fight snapshot" hypothesis and has implications beyond display (flagged, not investigated: §10, R-X). |

---

## 1. Source-file inventory

All under `C:\Users\sagas\sciphr\data\` (an older sibling checkout of the project, outside the repo). Hashes computed read-only.

| File | Bytes | Rows | Cols | mtime | SHA-256 | Role |
|---|---|---|---|---|---|---|
| `UFC_full_data_golden.csv` | 397,033,723 | 8,231 | 5,437 | 2025-11-17 23:56 | `09d939da…33d100` | **Original** (one row per bout; `f_1_*`/`f_2_*` corners) |
| `golden_full_converted.csv` | 397,447,852 | 8,231 | 5,426 | 2025-11-18 00:30 | `96ec2ac3…cb80d` | **Converted** (`r_*`/`b_*`); this is what was migrated |
| `golden_converted.csv` | 3,093,707 | 8,231 | 55 | 2025-11-18 | `f35c8bb1…89dc8` | Auxiliary, older/slimmer export (`src/convert_golden_dataset.py`) — **not** the DB source (§1.2) |
| other files in folder | — | — | — | — | — | `kaggle_processed*.csv`, `large_dataset.csv`, `processed_fights.csv`, `ufc_fights.csv` (not examined; not part of the lineage) |

Also verified: `C:\Users\sagas\sciphr\src\convert_golden_FULL.py` is **byte-identical** to the repo's `src/convert_golden_FULL.py`; `models/golden_model.pkl` is byte-identical to the repo's. The older checkout's `backend/scripts/migrate_csv.py` **differs** from the repo copy (older version; not analysed further — the repo copy is the one that produced the DB per the STATUS.md decision log; the DB content is consistent with the repo logic, §8).

### 1.1 Original file structure (CONFIRMED)

- **Single-valued bout columns (24):** `event_name, referee, winner, num_rounds, title_fight, weight_class, gender, result, result_details, finish_round, finish_time, fight_url, event_date, event_city/state/country, event_url, winner_encoded, fight_duration_minutes, r1…r5_duration`.
- **Per-corner columns:** `f_1_*` (red) / `f_2_*` (blue): identity (`name, url, f_name, l_name, nickname`), physical (`fighter_height_cm, fighter_weight_lbs, fighter_reach_cm, fighter_stance, fighter_dob, age`), career block (`fighter_w/l/d/nc_dq`, `fighter_SlpM/Str_Acc/SApM/Str_Def/TD_Avg/TD_Acc/TD_Def/Sub_Avg`), in-bout totals (`knockdowns, sig_strikes_*, takedown_*, submission_att, ctrl_time_sec, round-level r1…r5`), `fight_number`, `ranking`, odds, and rolling-window columns (`*_3_f_1 … *_15_f_1`).
- **Identity:** 2,615 unique `f_*_name` ⇔ 2,615 unique `f_*_url` (1:1 name↔URL; no name collisions, no duplicate identities) (**CONFIRMED**). `(date, r_name, b_name)` unique in both CSVs and the DB (0 duplicates).
- **No `finish` column exists** in either CSV (`'finish' in converted header → False`).

### 1.2 Auxiliary `golden_converted.csv`
55 columns (`r_fighter, r_height, r_age, r_wins_total, r_SLpM_total, …`), **0 NaN anywhere** (already filled), **no** `result`, `gender`, `weight_class`. Contains `r_reach = 0` for 419 rows. It cannot supply method, sex, or division, and its NaN-free state means it cannot supply missingness either. **Not a repair source.**

---

## 2. Original-to-database lineage

```
C:\Users\sagas\sciphr\data\UFC_full_data_golden.csv           8,231 × 5,437   (NaN preserved)
   │   [pandas read_csv]  src/convert_golden_FULL.py  (identical in repo & old checkout)
   │     :26  date  = to_datetime(event_date);  :27 event = event_name
   │     :33-45  f_1_* → r_*,  f_2_* → b_*          (rolling `_N_f_1` → `_N_r`, etc.)
   │     :76-82  copies weight_class, gender, result, result_details, finish_round,
   │             finish_time, event_*, referee, num_rounds, title_fight  (all PRESENT in source)
   │     :86  converted = converted.fillna(0)       ← NaN → 0 (height/reach/age/weight/ weight_class/ result_details)
   │     DROPPED (13 cols): event_name→event, fight_url, event_url, fight_duration_minutes,
   │             r1…r5_duration, fight_ordinal_f_1/2, fighter_dob_f_1/2   (the first-4-groups matter below)
   ▼
C:\Users\sagas\sciphr\data\golden_full_converted.csv          8,231 × 5,426   (NaN → 0; '0' strings in text cols)
   │   [pandas read_csv, sort date asc]   backend/scripts/migrate_csv.py
   │     :346  method = row.get("finish")       ← column ABSENT → always NaN → NULL   ★ root cause
   │     :347  weight_class = row.get("weight_class")  (raw; NaN→0 → '0' string, 10 rows)
   │     :182-208  fighter base columns from LATEST row per fighter (unstable same-date tie-break)
   │     :191  weight default 185 when 0/NaN → Middleweight (18 fighters)
   │     :132-149 _clean → latest_features JSONB (NaN → 0.0)   [MODEL INPUT — do not touch]
   ▼
Supabase: fighters (2,615) · fights (8,231; ids 16501-24731) · predictions_log (9) · events/event_fights/odds_history/narrative_outcomes (0 rows each)
   ├─ MODEL:   fighters.latest_features → build_full_feature_vector() → XGBoost (frozen)
   └─ DISPLAY: fighters base columns → get_latest_fighter_stats() → GET /fighter/{name} → FighterProfile.jsx
```

**Is the original the true pre-conversion source of the DB? Yes (CONFIRMED).** Evidence in §8: row-for-row agreement on all 8,231 bouts (including the 10 `'0'` weight-class artefacts, which only arise from `fillna(0)` on the original's 10 NaN), the 21 `result_details` NaN→`0`, and 0 mismatches on all 14 stat columns.

---

## 3. Field-by-field provenance

"Latest" = the row the migration selects per fighter (most recent bout). n = 2,615 fighters unless stated; 16,462 = all corner-rows. "DB" = Supabase value. All CONFIRMED.

### 3.1 Core table

| Field | Original column | NaN preserved in original? | Original NaN (all rows / latest) | Original explicit 0 (all rows / latest) | Converter | DB | Restorable? | Class |
|---|---|---|---|---|---|---|---|---|
| Height | `f_N_fighter_height_cm` | **Yes** | 48 (0.29%) / **41 (1.57%)** | 0 / 0 | `fillna(0)` → 0 | `height_cm = 0.0` ×41 | Deterministic: NaN ⇔ DB 0 (41/41) | **B** |
| Reach | `f_N_fighter_reach_cm` | **Yes** | 1,322 (8.03%) / **671 (25.66%)** | 0 / 0 | → 0 | `reach_cm = 0.0` ×671 | Deterministic (671/671) | **B** |
| Age | `f_N_age` (age at bout; DOB in `fighter_dob`) | **Yes** | 269 (1.63%) / **158 (6.04%)** | 0 / 0 | → 0 (`fighter_dob` itself dropped) | `age = 0.0` ×158 | NaN ⇔ DB 0 (158/158). Age is **age at last bout**, varies across rows (97%) | **B** |
| Weight (lbs) | `f_N_fighter_weight_lbs` | **Yes** | 22 (0.13%) / **18 (0.69%)** | 0 / 0 | → 0 | migration: 0/NaN → **185** → "Middleweight" ×18 | Deterministic: 18 NaN-weight fighters are the defaulted ones. Their bout divisions: Lightweight 6, Heavyweight 2, Middleweight 2, none standard 8 | **B** |
| Record `w/l/d` | `fighter_w/l/d` | n/a (never NaN) | 0 | w:52, l:71, d:2,179 (latest) | — | exact | Values exact. **Scrape-time** record (§3.4) | — |
| `SlpM` | `fighter_SlpM` | **No NaN exists** | 0 / 0 | 340 (2.07%) / **200 (7.65%)** | — | exact (0 mismatches) | Zeros are in the source; official value **not recoverable** | **D** (official) / **B** (derived, §3.3) |
| `Str_Acc` | `fighter_Str_Acc` | No NaN | 0 / 0 | 340 / 200 | — | exact | as above | D / B |
| `SApM` (not in DB) | `fighter_SApM` | No NaN | 0 / 0 | 320 / 184 | — | not stored in base columns | n/a | — |
| `Str_Def` | `fighter_Str_Def` | No NaN | 0 / 0 | 322 / **186** | — | exact | as above | D / B |
| `TD_Avg` | `fighter_TD_Avg` | No NaN | 0 / 0 | 1,674 (10.17%) / **661 (25.28%)** | — | exact | zeros mix legit "no takedowns" and missing | D / B |
| `TD_Acc` | `fighter_TD_Acc` | No NaN | 0 / 0 | 1,674 / 661 | — | exact | `TD_Acc = 0 ⇔ TD_Avg = 0` (identical counts; structural) | rule |
| `TD_Def` | `fighter_TD_Def` | No NaN | 0 / 0 | 921 (5.59%) / **471 (18.01%)** | — | exact | ambiguous (legit 0% and 100% (153) both occur) | D |
| `Sub_Avg` | `fighter_Sub_Avg` | No NaN | 0 / 0 | 3,983 (24.2%) / **1,100 (42.07%)** | — | exact | mostly legit zero | D |
| Knockdowns | `f_N_knockdowns` (**per-bout**) | **Yes** | 42 (0.26%) / 25 | 13,401 (81.41%) / 2,370 | `fillna(0)`; stored only inside `latest_features['r_knockdowns']` (last bout) | **No career column**; API hard-codes 0.0 | Career total = Σ per-bout over the fighter's dataset bouts: computable for 2,598 fighters; 1,190 have ≥1 KD. The 42 NaN rows are 1994–1999 bouts (true absence) | **B** (dataset-derived; label as such) |
| Method | `result` (+`result_details`) | **Yes, complete** | `result`: 0; `result_details`: 21 | — | copied unchanged (`other_important`) | `fights.method` NULL ×8,231 | §6 | **B** |
| Winner | `winner` | complete | 0 | — | copied | exact (0 mismatches) | — | — |
| Sex | `gender` (`M`/`F`) | complete | 0 | — | copied | **not stored** | §7 | **B** |
| Division | `weight_class` | NaN preserved | 10 | — | `fillna(0)` → `'0'` | `fights.weight_class` exact incl. `'0'`×10; `fighters.weight_class` = lbs-derived | §7 | **B** |
| Nickname/stance/DOB | `fighter_nickname/stance/dob` | preserved | dob: 269 | — | dob dropped | `nickname` column unused (NULL) | recoverable | **B** (out of FTR-01 scope) |
| Fight URL / event URL / duration | `fight_url`, `event_url`, `fight_duration_minutes` | complete (duration 0 NaN, 2 zeros) | 0 | — | **dropped** | not stored | recoverable; durations enable derived per-minute stats | **B** |

### 3.2 What "constant across rows" means (CONFIRMED)
For the 1,785 fighters with ≥3 bouts: `fighter_SlpM` varies across a fighter's rows for **0.1%** of fighters; `fighter_w`: 0.1%; `fighter_height_cm`: 0.1%; **`age` varies for 97.1%**. Example: a fighter with 9 dataset bouts from 2002–2013 carries the identical `30-14-1`, `SlpM 3.45`, `Str_Acc 0.34` on all nine rows while `age` rises 21 → 32. So `fighter_*` career values are **one scrape-time value copied to every bout**, not a pre-fight snapshot. The "latest row" selection therefore changes only `age` (and rolling/in-bout columns); the display stats are the same on any row of that fighter.

### 3.3 Dataset-derived career stats (recoverable alternative, caveated)
Per-bout totals + `fight_duration_minutes` allow recomputing: SlpM = Σsig_succ/Σmin; Str_Acc = Σsucc/Σatt; Str_Def = 1 − Σopp_succ/Σopp_att; TD_Avg = 15·Σtd/Σmin; TD_Def; Sub_Avg = 15·Σsub_att/Σmin; career knockdowns = Σ. Validation against the official scrape values for 1,187 non-zero fighters with ≥5 bouts:

| Stat | corr. with official | median \|diff\| | within 5% (relative) |
|---|---|---|---|
| SlpM | 0.962 | 0.043 | 70.9% |
| Str_Acc | 0.930 | 0.007 | 85.9% |
| Str_Def | 0.944 | 0.007 | 87.8% |
| TD_Avg | 0.965 | 0.032 | 56.6% |
| TD_Acc | 0.889 | 0.007 | 64.9% |
| TD_Def | 0.929 | 0.008 | 74.7% |
| Sub_Avg | 0.923 | 0.033 | 44.7% |

Conclusion (CONFIRMED): derived values track the official ones closely but are **not equal** (different bout coverage/definitions). They must be stored/served as a **separately named, provenance-labelled** metric (`dataset_derived`), never silently substituted for official values. Coverage for the 181 all-zero fighters: **164** have non-zero bout minutes and **147** have strike attempts (141 pre-2001 fighters of which 17 have zero strike attempts; all 23 post-2000 fighters covered). Pico: 1 bout, 3.35 min, 13/29 sig. strikes → derived SlpM 3.88, Str_Acc 0.45 (single-bout, **LIMITED evidence**).

### 3.4 Records and snapshot semantics
- `fighter_w/l/d` are scrape-time (constant per fighter). They are **career/pro** records (every fighter has `w+l+d ≥ dataset bouts`).
- Dataset **observed wins never exceed scraped wins** (0 fighters), but **131 fighters have observed non-wins > scraped losses** (116 by +1, 14 by +2, 1 by +6); only 32 of those are explained by draws/NC/DQ columns. Cause **UNKNOWN** (likely scrape timing vs. last bouts or classification of NC/DQ); consequence: the profile record can lag the dataset for some fighters. Expose `record_scope: "scraped_career_record"`, never as "as of last bout".
- `fight_number` (0-based) equals `dataset_bouts − 1` for **99.5%** of fighters ⇒ the dataset contains each fighter's **complete UFC career** (CONFIRMED). The audit's "UFC fights in dataset" is therefore effectively "UFC fights".

---

## 4. Missingness and zero-value coverage

### 4.1 The 181 all-zero fighters (CONFIRMED)
- **181/181 are all-zero in the original itself** and in **every row** of theirs (no fighter has a non-zero earlier row). The conversion/migration added nothing.
- **Every one has a non-zero record** (`w+l+d > 0`), so "zero because no fights" is false.
- **Era structure:** last bout 1993–2000: **158 (87%)**; 2006–2010: 1; **2024–2026: 22** (20 debuts, `fight_number = 0`; 2 second bouts). By contrast fighters last active 2001–2005 and 2011–2023: **0**.
- Interpretation (**INFERRED**): two mechanisms — (1) early-UFC era with no stat tracking on the official profile; (2) 2025 debutants whose profile stats were not yet populated at scrape time (37 other 2024+ single-bout fighters *do* have stats, so debut ≠ always zero). Whatever the mechanism, the source value is a **placeholder zero**, and an all-seven-zero block is a **perfect structural-missingness signature** (no false positives are visible: no all-zero fighter has a plausible measurement; no fighter with a real measurement has all seven zero).
- In-bout evidence: of the 181, last-bout `sig_strikes_att` is NaN for 25, 0 for 19, >0 for 137.

### 4.2 Partial zeros (CONFIRMED counts, latest row)
| Pattern (not all-zero) | Fighters | Reading |
|---|---|---|
| `SlpM = 0 ∧ Str_Acc = 0` (SApM > 0) | 19 (16 with 1 bout; years 2000–2025) | plausible ultra-short/zero-offense bout *or* partial scrape; **ambiguous** |
| `Str_Def = 0` | 5 | implausible as measurement; treat as unavailable (as audit §4.2) |
| `TD_Acc = 0 ∧ TD_Avg > 0` | 0 | structural identity holds exactly |
| `TD_Def = 0` | 290 total non-all-zero (154 with TD_Avg>0) | ambiguous; legitimate small-sample extreme |
| `TD_Def = 1.0` | 153 | legit extreme |

### 4.3 Physical/other (latest row)
Height NaN 41 · reach NaN 671 (123 of them for fighters last active ≥2015) · age NaN 158 · weight NaN 18. **No values below plausible ranges** (height 152.4–210.8, reach 147.3–213.4, age 18–51). No unit conversions are performed anywhere in the lineage (all cm / lbs in source).

### 4.4 Tournament-era ties (CONFIRMED)
45 fighters have **two bouts on the same date** (UFC 1–~13 tournament nights, 1994–1997). "Latest row" is ambiguous for them; migration used an unstable sort. Stats are identical either way (constant per fighter); only `was_red`/rolling/in-bout columns inside `latest_features` can differ (§8).

---

## 5. Fighter-specific examples

| Fighter | Source facts (original, CONFIRMED) | DB / API today | After recovery |
|---|---|---|---|
| **Aaron Pico** (regression) | 1 bout (2025-08-16 vs Lerone Murphy, blue corner), `fight_number 0`; 13-4-0 (scraped); height NaN, reach NaN, weight 145, age 28, DOB 1996-09-23; all 7 career stats **0 in source**; bout totals: sig 13/29, ctrl 121 s, KD 0, 3.35 min | all zeros, "145 → Featherweight", STRIKER, Composite 100, Mirage 22.9 | height/reach → unavailable (**B**, NaN in source); career block → unavailable (placeholder zero; **D** official); dataset-derived SlpM 3.88 / acc 0.45 available but **LIMITED** (1 bout, 3.35 min); sex F/M from bout `gender`; division = Featherweight (bout) |
| Complete record | e.g. fighters with ≥5 bouts and non-zero block (1,187 compared) | correct | unchanged; derived stats corroborate |
| Single UFC bout | 399 fighters have 1 bout: 121 all-zero, 278 with stats | indistinguishable | all-zero → unavailable; 278 `LIMITED` evidence |
| Multi-bout, zero block | 60 fighters (≥2 bouts, all-zero) — nearly all 1990s | zero | unavailable (source placeholder); derived stats for most |
| Women's catch-weight | 14 women have both `F`- and `M`-tagged bouts (their **Catch Weight** bouts are tagged `M`) | n/a | sex rule in §7 |
| Tournament fighter | e.g. Scott Morris, Remco Pardoel: two bouts on one date | tie-break arbitrary | stats unaffected |

---

## 6. Finish-method recoverability

### 6.1 Root cause (CONFIRMED)
`migrate_csv.py:346` → `method = _clean(row.get("finish")) if not pd.isna(row.get("finish", nan)) else None`. No column named `finish` exists in the converted CSV (`convert_golden_FULL.py:76-78` copies `result`, `result_details`, `finish_round`, `finish_time` but there is no `finish` source column) → `row.get` returns NaN → `None`. The information was present all along in `result`/`result_details`.

### 6.2 Source vocabulary and coverage (original; converted is identical after NaN→0)
`result` — **0 NaN**, 8,231/8,231:

| `result` value | Bouts | Meaning | `result_details` content |
|---|---|---|---|
| `Decision` | 3,698 | decision, type in details | `Unanimous` 2,870 / `Split` 767 / `Majority` 61 |
| `KO/TKO` | 2,635 | knockout/TKO | technique/target text |
| `Submission` | 1,626 | submission | hold name (1 NaN) |
| `Decision - Unanimous` | 131 | decision | scorecards text |
| `TKO - Doctor's Stoppage` | 98 | doctor stoppage | text (**19 NaN**) |
| `DQ` | 23 | disqualification | reason (1 NaN) |
| `Decision - Split` | 19 | decision | scorecards |
| `Could Not Continue` | 1 | the single No Contest (winner `No Contest`, `winner_encoded −1`; "Kick to Groin by Reese", Reese–Dumas 2025-09-13) | text |

`finish_round` / `finish_time`: complete (0 NaN); `num_rounds` 0 for 31 early bouts, 1 for 167.

### 6.3 Ambiguities (CONFIRMED / UNKNOWN)
- **Draws are not representable:** `winner` is always a corner name except the one `No Contest`; no `result_details` contains "Draw"; "Majority" (61) occurs only as `Decision` with a named winner (majority *draws*, if any existed, are absent or recorded as wins — **UNKNOWN**). 436 fighters carry draws in their scraped record, 0 bouts in the dataset are draws.
- `Could Not Continue` is used for the NC; count 1 ⇒ any logic treating it as a *finish* (`utils._is_finish` matches "COULD NOT CONTINUE") would count the NC as a finish.
- `TKO - Doctor's Stoppage` vs `KO/TKO`: separate categories; both are finishes.
- `DQ` is neither a finish nor a decision (is a result by rule); existing `win_path._method_counts` would count DQ wins as decisions (`else: dec += 1`).
- Missing `result_details` (21) never affects category (the `result` is present).

### 6.4 Proposed deterministic mapping (PROPOSED; evidence supports it fully)
| `result` | `method_category` | `decision_type` | finish? |
|---|---|---|---|
| `KO/TKO` | `KO_TKO` | — | yes |
| `TKO - Doctor's Stoppage` | `TKO_DOCTOR` | — | yes |
| `Submission` | `SUBMISSION` | — | yes |
| `Decision` + details `Unanimous/Split/Majority` | `DECISION` | UNANIMOUS/SPLIT/MAJORITY | no |
| `Decision - Unanimous` / `Decision - Split` | `DECISION` | UNANIMOUS / SPLIT | no |
| `DQ` | `DQ` | — | no |
| `Could Not Continue` ∧ `winner = 'No Contest'` | `NO_CONTEST` | — | no |
| anything else | `UNKNOWN` | — | — |

Compatibility note (CONFIRMED by reading `utils._is_finish`, `win_path._method_counts`, `fight_dna`): storing the **raw `result` string** in `fights.method` would make the existing substring logic work for KO/TKO, TKO-Doctor, Submission and "DECISION*", while the NC and DQ rows need care (NC counted as finish; DQ counted as decision). A normalized `method_category` column (new, additive) is safer than overloading `method`. **No DB update was run.**
Coverage: **8,231/8,231 (100%)** of fights; 0 unmapped.

---

## 7. Divisions and fighter identity

### 7.1 What the original provides (CONFIRMED)
- `gender`: complete; **F = 864 bouts = exactly the 864 Women's-division bouts** (Women's Strawweight 347, Flyweight 258, Bantamweight 229, Featherweight 30); 0 `F` bouts outside a Women's division; 0 `M` bouts inside one.
- `weight_class`: 13 standard divisions (9 men's + 4 women's) = 7,880 bouts; `Open Weight` 101; `Catch Weight` 72; 10 NaN; 8 odd labels (`UFC 2/3/4 Tournament Title`, `UFC Middleweight/Light Heavyweight/Bantamweight Title`, `Nieznana`). 190 bouts are non-standard.
- Identity: `f_*_url` unique per fighter; names unique (2,615 ⇔ 2,615).
- Corners, event dates: complete (`f_1`=red, `f_2`=blue; dates 1994-03-11 → 2025-10-04).

### 7.2 Problems (CONFIRMED)
| Issue | Data |
|---|---|
| Women collapsed into men's labels in DB | `fighters.weight_class` is lbs-derived from `fighter_weight_lbs` (women: 115→Strawweight 102, 125→Flyweight 79, 135→Bantamweight 68, 145→Featherweight 7) |
| Fighter sex | Not stored. **Per-bout `gender` is unreliable for catch-weight bouts of women** (tagged `M`): 14 women have both F and M tags. Rule that holds on all data: **sex = F iff any bout has `gender = F` or a Women's division**; no fighter appears in both women's and men's standard divisions (0) |
| Multi-division careers | Standard-division count per fighter: 1 → 1,760; 2 → 723; 3 → 54; 4 → 2; **0 → 76** (Open/Catch/tournament only; none female) |
| lbs-derived vs bout division | derived-from-lbs ≠ most-recent standard division for **186/2,539**; ≠ modal division for **334**; most-recent ≠ modal for **287** (divisional moves are common) |
| Defaulted weight | 18 fighters (NaN weight → 185 → Middleweight); bout divisions: Lightweight 6, Heavyweight 2, Middleweight 2, none 8 |
| Name collisions | none (name ⇔ URL 1:1) |
| `weight_lbs` as a division source | the five top values (170/155/135/145/125/205/115) are division limits, not true weights, for most fighters ⇒ lbs-derived class mostly equals the *limit* class but lags moves |

### 7.3 Proposed division/sex resolution (PROPOSED; no inference from personal attributes)
1. **Sex:** `F` if any bout has `gender='F'` or a `Women's …` `weight_class`, else `M`. Never infer from height/weight/name.
2. **Peer-group key = (sex, bout division)** where division is the **most recent bout in a standard division** (13 values; Women's divisions keep the `Women's` prefix). Never mix sexes.
3. **Fallbacks:** (a) fighters with no standard-division bout (76; all male): `division = null`, `division_basis = "open_catch_or_tournament_only"`, **excluded from style peer groups** (they can still be classified *against* a pooled male reference only if D6 approves); (b) fighters whose only division evidence is a defaulted weight: `division = null`.
4. **Never use** `fighters.weight_class`/`weight_lbs` as the key (kept only as informational `weight_lbs`).
5. Report `divisions_fought` (list) and `moved_divisions: true` for multi-division careers (777 fighters); decide recency vs modal under D6.
6. Small groups: Women's Featherweight has only 30 bouts (≈≤20 fighters) ⇒ pooling policy stays an open decision; pooling must stay **within sex**.

---

## 8. Reconciliation with Supabase (SELECT-only)

| Check | Result |
|---|---|
| Fighter name sets (CSV vs DB) | **identical** (2,615) |
| `wins, losses, draws, age, height_cm, reach_cm, weight_lbs, slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg` (original, latest row, NaN→0 / weight NaN→185) vs `fighters` | **0 mismatches on all 14** |
| `last_fight_date` vs original latest bout date | 0 mismatches |
| `fights` outer join on (r_name, b_name, date) | both = 8,231; left-only 0; right-only 0 |
| `winner` / `weight_class` (NaN→'0') vs original | 0 / 0 mismatches |
| `fights.method` | NULL ×8,231 (source `result` complete) |
| `latest_features` vs converted CSV, 10 sample keys over 2,615 fighters (`r_fighter_SlpM`, `r_ctrl_time_sec`, `r_odds`, `r_age` → 0 mismatches; `r_knockdowns` 2; `r_sig_strikes_succ` 9; `r_sig_strikes_att` 10; `r_fight_number` 13; `wins_3_r` 9; `slpm_3_r` 11) | all residual mismatches belong to the **45 same-date multi-bout (tournament) fighters** (migration's unstable tie-break vs my stable sort); `was_red` differs for 9–10 of them. This is an ordering ambiguity, not corruption. |
| Fight IDs | 16,501–24,731, unique 8,231; gapped (earlier inserts) |
| `predictions_log` rows | **9** (reference fighters by **name text**, not FK to `fights`) |
| `events`, `event_fights`, `odds_history`, `narrative_outcomes` | 0 rows each |

**Can a source-derived repair preserve everything (PROPOSED, class B):**
- *Fighter identities:* yes — match on `name` (unique) / source URL; `id` untouched.
- *Record history:* yes — stored `wins/losses/draws` already equal the source; no change needed.
- *Fight IDs & relationships:* yes — update by `(r_name, b_name, date)` natural key (unique constraint `uq_fight`); `id` unchanged; no table references `fights.id` (predictions_log uses names).
- *Prediction logs:* untouched (9 rows by name).
- *ML feature vectors / model artifact:* **do not touch `latest_features`**; repairs go only into **new** columns/tables or API-time derivation. Model hash unchanged (`a465a75a…74a44`; also byte-identical to the older checkout's copy).

---

## 9. Proposed safe repair strategy

All items **PROPOSED**; none executed. Order by risk. Classes per §header.

| # | Correction | Class | Method | Touches model inputs? |
|---|---|---|---|---|
| R1 | Method for 8,231 bouts | **B** | New columns `fights.method_category`, `fights.decision_type`, `fights.finish_round`, `fights.finish_time` (+ optionally `result_raw`, `result_details`) filled from the original by natural key; do **not** repurpose the existing NULL `method` until consumers are tested | No |
| R2 | Sex per fighter | **B** | New `fighters.sex` (rule §7.3) | No |
| R3 | Bout division per fight (Women's labels, `'0'`→NULL, standard flag) | **B** | New `fights.division_std`, `fights.is_standard_division`; clean `'0'`/`Nieznana`→NULL in the new column only | No |
| R4 | Fighter division | **B** (+**D** for 76) | New `fighters.division_std` = most-recent standard division per §7.3; NULL + basis for the 76 | No |
| R5 | Height / reach / age / weight availability | **B** | New nullable columns (or an availability table) from original NaN; keep existing 0.0 columns unchanged for backward compat | No |
| R6 | Career stats availability (all-zero block) | **A** | Rule: all seven zero ⇒ unavailable. Now **validated** against the source: 181/181 placeholder zeros, 0 false positives; `basis: "source_placeholder_zero"` | No |
| R7 | Partial-zero fields | **D** | Cannot be established from either file (no attempt counts); keep `low_sample` flag only | No |
| R8 | Dataset-derived career stats + career knockdowns | **B** | Derive from bout totals/durations into a separate `fighter_derived_stats` (or API-time) object labelled `source: dataset_derived`; never overwrite official columns | No |
| R9 | Draws | **D** / **C** | Not in source; need an external UFC results source to establish draws. Display-only fix (D/NC enum) is **A** | No |
| R10 | Activity (`RECENT/NOT_RECENT`) | **A** | From `last_fight_date` vs dataset end (unchanged from audit) | No |
| R11 | Record vs dataset lag (131 fighters) | **D** | Cause unknown; label `record_scope` | No |
| R12 | Current weight/division after 2025-10-04, retirements, new bouts | **C** | needs fresh scrape | No |
| R13 | Tournament-era latest-row ambiguity (45 fighters) | **D** for `latest_features`; irrelevant for display | do not alter model inputs | **Yes — leave alone** |

Execution preconditions (for a later ticket): backup/snapshot; dry-run diff report; idempotent upsert by natural key; additive columns only; no change to `latest_features`, `golden_model.pkl`, or existing columns; reconciliation script re-run after (the checks in §8 become the acceptance test).

---

## 10. Re-assessment of FTR-01A assumptions and decisions D1–D12

### 10.1 Audit assumptions
| Audit statement | Now |
|---|---|
| Nullability lost at `convert_golden_FULL.py:86` and `_clean` | **CONFIRMED** (source had NaN for height/reach/age/weight/weight_class/result_details only) |
| DB cannot distinguish missing from measured zero | **CONFIRMED for DB** — but **REFUTED as a source limitation for physicals**: original preserves NaN |
| Career stat zeros might be NaN→0 conversions | **REFUTED**: zero in the original; no NaN ever existed in those columns |
| All-zero block ⇒ missing (inferred rule) | **CONFIRMED** (181/181 placeholder zeros; era structure; no counter-examples) |
| `fighter_*` are pre-fight snapshots (audit §2.4, "mixed") | **REFUTED**: constant per fighter = scrape-time values |
| 278 single-bout fighters with stats contradict "debut ⇒ zero" | **Resolved**: scrape-time values; debut does not imply zero |
| Record includes last bout? (UNKNOWN) | **STILL UNKNOWN** (scraped record; 131 fighters lag) |
| `finish` is not a column; method info may exist | **CONFIRMED** (and fully present in `result`) |
| Draws not representable in `fights` | **CONFIRMED** (also absent from the source) |
| Women's divisions collapsed into men's | **CONFIRMED**; source provides `gender` and Women's divisions (**B**) |
| `weight_lbs = 185` ambiguous default | **CONFIRMED**: 18 defaulted, identifiable (NaN in source) |
| Knockdowns unavailable | **REFUTED as "unavailable"**: career totals derivable from per-bout columns (**B**) |
| Division key from `fights` table | **CONFIRMED & strengthened** (plus `gender`) |
| Fighters have complete UFC career in `fights` | **CONFIRMED** (99.5% `fight_number = n−1`) |
| `latest_features` contains last-bout in-fight values | **CONFIRMED**; new fact: career-level `fighter_*` features inside it are scrape-time (**R-X below**) |
| Whether the model was trained with same-fight or future information | **STILL UNKNOWN** (see R-X) |

**R-X (flag only, out of scope):** because `fighter_*` (and the model feature `r_fighter_SlpM` etc.) carry one scrape-time value on every historical bout, training rows for old bouts contain career figures that include later fights. Whether this inflates the 85.7% test accuracy is **UNKNOWN** and must go to the model owner (audit D10). Nothing in this ticket should change model inputs.

### 10.2 Revised decisions
| ID | Audit decision | Revised |
|---|---|---|
| **D1** Source location | open | **RESOLVED** — `C:\Users\sagas\sciphr\data\`. Remaining: move/copy to a stable, backed-up location (outside Git; hash recorded in §1) |
| **D2** Availability storage | read-time vs persisted | **Revised:** persist **additive** availability/provenance columns (R5/R6) once approved; read-time rule for the career block remains valid (now source-validated). Both viable; persisted preferred for physicals, since NaN is lost without a write |
| **D3** `stats` null-ification | additive for N | Unchanged; physicals can now be truly `null` from source, career block `null` by validated rule |
| **D4** `intelligence.style` | null-guard | Unchanged; strengthened — default STRIKER applied to 181 placeholder-zero fighters |
| **D5** Thresholds / confidence | after sensitivity | Unchanged — **no thresholds approved here**. Note: dataset-derived metrics (R8) offer a *uniform* basis (same definition for all fighters) vs mixed scrape values; **new decision D5b:** classifier input = official scraped stats vs dataset-derived stats (derived: complete UFC-career basis, includes minutes/attempt denominators → enables real evidence gates; official: matches UFCStats pages) |
| **D6** Peer group | proposal | **Resolved in principle:** (sex, most-recent standard bout division); open: recency vs modal (287 differ), pooling of small women's divisions, era banding, the 76 |
| **D7** Debut/LIMITED handling | open | Debut-vs-gap now distinguishable via `fight_number` + all-zero + era; evidence tiers can use **bout minutes** (derived) instead of fight count |
| **D8** Activity | open | Unchanged; dataset end = 2025-10-04 (confirmed from source) |
| **D9** Score relabel/redefine | open | Unchanged; Mirage/Composite fixes still app-level |
| **D10** Leakage review | separate | **Escalated** by R-X (still separate, still no action in FTR-01) |
| **D11** Model selection | as written | unchanged |
| **D12** R1 / R4 fast-track | open | unchanged |
| **New D13** | Which repairs run against Supabase (R1–R5, R8) and in what order; who approves the write | needs human approval; recommended order §11 |
| **New D14** | Where `method` semantic lives (new `method_category` vs overloading `method`) | recommend new columns (§6.4) |

### 10.3 Effect on specific FTR-01 design elements
- **Availability statuses:** keep the five statuses; `basis` values become `source_nan` (height/reach/age/weight), `source_placeholder_zero` (career block), `inferred_ambiguous` (partial zeros), `not_in_source` (draws), `dataset_derived` (R8).
- **`data_quality` contract:** add `sex`, `division_basis`, `divisions_fought`, `record_scope: scraped_career_record`, `stats_basis: scraped_current_career`, `bout_minutes`, `method_coverage`, `data_through: 2025-10-04`. No schema-breaking changes.
- **Style gates:** replace "fight count ≥ N" proxy with **bout minutes / strike & takedown attempts** when R8 data exists; fight-count remains the fallback.
- **Historical coverage:** now establishable per fighter (complete career in dataset), plus method coverage → 100% after R1.
- **Intelligence availability:** finish-dependent signals (finish rate, chaos 55-pt component, aura, win_path, fight_dna cardio/chin) become computable after R1 — but this changes `/predict` intelligence outputs, so it needs its own ticket and scorecard-impact review (audit FTR-01D).

---

## 11. Recommended implementation order

1. **Safeguard the sources:** copy both CSVs (+ hashes) to a backed-up, non-Git location; record hashes in the repo doc (done in §1). *(no write to DB)*
2. **Approve D13/D14**, then build an **offline, read-only reconciliation/dry-run script** that emits diff reports for R1–R5/R8 (no DB writes) — becomes the acceptance test.
3. **A-class API work (FTR-01B part 1)** that needs no data repair: availability rules, `data_quality`, scores fixes, result enum, activity, null handling in `FighterProfile.jsx`. Ship first; value without waiting.
4. **R1 (method) + R3/R4/R2 (division, sex)** as additive columns (smallest, fully deterministic, 100% coverage).
5. **R5 (physical availability)** additive nullable columns.
6. **R8 (dataset-derived stats, career knockdowns)** into a separate store, after D5b.
7. **Style classifier (FTR-01B part 2)** on the repaired inputs; sensitivity study; human threshold approval (D5).
8. **FTR-01D** (intelligence guards using restored methods) with scorecard impact analysis; **FTR-01C** (frontend).
9. Leave **R9/R11/R12/R13** and model-leakage review (R-X) as separate, explicitly out-of-scope items.

## 12. Remaining open questions

1. Why are the 131 fighters' observed non-wins larger than their scraped losses (UNKNOWN)? Which scrape date produced `fighter_*`? (file mtime 2025-11-17 is only the CSV build time; the scrape time is not in the data).
2. Are UFC draws genuinely absent from the dataset, or dropped/recorded as named winners? Needs an external results list (class **C**).
3. D5b: official scraped stats vs dataset-derived stats as classifier input?
4. How to treat the 76 fighters without a standard division, and pooling for small Women's divisions (D6).
5. Do any downstream consumers rely on `fights.method` being NULL or on current `fighters.weight_class` (e.g., `chaos_scorer` multipliers, `FighterSearch` weight-class filter)? (A repair adds columns, but switching consumers is a behaviour change.)
6. R-X: model-training implications of scrape-time `fighter_*` features (model owner).
7. Is the older checkout (`C:\Users\sagas\sciphr`) authoritative for anything besides the data (its `migrate_csv.py` differs from the repo's)? Which version ran against Supabase?
8. Fighter photos, nicknames, stance, DOB are recoverable (B) but out of FTR-01 scope — confirm.

---

## Appendix — method of investigation

- Read-only: pandas `read_csv` with `usecols`/`nrows` (no file modified; no copy of data stored in the repo); Supabase via SQLAlchemy with `default_transaction_read_only=on`, SELECT only; `.env` read for the DB URL only (not printed).
- Scratch scripts and pickled extracts (metadata/long-form fighter rows) live only in the session scratchpad (outside the repo).
- Evidence queries: header/shape; per-column NaN/zero counts over all 16,462 corner-rows and over each fighter's latest row; per-fighter constancy test; derived-vs-official stat comparison (1,187 fighters); full row-level join on 8,231 bouts; name-level join of 2,615 fighters on 14 columns; feature-level join on 10 `latest_features` keys; draw/DQ/NC reconciliation against records.
