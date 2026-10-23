import React, { useState, useEffect } from 'react';
import { 
  Search, RefreshCw, BarChart2, ShieldCheck, Activity, 
  ExternalLink, ArrowUpRight, ArrowDownRight, Filter, 
  Layers, Compass, X, SlidersHorizontal, Terminal, Zap, Globe 
} from 'lucide-react';

import ThreeCanvas from './components/ThreeCanvas';
import { CustomCursor, TiltCard } from './components/CyberHUD';
import StockChart from './components/StockChart';
import RegimeView from './components/RegimeView';
import BacktestLab from './components/BacktestLab';

export default function App() {
  const [activeTab, setActiveTab] = useState('screener'); // 'screener' | 'regime' | 'backtest'
  const [regimeData, setRegimeData] = useState(null);
  const [screenerData, setScreenerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [optimalOnly, setOptimalOnly] = useState(false);
  const [selectedChartTrade, setSelectedChartTrade] = useState(null);

  // Load Market Regime
  const loadRegime = async () => {
    try {
      const res = await fetch('/api/regime');
      const data = await res.json();
      setRegimeData(data);
    } catch (err) {
      console.error("Failed to load regime", err);
    }
  };

  // Run Screener
  const runScreener = async (forceRefresh = false) => {
    setLoading(true);
    try {
      const url = forceRefresh ? '/api/screener/run?force_refresh=true' : '/api/screener/run';
      const res = await fetch(url);
      const data = await res.json();
      setScreenerData(data);
      if (data.regime) {
        setRegimeData(data.regime);
      }
    } catch (err) {
      console.error("Failed to run screener", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRegime();
    runScreener(false);
  }, []);

  const allSignals = screenerData?.signals || [];
  const filteredSignals = allSignals.filter(sig => {
    const matchesSearch = sig.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStrategy = strategyFilter === 'ALL' || sig.strategy === strategyFilter;
    const matchesOptimal = !optimalOnly || sig.regime_status === 'OPTIMAL';
    return matchesSearch && matchesStrategy && matchesOptimal;
  });

  const optimalCount = allSignals.filter(s => s.regime_status === 'OPTIMAL').length;

  return (
    <>
      {/* 3D Three.js Fluid Background */}
      <ThreeCanvas regime={regimeData?.regime} isScanning={loading} />

      {/* Cybernetic Custom Cursor */}
      <CustomCursor />

      {/* Laser Scanning Beam when scan is in progress */}
      {loading && <div className="scan-beam" />}

      {/* Top Ticker Tape Marquee */}
      <div className="ticker-tape-wrap">
        <div className="ticker-tape-content">
          &nbsp;&nbsp;◈&nbsp;&nbsp;NSE: NIFTY 50 ₹{regimeData?.metrics?.nifty_close || '22,687.65'} ({regimeData?.metrics?.dist_20ema_pct || '-0.8'}%)
          &nbsp;&nbsp;◈&nbsp;&nbsp;REGIME: {regimeData?.regime || 'BEARISH_CORRECTION'}
          &nbsp;&nbsp;◈&nbsp;&nbsp;BREADTH: {regimeData?.metrics?.breadth_above_50ema_pct || '35.7'}% STOCKS &gt; 50 EMA
          &nbsp;&nbsp;◈&nbsp;&nbsp;DEFENSIVE CASH TARGET: {100 - (regimeData?.max_capital_exposure_pct || 25)}%
          &nbsp;&nbsp;◈&nbsp;&nbsp;NODE 01: MUMBAI EXCHANGE HIGH-SPEED TELEMETRY
          &nbsp;&nbsp;◈&nbsp;&nbsp;ALGORITHMIC PIPELINE: ACTIVE [4 STRATEGIES REGISTERED]
          &nbsp;&nbsp;◈&nbsp;&nbsp;NSE: NIFTY 50 ₹{regimeData?.metrics?.nifty_close || '22,687.65'}
        </div>
      </div>

      <div className="app-container">
        {/* Navbar */}
        <nav className="navbar">
          <div className="brand-section">
            <div className="brand-logo-container">
              <Zap color="#38bdf8" size={24} />
            </div>
            <div>
              <div className="brand-title">QUANTUM // AETHER</div>
              <div className="brand-sub">NSE QUANTITATIVE STUDIO v2.0</div>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <div className="nav-tabs">
            <button 
              className={`nav-tab-btn ${activeTab === 'screener' ? 'active' : ''}`}
              onClick={() => setActiveTab('screener')}
            >
              <Layers size={16} /> Cockpit ({filteredSignals.length})
            </button>
            <button 
              className={`nav-tab-btn ${activeTab === 'regime' ? 'active' : ''}`}
              onClick={() => setActiveTab('regime')}
            >
              <Compass size={16} /> Regime Matrix
            </button>
            <button 
              className={`nav-tab-btn ${activeTab === 'backtest' ? 'active' : ''}`}
              onClick={() => setActiveTab('backtest')}
            >
              <BarChart2 size={16} /> Backtest Lab
            </button>
          </div>

          {/* Right Action & Regime Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* Volatility Equalizer */}
            <div className="equalizer-wrap" title="Live Telemetry Stream">
              <div className="eq-bar"></div>
              <div className="eq-bar"></div>
              <div className="eq-bar"></div>
              <div className="eq-bar"></div>
            </div>

            {regimeData && (
              <div 
                className="btn-cyber-ghost clickable" 
                onClick={() => setActiveTab('regime')}
                style={{
                  border: `1px solid ${regimeData.color}60`,
                  background: `${regimeData.color}15`,
                  color: regimeData.color
                }}
              >
                <span className="live-dot" style={{ background: regimeData.color, width: 7, height: 7 }}></span>
                <span>{regimeData.title}</span>
              </div>
            )}

            <button 
              onClick={() => runScreener(true)} 
              disabled={loading}
              className="btn-cyber-primary"
            >
              <RefreshCw size={15} className={loading ? 'live-dot' : ''} />
              {loading ? 'Laser Scan...' : 'Scan NSE'}
            </button>
          </div>
        </nav>

        {/* TAB 1: COCKPIT / SCREENER */}
        {activeTab === 'screener' && (
          <main>
            {/* Lusion / Dogstudio Style Editorial Hero */}
            <div className="hero-editorial">
              <div>
                <div className="hero-meta-badge">
                  <Terminal size={14} color="#38bdf8" />
                  <span>[01 // HIGH-CONVICTION OPPORTUNITIES]</span>
                  <span>•</span>
                  <span>NIFTY 100 UNIVERSE</span>
                </div>
                <h1 className="hero-main-title">
                  TACTICAL<br />CONVERGENCE
                </h1>
              </div>

              {/* Status HUD Block */}
              <div style={{ 
                background: 'rgba(10, 15, 26, 0.75)', 
                border: '1px solid rgba(255,255,255,0.1)', 
                borderRadius: '16px', 
                padding: '1.25rem 1.75rem',
                backdropFilter: 'blur(20px)',
                minWidth: '280px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                  <span>REGIME STATUS</span>
                  <span style={{ color: regimeData?.color || '#38bdf8', fontWeight: 'bold' }}>{regimeData?.regime || 'LIVE'}</span>
                </div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 800, color: '#fff' }}>
                  {filteredSignals.length} <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 400 }}>SIGNALS</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.25rem', fontFamily: 'var(--font-mono)' }}>
                  ◈ {optimalCount} Optimal to current market cycle
                </div>
              </div>
            </div>

            {/* Controls Bar */}
            <div className="controls-bar" style={{ 
              background: 'rgba(8, 12, 20, 0.75)', 
              backdropFilter: 'blur(16px)', 
              border: '1px solid var(--border-glass)',
              borderRadius: '16px',
              padding: '1rem 1.5rem',
              marginBottom: '2rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                <div className="search-input-wrap" style={{ width: '280px', background: 'rgba(0,0,0,0.5)', borderColor: 'rgba(255,255,255,0.1)' }}>
                  <Search size={16} color="#64748b" />
                  <input 
                    type="text" 
                    placeholder="Filter ticker (e.g. RELIANCE, TRENT)..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="search-input"
                  />
                </div>

                <div className="filter-group">
                  <SlidersHorizontal size={15} color="#94a3b8" />
                  <select 
                    value={strategyFilter} 
                    onChange={(e) => setStrategyFilter(e.target.value)}
                    className="select-dropdown"
                    style={{ background: 'rgba(0,0,0,0.5)' }}
                  >
                    <option value="ALL">All Strategies</option>
                    <option value="trend_pullback">Trend EMA Pullback</option>
                    <option value="relative_strength">Relative Strength Leader</option>
                    <option value="capitulation_reversal">Capitulation Oversold Bounce</option>
                    <option value="volatility_squeeze">Volatility Squeeze Expansion</option>
                  </select>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                  <input 
                    type="checkbox" 
                    checked={optimalOnly} 
                    onChange={(e) => setOptimalOnly(e.target.checked)}
                    style={{ accentColor: '#10b981' }}
                  />
                  <span style={{ color: optimalOnly ? '#10b981' : 'var(--text-muted)', fontWeight: 500 }}>
                    Optimal Regime Only
                  </span>
                </label>
              </div>

              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                TELEMETRY: {screenerData?.timestamp || 'SYNCED'}
              </div>
            </div>

            {/* Signal Cards Grid with 3D Tilt Effect */}
            {loading ? (
              <div className="empty-state" style={{ padding: '5rem 1rem' }}>
                <div className="live-dot" style={{ margin: '0 auto 1.5rem', width: 16, height: 16, background: '#38bdf8' }}></div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', letterSpacing: '0.05em', color: '#fff' }}>
                  SCANNING TELEMETRY & MULTI-TIMEFRAME INDICATORS...
                </div>
              </div>
            ) : filteredSignals.length === 0 ? (
              <div className="glass-card empty-state" style={{ padding: '4rem 1rem' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>◈</div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', marginBottom: '0.5rem' }}>
                  No Setup Confluences Found
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Adjust active filters or initiate a fresh scan of the NSE universe.
                </p>
              </div>
            ) : (
              <div className="signals-grid">
                {filteredSignals.map((sig, idx) => {
                  const isOptimal = sig.regime_status === 'OPTIMAL';
                  const isPos = sig.change_pct >= 0;

                  return (
                    <TiltCard key={idx} className="signal-card">
                      <div>
                        {/* Top Header */}
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 800, color: '#fff' }}>
                                {sig.symbol}
                              </span>
                              <span className={`change-pill ${isPos ? 'pos' : 'neg'}`}>
                                {isPos ? '+' : ''}{sig.change_pct}%
                              </span>
                            </div>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                              LTP: ₹{sig.current_price?.toFixed(2)}
                            </div>
                          </div>

                          <span style={{ 
                            fontSize: '0.65rem',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 800,
                            letterSpacing: '0.08em',
                            padding: '0.25rem 0.65rem',
                            borderRadius: '9999px',
                            textTransform: 'uppercase',
                            background: isOptimal ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                            color: isOptimal ? '#10b981' : '#f59e0b',
                            border: `1px solid ${isOptimal ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`
                          }}>
                            {sig.regime_status}
                          </span>
                        </div>

                        {/* Strategy Badge */}
                        <div style={{
                          display: 'inline-block',
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-body)',
                          fontWeight: 600,
                          padding: '0.25rem 0.65rem',
                          borderRadius: '6px',
                          background: 'rgba(56, 189, 248, 0.1)',
                          color: '#38bdf8',
                          border: '1px solid rgba(56, 189, 248, 0.25)',
                          marginBottom: '0.75rem'
                        }}>
                          {sig.strategy_title}
                        </div>

                        {/* Trade Parameters Cockpit */}
                        <div className="trade-plan-cockpit">
                          <div>
                            <div className="cockpit-title">Target Entry</div>
                            <div className="cockpit-val" style={{ color: '#fff' }}>₹{sig.entry_price}</div>
                          </div>
                          <div>
                            <div className="cockpit-title">Stop Loss (-{sig.risk_pct}%)</div>
                            <div className="cockpit-val" style={{ color: '#f43f5e' }}>₹{sig.stop_loss}</div>
                          </div>
                          <div>
                            <div className="cockpit-title">Target (2R)</div>
                            <div className="cockpit-val" style={{ color: '#10b981' }}>₹{sig.target_2}</div>
                          </div>
                        </div>

                        {/* Setup Reasons Checklist */}
                        <ul className="setup-reasons-list">
                          {sig.reasons?.slice(0, 3).map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      </div>

                      {/* Card Bottom Bar */}
                      <div className="card-footer" style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                        <div className="confidence-meter">
                          <span>CONVICTION:</span>
                          <span className="confidence-val">{sig.confidence_score}%</span>
                          <span style={{ color: '#475569' }}>| R:R 1:{sig.risk_reward}</span>
                        </div>

                        <button 
                          onClick={() => setSelectedChartTrade(sig)}
                          className="btn-cyber-ghost"
                          style={{ padding: '0.4rem 0.85rem' }}
                        >
                          <BarChart2 size={13} color="#38bdf8" /> Hologram Chart
                        </button>
                      </div>
                    </TiltCard>
                  );
                })}
              </div>
            )}
          </main>
        )}

        {/* TAB 2: MARKET REGIME VIEW */}
        {activeTab === 'regime' && (
          <RegimeView 
            regimeData={regimeData} 
            onSelectStrategy={(strat) => {
              setStrategyFilter(strat);
              setActiveTab('screener');
            }}
          />
        )}

        {/* TAB 3: BACKTEST LAB VIEW */}
        {activeTab === 'backtest' && (
          <BacktestLab />
        )}

        {/* CHART MODAL */}
        {selectedChartTrade && (
          <div className="modal-overlay" onClick={() => setSelectedChartTrade(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: '#38bdf8', letterSpacing: '0.1em' }}>
                    [TELEMETRY BLUEPRINT // {selectedChartTrade.strategy_title}]
                  </div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800 }}>
                    {selectedChartTrade.symbol} — Execution Plan
                  </h3>
                </div>
                <button className="close-btn" onClick={() => setSelectedChartTrade(null)}>
                  <X size={22} />
                </button>
              </div>

              {/* Interactive Candlestick Chart */}
              <StockChart 
                symbol={selectedChartTrade.symbol} 
                tradePlan={selectedChartTrade} 
              />

              {/* Bottom Trade Details Breakdown */}
              <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.75rem' }}>
                <div className="metric-item">
                  <div className="metric-label">Execution Entry</div>
                  <div className="metric-val" style={{ color: '#38bdf8' }}>₹{selectedChartTrade.entry_price}</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">Stop-Loss (Hard)</div>
                  <div className="metric-val" style={{ color: '#f43f5e' }}>₹{selectedChartTrade.stop_loss}</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">Target 1 (1.5R)</div>
                  <div className="metric-val" style={{ color: '#10b981' }}>₹{selectedChartTrade.target_1}</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">Target 2 (2.5R)</div>
                  <div className="metric-val" style={{ color: '#10b981' }}>₹{selectedChartTrade.target_2}</div>
                </div>
                <div className="metric-item">
                  <div className="metric-label">Risk Per Share</div>
                  <div className="metric-val">₹{selectedChartTrade.risk_per_share} ({selectedChartTrade.risk_pct}%)</div>
                </div>
              </div>

              {/* Setup Reasons Checklist */}
              <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)', padding: '1rem 1.25rem', borderRadius: '12px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.4rem', textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>
                  Technical Confluence Pillars
                </div>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
                  {selectedChartTrade.reasons?.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
