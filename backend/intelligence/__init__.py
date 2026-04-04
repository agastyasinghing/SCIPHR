"""
SCIPHR Intelligence Engine — Phase 2

Public interface:
    IntelligenceOrchestrator  — coordinates all 9 modules per /predict call
    IntelligenceResult        — bundled output from orchestrator.compute()
    FighterContext            — input model (pre-loaded by orchestrator)
    All result models         — ChaosResult, PerceptionGapResult, etc.

Usage:
    from intelligence import IntelligenceOrchestrator, IntelligenceResult

    orchestrator = IntelligenceOrchestrator(engine)
    result: IntelligenceResult = orchestrator.compute(
        f1_name="Conor McGregor",
        f2_name="Khabib Nurmagomedov",
        model_probs=(0.32, 0.68),
        fight_id=None,
    )
"""

from .orchestrator import IntelligenceOrchestrator
from .models import (
    Badge,
    ChaosResult,
    FalseConsensusResult,
    FightDNAResult,
    FighterContext,
    IntelligenceResult,
    NarrativeTrapResult,
    NightmareResult,
    PerceptionGapResult,
    ValueBetResult,
    WinPathResult,
)

__all__ = [
    "IntelligenceOrchestrator",
    "IntelligenceResult",
    "FighterContext",
    "Badge",
    "ChaosResult",
    "PerceptionGapResult",
    "NarrativeTrapResult",
    "ValueBetResult",
    "FightDNAResult",
    "FalseConsensusResult",
    "NightmareResult",
    "WinPathResult",
]
