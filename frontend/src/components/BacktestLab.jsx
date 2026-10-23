import React, { useState, useEffect } from 'react';
import { Play, TrendingUp, AlertTriangle, ShieldCheck, Activity, Award } from 'lucide-react';

export default function BacktestLab() {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('trend_pullback');
  const [period, setPeriod] = useState('2y');
  const [holdingDays, setHoldingDays] = useState(15);
  const [riskPct, setRiskPct] = useState(1.5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  useEffect(() => {
    fetch('/api/strategies')
      .then(res => res.json())
      .then(data => {
        setStrategies(data);
        if (data.length > 0) setSelectedStrategy(data[0].id);
      })
      .catch(err => console.error("Error loading strategies", err));
  }, []);

  const handleRunBacktest = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy: selectedStrategy,
          period,
          max_holding_days: Number(holdingDays),
          risk_per_trade_pct: Number(riskPct)
        })
      });
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error("Backtest failed", err);
    } finally {
      setLoading(false);
    }
  };

  // Automatically run first backtest when strategies are loaded
  useEffect(() => {
    if (selectedStrategy && !results && !loading) {
      handleRunBacktest();
    }
  }, [selectedStrategy]);

  // Equity Curve SVG path generator
  const renderEquityCurve = () => {
    if (!results || !results.equity_curve || results.equity_curve.length < 2) return null;
    const curve = results.equity_curve;
    const width = 760;
    const height = 200;
    const pad = { top: 20, right: 30, bottom: 30, left: 50 };

    const minEq = Math.min(...curve.map(c => c.equity)) * 0.98;
    const maxEq = Math.max(...curve.map(c => c.equity)) * 1.02;
    const range = maxEq - minEq || 1;

    const getX = (idx) => pad.left + (idx / (curve.length - 1)) * (width - pad.left - pad.right);
    const getY = (val) => pad.top + (1 - (val - minEq) / range) * (height - pad.top - pad.bottom);

    const points = curve.map((c, i) => `${getX(i)},${getY(c.equity)}`).join(' ');
    const areaPoints = `${getX(0)},${height - pad.bottom} ${points} ${getX(curve.length - 1)},${height - pad.bottom}`;

    const isPositive = results.total_return_pct >= 0;
    const strokeColor = isPositive ? '#10b981' : '#f43f5e';
    const gradId = isPositive ? 'eqGradGreen' : 'eqGradRed';

    return (
      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', background: 'rgba(0,0,0,0.2)', borderRadius: 10 }}>
        <defs>
          <linearGradient id="eqGradGreen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.35"/>
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0"/>
          </linearGradient>
          <linearGradient id="eqGradRed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.35"/>
            <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.0"/>
          </linearGradient>
        </defs>

        {/* Baseline 100 */}
        <line x1={pad.left} y1={getY(100)} x2={width - pad.right} y2={getY(100)} stroke="rgba(255,255,255,0.15)" strokeDasharray="3 3" />
        <text x={pad.left - 40} y={getY(100) + 4} fill="#64748b" fontSize="10" fontFamily="var(--font-mono)">₹100</text>

        {/* Area & Line */}
        <polygon points={areaPoints} fill={`url(#${gradId})`} />
        <polyline points={points} fill="none" stroke={strokeColor} strokeWidth="2.2" />

        {/* Start and End labels */}
        <text x={pad.left} y={height - 8} fill="#64748b" fontSize="10" fontFamily="var(--font-mono)">{curve[0].date}</text>
        <text x={width - pad.right - 60} y={height - 8} fill="#64748b" fontSize="10" fontFamily="var(--font-mono)">{curve[curve.length - 1].date}</text>
      </svg>
    );
  };

  return (
    <div>
      <div className="backtest-layout">
        {/* Left Settings Panel */}
        <div className="glass-card" style={{ height: 'fit-content' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} color="#38bdf8" /> Backtest Parameters
          </h3>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', display: 'block', marginBottom: '0.4rem' }}>
              Select Strategy
            </label>
            <select 
              value={selectedStrategy} 
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="select-dropdown"
              style={{ width: '100%' }}
            >
              {strategies.map(s => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
            {strategies.find(s => s.id === selectedStrategy) && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem', lineHeight: '1.4' }}>
                {strategies.find(s => s.id === selectedStrategy).description}
              </p>
            )}
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', display: 'block', marginBottom: '0.4rem' }}>
              Data Period
            </label>
            <select 
              value={period} 
              onChange={(e) => setPeriod(e.target.value)}
              className="select-dropdown"
              style={{ width: '100%' }}
            >
              <option value="1y">1 Year Walk-Forward</option>
              <option value="2y">2 Years Walk-Forward</option>
            </select>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-dim)', textTransform: 'uppercase' }}>Max Hold Period</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{holdingDays} Days</span>
            </div>
            <input 
              type="range" 
              min="5" 
              max="30" 
              value={holdingDays} 
              onChange={(e) => setHoldingDays(e.target.value)}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-dim)', textTransform: 'uppercase' }}>Risk Per Trade</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{riskPct}%</span>
            </div>
            <input 
              type="range" 
              min="0.5" 
              max="3" 
              step="0.5"
              value={riskPct} 
              onChange={(e) => setRiskPct(e.target.value)}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
          </div>

          <button 
            onClick={handleRunBacktest} 
            disabled={loading}
            className="btn-primary" 
            style={{ width: '100%', justifyContent: 'center' }}
          >
            {loading ? (
              <>Simulating Walk-Forward...</>
            ) : (
              <><Play size={16} /> Run Walk-Forward Simulation</>
            )}
          </button>
        </div>

        {/* Right Results & Visualizations */}
        <div>
          {results && (
            <>
              {/* Primary KPIs */}
              <div className="stats-card-grid">
                <div className="stat-card">
                  <div className="stat-label">Win Rate</div>
                  <div className="stat-value" style={{ color: results.win_rate_pct >= 50 ? '#10b981' : '#f59e0b' }}>
                    {results.win_rate_pct}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                    {results.total_trades} Total Trades Executed
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">Profit Factor</div>
                  <div className="stat-value" style={{ color: results.profit_factor >= 1.5 ? '#10b981' : '#f43f5e' }}>
                    {results.profit_factor}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                    Gross Profit / Gross Loss
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">Total Simulated Return</div>
                  <div className="stat-value" style={{ color: results.total_return_pct >= 0 ? '#10b981' : '#f43f5e' }}>
                    {results.total_return_pct > 0 ? '+' : ''}{results.total_return_pct}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                    Compounded portfolio return
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-label">Max Drawdown</div>
                  <div className="stat-value" style={{ color: results.max_drawdown_pct < 12 ? '#10b981' : '#f43f5e' }}>
                    -{results.max_drawdown_pct}%
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                    Peak-to-trough risk
                  </div>
                </div>
              </div>

              {/* Equity Curve Card */}
              <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <TrendingUp size={16} color="#10b981" /> Portfolio Equity Curve (Base ₹100)
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Avg Win: +{results.avg_win_pct}% | Avg Loss: -{results.avg_loss_pct}%
                  </span>
                </div>
                {renderEquityCurve()}
              </div>

              {/* Regime-Split Breakdown Table */}
              <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ marginBottom: '0.75rem' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Award size={16} color="#38bdf8" /> Market Regime Performance Breakdown
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Proof of performance: Comparing how this strategy performed when Nifty was Bullish vs Bearish.
                  </p>
                </div>

                <div className="regime-table-wrap">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Market Regime</th>
                        <th>Trades Taken</th>
                        <th>Win Rate</th>
                        <th>Total Net Return</th>
                        <th>Profit Factor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.regime_breakdown && Object.keys(results.regime_breakdown).length > 0 ? (
                        Object.entries(results.regime_breakdown).map(([regimeKey, rData]) => (
                          <tr key={regimeKey}>
                            <td>
                              <span style={{ 
                                padding: '0.2rem 0.5rem', 
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                fontWeight: 700,
                                background: regimeKey === 'BULLISH' ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)',
                                color: regimeKey === 'BULLISH' ? '#10b981' : '#f43f5e'
                              }}>
                                {regimeKey}
                              </span>
                            </td>
                            <td>{rData.trades}</td>
                            <td style={{ color: rData.win_rate >= 50 ? '#10b981' : '#f59e0b' }}>{rData.win_rate}%</td>
                            <td style={{ color: rData.total_return_pct >= 0 ? '#10b981' : '#f43f5e' }}>
                              {rData.total_return_pct > 0 ? '+' : ''}{rData.total_return_pct}%
                            </td>
                            <td style={{ color: rData.profit_factor >= 1.5 ? '#10b981' : '#f59e0b' }}>
                              {rData.profit_factor}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="5" style={{ textAlign: 'center', color: '#64748b' }}>No regime data recorded</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recent Executed Trades */}
              <div className="glass-card">
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  Recent Simulated Trades (Last {results.trades.length})
                </h4>
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Stock</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Return</th>
                        <th>Holding</th>
                        <th>Exit Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.trades.map((t, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{t.entry_date}</td>
                          <td style={{ fontWeight: 'bold' }}>{t.symbol}</td>
                          <td>₹{t.entry_price}</td>
                          <td>₹{t.exit_price}</td>
                          <td style={{ color: t.is_win ? '#10b981' : '#f43f5e', fontWeight: 600 }}>
                            {t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct}%
                          </td>
                          <td>{t.holding_days}d</td>
                          <td style={{ fontSize: '0.75rem' }}>
                            <span style={{ 
                              color: t.exit_reason === 'TARGET_HIT' ? '#10b981' : t.exit_reason === 'STOP_LOSS' ? '#f43f5e' : '#f59e0b' 
                            }}>
                              {t.exit_reason}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
