import pandas as pd

DEFAULT_STARTING_CAPITAL = 1_000_000
DEFAULT_RISK_PER_TRADE_PCT = 1.0
DEFAULT_MAX_POSITIONS = 6
DEFAULT_MAX_POSITION_PCT = 20.0


def simulate_portfolio(trades_df, starting_capital=DEFAULT_STARTING_CAPITAL,
                       risk_per_trade_pct=DEFAULT_RISK_PER_TRADE_PCT,
                       max_positions=DEFAULT_MAX_POSITIONS,
                       max_position_pct=DEFAULT_MAX_POSITION_PCT,
                       rank_column="Momentum60D"):
    if trades_df is None or trades_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    trades = trades_df.copy()
    trades["EntryDate"] = pd.to_datetime(trades["EntryDate"])
    trades["ExitDate"] = pd.to_datetime(trades["ExitDate"])
    if rank_column not in trades.columns:
        trades[rank_column] = 0.0
    trades[rank_column] = trades[rank_column].fillna(float("-inf"))
    trades = trades.sort_values(["EntryDate", rank_column], ascending=[True, False])

    cash = float(starting_capital)
    open_positions = []
    taken_rows = []
    equity_points = [(trades["EntryDate"].min(), float(starting_capital))]
    skipped_for_capacity = 0
    skipped_for_size = 0

    def release_closed(before_date):
        nonlocal cash
        closed = sorted((p for p in open_positions if p["exit_date"] < before_date),
                        key=lambda position: position["exit_date"])
        remaining = [p for p in open_positions if p["exit_date"] >= before_date]
        invested = sum(p["cost_basis"] for p in open_positions)
        for position in closed:
            invested -= position["cost_basis"]
            cash += position["cost_basis"] + position["rupee_pnl"]
            equity_points.append((position["exit_date"], cash + invested))
        open_positions[:] = remaining

    for _, trade in trades.iterrows():
        release_closed(trade["EntryDate"])

        if len(open_positions) >= max_positions:
            skipped_for_capacity += 1
            continue

        invested = sum(p["cost_basis"] for p in open_positions)
        equity = cash + invested
        risk_per_share = float(trade["RiskPerShare"])
        entry_price = float(trade["EntryPrice"])
        if risk_per_share <= 0 or entry_price <= 0:
            continue

        shares_by_risk = int((equity * risk_per_trade_pct / 100) / risk_per_share)
        shares_by_size = int((equity * max_position_pct / 100) / entry_price)
        shares_by_cash = int(cash / entry_price)
        shares = min(shares_by_risk, shares_by_size, shares_by_cash)
        if shares < 1:
            skipped_for_size += 1
            continue

        cost_basis = shares * entry_price
        rupee_pnl = cost_basis * float(trade["ReturnPct"]) / 100
        cash -= cost_basis
        open_positions.append({
            "exit_date": trade["ExitDate"],
            "cost_basis": cost_basis,
            "rupee_pnl": rupee_pnl,
        })
        taken_rows.append({
            "Strategy": trade.get("Strategy"),
            "Stock": trade.get("Stock"),
            "EntryDate": trade["EntryDate"],
            "ExitDate": trade["ExitDate"],
            "Shares": shares,
            "CostBasis": round(cost_basis, 2),
            "RupeePnL": round(rupee_pnl, 2),
            "ReturnPct": float(trade["ReturnPct"]),
        })

    release_closed(pd.Timestamp.max)

    taken = pd.DataFrame(taken_rows)
    equity_curve = pd.DataFrame(equity_points, columns=["Date", "Equity"]).sort_values("Date")
    equity_curve = equity_curve.groupby("Date", as_index=False).last()

    summary = summarize_portfolio(taken, equity_curve, starting_capital,
                                  len(trades), skipped_for_capacity, skipped_for_size)
    return summary, equity_curve


def summarize_portfolio(taken, equity_curve, starting_capital, signals_total,
                        skipped_for_capacity, skipped_for_size):
    if taken.empty:
        return pd.DataFrame([{"Signals": signals_total, "TradesTaken": 0}])

    final_equity = float(equity_curve["Equity"].iloc[-1])
    running_peak = equity_curve["Equity"].cummax()
    drawdown_pct = ((equity_curve["Equity"] / running_peak - 1) * 100).min()
    wins = taken[taken["RupeePnL"] > 0]
    losses = taken[taken["RupeePnL"] <= 0]
    gross_loss = abs(losses["RupeePnL"].sum())

    return pd.DataFrame([{
        "Signals": signals_total,
        "TradesTaken": len(taken),
        "SkippedMaxPositions": skipped_for_capacity,
        "SkippedTooSmall": skipped_for_size,
        "WinRate%": round(len(wins) / len(taken) * 100, 1),
        "ProfitFactor": round(wins["RupeePnL"].sum() / gross_loss, 2) if gross_loss else float("inf"),
        "StartCapital": round(float(starting_capital), 0),
        "EndCapital": round(final_equity, 0),
        "NetReturn%": round((final_equity / starting_capital - 1) * 100, 2),
        "MaxDrawdown%": round(float(drawdown_pct), 2),
    }])
