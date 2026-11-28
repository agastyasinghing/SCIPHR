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
| `coverage` | `ufc_fights_in_dataset` (**`null`, never 0, when bouts exist but none can be attributed reliably**), `coverage_verified`, `identity_status`, `withheld_ambiguous_bouts`, `first_dataset_fight, last_dataset_fight, snapshot_date, dataset_end (MAX(fights.date)), methods_available_fraction, record_scope, record_as_of (null: scrape date unknown), record_note, stats_basis, age_basis` |
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
Required nested objects/keys are present; every `data_quality.fields.*` entry has `value/status/basis/unit` with known enum values (**type-checked first**: lists, dicts, numbers, null and unknown strings are all rejected, never raised as `TypeError`), `measured`/`measured_zero` carry a finite value and `unavailable`/`not_stored` carry `null`; `core_stat_block` has a known `status`, boolean `available == (status == "complete")` and the three field lists; `coverage` has its documented keys, a non-negative integer fight count (or `null` with `coverage_verified: false`) and a fraction in 0–1; no NaN/±inf anywhere. Each of the four scores: `available: true` ⇒ finite value in 0–100 and `status: provisional`; `available: false` ⇒ `value: null`, `status: unavailable` and a non-empty `reason`. Any violation — including any unexpected exception raised by malformed data inside the validator — ⇒ `data_quality`/`scores` are `null` with `INVALID_SHAPE` (HTTP 200; never a 500, never reported as a success, nothing silently nulled afterwards). **Logging:** validation failures log only the fighter name, a fixed reason code (e.g. `FIELD_STATUS_INVALID`, `NON_FINITE_NUMBER`, `VALIDATION_FAULT`) and an identifier from a fixed allowlist (field/score names defined in code). Payload keys, payload values, exception messages, SQL and URLs are never logged.

### `legacy_integrity` (top-level, always present; independent of the extension)
`{schema: "legacy_integrity_v1", corrupted, raw_input_corruption[], stored_score_corruption[], derived_scores_affected[], note}`. Three kinds are kept distinct:
- `raw_input_corruption[]` — `{field (legacy raw key, e.g. fighter_SlpM), reason, legacy_placeholder}` for a raw number that is malformed/non-finite (`invalid_value`) or impossible (`invalid_range`: negative or fractional counts, fractions outside 0–1, rates > 60, physicals outside sanity bounds; a zero physical is *missing*, not corruption). In legacy `stats` the field shows the **placeholder** (`0`, or `185` for weight) — a placeholder, not a measurement.
- `stored_score_corruption[]` — a stored aura/composite/chaos/mirage value that is malformed, non-finite or outside 0–100. If any is corrupted **all** stored scores are ignored: legacy scores fall back to their documented heuristics and `intelligence.scores_source` is `"heuristic"` (never `"computed"`).
- `derived_scores_affected[]` — `{score, depends_on[], legacy_value: null, reason: "derived_from_corrupted_inputs"}` for legacy heuristic scores whose inputs were corrupted. Those `intelligence.*` score keys are **`null`** (same keys, withheld values) instead of a number that looks trustworthy. Dependencies: `aura_score`←wins, losses, SlpM, TD_Avg; `composite_score`←wins, losses, Str_Acc, Str_Def; `chaos_contribution`←SlpM, Str_Def; `mirage_meter`←wins, losses, Str_Def. A valid stored score is not a heuristic and is never withheld because of raw-input corruption.

For valid data the legacy `stats`/`intelligence` values and types are exactly as before. `data_quality.legacy_corrupted_fields` lists the corrupted raw keys (convenience copy; only present while the extension is available).

### Malformed persisted numbers (profile-only read path)
The shared `GoldenFeatureCalculator.get_latest_fighter_stats` (unchanged) raises on a malformed stored number. On `ValueError`/`TypeError` the endpoint inspects the stored row with `fighter_profile.legacy.inspect_legacy_raw_stats` (SELECT only) and **recovers only if it finds a stored value that `float()` cannot convert** (e.g. non-numeric text) — evidence that explains the failure. Otherwise (valid row, or only NaN/inf which `float()` accepts, or no row) the **original exception is re-raised**: it is a real bug and must not be hidden behind a 200 with `corrupted: false`. When recovering, the same columns are read (SELECT only; same `float(x or 0)` semantics for valid values, weight default 185; a malformed/non-finite value becomes `None` and is reported). Database/connection errors and unrelated programming errors are **not** caught: they remain HTTP 500, never fabricated data. Non-finite output values are converted to `null` by a final boundary sanitiser, so the JSON is always standards-compliant. (SQLite permits text in numeric columns; whether PostgreSQL can hold such values has not been verified.)

**`intelligence.scores_source` is coarse legacy provenance**: one label for the whole object (`"computed"` only when a stored `aura_score` was present and valid and no stored score was corrupted, else `"heuristic"`). It is not per-score proof of where each value came from. Use `legacy_integrity` and `scores.*.provenance` for per-score information.

## Fighter identity resolution (R4 — both routes, before `search_fighter`)

`GET /fighter/{name}` and `GET /fighter/{name}/history` resolve ONE stored fighter name
(`fighter_profile.resolve_fighter_identity`) before the predictor's case-insensitive
first-match `search_fighter()` is consulted. `search_fighter()` itself is unchanged and
still serves prediction. Policy, in order:

