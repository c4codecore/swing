import React, { useState, useEffect, useRef } from 'react';
import { Play, TrendingUp, AlertTriangle, ShieldCheck, Activity, Award, BarChart2, Filter, CheckCircle2, XCircle, Clock, ChevronDown } from 'lucide-react';
import { playTone } from '../utils/soundFx';
import { formatINR, formatPercent } from '../utils/formatters';

export default function BacktestLab({ onSelectStock }) {
  const simpleStrategyLabels = {
    trend_pullback: 'Buy a dip in a rising share',
    relative_strength: 'Shares doing better than Nifty',
    capitulation_reversal: 'Possible bounce after a sharp fall',
    volatility_squeeze: 'Breakout after a quiet period',
    multi_factor: 'Several positive checks agree',
  };
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('relative_strength');
  const [period, setPeriod] = useState('1y');
  const [holdingDays, setHoldingDays] = useState(15);
  const [riskPct, setRiskPct] = useState(1.5);
  const [loading, setLoading] = useState(false);
  const [backtestError, setBacktestError] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [results, setResults] = useState(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [tradeFilter, setTradeFilter] = useState('ALL'); // 'ALL' | 'WIN' | 'LOSS'
  const [regimeFilter, setRegimeFilter] = useState('ALL'); // 'ALL' | 'BULLISH' | 'BEARISH'
  const [expandedTradeKey, setExpandedTradeKey] = useState(null);
  const [dailyHistoryByTrade, setDailyHistoryByTrade] = useState({});
  const [dailyHistoryLoading, setDailyHistoryLoading] = useState(null);
  const [dailyHistoryError, setDailyHistoryError] = useState({});

  useEffect(() => {
    if (!loading) return undefined;
    const startedAt = Date.now();
    const timer = window.setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    fetch('/api/strategies')
      .then(res => res.json())
      .then(data => {
        setStrategies(data);
        if (data.length > 0 && !selectedStrategy) setSelectedStrategy(data[0].id);
      })
      .catch(err => console.error("Error loading strategies", err));
  }, []);

  const handleRunBacktest = async () => {
    setLoading(true);
    setElapsedSeconds(0);
    setBacktestError('');
    playTone('scan');
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 120_000);
    try {
      const res = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          strategy: selectedStrategy,
          period,
          max_holding_days: Number(holdingDays),
          risk_per_trade_pct: Number(riskPct)
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'The past-price check could not be completed.');
      setResults(data);
      playTone('success');
    } catch (err) {
      console.error("Backtest failed", err);
      setBacktestError(err.name === 'AbortError'
        ? 'This check took longer than two minutes and was stopped. Try a shorter past-price period or retry later.'
        : err.message || 'The past-price check could not be completed. Check your connection and try again.');
      playTone('alert');
    } finally {
      window.clearTimeout(timeout);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedStrategy && !results && !loading) {
      handleRunBacktest();
    }
  }, [selectedStrategy]);

  // Equity Curve SVG with Interactive Hover Scrub
  const renderEquityCurve = () => {
    if (!results || !results.equity_curve || results.equity_curve.length < 2) return null;
    const curve = results.equity_curve;
    const width = 840;
    const height = 240;
    const pad = { top: 25, right: 40, bottom: 35, left: 55 };

    const minEq = Math.min(...curve.map(c => c.equity)) * 0.97;
    const maxEq = Math.max(...curve.map(c => c.equity)) * 1.03;
    const range = maxEq - minEq || 1;

    const getX = (idx) => pad.left + (idx / (curve.length - 1)) * (width - pad.left - pad.right);
    const getY = (val) => pad.top + (1 - (val - minEq) / range) * (height - pad.top - pad.bottom);

    const points = curve.map((c, i) => `${getX(i).toFixed(1)},${getY(c.equity).toFixed(1)}`).join(' ');
    const areaPoints = `${getX(0).toFixed(1)},${height - pad.bottom} ${points} ${getX(curve.length - 1).toFixed(1)},${height - pad.bottom}`;

    const isPositive = results.total_return_pct >= 0;
    const strokeColor = '#d8d8d8';
    const gradId = 'eqGradGray';

    const activePoint = hoveredPoint !== null ? curve[hoveredPoint] : curve[curve.length - 1];
    const activePointIdx = hoveredPoint !== null ? hoveredPoint : curve.length - 1;
    const activeX = getX(activePointIdx);
    const activeY = getY(activePoint?.equity || 100);

    return (
      <div style={{ position: 'relative' }}>
        <svg 
          viewBox={`0 0 ${width} ${height}`} 
          style={{ width: '100%', height: 'auto', background: 'rgba(5, 8, 16, 0.65)', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.06)' }}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const clientX = e.clientX - rect.left;
            const ratio = (clientX * (width / rect.width) - pad.left) / (width - pad.left - pad.right);
            const idx = Math.round(ratio * (curve.length - 1));
            if (idx >= 0 && idx < curve.length) {
              setHoveredPoint(idx);
            }
          }}
          onMouseLeave={() => setHoveredPoint(null)}
        >
          <defs>
            <linearGradient id="eqGradGray" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#d8d8d8" stopOpacity="0.25"/>
              <stop offset="100%" stopColor="#d8d8d8" stopOpacity="0.0"/>
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={pad.left} y1={getY(100)} x2={width - pad.right} y2={getY(100)} stroke="rgba(255,255,255,0.22)" strokeDasharray="3 3" />
          <text x={pad.left - 45} y={getY(100) + 4} fill="#cbd5e1" fontSize="10.5" fontWeight="600" fontFamily="var(--font-mono)">₹100.0</text>

          {/* Area & Polyline */}
          <polygon points={areaPoints} fill={`url(#${gradId})`} />
          <polyline points={points} fill="none" stroke={strokeColor} strokeWidth="2.5" />

          {/* Interactive Scrub Indicator */}
          {activeX && (
            <g pointerEvents="none">
              <line x1={activeX} y1={pad.top} x2={activeX} y2={height - pad.bottom} stroke="rgba(255,255,255,0.35)" strokeDasharray="3 3" />
              <circle cx={activeX} cy={activeY} r="5" fill="#fff" stroke={strokeColor} strokeWidth="2.5" />
            </g>
          )}

          {/* Start and End labels */}
          <text x={pad.left} y={height - 12} fill="#cbd5e1" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">{curve[0].date}</text>
          <text x={width - pad.right - 65} y={height - 12} fill="#cbd5e1" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">{curve[curve.length - 1].date}</text>
        </svg>

        {/* Hover Floating Tooltip */}
        {activePoint && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.5rem 1rem',
            background: 'rgba(10, 16, 28, 0.85)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '10px',
            marginTop: '0.5rem',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem'
          }}>
            <span style={{ color: 'var(--text-dim)' }}>DATE: <b style={{ color: '#fff' }}>{activePoint.date}</b></span>
            <span style={{ color: 'var(--text-dim)' }}>
              PORTFOLIO: <b>{formatINR(activePoint.equity)}</b> ({activePoint.equity >= 100 ? '▲ GAIN ' : '▼ LOSS '}{formatPercent(Math.abs(activePoint.equity - 100), { signed: activePoint.equity >= 100 })})
            </span>
          </div>
        )}
      </div>
    );
  };

  const filteredTrades = results?.trades?.filter(t => {
    const matchesOutcome = tradeFilter === 'ALL' || (tradeFilter === 'WIN' ? t.is_win : !t.is_win);
    const matchesRegime = regimeFilter === 'ALL' || t.regime === regimeFilter;
    return matchesOutcome && matchesRegime;
  }) || [];

  const toggleTradeDetails = async (trade, tradeKey) => {
    if (expandedTradeKey === tradeKey) {
      setExpandedTradeKey(null);
      return;
    }
    setExpandedTradeKey(tradeKey);
    setDailyHistoryError(current => ({ ...current, [tradeKey]: null }));
    if (trade.daily_performance?.length || dailyHistoryByTrade[tradeKey] || dailyHistoryLoading === tradeKey) return;

    setDailyHistoryLoading(tradeKey);
    try {
      const requestedPeriod = results?.period || period;
      const makeRequest = (requested) => fetch(`/api/chart/${encodeURIComponent(trade.symbol)}?period=${requested}&history=true`);
      let response = await makeRequest(requestedPeriod);
      if (!response.ok && requestedPeriod !== '1y') response = await makeRequest('1y');
      if (!response.ok) throw new Error('Could not fetch historical candles.');
      const chart = await response.json();
      const candles = chart.candles || [];
      const entryIndex = candles.findIndex(candle => candle.time === trade.entry_date);
      const range = candles.filter(candle => candle.time >= trade.entry_date && candle.time <= trade.exit_date);
      if (!range.length) throw new Error('Daily candles for this trade date range were not returned.');

      const daily = range.map((candle, index) => {
        const candleIndex = candles.indexOf(candle);
        const isExitDay = candle.time === trade.exit_date;
        const tradeMarkPrice = isExitDay ? trade.exit_price : candle.close;
        const previousMark = index === 0 ? trade.entry_price : candles[candleIndex - 1]?.close;
        return {
          date: candle.time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          trade_mark_price: tradeMarkPrice,
          daily_change_pct: previousMark ? Number(((tradeMarkPrice / previousMark - 1) * 100).toFixed(2)) : 0,
          from_entry_pct: Number(((tradeMarkPrice / trade.entry_price - 1) * 100).toFixed(2)),
        };
      });
      if (entryIndex < 0) throw new Error('Entry-day candle is outside the available history.');
      setDailyHistoryByTrade(current => ({ ...current, [tradeKey]: daily }));
    } catch (error) {
      setDailyHistoryError(current => ({ ...current, [tradeKey]: error.message || 'Unable to load daily history.' }));
    } finally {
      setDailyHistoryLoading(null);
    }
  };

  const renderTradeFilter = (label, options, value, onChange) => (
    <div className="trade-filter-group" aria-label={`${label} filter`}>
      <span>{label}</span>
      <div className="trade-filter-buttons">
        {options.map(option => <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          className={value === option.value ? 'active' : ''}
          onClick={() => onChange(option.value)}
        >{option.label}</button>)}
      </div>
    </div>
  );

  return (
    <div className="backtest-lab" style={{ animation: 'fadeInUp 0.35s ease' }}>
      {/* Top Configuration Controls */}
      <div className="glass-card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: '#38bdf8', letterSpacing: '0.1em' }}>
              CHECK A STRATEGY USING PAST PRICES
            </div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800 }}>
              How would this strategy have done?
            </h2>
          </div>

          <button 
            onClick={handleRunBacktest}
            disabled={loading}
            className="btn-cyber-primary"
          >
            <Play size={15} fill="#fff" />
            {loading ? `Checking · ${elapsedSeconds}s` : backtestError ? 'Try again' : 'Run past-price check'}
          </button>
        </div>
        {loading && <p className="backtest-progress" role="status">Checking past share prices. Larger periods can take longer; this page will show an error and retry option if it exceeds two minutes.</p>}
        {backtestError && <div className="portfolio-notice status-warning" role="alert"><AlertTriangle size={18} /><span>{backtestError}</span><button type="button" className="text-action" onClick={handleRunBacktest}>Try again</button></div>}

        {/* Input Parameters Controls Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              How to find shares
            </label>
            <select 
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="select-dropdown"
              style={{ width: '100%', background: 'rgba(0,0,0,0.4)' }}
            >
              {strategies.map(s => (
                <option key={s.id} value={s.id}>{simpleStrategyLabels[s.id] || s.title}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              Past price period
            </label>
            <select 
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="select-dropdown"
              style={{ width: '100%', background: 'rgba(0,0,0,0.4)' }}
            >
              <option value="6mo">Last 6 Months</option>
              <option value="1y">Last 1 Year</option>
              <option value="2y">Last 2 Years</option>
              <option value="3y">Last 3 Years</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              Sell after at most ({holdingDays} market days)
            </label>
            <input 
              type="range" 
              min="5" 
              max="45" 
              value={holdingDays}
              onChange={(e) => setHoldingDays(e.target.value)}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>
              Maximum account loss per trade ({Number(riskPct).toFixed(2)}%)
            </label>
            <input 
              type="range" 
              min="0.5" 
              max="5.0" 
              step="0.5"
              value={riskPct}
              onChange={(e) => setRiskPct(e.target.value)}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
          </div>
        </div>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.78rem', lineHeight: 1.5, marginTop: '1rem' }}>This is a check using old prices, not a promise about future results. Fees and real-world delays can change what happens.</p>
      </div>

      {/* Results Overview */}
      {loading ? (
        <div className="glass-card empty-state" style={{ padding: '5rem 1rem' }}>
          <div className="live-dot" style={{ margin: '0 auto 1.5rem', width: 14, height: 14, background: '#38bdf8' }} />
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem', color: 'var(--text)' }}>
            Checking past share prices · {elapsedSeconds}s elapsed. Larger checks may take longer.
          </div>
        </div>
      ) : results ? (
        <>
          {/* Simple result cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
            <div className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Change in test account
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.75rem', fontWeight: 800, color: results.total_return_pct >= 0 ? '#10b981' : '#f43f5e' }}>
                {results.total_return_pct >= 0 ? '▲ GAIN ' : '▼ LOSS '}{formatPercent(results.total_return_pct, { signed: true })}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Starting with ₹100</div>
            </div>

            <div className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Trades that made money
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.75rem', fontWeight: 800, color: results.win_rate_pct >= 50 ? '#10b981' : '#f59e0b' }}>
                {formatPercent(results.win_rate_pct)}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Out of {results.total_trades} finished trades</div>
            </div>

            <div className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Total gains compared with losses
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.75rem', fontWeight: 800, color: results.profit_factor >= 1.5 ? '#10b981' : '#f59e0b' }}>
                {results.profit_factor == null ? (results.total_trades ? '∞' : '—') : results.profit_factor}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Above 1 means gains were larger</div>
            </div>

            <div className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Largest fall from a high
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.75rem', fontWeight: 800, color: '#f43f5e' }}>
                ▼ LOSS {formatPercent(-Math.abs(Number(results.max_drawdown_pct) || 0))}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Biggest drop before recovery</div>
            </div>

            <div className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Average gain / average loss
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.25rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.4rem' }}>
                <span>▲ GAIN {formatPercent(Math.abs(Number(results.avg_win_pct) || 0), { signed: true })}</span> / <span>▼ LOSS {formatPercent(-Math.abs(Number(results.avg_loss_pct) || 0))}</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>For each finished trade</div>
            </div>
          </div>

          {/* Equity Curve Visualizer */}
          <div className="glass-card" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp size={18} color="#10b981" /> Test account value over time
              </h3>
              <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                Move over the chart to see each date
              </span>
            </div>
            {renderEquityCurve()}
          </div>

          {/* Regime Performance Breakdown Table */}
          {results.regime_breakdown && Object.keys(results.regime_breakdown).length > 0 && (
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Activity size={18} color="#a855f7" /> Results in different market moods
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table className="backtest-table" style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-dim)', textAlign: 'left' }}>
                      <th style={{ padding: '0.75rem 1rem' }}>MARKET MOOD</th>
                      <th style={{ padding: '0.75rem 1rem' }}>TRADES</th>
                      <th style={{ padding: '0.75rem 1rem' }}>MADE MONEY</th>
                      <th style={{ padding: '0.75rem 1rem' }}>ACCOUNT CHANGE</th>
                      <th style={{ padding: '0.75rem 1rem' }}>GAINS VS LOSSES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(results.regime_breakdown).map(([regKey, rData]) => (
                      <tr key={regKey} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td className={`regime-badge state-${regKey.toLowerCase().replaceAll('_', '-')}`}>
                          {regKey}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>{rData.trades}</td>
                        <td>
                          {formatPercent(rData.win_rate)} · {rData.win_rate >= 50 ? 'half or more' : 'less than half'}
                        </td>
                        <td className={rData.total_return_pct >= 0 ? 'positive' : 'negative'}>
                          {rData.total_return_pct >= 0 ? '▲ GAIN ' : '▼ LOSS '}{formatPercent(rData.total_return_pct, { signed: true })}
                        </td>
                        <td style={{ padding: '0.75rem 1rem' }}>{rData.profit_factor}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Trade Execution Log */}
          {results.trades && results.trades.length > 0 && (
            <div className="glass-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Award size={18} color="#38bdf8" /> Past trades in this check ({filteredTrades.length})
                </h3>

                <div className="trade-log-filters">
                  {renderTradeFilter('Result', [
                    { value: 'ALL', label: 'All' }, { value: 'WIN', label: 'Wins' }, { value: 'LOSS', label: 'Losses' },
                  ], tradeFilter, setTradeFilter)}
                  {renderTradeFilter('Market mood', [
                    { value: 'ALL', label: 'All' }, { value: 'BULLISH', label: 'Bullish' }, { value: 'BEARISH', label: 'Bearish' },
                  ], regimeFilter, setRegimeFilter)}
                </div>
              </div>

              <p className="trade-regime-note">Use these filters to compare winning and losing trades in rising or falling markets. Select a share to see its price changes by day.</p>

              <div style={{ overflowX: 'auto', maxHeight: '420px', overflowY: 'auto' }}>
                <table className="trade-table" style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#080d18', zIndex: 5 }}>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-dim)', textAlign: 'left' }}>
                      <th style={{ padding: '0.65rem 0.75rem' }}>SYMBOL</th>
                      <th style={{ padding: '0.65rem 0.75rem' }} title="Nifty regime on the strategy signal date">REGIME</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>ENTRY</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>EXIT</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>ENTRY ₹</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>EXIT ₹</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>P&L %</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>DAYS</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>EXIT REASON</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrades.map((t, idx) => {
                      const isWin = t.is_win;
                      const tradeKey = `${t.symbol}:${t.entry_date}`;
                      const isExpanded = expandedTradeKey === tradeKey;
                      return (
                        <React.Fragment key={tradeKey}>
                        <tr className={isExpanded ? 'trade-log-row expanded' : 'trade-log-row'} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                          <td style={{ padding: '0.65rem 0.75rem', fontWeight: 700 }}>
                            <span className="trade-symbol-actions">
                              <button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ symbol: t.symbol, source: 'backtest' })} aria-label={`View ${t.symbol} stock research`}>{t.symbol}</button>
                              <button
                                type="button"
                                className="trade-symbol-toggle"
                                aria-expanded={isExpanded}
                                aria-label={`${isExpanded ? 'Hide' : 'Show'} daily performance for ${t.symbol}, ${t.entry_date}`}
                                onClick={() => toggleTradeDetails(t, tradeKey)}
                              ><ChevronDown size={14} className={isExpanded ? 'rotated' : ''} /></button>
                            </span>
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>
                            <span className={`trade-regime-chip ${t.regime === 'BULLISH' ? 'bullish' : t.regime === 'BEARISH' ? 'bearish' : 'unknown'}`} title="Whether Nifty was generally rising or falling that day">
                              {t.regime === 'BULLISH' ? 'Market rising' : t.regime === 'BEARISH' ? 'Market falling' : 'Unknown'}
                            </span>
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-dim)' }}>{t.entry_date}</td>
                          <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-dim)' }}>{t.exit_date}</td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>{formatINR(t.entry_price)}</td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>{formatINR(t.exit_price)}</td>
                          <td className={isWin ? 'positive' : 'negative'} style={{ padding: '0.65rem 0.75rem', fontWeight: 700 }}>
                            {isWin ? '▲ GAIN ' : '▼ LOSS '}{formatPercent(t.pnl_pct, { signed: true })}
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>{t.holding_days}d</td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>
                            <span className={`trade-exit-reason ${isWin ? 'win' : 'loss'}`}>
                              {({ TARGET_HIT: 'Target price reached', STOP_LOSS: 'Loss limit reached', TIME_EXIT: 'Time limit ended', END_OF_DATA: 'Price history ended' }[t.exit_reason] || t.exit_reason?.replace(/_/g, ' ').toLowerCase())}
                            </span>
                          </td>
                        </tr>
                        {isExpanded && <tr className="trade-detail-row">
                          <td colSpan={9}>
                            <div className="trade-daily-detail">
                              <div className="trade-daily-heading">
                                <div><strong><button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ symbol: t.symbol, source: 'backtest' })} aria-label={`View ${t.symbol} stock research`}>{t.symbol}</button> · Daily performance</strong><span>{t.entry_date} to {t.exit_date} · {t.holding_days} trading session{t.holding_days === 1 ? '' : 's'}</span></div>
                                <span className={`trade-result-chip ${isWin ? 'win' : 'loss'}`}>{isWin ? '▲ GAIN' : '▼ LOSS'} · {formatPercent(t.pnl_pct, { signed: true })} net</span>
                              </div>
                              <p>Trade mark uses the daily close until exit day, then the modeled exit fill. Day change is measured against the previous session close; on the first day it is measured from entry. Final net P&amp;L includes estimated trading costs. Daily OHLC is candle data, so it does not show the exact intraday exit moment.</p>
                              {t.daily_performance?.length || dailyHistoryByTrade[tradeKey]?.length ? <div className="trade-daily-table-wrap">
                                <table className="trade-daily-table">
                                  <thead><tr><th>DATE</th><th>OPEN ₹</th><th>HIGH ₹</th><th>LOW ₹</th><th>CLOSE ₹</th><th>TRADE MARK ₹</th><th>DAY CHANGE</th><th>RETURN FROM ENTRY</th></tr></thead>
                                  <tbody>{(t.daily_performance?.length ? t.daily_performance : dailyHistoryByTrade[tradeKey]).map((day) => <tr key={day.date}>
                                    <td>{day.date}</td><td>{formatINR(day.open)}</td><td>{formatINR(day.high)}</td><td>{formatINR(day.low)}</td><td>{formatINR(day.close)}</td><td>{formatINR(day.trade_mark_price)}</td>
                                    <td className={day.daily_change_pct >= 0 ? 'positive' : 'negative'}>{formatPercent(day.daily_change_pct, { signed: true })}</td>
                                    <td className={day.from_entry_pct >= 0 ? 'positive' : 'negative'}>{formatPercent(day.from_entry_pct, { signed: true })}</td>
                                  </tr>)}</tbody>
                                </table>
                              </div> : dailyHistoryLoading === tradeKey
                                ? <div className="trade-daily-empty">Loading daily price history…</div>
                                : <div className="trade-daily-empty">{dailyHistoryError[tradeKey] || 'Daily price history is unavailable for this date range.'}</div>}
                            </div>
                          </td>
                        </tr>}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
