"""
FTR-01B1 — profile heuristic scores (pure functions).
"""

import itertools

import pytest

from fighter_profile.availability import build_fields
from fighter_profile import scores as S


def _fields(**kw):
    base = dict(
        wins=18, losses=3, draws=0, age=30.0, height_cm=178.0, reach_cm=182.0,
        weight_lbs=155.0, slpm=4.2, str_acc=0.48, str_def=0.58,
        td_avg=1.2, td_acc=0.40, td_def=0.70, sub_avg=0.3,
    )
    base.update(kw)
    return build_fields(base)


PICO = dict(wins=13, losses=4, draws=0, age=28.0, height_cm=0.0, reach_cm=0.0,
            weight_lbs=145.0, slpm=0.0, str_acc=0.0, str_def=0.0,
            td_avg=0.0, td_acc=0.0, td_def=0.0, sub_avg=0.0)

ALL = ("composite", "aura", "chaos_contribution", "mirage")


class TestComposite:
    def test_known_value_not_saturated(self):
        # 18/21 = 0.857142…  -> 34.2857 + 0.48*30 + 0.58*30 = 66.0857
        assert S.composite(_fields())["value"] == 66.1

    def test_legacy_bug_inputs_do_not_saturate(self):
        # legacy returned 100.0 for 6-5 with 30%/30%
        c = S.composite(_fields(wins=6, losses=5, str_acc=0.30, str_def=0.30))
        assert c["value"] == pytest.approx(6 / 11 * 40 + 18, abs=0.06)
        assert c["value"] < 100

    def test_boundaries(self):
        top = S.composite(_fields(wins=10, losses=0, draws=0, str_acc=1.0, str_def=1.0))
        assert top["value"] == 100.0
        low = S.composite(_fields(wins=0, losses=10, draws=0, str_acc=0.001, str_def=0.001))
        assert 0.0 <= low["value"] <= 0.1

    def test_range_over_grid(self):
        grid = [0.001, 0.25, 0.5, 0.75, 1.0]
        for w, a, d in itertools.product([0, 5, 10], grid, grid):
            c = S.composite(_fields(wins=w, losses=10 - w, draws=0, str_acc=a, str_def=d))
            assert 0.0 <= c["value"] <= 100.0

    def test_monotonic_in_each_input(self):
        vals = [S.composite(_fields(str_acc=a))["value"] for a in (0.2, 0.4, 0.6, 0.8)]
        assert vals == sorted(vals) and len(set(vals)) == 4
        vals = [S.composite(_fields(str_def=d))["value"] for d in (0.2, 0.4, 0.6, 0.8)]
        assert vals == sorted(vals) and len(set(vals)) == 4
        vals = [S.composite(_fields(wins=w, losses=10 - w))["value"] for w in (2, 4, 6, 8)]
        assert vals == sorted(vals) and len(set(vals)) == 4

    def test_not_constant_over_ordinary_fighters(self):
        a = S.composite(_fields(wins=6, losses=5, str_acc=0.3, str_def=0.3))["value"]
        b = S.composite(_fields(wins=20, losses=1, str_acc=0.5, str_def=0.6))["value"]
        assert a != b


class TestDrawsAndRecordDefinition:
    def test_draws_count_in_denominator(self):
        with_draw = S.composite(_fields(wins=10, losses=0, draws=5))["value"]
        no_draw = S.composite(_fields(wins=10, losses=0, draws=0))["value"]
        assert with_draw < no_draw
        # 10/15 * 40 + 0.48*30 + 0.58*30
        assert with_draw == pytest.approx(10 / 15 * 40 + 14.4 + 17.4, abs=0.06)

    def test_definition_documented_in_meta(self):
        meta = S.build_scores(_fields())["meta"]
        assert "wins + losses + draws" in meta["record_definition"]

    def test_zero_record_unavailable(self):
        c = S.composite(_fields(wins=0, losses=0, draws=0))
        assert c["available"] is False and "record_total" in c["inputs_missing"]


