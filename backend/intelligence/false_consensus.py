"""
False Consensus Detector — detects fights the public thinks are
decisive but are actually coinflips.

Display name: Invisible Coinflip
Badge it powers: FALSE_FAVORITE (red) — shared with perception_gap

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the false consensus / invisible coinflip formula.

Concept:
    The public perceives one fighter as a clear favourite (high aura score
    disparity in perception_gap), but the model sees a near-coinflip
    (abs(prob_f1 - prob_f2) < threshold).
    This is the "Invisible Coinflip" — the market is confidently wrong.

Inputs available:
    f1_ctx, f2_ctx   — fighter contexts
    chaos_res        — ChaosResult (may be None if chaos_scorer failed)
    model_probs      — (prob_f1, prob_f2) from XGBoost

Key signal:
    actual_gap = abs(prob_f1 - prob_f2)
    If actual_gap < coinflip_threshold AND chaos_res.score > chaos_threshold:
        is_coinflip = True

Coinflip threshold (Opus to calibrate):
    A fight is an "invisible coinflip" when model sees < X% probability gap.
    Suggested starting point: actual_gap < 0.12 (within 12pp of 50/50).
    Adjust based on dataset distribution of model probability gaps.

Chaos cross-reference:
    chaos_res can deepen the signal — a high-chaos fight that ALSO looks
    like a coinflip is a stronger invisible coinflip signal.
    If chaos_res is None, still compute false_consensus from model_probs alone.

consensus_fighter logic:
    Which fighter does the public think is the clear favourite?
    Proxy: the fighter with the higher historical win rate in similar
    weight classes, or the higher aura_score from perception_gap.
    Since false_consensus doesn't have perception_gap as input,
    use fight record (wins/losses) as the public consensus proxy.

Expected output:
    FalseConsensusResult(
        available=True,
        is_coinflip=True | False,
        consensus_fighter="Fighter Name" | None,
        actual_gap=float in [0.0, 1.0],
        label="INVISIBLE_COINFLIP" | "NONE",
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional

from .models import ChaosResult, FalseConsensusResult, FighterContext


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    chaos: Optional[ChaosResult],
    model_probs: tuple[float, float],
) -> FalseConsensusResult:
    """
    Detect whether this fight is an invisible coinflip.

    Args:
        f1_ctx:      Pre-loaded context for fighter 1.
        f2_ctx:      Pre-loaded context for fighter 2.
        chaos:       ChaosResult from chaos_scorer (may be None).
        model_probs: (prob_f1, prob_f2) from XGBoost prediction.

    Returns:
        FalseConsensusResult.

    TODO(opus): Implement the coinflip detection logic.
    """
    raise NotImplementedError(
        "false_consensus formula: implement in Opus session. "
        "See module docstring for coinflip threshold calibration guide."
    )
