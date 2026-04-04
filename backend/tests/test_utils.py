"""
Tests for intelligence/utils.py

Covers all 5 utility functions and all branches:
  [8]  classify_style() → 5 style labels + default (6 branches)
  [9]  finish_rate() with fights, empty list, no matching fights
  [10] win_streak() positive, negative, 0-fight fighter
  [11] kelly_fraction() positive edge, negative edge, zero edge
  [12] american_to_implied() favourite (-), underdog (+), even (0)
  [29] classify_style with all-zero stats → 'STRIKER' default
"""

import pytest

from intelligence.utils import (
    american_to_implied,
    classify_style,
    finish_rate,
    kelly_fraction,
    win_streak,
)


# ---------------------------------------------------------------------------
# classify_style
# ---------------------------------------------------------------------------

class TestClassifyStyle:
    def test_grappler_high_sub_avg(self):
        stats = {"sub_avg": 2.0, "td_avg": 3.5, "slpm": 2.0, "str_acc": 0.40, "str_def": 0.55}
        assert classify_style(stats) == "GRAPPLER"

    def test_wrestler_high_td_low_sub(self):
        stats = {"sub_avg": 0.5, "td_avg": 4.2, "slpm": 2.5, "str_acc": 0.38, "str_def": 0.58}
        assert classify_style(stats) == "WRESTLER"

    def test_striker_high_slpm_low_td(self):
        stats = {"sub_avg": 0.2, "td_avg": 0.8, "slpm": 5.5, "str_acc": 0.48, "str_def": 0.56}
        assert classify_style(stats) == "STRIKER"

    def test_brawler_high_slpm_and_str_acc(self):
        stats = {"sub_avg": 0.3, "td_avg": 1.0, "slpm": 4.5, "str_acc": 0.55, "str_def": 0.50}
        assert classify_style(stats) == "BRAWLER"

    def test_counter_high_str_def_low_slpm(self):
        stats = {"sub_avg": 0.4, "td_avg": 1.2, "slpm": 2.0, "str_acc": 0.45, "str_def": 0.70}
        assert classify_style(stats) == "COUNTER"

    def test_all_zero_defaults_to_striker(self, zero_stats):
        # [29] Critical edge case: stats all zero → default STRIKER
        assert classify_style(zero_stats) == "STRIKER"

    def test_empty_dict_defaults_to_striker(self):
        assert classify_style({}) == "STRIKER"

    def test_none_values_handled(self):
        # None values in stats dict should not raise
        stats = {"sub_avg": None, "td_avg": None, "slpm": None, "str_acc": None, "str_def": None}
        result = classify_style(stats)
        assert result in ("STRIKER", "WRESTLER", "GRAPPLER", "BRAWLER", "COUNTER")


# ---------------------------------------------------------------------------
# finish_rate
# ---------------------------------------------------------------------------

class TestFinishRate:
    def _fight(self, r_name, b_name, winner, method):
        return {"r_name": r_name, "b_name": b_name, "winner": winner, "method": method}

    def test_returns_zero_for_empty_fights(self):
        # [9] Critical: must not divide by zero
        assert finish_rate([], "F1") == 0.0

    def test_all_ko_tko_returns_1(self):
        fights = [
            self._fight("F1", "Opp1", "F1", "KO/TKO"),
            self._fight("F1", "Opp2", "F1", "KO/TKO"),
            self._fight("Opp3", "F1", "Opp3", "KO/TKO"),  # F1 lost by KO — still a finish
        ]
        assert finish_rate(fights, "F1") == pytest.approx(1.0)

    def test_all_decisions_returns_0(self):
        fights = [
            self._fight("F1", "Opp1", "F1", "Decision - Unanimous"),
            self._fight("F1", "Opp2", "F1", "Decision - Split"),
        ]
        assert finish_rate(fights, "F1") == pytest.approx(0.0)

    def test_mixed_returns_proportion(self):
        fights = [
            self._fight("F1", "Opp1", "F1", "KO/TKO"),
            self._fight("F1", "Opp2", "F1", "Submission"),
            self._fight("F1", "Opp3", "F1", "Decision - Unanimous"),
            self._fight("F1", "Opp4", "F1", "Decision - Split"),
        ]
        assert finish_rate(fights, "F1") == pytest.approx(0.5)

    def test_submission_method_counts_as_finish(self):
        fights = [self._fight("F1", "Opp1", "Opp1", "Submission")]
        # Submission loss still counts — fighter was involved in a finish
        assert finish_rate(fights, "F1") == pytest.approx(1.0)

    def test_tko_doctor_stoppage_counts_as_finish(self):
        fights = [self._fight("F1", "Opp1", "Opp1", "TKO - Doctor's Stoppage")]
        assert finish_rate(fights, "F1") == pytest.approx(1.0)

    def test_fighter_name_not_used_in_calculation(self):
        # finish_rate counts method-based finishes regardless of winner
        fights = [self._fight("A", "B", "B", "KO/TKO")]
        # Both fighters have finish_rate = 1.0 for this fight
        assert finish_rate(fights, "A") == pytest.approx(1.0)
        assert finish_rate(fights, "B") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# win_streak
# ---------------------------------------------------------------------------

