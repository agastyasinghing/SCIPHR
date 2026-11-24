# FTR-01B1 — Profile API contract (additive)

Package: `backend/fighter_profile/` (read-only; SELECT on `fighters` display columns and `fights` metadata; never reads `latest_features`; no imports of the predictor, feature calculator, XGBoost or `backend/intelligence`). The directory is `fighter_profile`, not `profile`, because a top-level `profile` package shadows the stdlib module and breaks `import cProfile` (reproduced).

**Internal checkpoint — not a deployment approval.** The legacy frontend still renders the legacy `stats`/`intelligence` values, which remain misleading (see `data_quality.legacy_compat`).

## GET /fighter/{fighter_name}

Legacy keys `name`, `stats`, `intelligence` are unchanged (same keys, same types, same values). Added: `data_quality`, `scores`, `extension_status`, `legacy_integrity`. If the read-model is unavailable, `data_quality` and `scores` are `null`, `extension_status = {available:false, reason: NOT_FOUND | ERROR | INVALID_SHAPE}` and the request still succeeds with the legacy response. Legacy scores are never substituted for the new ones. `extension_status.reason`: `ERROR` = the builder (or engine access) raised, including a builder `ValueError`; `INVALID_SHAPE` = the builder returned but the payload violated this contract; `NOT_FOUND` = no such fighter row. The extension is validated before use (see *Extension validation*); failures are logged with the fighter name and exception *type* only (no message, traceback or connection string).

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

### Extension validation (`extension_status.available = true` only if all hold)
Required nested objects/keys are present; every `data_quality.fields.*` entry has `value/status/basis/unit` with known enum values, `measured`/`measured_zero` carry a finite value and `unavailable`/`not_stored` carry `null`; `core_stat_block` has a known `status`, boolean `available == (status == "complete")` and the three field lists; `coverage` has its documented keys, a non-negative integer fight count and a fraction in 0–1; no NaN/±inf anywhere. Each of the four scores: `available: true` ⇒ finite value in 0–100 and `status: provisional`; `available: false` ⇒ `value: null`, `status: unavailable` and a non-empty `reason`. Any violation ⇒ `data_quality`/`scores` are `null` with `INVALID_SHAPE` (the response is never reported as a success and nothing is silently nulled afterwards).

### `legacy_integrity` (top-level, always present; independent of the extension)
`{schema: "legacy_integrity_v1", corrupted, raw_input_corruption[], stored_score_corruption[], derived_scores_affected[], note}`. Three kinds are kept distinct:
- `raw_input_corruption[]` — `{field (legacy raw key, e.g. fighter_SlpM), reason, legacy_placeholder}` for a raw number that is malformed/non-finite (`invalid_value`) or impossible (`invalid_range`: negative or fractional counts, fractions outside 0–1, rates > 60, physicals outside sanity bounds; a zero physical is *missing*, not corruption). In legacy `stats` the field shows the **placeholder** (`0`, or `185` for weight) — a placeholder, not a measurement.
- `stored_score_corruption[]` — a stored aura/composite/chaos/mirage value that is malformed, non-finite or outside 0–100. If any is corrupted **all** stored scores are ignored: legacy scores fall back to their documented heuristics and `intelligence.scores_source` is `"heuristic"` (never `"computed"`).
- `derived_scores_affected[]` — `{score, depends_on[], legacy_value: null, reason: "derived_from_corrupted_inputs"}` for legacy heuristic scores whose inputs were corrupted. Those `intelligence.*` score keys are **`null`** (same keys, withheld values) instead of a number that looks trustworthy. Dependencies: `aura_score`←wins, losses, SlpM, TD_Avg; `composite_score`←wins, losses, Str_Acc, Str_Def; `chaos_contribution`←SlpM, Str_Def; `mirage_meter`←wins, losses, Str_Def. A valid stored score is not a heuristic and is never withheld because of raw-input corruption.

For valid data the legacy `stats`/`intelligence` values and types are exactly as before. `data_quality.legacy_corrupted_fields` lists the corrupted raw keys (convenience copy; only present while the extension is available).

### Malformed persisted numbers (profile-only read path)
The shared `GoldenFeatureCalculator.get_latest_fighter_stats` (unchanged) raises on a malformed stored number. The endpoint catches only that coercion failure (`ValueError`/`TypeError`) and re-reads the same columns with `fighter_profile.legacy.read_legacy_raw_stats` (SELECT only; same `float(x or 0)` semantics for valid values, weight default 185; a malformed/non-finite value becomes `None` and is reported). Database/connection errors and unrelated programming errors are **not** caught: they remain HTTP 500, never fabricated data. Non-finite output values are converted to `null` by a final boundary sanitiser, so the JSON is always standards-compliant. (SQLite permits text in numeric columns; whether PostgreSQL can hold such values has not been verified.)

## GET /fighter/{fighter_name}/history

Preserved: `name`, `fights[].{opponent,date,result,method,weight_class}`, `count`. Added: `fights[].method_available`, `result_counts`, `methods_available_fraction`, `history_scope`, `name_match`, `history_note`.
**Scope:** the endpoint returns the latest 20 bouts; `result_counts` and `methods_available_fraction` describe those returned rows only, not necessarily the whole career (`history_scope.window = latest_20_fights`, `may_be_truncated`).
`result` ∈ `W | L | D | NC | UNKNOWN` (legacy: `W | L`). Names and winners are compared after whitespace/case normalisation (display names unchanged). Winner = fighter → `W`; = opponent → `L`; `Draw` → `D`; `No Contest` → `NC`; missing, not attributable, or fighter not on the card → `UNKNOWN`. `method` is `""` (and `method_available: false`) when the DB field is NULL, empty or whitespace-only; a missing method is never inferred to be a decision (until FTR-01B2).

### Participant matching (history and profile coverage share it)
Fights are selected by `LOWER(TRIM(REPLACE(REPLACE(REPLACE(col,'  ',' '),'  ',' '),'  ',' '))) = key` on `r_name` or `b_name` (portable SQLite/PostgreSQL; trims, ignores case, collapses runs of up to 8 spaces), then each candidate is confirmed in Python with the full whitespace-collapse + casefold comparison. No `LIKE`/substring/fuzzy matching. Stored display names are returned unchanged; the opponent is chosen by normalised identity. `name_match = {stored_spellings, fighter_rows_matching_name, ambiguous_identity}` — `ambiguous_identity` is true when more than one `fighters` row normalises to the same name (their fights would be merged). **Limitations:** tabs/newlines/NBSP inside stored names and non-ASCII case folding on SQLite are not matched by the SQL stage; the lookup applies functions to columns, so it scans `fights` (≈8k rows) instead of using the name index — acceptable now, deferred optimisation.
