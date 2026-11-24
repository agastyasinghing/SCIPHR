# FTR-01B1 — Profile API contract (additive)

Package: `backend/fighter_profile/` (read-only; SELECT on `fighters` display columns and `fights` metadata; never reads `latest_features`; no imports of the predictor, feature calculator, XGBoost or `backend/intelligence`). The directory is `fighter_profile`, not `profile`, because a top-level `profile` package shadows the stdlib module and breaks `import cProfile` (reproduced).

**Internal checkpoint — not a deployment approval.** The legacy frontend still renders the legacy `stats`/`intelligence` values, which remain misleading (see `data_quality.legacy_compat`).

## GET /fighter/{fighter_name}

Legacy keys `name`, `stats`, `intelligence` are unchanged (same keys, same types, same values). Added: `data_quality`, `scores`, `extension_status`. If the read-model is unavailable, `data_quality` and `scores` are `null`, `extension_status = {available:false, reason: NOT_FOUND | ERROR | INVALID_SHAPE}` and the request still succeeds with the legacy response. Legacy scores are never substituted for the new ones. The extension shape is validated before use; failures are logged with the fighter name and exception *type* only (no message, traceback or connection string).

### `data_quality`
| Key | Meaning |
|---|---|
| `schema` | `fighter_profile_quality_v1` |
| `fields.<name>` | `{value, status, basis, unit, note?}` for `wins, losses, draws, age, height_cm, reach_cm, weight_lbs, slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg, career_knockdowns`. Units are raw (`str_acc/str_def/td_acc/td_def` are 0–1 fractions, unlike legacy `stats`, which multiplies by 100). |
| `core_stat_block` | `{available, status, basis, fields, usable_fields, unconfirmed_fields, invalid_fields}` — the seven career stats. `status`: `complete` (all usable) · `partial` · `unavailable` (e.g. placeholder). `available` is true only for `complete`: an ambiguous or invalid field means the block does not claim full measured coverage. |
| `coverage` | `ufc_fights_in_dataset, first_dataset_fight, last_dataset_fight, snapshot_date, dataset_end (MAX(fights.date)), methods_available_fraction, record_scope, record_as_of (null: scrape date unknown), record_note, stats_basis, age_basis` |
| `legacy_compat` | Known problems in legacy fields, keyed by field path |
| `legacy_corrupted_fields` | Raw legacy keys (e.g. `fighter_SlpM`) that were NaN/inf/non-numeric and neutralised at the response boundary |

**`status`** (enum): `measured` · `measured_zero` · `ambiguous` · `unavailable` · `not_stored`.
**`basis`** (enum): `measured` · `source_nan` · `source_placeholder_zero` · `ambiguous_source_zero` · `not_stored` · `scraped_career_record` · `possible_default` · `invalid_value` (malformed / NaN / ±inf / non-numeric) · `invalid_range` (finite but impossible) · `heuristic`. Invalid values are never `source_nan` and never `measured`.

Rules (evidence: `docs/FTR-01_SOURCE_RECOVERY.md`)
- `height_cm`, `reach_cm`, `age` stored as 0/NULL → `value: null`, `unavailable`, `source_nan`.
- All seven career stats zero/NULL → every one `value: null`, `unavailable`, `source_placeholder_zero` (`source_nan` if all NULL).
- Otherwise only `sub_avg` = 0 is accepted as `measured_zero`. Every other isolated zero — `td_avg`, `td_acc` (with or without takedowns), `slpm`, `str_acc`, `str_def`, `td_def` — is `ambiguous` / `ambiguous_source_zero`: the literal `0.0` is returned with the flag and is never a score input (`is_usable` rejects `ambiguous`). Takedown attempts are not stored and are never inferred from the landed rate.
- Validation: record counts must be non-negative whole numbers (7.9 is rejected, not truncated); sanity bounds age 16–80, height/reach 100–260 cm, weight 70–800 lbs, rates ≤ 60, fractions 0–1 (bounds reject only clearly impossible values; they are not data-derived).
- `career_knockdowns` → `null`, `not_stored`.
- `age` is age at the last recorded bout. Records are scraped career records (`record_as_of: null`).
- `weight_lbs == 185` → `ambiguous` / `possible_default`.

### `scores`
`meta` (`schema: fighter_profile_scores_v1`, `kind: profile_heuristics`, `not_model_output: true`, `validated: false`, `record_definition`) plus `composite`, `aura`, `chaos_contribution`, `mirage`. Each: `{value|null, available, status (provisional|unavailable), reason, inputs_required, inputs_missing, provenance: "heuristic", validated: false, label, description, unsupported_claims}`.

Record definition: `win_rate = wins / (wins + losses + draws)`; no-contests are not stored.
- `composite = 40·win_rate + 30·str_acc + 30·str_def` (0–100; legacy had an extra ×100).
- `aura` — record/career-length/volume proxy; **not** public sentiment (`unsupported_claims: public_sentiment`). Requires usable `slpm` **and** `td_avg` (an ambiguous zero `td_avg` makes it unavailable).
- `chaos_contribution = 100·(½·min(1, slpm/7) + ½·(1 − str_def))`; unavailable without measured `slpm` and `str_def`.
- `mirage` — **withheld** for this checkpoint (human decision): always `value: null, available: false, status: unavailable, reason: UNVALIDATED_HEURISTIC`, `unsupported_claims: opposition_quality, resume_inflation`. The internal win-rate-vs-defence calculation exists (`scores._mirage_internal`, not exposed) and no eligibility cutoff is claimed. Legacy `intelligence.mirage_meter` is unchanged and known incorrect.

### Non-finite / malformed legacy values (exceptional behaviour)
A NaN/±inf/non-numeric value in the legacy raw stats used to produce HTTP 500 (non-JSON-compliant float). At the response boundary (`fighter_profile.sanitize`, no change to the shared calculator or predictor) such a value is replaced by `None` before the legacy formulas run, so the **legacy** `stats`/`intelligence` show their existing placeholder `0` for that field (not a measurement); any remaining non-finite output becomes `null`. Valid values and types are untouched. The new `data_quality.fields[*]` reads the database independently and reports the field as `invalid_value`; scores that need it are unavailable.

## GET /fighter/{fighter_name}/history

Preserved: `name`, `fights[].{opponent,date,result,method,weight_class}`, `count`. Added: `fights[].method_available`, `result_counts`, `methods_available_fraction`, `history_scope`, `history_note`.
**Scope:** the endpoint returns the latest 20 bouts; `result_counts` and `methods_available_fraction` describe those returned rows only, not necessarily the whole career (`history_scope.window = latest_20_fights`, `may_be_truncated`).
`result` ∈ `W | L | D | NC | UNKNOWN` (legacy: `W | L`). Names and winners are compared after whitespace/case normalisation (display names unchanged). Winner = fighter → `W`; = opponent → `L`; `Draw` → `D`; `No Contest` → `NC`; missing, not attributable, or fighter not on the card → `UNKNOWN`. `method` is `""` (and `method_available: false`) when the DB field is NULL, empty or whitespace-only; a missing method is never inferred to be a decision (until FTR-01B2).
