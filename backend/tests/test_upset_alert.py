"""
Tests for intelligence/upset_alert.py (PRD §10.8).

Covers both branches:
    NO_ODDS fallback (value_bet=None or signal=NO_ODDS)
        → MODEL_CONFIDENCE_NEAR_EVEN when 0.45 <= dog_prob < 0.55
    With odds
        → UNDERDOG_EDGE when dog_model_prob >= 0.45
          AND reconstructed american >= +150 AND edge >= 0.08
"""

import pytest

from intelligence.upset_alert import compute, _implied_to_american, _payout_multiplier
from intelligence.models import UpsetResult, ValueBetResult


# ---------------------------------------------------------------------------
# No-odds fallback branch
# ---------------------------------------------------------------------------

def test_no_value_bet_near_coinflip_fires_alert(f1_ctx, f2_ctx):
    """value_bet=None and loser prob in [0.45, 0.55) → MODEL_CONFIDENCE_NEAR_EVEN."""
    result = compute(f1_ctx, f2_ctx, model_probs=(0.52, 0.48), value_bet=None)
    assert isinstance(result, UpsetResult)
    assert result.is_alert is True
    assert result.reason == "MODEL_CONFIDENCE_NEAR_EVEN"
    # Underdog = fighter with lower prob (f2)
    assert result.underdog_name == f2_ctx.name
    assert result.model_probability == pytest.approx(0.48)
    # No-odds branch leaves odds fields blank
    assert result.implied_probability is None
    assert result.american_odds is None
    assert result.edge is None


def test_no_value_bet_clear_favorite_does_not_fire(f1_ctx, f2_ctx):
    """Loser prob < 0.45 → no alert (not near-even)."""
    result = compute(f1_ctx, f2_ctx, model_probs=(0.75, 0.25), value_bet=None)
    assert result.is_alert is False
    assert result.reason is None
    assert result.underdog_name is None


def test_no_value_bet_exactly_055_does_not_fire(f1_ctx, f2_ctx):
    """Upper bound is exclusive: dog_prob == 0.55 → no alert."""
    result = compute(f1_ctx, f2_ctx, model_probs=(0.45, 0.55), value_bet=None)
    # Dog (lower prob) = f1 with 0.45 → in range → fires
    assert result.is_alert is True
    assert result.underdog_name == f1_ctx.name

    # Now push the loser above 0.55 — should not fire
    result2 = compute(f1_ctx, f2_ctx, model_probs=(0.40, 0.60), value_bet=None)
    assert result2.is_alert is False


def test_value_bet_signal_no_odds_uses_fallback(f1_ctx, f2_ctx):
    """ValueBetResult(signal=NO_ODDS) → no-odds branch."""
    vb = ValueBetResult(signal="NO_ODDS", active=False)
    result = compute(f1_ctx, f2_ctx, model_probs=(0.50, 0.50), value_bet=vb)
    assert result.is_alert is True
    assert result.reason == "MODEL_CONFIDENCE_NEAR_EVEN"
    assert result.american_odds is None


# ---------------------------------------------------------------------------
# With-odds branch
# ---------------------------------------------------------------------------

def test_underdog_edge_fires_alert(f1_ctx, f2_ctx):
    """
    Underdog f2: implied 0.40 (→ +150), model 0.50, edge 0.10.
    All three thresholds met → is_alert=True, reason=UNDERDOG_EDGE.
    """
    vb = ValueBetResult(
        signal="EDGE_DETECTED", active=True,
        model_prob_f1=0.50, implied_prob_f1=0.60,
        model_prob_f2=0.50, implied_prob_f2=0.40,
    )
    result = compute(f1_ctx, f2_ctx, model_probs=(0.50, 0.50), value_bet=vb)
    assert result.is_alert is True
    assert result.reason == "UNDERDOG_EDGE"
    assert result.underdog_name == f2_ctx.name
    assert result.model_probability == pytest.approx(0.50)
    assert result.implied_probability == pytest.approx(0.40)
    assert result.edge == pytest.approx(0.10)
    assert result.american_odds == 150
    assert result.payout_multiplier == pytest.approx(2.50)


