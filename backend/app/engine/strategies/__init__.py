"""
Strategy Registry
"""
from typing import Dict, List, Type
from app.engine.strategies.base import BaseStrategy
from app.engine.strategies.trend_pullback import TrendPullbackStrategy
from app.engine.strategies.relative_strength import RelativeStrengthBreakoutStrategy
from app.engine.strategies.capitulation_reversal import CapitulationReversalStrategy
from app.engine.strategies.volatility_squeeze import VolatilitySqueezeStrategy

STRATEGY_REGISTRY: Dict[str, BaseStrategy] = {
    "trend_pullback": TrendPullbackStrategy(),
    "relative_strength": RelativeStrengthBreakoutStrategy(),
    "capitulation_reversal": CapitulationReversalStrategy(),
    "volatility_squeeze": VolatilitySqueezeStrategy()
}


def get_all_strategies() -> List[BaseStrategy]:
    return list(STRATEGY_REGISTRY.values())


def get_strategy(name: str) -> BaseStrategy:
    return STRATEGY_REGISTRY.get(name)
