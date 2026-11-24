# FTR-01B1 — Profile API contract (additive)

Package: `backend/fighter_profile/` (read-only; SELECT on `fighters` display columns and `fights` metadata; never reads `latest_features`; no imports of the predictor, feature calculator, XGBoost or `backend/intelligence`). The directory is `fighter_profile`, not `profile`, because a top-level `profile` package shadows the stdlib module and breaks `import cProfile` (reproduced).

**Internal checkpoint — not a deployment approval.** The legacy frontend still renders the legacy `stats`/`intelligence` values, which remain misleading (see `data_quality.legacy_compat`).

## GET /fighter/{fighter_name}

Legacy keys `name`, `stats`, `intelligence` are unchanged (same keys, same types, same values). Added: `data_quality`, `scores` (each may be `null` if the read-model fails; the request still succeeds).

### `data_quality`
| Key | Meaning |
|---|---|
| `schema` | `fighter_profile_quality_v1` |
| `fields.<name>` | `{value, status, basis, unit, note?}` for `wins, losses, draws, age, height_cm, reach_cm, weight_lbs, slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg, career_knockdowns`. Units are raw (`str_acc/str_def/td_acc/td_def` are 0–1 fractions, unlike legacy `stats`, which multiplies by 100). |
| `core_stat_block` | `{available, basis, fields}` — all seven career combat stats |
| `coverage` | `ufc_fights_in_dataset, first_dataset_fight, last_dataset_fight, snapshot_date, dataset_end (MAX(fights.date)), methods_available_fraction, record_scope, record_as_of (null: scrape date unknown), record_note, stats_basis, age_basis` |
| `legacy_compat` | Known problems in legacy fields, keyed by field path |

**`status`** (enum): `measured` · `measured_zero` · `ambiguous` · `unavailable` · `not_stored`.
**`basis`** (enum): `measured` · `source_nan` · `source_placeholder_zero` · `ambiguous_source_zero` · `not_stored` · `scraped_career_record` · `possible_default` · `invalid_range` · `heuristic`.

Rules (evidence: `docs/FTR-01_SOURCE_RECOVERY.md`)
- `height_cm`, `reach_cm`, `age` stored as 0/NULL → `value: null`, `unavailable`, `source_nan`.
- All seven career stats zero/NULL → every one `value: null`, `unavailable`, `source_placeholder_zero` (`source_nan` if all NULL).
- Otherwise `td_avg`/`sub_avg` = 0 → `measured_zero` (kept 0). `td_acc` = 0 with `td_avg` = 0 → `ambiguous` (not declared undefined). `slpm`, `str_acc`, `str_def`, `td_def` = 0 → `ambiguous` / `ambiguous_source_zero`: the literal `0.0` is returned with the flag and is never used as score input.
- `career_knockdowns` → `null`, `not_stored`.
- `age` is age at the last recorded bout. Records are scraped career records (`record_as_of: null`).
- `weight_lbs == 185` → `ambiguous` / `possible_default`.

### `scores`
`meta` (`schema: fighter_profile_scores_v1`, `kind: profile_heuristics`, `not_model_output: true`, `validated: false`, `record_definition`) plus `composite`, `aura`, `chaos_contribution`, `mirage`. Each: `{value|null, available, status (provisional|unavailable), reason, inputs_required, inputs_missing, provenance: "heuristic", validated: false, label, description, unsupported_claims}`.

Record definition: `win_rate = wins / (wins + losses + draws)`; no-contests are not stored.
- `composite = 40·win_rate + 30·str_acc + 30·str_def` (0–100; legacy had an extra ×100).
- `aura` — record/career-length/volume proxy; **not** public sentiment (`unsupported_claims: public_sentiment`).
- `chaos_contribution = 100·(½·min(1, slpm/7) + ½·(1 − str_def))`; unavailable without measured `slpm` and `str_def`.
- `mirage` — high win rate with weak striking defence; **not** opposition quality (`unsupported_claims: opposition_quality, resume_inflation`); requires measured `str_def` and ≥ 5 recorded bouts (provisional guard).

## GET /fighter/{fighter_name}/history

Preserved: `name`, `fights[].{opponent,date,result,method,weight_class}`, `count`. Added: `fights[].method_available`, `result_counts`, `methods_available_fraction`, `history_note`.
`result` ∈ `W | L | D | NC | UNKNOWN` (legacy: `W | L`). Winner = fighter → `W`; = opponent → `L`; `Draw` → `D`; `No Contest` → `NC`; missing or not attributable → `UNKNOWN`. `method` stays `""` when the DB field is empty (no inference) until FTR-01B2.
