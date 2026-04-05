"""
False Consensus Detector — detects fights the public thinks are
decisive but are actually coinflips.

Display name: Invisible Coinflip
Badge it powers: FALSE_FAVORITE (red) — shared with perception_gap

Key signal:
    actual_gap = abs(prob_f1 - prob_f2)
    coinflip when: actual_gap < 0.12 AND (chaos HIGH+ OR gap very tight)

consensus_fighter: the fighter with the better public record.
"""

from __future__ import annotations

from typing import Optional

from .models import ChaosResult, FalseConsensusResult, FighterContext


# A fight is an "invisible coinflip" when model sees < 12pp gap
_COINFLIP_THRESHOLD = 0.12
# Even without chaos data, a very tight gap triggers coinflip
_TIGHT_THRESHOLD = 0.08
# Chaos score that strengthens the coinflip signal
_CHAOS_HIGH = 55.0


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    chaos: Optional[ChaosResult],
    model_probs: tuple[float, float],
) -> FalseConsensusResult:
    """Detect whether this fight is an invisible coinflip."""
    prob_f1, prob_f2 = model_probs
    actual_gap = abs(prob_f1 - prob_f2)

    # Is the model probability close enough to be a coinflip?
    is_close = actual_gap < _COINFLIP_THRESHOLD

    # Chaos cross-reference: high-chaos + close model = strong coinflip
    chaos_high = (
        chaos is not None
        and chaos.available
        and chaos.score >= _CHAOS_HIGH
    )

    is_coinflip = is_close and (chaos_high or actual_gap < _TIGHT_THRESHOLD)

    # Consensus fighter: who does the public perceive as favourite?
    f1_total = f1_ctx.wins + f1_ctx.losses + f1_ctx.draws
    f2_total = f2_ctx.wins + f2_ctx.losses + f2_ctx.draws
    f1_rate = f1_ctx.wins / f1_total if f1_total > 0 else 0.0
    f2_rate = f2_ctx.wins / f2_total if f2_total > 0 else 0.0

    consensus: Optional[str] = None
    if abs(f1_rate - f2_rate) > 0.05:
        consensus = f1_ctx.name if f1_rate > f2_rate else f2_ctx.name

    # ── Label and display message ─────────────────────────────────────
    # Using actual model gap (abs(prob_f1 - prob_f2)) as proxy.
    # Phase 3 will wire in implied_prob for true consensus_gap per PRD §10.14
    # (PRD's thresholds apply to market vs model gap, a different measurement).
    if not is_coinflip:
        label = "NONE"
        message = ""
    elif actual_gap < 0.05:
        # Near-perfect 50/50: tightest possible coinflip
        label = "INVISIBLE_COINFLIP"
        message = (
            "The public sees a walkover. The model sees a coinflip. "
            "Someone is very wrong."
        )
    elif actual_gap < 0.09:
        label = "FAKE_MISMATCH"
        message = "This fight is being sold as obvious. The data disagrees significantly."
    elif actual_gap < 0.12:
        label = "PUBLIC_CERTAINTY_TRAP"
        message = (
            "Market confidence exceeds what the model justifies. Proceed with caution."
        )
    else:
        label = "MILD_OVERCONFIDENCE"
        message = "Mild market overconfidence detected — model sees this closer than odds suggest."

    return FalseConsensusResult(
        available=True,
        is_coinflip=is_coinflip,
        consensus_fighter=consensus if is_coinflip else None,
        actual_gap=round(actual_gap, 4),
        label=label,
        display_message=message,
    )