class TestWinStreak:
    def _fight(self, r_name, b_name, winner):
        return {"r_name": r_name, "b_name": b_name, "winner": winner, "method": "Decision"}

    def test_returns_zero_for_empty_fights(self):
        # [10] Critical edge case
        assert win_streak([], "F1") == 0

    def test_three_consecutive_wins(self):
        fights = [
            self._fight("F1", "Opp1", "F1"),   # most recent
            self._fight("F1", "Opp2", "F1"),
            self._fight("F1", "Opp3", "F1"),
        ]
        assert win_streak(fights, "F1") == 3

    def test_two_consecutive_losses(self):
        fights = [
            self._fight("F1", "Opp1", "Opp1"),   # most recent
            self._fight("F1", "Opp2", "Opp2"),
            self._fight("F1", "Opp3", "F1"),      # older win, not counted
        ]
        assert win_streak(fights, "F1") == -2

    def test_win_streak_broken_by_loss(self):
        fights = [
            self._fight("F1", "Opp1", "F1"),   # win — starts streak
            self._fight("F1", "Opp2", "Opp2"),  # loss — stops here
            self._fight("F1", "Opp3", "F1"),    # older win
        ]
        assert win_streak(fights, "F1") == 1

    def test_loss_streak_broken_by_win(self):
        fights = [
            self._fight("F1", "Opp1", "Opp1"),  # loss — starts streak
            self._fight("F1", "Opp2", "F1"),     # win — stops here
            self._fight("F1", "Opp3", "Opp3"),   # older loss
        ]
        assert win_streak(fights, "F1") == -1

    def test_draw_stops_streak_at_zero(self):
        fights = [
            self._fight("F1", "Opp1", "Draw"),
            self._fight("F1", "Opp2", "F1"),
        ]
        assert win_streak(fights, "F1") == 0

    def test_single_win(self):
        fights = [self._fight("F1", "Opp1", "F1")]
        assert win_streak(fights, "F1") == 1

    def test_single_loss(self):
        fights = [self._fight("F1", "Opp1", "Opp1")]
        assert win_streak(fights, "F1") == -1


# ---------------------------------------------------------------------------
# kelly_fraction
# ---------------------------------------------------------------------------

class TestKellyFraction:
    def test_positive_edge_returns_fraction(self):
        # model sees 60% chance, market prices 50% implied
        frac = kelly_fraction(0.60, 0.50)
        assert frac > 0.0
        assert frac <= 0.5  # half-Kelly cap

    def test_zero_edge_returns_zero(self):
        # model agrees with market exactly
        assert kelly_fraction(0.50, 0.50) == pytest.approx(0.0)

    def test_negative_edge_returns_zero(self):
        # model rates fighter lower than market — negative edge clamped to 0
        frac = kelly_fraction(0.40, 0.60)
        assert frac == pytest.approx(0.0)

    def test_zero_implied_prob_returns_zero(self):
        # guard against division by zero
        assert kelly_fraction(0.60, 0.0) == pytest.approx(0.0)

    def test_implied_prob_one_returns_zero(self):
        # degenerate case: 100% implied probability
        assert kelly_fraction(0.60, 1.0) == pytest.approx(0.0)

    def test_model_prob_zero_returns_zero(self):
        assert kelly_fraction(0.0, 0.50) == pytest.approx(0.0)

    def test_model_prob_one_returns_zero(self):
        # we don't trust extreme model probabilities
        assert kelly_fraction(1.0, 0.50) == pytest.approx(0.0)

    def test_large_edge_capped_at_half_kelly(self):
        # even with 90% model vs 20% implied, cap at 0.5
        frac = kelly_fraction(0.90, 0.20)
        assert frac == pytest.approx(0.5)

    def test_known_calculation(self):
        # model=0.65, implied=0.55: edge = (0.65-0.55)/(1-0.55) = 0.10/0.45 ≈ 0.222
        frac = kelly_fraction(0.65, 0.55)
        assert frac == pytest.approx(0.1 / 0.45, rel=1e-4)


# ---------------------------------------------------------------------------
# american_to_implied
# ---------------------------------------------------------------------------

class TestAmericanToImplied:
    def test_heavy_favourite(self):
        # -185: implied = 185/285 ≈ 0.6491
        prob = american_to_implied(-185)
        assert prob == pytest.approx(185 / 285, rel=1e-4)

    def test_underdog(self):
        # +150: implied = 100/250 = 0.40
        prob = american_to_implied(150)
        assert prob == pytest.approx(0.40, rel=1e-4)

    def test_even_money(self):
        # 0: returns 0.5
        assert american_to_implied(0) == pytest.approx(0.5)

    def test_pick_em_minus_110(self):
        # -110: implied = 110/210 ≈ 0.5238
        prob = american_to_implied(-110)
        assert prob == pytest.approx(110 / 210, rel=1e-4)

    def test_big_underdog(self):
        # +400: implied = 100/500 = 0.20
        assert american_to_implied(400) == pytest.approx(0.20)

    def test_result_in_valid_range(self):
        for odds in [-500, -200, -110, 100, 200, 500]:
            p = american_to_implied(odds)
            assert 0.0 < p < 1.0, f"Probability {p} out of range for odds {odds}"
