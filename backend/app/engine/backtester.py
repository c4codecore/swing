"""
Comprehensive Walk-Forward Backtest Simulator
Evaluates strategies with regime attribution, equity curve generation, and risk metrics.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from app.core.config import DEFAULT_UNIVERSE
from app.core.data_fetcher import fetch_ohlcv, fetch_benchmark
from app.engine.strategies import STRATEGY_REGISTRY
from app.core.indicators import ema


def run_strategy_backtest(
    strategy_name: str,
    symbols: Optional[List[str]] = None,
    period: str = "2y",
    max_holding_days: int = 15,
    initial_capital: float = 100000.0,
    risk_per_trade_pct: float = 1.5
) -> Dict[str, Any]:
    """
    Backtests a given strategy across universe with realistic trade mechanics:
    - Signal detected at close (t)
    - Entry executed at Open next day (t+1)
    - Stop-loss and Target evaluated bar-by-bar
    - Tagged by market regime at entry
    """
    strategy = STRATEGY_REGISTRY.get(strategy_name)
    if not strategy:
        return {"error": f"Strategy {strategy_name} not found"}

    test_symbols = (symbols or DEFAULT_UNIVERSE)[:25]  # Balanced test set
    bench_df = fetch_benchmark(period=period)
    bench_close = bench_df['Close'] if not bench_df.empty else pd.Series()
    bench_ema50 = ema(bench_close, 50) if not bench_close.empty else pd.Series()

    trades: List[Dict[str, Any]] = []

    for sym in test_symbols:
        try:
            df = fetch_ohlcv(sym, period=period)
            if len(df) < 70:
                continue

            clean_sym = sym.replace(".NS", "")
            n_bars = len(df)
            
            # Walk-forward simulation
            bar_idx = 55
            while bar_idx < n_bars - 2:
                # Historical slice up to current bar
                sub_df = df.iloc[:bar_idx + 1]
                sub_bench = bench_df.iloc[:bar_idx + 1] if not bench_df.empty else None

                # Check signal at EOD
                sig = strategy.evaluate(sub_df, benchmark_df=sub_bench)
                if sig and sig.get("signal") == "BUY":
                    # Determine market regime on signal date
                    sig_date = df.index[bar_idx]
                    regime_tag = "BULLISH"
                    if not bench_close.empty and sig_date in bench_close.index:
                        b_val = bench_close.loc[sig_date]
                        b_50 = bench_ema50.loc[sig_date]
                        regime_tag = "BULLISH" if b_val >= b_50 else "BEARISH"

                    # Execution next day Open
                    entry_bar = bar_idx + 1
                    entry_date = df.index[entry_bar].strftime("%Y-%m-%d")
                    entry_price = float(df['Open'].iloc[entry_bar])

                    sl = float(sig['stop_loss'])
                    tgt1 = float(sig['target_1'])
                    tgt2 = float(sig['target_2'])

                    # Forward trace trade outcome
                    exit_price = entry_price
                    exit_date = entry_date
                    exit_reason = "TIME_EXIT"
                    holding_days = 0

                    for forward_step in range(1, max_holding_days + 1):
                        curr_fwd_idx = entry_bar + forward_step
                        if curr_fwd_idx >= n_bars:
                            break

                        holding_days = forward_step
                        bar_high = float(df['High'].iloc[curr_fwd_idx])
                        bar_low = float(df['Low'].iloc[curr_fwd_idx])
                        bar_close = float(df['Close'].iloc[curr_fwd_idx])
                        bar_date = df.index[curr_fwd_idx].strftime("%Y-%m-%d")

                        # Stop-loss check
                        if bar_low <= sl:
                            exit_price = sl
                            exit_date = bar_date
                            exit_reason = "STOP_LOSS"
                            break

                        # Target check (partial/full at Target 1 / 2)
                        if bar_high >= tgt1:
                            exit_price = tgt1
                            exit_date = bar_date
                            exit_reason = "TARGET_HIT"
                            break

                        # Time stop at end of window
                        if forward_step == max_holding_days:
                            exit_price = bar_close
                            exit_date = bar_date
                            exit_reason = "TIME_EXIT"

                    pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
                    is_win = pnl_pct > 0

                    trades.append({
                        "symbol": clean_sym,
                        "entry_date": entry_date,
                        "exit_date": exit_date,
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(exit_price, 2),
                        "stop_loss": round(sl, 2),
                        "target": round(tgt1, 2),
                        "pnl_pct": pnl_pct,
                        "holding_days": holding_days,
                        "exit_reason": exit_reason,
                        "regime": regime_tag,
                        "is_win": is_win
                    })

                    # Skip bars while in trade to avoid overlapping entries on same stock
                    bar_idx = entry_bar + holding_days
                else:
                    bar_idx += 1

        except Exception:
            continue

    if not trades:
        return {
            "strategy": strategy_name,
            "display_name": strategy.display_name,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "trades": [],
            "equity_curve": [],
            "regime_breakdown": {}
        }

    # Sort trades by exit date
    trades.sort(key=lambda t: t['exit_date'])

    # Performance Metrics
    total_trades = len(trades)
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]

    win_rate = round((len(wins) / total_trades) * 100, 1)

    gross_profit = sum(t['pnl_pct'] for t in wins)
    gross_loss = abs(sum(t['pnl_pct'] for t in losses))
    profit_factor = round(gross_profit / (gross_loss if gross_loss > 0 else 0.001), 2)

    avg_win = round(gross_profit / len(wins), 2) if wins else 0.0
    avg_loss = round(gross_loss / len(losses), 2) if losses else 0.0

    # Equity Curve Simulation
    equity = 100.0  # Base 100
    peak = 100.0
    max_dd = 0.0
    equity_curve: List[Dict[str, Any]] = [{"date": trades[0]["entry_date"], "equity": 100.0}]

    for t in trades:
        # 1% risk adjusted return
        trade_return = t['pnl_pct'] * (risk_per_trade_pct / 4.0)
        equity = equity * (1.0 + (trade_return / 100.0))
        if equity > peak:
            peak = equity
        dd = ((peak - equity) / peak) * 100.0
        if dd > max_dd:
            max_dd = dd

        equity_curve.append({
            "date": t["exit_date"],
            "equity": round(equity, 2),
            "pnl": t['pnl_pct'],
            "symbol": t['symbol']
        })

    # Regime Breakdown
    regimes = ["BULLISH", "BEARISH"]
    regime_breakdown = {}
    for r in regimes:
        r_trades = [t for r_t in trades if (r_t["regime"] == r) for t in [r_t]]
        if r_trades:
            r_wins = [t for t in r_trades if t['is_win']]
            r_gp = sum(t['pnl_pct'] for t in r_wins)
            r_gl = abs(sum(t['pnl_pct'] for t in r_trades if not t['is_win']))
            r_pf = round(r_gp / (r_gl if r_gl > 0 else 0.001), 2)
            regime_breakdown[r] = {
                "trades": len(r_trades),
                "win_rate": round((len(r_wins) / len(r_trades)) * 100, 1),
                "total_return_pct": round(sum(t['pnl_pct'] for t in r_trades), 2),
                "profit_factor": r_pf
            }

    return {
        "strategy": strategy_name,
        "display_name": strategy.display_name,
        "total_trades": total_trades,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "max_drawdown_pct": round(max_dd, 2),
        "total_return_pct": round(equity - 100.0, 2),
        "trades": trades[-50:],  # Return latest 50 for display
        "equity_curve": equity_curve,
        "regime_breakdown": regime_breakdown
    }