class TestPicoGating:
    def setup_method(self):
        self.s = S.build_scores(build_fields(PICO))

    @pytest.mark.parametrize("name", ALL)
    def test_every_score_unavailable_with_null_value(self, name):
        sc = self.s[name]
        assert sc["value"] is None and sc["available"] is False
        assert sc["status"] == "unavailable"
        assert sc["reason"] == "MISSING_OR_UNCONFIRMED_INPUTS"
        assert sc["inputs_missing"]

    def test_chaos_not_fifty_and_mirage_not_triggered(self):
        assert self.s["chaos_contribution"]["value"] is None   # legacy: 50.0
        assert self.s["mirage"]["value"] is None               # legacy: 22.9


class TestMissingDefenceGating:
    def test_zero_str_def_alone_blocks_chaos_mirage_composite(self):
        f = _fields(wins=16, losses=4, str_def=0.0)   # 80% win rate, str_def zero
        assert S.chaos_contribution(f)["value"] is None
        assert S.mirage(f)["value"] is None
        assert S.composite(f)["value"] is None
        assert "str_def" in S.chaos_contribution(f)["inputs_missing"]
        # scores that do not need defence still compute
        assert S.aura(f)["available"] is True

    def test_measured_defence_enables_scores(self):
        f = _fields(wins=16, losses=4, str_def=0.50)
        m = S.mirage(f)
        assert m["available"] is True
        assert m["value"] == pytest.approx((0.8 - 0.65) * 200, abs=0.06)
        assert S.chaos_contribution(f)["value"] == pytest.approx((4.2 / 7 * 0.5 + 0.5 * 0.5) * 100, abs=0.06)

    def test_mirage_zero_when_defence_good(self):
        assert S.mirage(_fields(wins=16, losses=4, str_def=0.70))["value"] == 0.0

    def test_mirage_small_record_guard(self):
        m = S.mirage(_fields(wins=3, losses=0, str_def=0.40))
        assert m["available"] is False and m["reason"] == "INSUFFICIENT_RECORD"

    def test_mirage_out_of_range_input_rejected(self):
        f = _fields(wins=16, losses=4, str_def=0.5)
        f["str_def"]["value"] = 1.7   # tamper: validation is defensive
        assert S.mirage(f)["reason"] == "INPUT_OUT_OF_RANGE"


class TestProvenanceAndHonesty:
    def test_every_score_is_marked_heuristic_provisional_unvalidated(self):
        s = S.build_scores(_fields())
        assert s["meta"]["not_model_output"] is True
        for name in ALL:
            sc = s[name]
            assert sc["provenance"] == "heuristic"
            assert sc["validated"] is False
            assert sc["status"] == "provisional" and sc["available"] is True
            assert sc["inputs_required"] and sc["inputs_missing"] == []
            assert sc["label"] and sc["description"]

    def test_aura_not_advertised_as_public_sentiment(self):
        a = S.aura(_fields())
        assert "public_sentiment" in a["unsupported_claims"]
        assert "NOT a measure of public sentiment" in a["description"]

    def test_mirage_not_advertised_as_opposition_quality(self):
        m = S.mirage(_fields(wins=16, losses=4, str_def=0.5))
        assert {"opposition_quality", "resume_inflation"} <= set(m["unsupported_claims"])
        assert "does NOT measure opposition quality" in m["description"]

    def test_ambiguous_zero_slpm_blocks_aura_and_chaos(self):
        f = _fields(slpm=0.0)
        assert S.aura(f)["available"] is False
        assert S.chaos_contribution(f)["available"] is False

    def test_zero_td_avg_is_a_valid_aura_input(self):
        assert S.aura(_fields(td_avg=0.0))["available"] is True

    def test_scores_in_range_for_extremes(self):
        f = _fields(wins=100, losses=0, slpm=30.0, td_avg=24.0, str_def=0.99)
        for fn in (S.aura, S.chaos_contribution, S.mirage, S.composite):
            v = fn(f)["value"]
            assert 0.0 <= v <= 100.0
