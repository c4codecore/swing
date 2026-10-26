"""Walk-forward strategy backtester with explicit fills, sizing, and cost assumptions."""
from typing import Any, Dict, List, Optional
import logging

import pandas as pd

from app.core.config import DEFAULT_UNIVERSE
from app.core.data_fetcher import MarketDataUnavailable, fetch_benchmark, fetch_ohlcv
from app.core.indicators import ema
from app.engine.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)
SUPPORTED_PERIODS = {"6mo", "1y", "2y", "3y"}


def run_strategy_backtest(strategy_name: str, symbols: Optional[List[str]] = None,
                          period: str = "2y", max_holding_days: int = 15,
                          initial_capital: float = 100000.0,
                          risk_per_trade_pct: float = 1.5,
                          max_open_positions: int = 5,
                          commission_bps: float = 2.5,
                          slippage_bps: float = 5.0) -> Dict[str, Any]:
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy.")
    if period not in SUPPORTED_PERIODS:
        raise ValueError("Unsupported backtest period.")
    if max_holding_days < 1 or max_holding_days > 90:
        raise ValueError("max_holding_days must be between 1 and 90.")
    if not 0.1 <= risk_per_trade_pct <= 5:
        raise ValueError("risk_per_trade_pct must be between 0.1 and 5.")
    if initial_capital <= 0 or not 1 <= max_open_positions <= 20:
        raise ValueError("Capital and max_open_positions are outside supported limits.")

    strategy = STRATEGY_REGISTRY[strategy_name]
    test_symbols = list(dict.fromkeys(symbols or DEFAULT_UNIVERSE))[:50]
    bench_df = fetch_benchmark(period=period)
    bench_close = bench_df["Close"]
    bench_ema50 = ema(bench_close, 50)
    candidates: List[Dict[str, Any]] = []
    failures = []

    for symbol in test_symbols:
        try:
            df = fetch_ohlcv(symbol, period=period)
            if len(df) < 70:
                failures.append(symbol)
                continue
            idx = 55
            while idx < len(df) - 1:
                signal = strategy.evaluate(df.iloc[:idx + 1], benchmark_df=bench_df.loc[:df.index[idx]])
                if not signal or signal.get("signal") != "BUY":
                    idx += 1
                    continue

                entry_bar = idx + 1
                raw_entry = float(df["Open"].iloc[entry_bar])
                stop = float(signal["stop_loss"])
                target = float(signal["target_1"])
                # Skip stale/gapped signals and invalid risk geometry.
                if not stop < raw_entry < target:
                    idx += 1
                    continue
                last_bar = min(len(df) - 1, entry_bar + max_holding_days - 1)
                exit_price, reason, exit_bar = float(df["Close"].iloc[last_bar]), "DATA_END", last_bar
                for forward in range(entry_bar, last_bar + 1):
                    high, low = float(df["High"].iloc[forward]), float(df["Low"].iloc[forward])
                    open_price = float(df["Open"].iloc[forward])
                    # If both levels are touched in one candle, assume stop first (conservative).
                    if low <= stop:
                        exit_price = min(open_price, stop) if open_price < stop else stop
                        reason, exit_bar = "STOP_LOSS", forward
                        break
                    if high >= target:
                        exit_price = max(open_price, target) if open_price > target else target
                        reason, exit_bar = "TARGET_HIT", forward
                        break
                    if forward == last_bar:
                        reason = "TIME_EXIT" if last_bar == entry_bar + max_holding_days - 1 else "DATA_END"

                signal_date = df.index[idx]
                regime = "BULLISH"
                if signal_date in bench_close.index and pd.notna(bench_ema50.loc[signal_date]):
                    regime = "BULLISH" if bench_close.loc[signal_date] >= bench_ema50.loc[signal_date] else "BEARISH"
                candidates.append({
                    "symbol": symbol.replace(".NS", ""),
                    "entry_date": df.index[entry_bar].strftime("%Y-%m-%d"),
                    "exit_date": df.index[exit_bar].strftime("%Y-%m-%d"),
                    "entry_price": raw_entry, "exit_price": exit_price,
                    "stop_loss": stop, "target": target,
                    "holding_days": max(1, exit_bar - entry_bar + 1),
                    "exit_reason": reason, "regime": regime,
                })
                idx = exit_bar + 1
        except Exception:
            logger.warning("Backtest data/strategy failure for %s", symbol, exc_info=True)
            failures.append(symbol)

    if not test_symbols or len(set(failures)) == len(test_symbols):
        raise MarketDataUnavailable("Market data is unavailable for every requested backtest symbol.")

    # Portfolio simulation: reserve capital while positions overlap; size by stop risk and slot capital.
    candidates.sort(key=lambda trade: (trade["entry_date"], trade["symbol"]))
    cash = initial_capital
    open_positions: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []
    skipped_capacity = 0
    fee_rate, slip_rate = commission_bps / 10000, slippage_bps / 10000

    def settle_until(date: str):
        nonlocal cash, open_positions
        remaining = []
        for position in open_positions:
            # A close on the entry date is not available to fund another open at that session's open.
            if position["exit_date"] < date:
                cash += position["capital"] + position["net_pnl"]
            else:
                remaining.append(position)
        open_positions = remaining

    for candidate in candidates:
        settle_until(candidate["entry_date"])
        if len(open_positions) >= max_open_positions:
            skipped_capacity += 1
            continue
        fill_entry = candidate["entry_price"] * (1 + slip_rate)
        fill_exit = candidate["exit_price"] * (1 - slip_rate)
        stop_distance = fill_entry - candidate["stop_loss"]
        if stop_distance <= 0 or cash <= 0:
            continue
        risk_budget = cash * risk_per_trade_pct / 100
        slot_capital = cash / max_open_positions
        shares = min(math.floor(risk_budget / stop_distance), math.floor(slot_capital / fill_entry))
        if shares <= 0:
            continue
        capital = shares * fill_entry
        entry_fee = capital * fee_rate
        exit_value = shares * fill_exit
        exit_fee = exit_value * fee_rate
        net_pnl = exit_value - capital - entry_fee - exit_fee
        cash -= capital
        pnl_pct = net_pnl / capital * 100
        record = {
            **candidate,
            "entry_price": round(fill_entry, 2), "exit_price": round(fill_exit, 2),
            "shares": shares, "capital_used": round(capital, 2),
            "pnl": round(net_pnl, 2), "pnl_pct": round(pnl_pct, 2),
            "costs": round(entry_fee + exit_fee, 2), "is_win": net_pnl > 0,
        }
        trades.append(record)
        open_positions.append({"exit_date": candidate["exit_date"], "capital": capital, "net_pnl": net_pnl})

    settle_until("9999-12-31")
    trades.sort(key=lambda trade: (trade["exit_date"], trade["symbol"]))
    wins = [trade for trade in trades if trade["is_win"]]
    losses = [trade for trade in trades if not trade["is_win"]]
    total_trades = len(trades)
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    equity = 100.0
    peak = equity
    max_drawdown = 0.0
    equity_curve = []
    for trade in trades:
        equity += trade["pnl"] / initial_capital * 100
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
        equity_curve.append({"date": trade["exit_date"], "equity": round(equity, 2), "pnl": trade["pnl_pct"], "symbol": trade["symbol"]})

    regimes = {}
    for regime in ("BULLISH", "BEARISH"):
        subset = [trade for trade in trades if trade["regime"] == regime]
        if subset:
            gp = sum(trade["pnl"] for trade in subset if trade["is_win"])
            gl = abs(sum(trade["pnl"] for trade in subset if not trade["is_win"]))
            regimes[regime] = {"trades": len(subset), "win_rate": round(sum(t["is_win"] for t in subset) / len(subset) * 100, 1),
                               "total_return_pct": round(sum(t["pnl"] for t in subset) / initial_capital * 100, 2),
                               "profit_factor": round(gp / gl, 2) if gl else (None if gp else 0.0)}

    return {
        "strategy": strategy_name, "display_name": strategy.display_name,
        "total_trades": total_trades, "win_rate_pct": round(len(wins) / total_trades * 100, 1) if total_trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else (None if gross_profit else 0.0),
        "avg_win_pct": round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_pct": round(abs(sum(t["pnl_pct"] for t in losses) / len(losses)), 2) if losses else 0.0,
        "max_drawdown_pct": round(max_drawdown, 2),
        "total_return_pct": round((cash / initial_capital - 1) * 100, 2),
        "trades": [{key: value for key, value in trade.items()} for trade in trades[-50:]],
        "equity_curve": equity_curve, "regime_breakdown": regimes,
        "data_status": "partial" if failures else "complete",
        "scan_summary": {"requested": len(test_symbols), "failed": len(set(failures)), "skipped_capacity": skipped_capacity},
        "assumptions": {"initial_capital": initial_capital, "risk_per_trade_pct": risk_per_trade_pct,
                        "max_open_positions": max_open_positions, "commission_bps_per_side": commission_bps,
                        "slippage_bps_per_side": slippage_bps, "fill_model": "next-session open; conservative stop-first on same-bar conflicts"},
    }
