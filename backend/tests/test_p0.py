"""
P0 bug fix regression tests.

Covers the three new codepaths introduced in Phase 0:
  1. Same-fighter guard on /predict → HTTP 400
  2. Rate limiter on /generate-ai-poster → HTTP 429 on 4th request
  3. ai_analyst underdog branch → implied_odds present in returned dict
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """
    TestClient with a mocked predictor so tests run without the
    XGBoost model or CSV on disk.
    """
    # Import after fixture setup so the app module is patchable
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    with patch('main.predictor') as mock_predictor:
        mock_predictor.predict_fight.return_value = {
            'fighter1': 'Jon Jones',
            'fighter2': 'Stipe Miocic',
            'winner': 'Jon Jones',
            'confidence': 0.72,
            'prob_fighter1': 0.72,
            'prob_fighter2': 0.28,
            'fighter1_stats': {
                'wins_total': 27, 'losses_total': 1, 'draw': 0,
                'SLpM_total': 4.5, 'sig_str_acc_total': 57,
                'sig_str_def_total': 64, 'td_avg_total': 1.9,
                'td_acc_total': 44, 'td_def_total': 96,
                'sub_avg_total': 0.5, 'age': 36,
                'height': 193.0, 'reach': 215.0, 'weight': 265.0,
                'weight_class': 'Heavyweight',
            },
            'fighter2_stats': {
                'wins_total': 20, 'losses_total': 4, 'draw': 0,
                'SLpM_total': 3.9, 'sig_str_acc_total': 52,
                'sig_str_def_total': 58, 'td_avg_total': 0.4,
                'td_acc_total': 36, 'td_def_total': 79,
                'sub_avg_total': 0.1, 'age': 41,
                'height': 193.0, 'reach': 201.0, 'weight': 265.0,
                'weight_class': 'Heavyweight',
            },
        }
        mock_predictor.search_fighter.side_effect = lambda name: name
        mock_predictor.available_fighters = ['Jon Jones', 'Stipe Miocic']

        from main import app
        yield TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — Same-fighter guard
# ---------------------------------------------------------------------------

class TestSameFighterGuard:
    def test_same_name_returns_400(self, client):
        """Identical fighter names must be rejected before hitting the model."""
        resp = client.post('/predict', json={
            'fighter1': 'Jon Jones',
            'fighter2': 'Jon Jones',
        })
        assert resp.status_code == 400
        assert 'different' in resp.json()['detail'].lower()

    def test_same_name_case_insensitive_returns_400(self, client):
        """Case differences must not bypass the same-fighter check."""
        resp = client.post('/predict', json={
            'fighter1': 'jon jones',
            'fighter2': 'JON JONES',
        })
        assert resp.status_code == 400

    def test_same_name_with_whitespace_returns_400(self, client):
        """Leading/trailing whitespace must not bypass the check."""
        resp = client.post('/predict', json={
            'fighter1': ' Jon Jones ',
            'fighter2': 'Jon Jones',
        })
        assert resp.status_code == 400

    def test_different_fighters_passes_guard(self, client):
        """Different fighters must not be blocked by the guard."""
        resp = client.post('/predict', json={
            'fighter1': 'Jon Jones',
            'fighter2': 'Stipe Miocic',
        })
        # Guard passes — result depends on predictor mock, not a 400
        assert resp.status_code != 400


# ---------------------------------------------------------------------------
# Test 2 — Rate limiter on /generate-ai-poster
# ---------------------------------------------------------------------------

class TestAIPosterRateLimit:
    def test_rate_limit_429_on_fourth_request(self, client):
        """
        /generate-ai-poster is limited to 3/hour per IP.
        The 4th request in the same window must return 429.
        """
        payload = {
            'fighter1_name': 'Jon Jones',
            'fighter2_name': 'Stipe Miocic',
            'prediction': {'winner': 'Jon Jones', 'confidence': 0.72},
        }

        fighter_stats = {
            'fighter_w': 27, 'fighter_l': 1, 'fighter_d': 0,
            'fighter_weight_lbs': 265, 'age': 36,
            'fighter_height_cm': 193, 'fighter_reach_cm': 215,
        }

        with patch('main.generate_ai_poster') as mock_poster, \
             patch('main.predictor') as mock_pred:
            mock_pred.feature_calculator.get_latest_fighter_stats.return_value = fighter_stats
            mock_poster.return_value = {
                'success': True,
                'style_name': 'Cinematic Photorealistic',
                'image_url': 'data:image/png;base64,abc',
                'response': 'ok',
            }
            responses = [client.post('/generate-ai-poster', json=payload) for _ in range(4)]

        # First 3 should succeed (200); 4th must be rate-limited (429)
        assert all(r.status_code == 200 for r in responses[:3]), \
            f"Expected first 3 to be 200, got {[r.status_code for r in responses[:3]]}"
        assert responses[3].status_code == 429, \
            f"Expected 4th request to be 429, got {responses[3].status_code}"


# ---------------------------------------------------------------------------
# Test 3 — ai_analyst underdog branch returns implied_odds
# ---------------------------------------------------------------------------

class TestAnalystImpliedOdds:
    """
    Before the Bug 1 fix, analysis['implied_odds'] = implied_odds ran before
    the analysis dict was defined, causing a NameError on the underdog path
    (confidence < 0.50).
    """

    def _make_data(self, confidence):
        return {
            'fighter1': 'Fighter A',
            'fighter2': 'Fighter B',
            'winner': 'Fighter A',
            'confidence': confidence,
            'prob_fighter1': confidence,
            'prob_fighter2': 1 - confidence,
            'fighter1_stats': {
                'wins_total': 10, 'losses_total': 5,
                'SLpM_total': 3.0, 'sig_str_acc_total': 50,
                'td_acc_total': 40, 'reach': 180.0, 'age': 30,
            },
            'fighter2_stats': {
                'wins_total': 8, 'losses_total': 3,
                'SLpM_total': 3.5, 'sig_str_acc_total': 48,
                'td_acc_total': 35, 'reach': 175.0, 'age': 28,
            },
        }

    def test_underdog_path_no_nameerror(self):
        """confidence < 0.50 must not raise NameError and must include implied_odds."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from ai_analyst import AIFightAnalyst

        analyst = AIFightAnalyst()
        result = analyst._generate_template_analysis(self._make_data(confidence=0.40), {})

        assert 'implied_odds' in result, "implied_odds must be present for underdog path"
        assert result['implied_odds'].startswith('+'), \
            f"Underdog odds should be positive, got: {result['implied_odds']}"

    def test_favorite_path_includes_implied_odds(self):
        """confidence >= 0.50 must also include implied_odds."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from ai_analyst import AIFightAnalyst

        analyst = AIFightAnalyst()
        result = analyst._generate_template_analysis(self._make_data(confidence=0.72), {})

        assert 'implied_odds' in result, "implied_odds must be present for favorite path"
        assert result['implied_odds'].startswith('-'), \
            f"Favorite odds should be negative, got: {result['implied_odds']}"
