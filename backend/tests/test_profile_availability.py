"""
FTR-01B1 — profile availability rules (pure functions, deterministic fixtures).

Evidence base: docs/FTR-01_SOURCE_RECOVERY.md
"""

import pytest

from fighter_profile.availability import (
    CORE_BLOCK, build_fields, core_block_summary, is_usable,
)


def _row(**kw):
    base = dict(
        wins=18, losses=3, draws=0, age=30.0, height_cm=178.0, reach_cm=182.0,
        weight_lbs=155.0, slpm=4.2, str_acc=0.48, str_def=0.58,
        td_avg=1.2, td_acc=0.40, td_def=0.70, sub_avg=0.3,
    )
    base.update(kw)
    return base


PICO = dict(wins=13, losses=4, draws=0, age=28.0, height_cm=0.0, reach_cm=0.0,
            weight_lbs=145.0, slpm=0.0, str_acc=0.0, str_def=0.0,
            td_avg=0.0, td_acc=0.0, td_def=0.0, sub_avg=0.0)


class TestPicoLikeAllZero:
    def setup_method(self):
        self.f = build_fields(PICO)

    def test_whole_core_block_unavailable_with_null_values(self):
        for k in CORE_BLOCK:
            assert self.f[k]["value"] is None
            assert self.f[k]["status"] == "unavailable"
            assert self.f[k]["basis"] == "source_placeholder_zero"
            assert not is_usable(self.f[k])

    def test_height_and_reach_zero_are_source_nan(self):
        for k in ("height_cm", "reach_cm"):
            assert self.f[k]["value"] is None
            assert self.f[k]["status"] == "unavailable"
            assert self.f[k]["basis"] == "source_nan"

    def test_age_present_but_labelled_age_at_last_bout(self):
        assert self.f["age"]["value"] == 28.0
        assert self.f["age"]["status"] == "measured"
        assert "last recorded bout" in self.f["age"]["note"]
        assert self.f["age"]["unit"] == "years_at_last_recorded_bout"

    def test_record_is_scraped_career_record_not_current(self):
        for k, v in (("wins", 13), ("losses", 4), ("draws", 0)):
            assert self.f[k]["value"] == v
            assert self.f[k]["basis"] == "scraped_career_record"
        assert "scrape date unknown" in self.f["wins"]["note"]

    def test_summary(self):
        s = core_block_summary(PICO)
        assert s["available"] is False and s["basis"] == "source_placeholder_zero"


def test_complete_striking_profile_all_measured():
    f = build_fields(_row())
    for k in CORE_BLOCK:
        assert f[k]["status"] == "measured" and f[k]["basis"] == "measured"
        assert f[k]["value"] == _row()[k]
    assert core_block_summary(_row())["available"] is True


class TestMeasuredZero:
    def test_zero_submission_rate_stays_a_measured_zero(self):
        f = build_fields(_row(sub_avg=0.0))
        assert f["sub_avg"]["value"] == 0.0 and f["sub_avg"]["status"] == "measured_zero"
        assert is_usable(f["sub_avg"])

    def test_isolated_zero_takedown_rate_is_ambiguous_not_measured(self):
        f = build_fields(_row(td_avg=0.0, td_acc=0.0))
        assert f["td_avg"]["value"] == 0.0                      # literal zero preserved
        assert f["td_avg"]["status"] == "ambiguous"
        assert f["td_avg"]["basis"] == "ambiguous_source_zero"
        assert not is_usable(f["td_avg"])

    def test_td_acc_not_declared_undefined_from_td_avg_zero(self):
        f = build_fields(_row(td_avg=0.0, td_acc=0.0))
        assert f["td_acc"]["status"] == "ambiguous"       # NOT "undefined"/null
        assert f["td_acc"]["value"] == 0.0
        assert f["td_acc"]["basis"] == "ambiguous_source_zero"

    def test_td_acc_zero_with_takedowns_is_conservatively_ambiguous(self):
        f = build_fields(_row(td_avg=1.0, td_acc=0.0))
        assert f["td_acc"]["status"] == "ambiguous" and not is_usable(f["td_acc"])
        assert f["td_avg"]["status"] == "measured"

    def test_single_zero_in_populated_block_does_not_unavailable_the_block(self):
        f = build_fields(_row(sub_avg=0.0))
        assert f["slpm"]["status"] == "measured"
        assert f["sub_avg"]["status"] == "measured_zero"


class TestAmbiguousIsolatedZero:
    @pytest.mark.parametrize("k", ["str_def", "td_def", "slpm", "str_acc"])
    def test_isolated_zero_is_ambiguous_not_missing_and_not_evidence(self, k):
        f = build_fields(_row(**{k: 0.0}))
        assert f[k]["status"] == "ambiguous"
        assert f[k]["basis"] == "ambiguous_source_zero"
        assert f[k]["value"] == 0.0           # literal source value, flagged
        assert not is_usable(f[k])            # never feeds a score
        # the rest of the block is untouched
        assert f["sub_avg"]["status"] == "measured"

    def test_defensive_hundred_percent_is_measured(self):
        f = build_fields(_row(td_def=1.0))
        assert f["td_def"]["status"] == "measured"


class TestPhysicalAndOther:
    @pytest.mark.parametrize("k", ["height_cm", "reach_cm", "age"])
    @pytest.mark.parametrize("v", [0, 0.0, None])
    def test_zero_or_null_is_source_nan(self, k, v):
        f = build_fields(_row(**{k: v}))
        assert f[k]["value"] is None
        assert f[k]["status"] == "unavailable"
        assert f[k]["basis"] == "source_nan"

    def test_present_physicals_are_measured(self):
        f = build_fields(_row())
        assert f["height_cm"]["value"] == 178.0 and f["height_cm"]["status"] == "measured"

    def test_weight_185_flagged_possible_default(self):
        f = build_fields(_row(weight_lbs=185.0))
        assert f["weight_lbs"]["status"] == "ambiguous"
        assert f["weight_lbs"]["basis"] == "possible_default"

    def test_career_knockdowns_not_stored(self):
        for row in (_row(), PICO):
            k = build_fields(row)["career_knockdowns"]
            assert k["value"] is None
            assert k["status"] == "not_stored" and k["basis"] == "not_stored"

    def test_all_null_core_block_is_source_nan(self):
        f = build_fields(_row(**{k: None for k in CORE_BLOCK}))
        assert f["slpm"]["status"] == "unavailable" and f["slpm"]["basis"] == "source_nan"

    def test_out_of_range_fraction_unavailable(self):
        f = build_fields(_row(str_acc=1.5))
        assert f["str_acc"]["status"] == "unavailable"
        assert f["str_acc"]["basis"] == "invalid_range"

    def test_every_field_has_status_basis_unit_keys(self):
        for name, fld in build_fields(_row()).items():
            assert {"value", "status", "basis", "unit"} <= set(fld), name
