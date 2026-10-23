"""
Base Strategy Blueprint for Swing Trading
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd


class BaseStrategy(ABC):
    name: str = "BaseStrategy"
    display_name: str = "Base Strategy"
    description: str = "Abstract base trading strategy"
    target_regimes: List[str] = ["STRONG_BULL", "PULLBACK_BULL"]
    default_holding_days: int = 10

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluate OHLCV data for entry signal.
        Returns None if no signal, or dict with trade plan details.
        """
        pass