1. **Exact precedence.** The request (URL-decoded, trimmed/validated as before) is compared
   to stored names by Python string equality (case and internal spaces count; the SQL
   result is re-checked in Python). Exactly one exact fighter wins, even if other fighters
   share its normalised name ("Case Twin" vs "CASE TWIN"; "Same Name" vs "Same  Name").
2. **Unique normalised fallback.** With no exact match, the case/whitespace-normalised
   candidates are used; exactly one is selected (`review red`, `  Review  Red  `).
3. **Ambiguity → HTTP 409.** More than one normalised candidate and no exact match never
   selects the first one:
   `{"detail": {"code": "AMBIGUOUS_FIGHTER_IDENTITY", "candidates": ["Same  Name", "Same Name"]}}`
   (actual stored names, sorted; no profile/history payload, no attribution is attempted).
4. **Fuzzy compatibility.** Otherwise the existing fuzzy search runs, and its answer is
   re-checked against the database identity candidates: a fuzzy result whose normalised
   name is shared by several fighters is a 409, never a bypass; a result that is not a
   stored fighter is unresolved.
5. **Not found.** Unresolvable → 404 (history keeps its previous "no fight history" 404).
6. **Failures.** A database error while resolving propagates (HTTP 500); it never falls
   back to a first match.

The resolved stored name is used for everything in the response: `name`, the calculator
stats, the profile-only corrupted-data fallback, `data_quality`, `scores`, attribution,
history result classification, coverage, and the stored `style` / `is_active` / legacy
scores (`WHERE name = :name`, row name re-verified in Python — no `LOWER(name)` match, so
one fighter's stored intelligence values are never mixed with another's).



Preserved: `name`, `fights[].{opponent,date,result,method,weight_class}`, `count`. Added: `fights[].method_available`, `result_counts`, `methods_available_fraction`, `history_scope`, `name_match`, `history_note`.
**Scope:** the endpoint returns the latest 20 bouts; `result_counts` and `methods_available_fraction` describe those returned rows only, not necessarily the whole career (`history_scope.window = latest_20_fights`, `may_be_truncated`).
`result` ∈ `W | L | D | NC | UNKNOWN` (legacy: `W | L`). Names and winners are compared after whitespace/case normalisation (display names unchanged). Winner = fighter → `W`; = opponent → `L`; `Draw` → `D`; `No Contest` → `NC`; missing, not attributable, or fighter not on the card → `UNKNOWN`. `method` is `""` (and `method_available: false`) when the DB field is NULL, empty or whitespace-only; a missing method is never inferred to be a decision (until FTR-01B2).

### Participant matching and identity collisions (history and profile coverage share ONE policy)
Candidate fighters are resolved first: every `fighters.name` whose normalised form equals the requested name's. Fights are selected by `LOWER(TRIM(REPLACE(REPLACE(REPLACE(col,'  ',' '),'  ',' '),'  ',' '))) = key` on `r_name` or `b_name` (portable SQLite/PostgreSQL; trims, ignores case, collapses runs of up to 8 spaces), then confirmed in Python with the full whitespace-collapse + casefold comparison. No `LIKE`/substring/fuzzy matching. Stored display names are returned unchanged.

- **Unique identity** (0 or 1 candidate): tolerant matching as above; `name_match.status = "unique"`.
- **Colliding identity** (>1 fighter records share the normalised name, e.g. `"Same Name"` / `"Same  Name"`): a bout is attributed to the requested fighter **only if its stored corner name equals the requested name exactly**. A bout whose matching name exactly equals another candidate is excluded (`excluded_other_identity_bouts`); a bout that matches the key but equals no candidate exactly (e.g. `"SAME NAME"`), or any bout when the requested name is not itself an exact candidate, is **withheld** (`withheld_ambiguous_bouts`) — never assigned because a normalised key matches. Winner/opponent resolution uses exact names in this mode (a variant-spelled winner is `UNKNOWN`).
- `name_match.status`: `unique` · `collision_resolved` (all matching bouts safely attributed or excluded) · `collision_partial` (some attributed, some withheld) · `ambiguous_unattributable` (nothing attributable, something withheld).
- **Coverage is verified only if nothing was withheld** (`coverage_verified`; present in `name_match`, `history_scope` and `data_quality.coverage`). With `ambiguous_unattributable`: history returns HTTP 200 with `count: 0`, `fights: []`, `methods_available_fraction: null` (not a 404 "no history"), and profile coverage reports `ufc_fights_in_dataset: null`, `coverage_verified: false` — a zero count is never presented as verified. A 404 is returned only when there are no matching bouts at all.
- `name_match = {stored_spellings, fighter_rows_matching_name, ambiguous_identity, status, candidates (collisions only), requested_exact_match, withheld_ambiguous_bouts, excluded_other_identity_bouts, coverage_verified}`.

**Limitations:** tabs/newlines/NBSP inside stored names and non-ASCII case folding on SQLite are not matched by the SQL stage; the lookup applies functions to columns, so it scans `fights` (≈8k rows) instead of using the name index — acceptable now, deferred optimisation. No fighter identities or rows are modified.