def test_no_edge_with_odds_does_not_fire(f1_ctx, f2_ctx):
    """Dog odds OK but edge < 0.08 → no alert."""
    # Underdog f2 implied 0.40, model 0.45 → edge 0.05 (< 0.08)
    vb = ValueBetResult(
        signal="NO_EDGE", active=True,
        model_prob_f1=0.55, implied_prob_f1=0.60,
        model_prob_f2=0.45, implied_prob_f2=0.40,
    )
    result = compute(f1_ctx, f2_ctx, model_probs=(0.55, 0.45), value_bet=vb)
    assert result.is_alert is False
    assert result.reason is None
    # Result still populated with dog info
    assert result.underdog_name == f2_ctx.name
    assert result.edge == pytest.approx(0.05)


def test_small_dog_does_not_fire(f1_ctx, f2_ctx):
    """Dog at only +120 (implied ~0.455) fails american_odds >= 150 threshold."""
    vb = ValueBetResult(
        signal="NO_EDGE", active=True,
        model_prob_f1=0.50, implied_prob_f1=0.545,
        model_prob_f2=0.50, implied_prob_f2=0.455,
    )
    result = compute(f1_ctx, f2_ctx, model_probs=(0.50, 0.50), value_bet=vb)
    assert result.is_alert is False
    assert result.american_odds is not None
    assert result.american_odds < 150


def test_model_prob_below_045_does_not_fire(f1_ctx, f2_ctx):
    """Model prob for dog < 0.45 fails the model threshold."""
    vb = ValueBetResult(
        signal="NO_EDGE", active=True,
        model_prob_f1=0.60, implied_prob_f1=0.65,
        model_prob_f2=0.40, implied_prob_f2=0.35,
    )
    result = compute(f1_ctx, f2_ctx, model_probs=(0.60, 0.40), value_bet=vb)
    assert result.is_alert is False


def test_payout_and_american_reconstruction(f1_ctx, f2_ctx):
    """
    implied 0.25 → american +300, payout 4.00.
    """
    vb = ValueBetResult(
        signal="EDGE_DETECTED", active=True,
        model_prob_f1=0.50, implied_prob_f1=0.75,
        model_prob_f2=0.50, implied_prob_f2=0.25,
    )
    result = compute(f1_ctx, f2_ctx, model_probs=(0.50, 0.50), value_bet=vb)
    assert result.american_odds == 300
    assert result.payout_multiplier == pytest.approx(4.00)
    # And this is a strong alert: model 0.50, implied 0.25 → edge 0.25
    assert result.is_alert is True


# ---------------------------------------------------------------------------
# Helper behaviour
# ---------------------------------------------------------------------------

def test_implied_to_american_symmetry():
    # Fair-odds probabilities
    assert _implied_to_american(0.40) == 150
    assert _implied_to_american(0.25) == 300
    # Favourite side
    assert _implied_to_american(0.60) == -150
    # Edge cases
    assert _implied_to_american(0.0) is None
    assert _implied_to_american(1.0) is None
    assert _implied_to_american(None) is None


def test_payout_multiplier_positive_and_negative():
    assert _payout_multiplier(150) == pytest.approx(2.50)
    assert _payout_multiplier(300) == pytest.approx(4.00)
    assert _payout_multiplier(-150) == pytest.approx(1.6667)
    assert _payout_multiplier(None) is None


def test_result_is_valid_pydantic_model(f1_ctx, f2_ctx):
    """UpsetResult round-trips through model_dump / rehydrate."""
    result = compute(f1_ctx, f2_ctx, model_probs=(0.52, 0.48), value_bet=None)
    rehydrated = UpsetResult(**result.model_dump())
    assert rehydrated.is_alert == result.is_alert
    assert rehydrated.reason == result.reason
