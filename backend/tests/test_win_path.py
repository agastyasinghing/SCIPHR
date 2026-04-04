"""
Tests for intelligence/win_path.py (Kill Chain)

Skipped until Opus implements the heuristic formula.
"""

import pytest

from intelligence.win_path import compute
from intelligence.models import WinPathResult

VALID_METHODS = {"KO", "TKO", "SUB", "DEC", "SPLIT_DEC", "UNKNOWN"}
VALID_PATH_LABELS = {
    "EARLY_KO", "GROUND_AND_POUND", "SUBMISSION",
    "TAKEDOWN_CONTROL", "DECISION_VOLUME", "DECISION_COUNTER", "SPLIT_DECISION",
}


def test_compute_raises_not_implemented_until_opus(f1_ctx, f2_ctx):
    with pytest.raises(NotImplementedError):
        compute(f1_ctx, f2_ctx, (0.55, 0.45))


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_returns_win_path_result(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, (0.55, 0.45))
    assert isinstance(result, WinPathResult)
    assert result.available is True


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_paths_not_empty(f1_ctx, f2_ctx):
    """Both fighters must have at least one win path."""
    result = compute(f1_ctx, f2_ctx, (0.55, 0.45))
    assert len(result.f1_paths) >= 1
    assert len(result.f2_paths) >= 1


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_path_probabilities_sum_to_1(f1_ctx, f2_ctx):
    """Win path probabilities for each fighter should sum to ~1.0."""
    result = compute(f1_ctx, f2_ctx, (0.55, 0.45))
    f1_sum = sum(p["probability"] for p in result.f1_paths)
    f2_sum = sum(p["probability"] for p in result.f2_paths)
    assert f1_sum == pytest.approx(1.0, abs=0.05)
    assert f2_sum == pytest.approx(1.0, abs=0.05)


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_path_labels_are_valid(f1_ctx, f2_ctx):
    """All path labels must be from the known vocabulary."""
    result = compute(f1_ctx, f2_ctx, (0.55, 0.45))
    for path in result.f1_paths + result.f2_paths:
        assert path["path"] in VALID_PATH_LABELS, f"Unknown path: {path['path']}"


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_most_likely_method_is_valid(f1_ctx, f2_ctx):
    """most_likely_method must be one of the known method values."""
    result = compute(f1_ctx, f2_ctx, (0.55, 0.45))
    assert result.most_likely_method in VALID_METHODS


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_striker_dominant_path_is_striking(f1_ctx, f2_ctx):
    """
    f1_ctx is a high-output striker with 5/6 KO wins.
    Their top win path should be EARLY_KO or GROUND_AND_POUND.
    most_likely_method should be KO or TKO.
    """
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    top_path = result.f1_paths[0]["path"] if result.f1_paths else None
    assert top_path in ("EARLY_KO", "GROUND_AND_POUND", "DECISION_VOLUME")
    assert result.f1_primary_threat in ("STRIKING", "CLINCH")


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_grappler_dominant_path_is_submission(f1_ctx, f2_ctx):
    """
    f2_ctx is a grappler with 4/5 submission wins.
    Their top path should be SUBMISSION or GROUND_AND_POUND.
    """
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    top_path = result.f2_paths[0]["path"] if result.f2_paths else None
    assert top_path in ("SUBMISSION", "GROUND_AND_POUND", "TAKEDOWN_CONTROL")
    assert result.f2_primary_threat in ("GRAPPLING", "WRESTLING")


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_decision_specialist_path_is_decision(dec_ctx_f1, dec_ctx_f2):
    """
    dec_ctx_f1: 7/10 decision wins. Primary path should be DECISION_VOLUME
    or DECISION_COUNTER. most_likely_method should be DEC or SPLIT_DEC.
    """
    result = compute(dec_ctx_f1, dec_ctx_f2, (0.55, 0.45))
    top_path = result.f1_paths[0]["path"] if result.f1_paths else None
    assert top_path in ("DECISION_VOLUME", "DECISION_COUNTER", "SPLIT_DECISION")


@pytest.mark.skip(reason="win_path (Kill Chain) formula: implement in Opus session")
def test_zero_fight_fighter_returns_unknown_method(zero_fight_ctx, f1_ctx):
    """A fighter with no history should return most_likely_method='UNKNOWN'."""
    result = compute(zero_fight_ctx, f1_ctx, (0.40, 0.60))
    assert result.most_likely_method == "UNKNOWN"
