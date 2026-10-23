import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Search, RefreshCw, BarChart2, ShieldCheck, Activity, 
  ExternalLink, ArrowUpRight, ArrowDownRight, Filter, 
  Layers, Compass, X, SlidersHorizontal, Terminal, Zap, Globe,
  Volume2, VolumeX, LayoutGrid, Table, Copy, Check, Info, Shield, Clock
} from 'lucide-react';

import ThreeCanvas from './components/ThreeCanvas';
import { CustomCursor, TiltCard, RiskRewardBar, RadialProgress } from './components/CyberHUD';
import StockChart from './components/StockChart';
import RegimeView from './components/RegimeView';
import BacktestLab from './components/BacktestLab';
import CyberToast from './components/CyberToast';
import { playTone, setSoundEnabled, isSoundEnabled } from './utils/soundFx';

export default function App() {
  const [activeTab, setActiveTab] = useState('screener'); // 'screener' | 'regime' | 'backtest'
  const [regimeData, setRegimeData] = useState(null);
  const [screenerData, setScreenerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [quickFilter, setQuickFilter] = useState('ALL'); // 'ALL' | 'OPTIMAL' | 'HIGH_RR' | 'HIGH_CONVICTION'
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'table'
  const [selectedChartTrade, setSelectedChartTrade] = useState(null);
  const [soundOn, setSoundOn] = useState(false);
  const [toast, setToast] = useState(null);
  const [copiedSymbol, setCopiedSymbol] = useState(null);
  const [currentTime, setCurrentTime] = useState('');

  const searchInputRef = useRef(null);

  // Real-time IST Clock & Market Session Status
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Format as IST
      const istString = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
      const dateString = now.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short' });
      setCurrentTime(`${dateString} • ${istString} IST`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Determine if NSE Market is currently live (Mon-Fri 09:15 to 15:30 IST)
  const isMarketOpen = useMemo(() => {
    try {
      const now = new Date();
      const istDate = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
      const day = istDate.getDay();
      if (day === 0 || day === 6) return false; // Weekend
      const hour = istDate.getHours();
      const min = istDate.getMinutes();
      const timeNum = hour * 100 + min;
      return timeNum >= 915 && timeNum <= 1530;
    } catch (e) {
      return false;
    }
  }, [currentTime]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 3800);
  };

  const toggleSound = () => {
    const nextState = !soundOn;
    setSoundOn(nextState);
    setSoundEnabled(nextState);
    if (nextState) {
      showToast('Cyber acoustic feedback enabled', 'info');
    }
  };

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
    playTone('scan');
    try {
      const url = forceRefresh ? '/api/screener/run?force_refresh=true' : '/api/screener/run';
      const res = await fetch(url);
      const data = await res.json();
      setScreenerData(data);
      if (data.regime) {
        setRegimeData(data.regime);
      }
      playTone('success');
      showToast(`Scan complete: ${data.signals?.length || 0} setups identified across NSE universe`, 'success');
    } catch (err) {
      console.error("Failed to run screener", err);
      playTone('alert');
      showToast('Telemetry scan encountered an error', 'warning');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRegime();
    runScreener(false);
  }, []);

  // Keyboard shortcut listener (/ to focus search, Esc to close modal)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === '/' && document.activeElement !== searchInputRef.current && !selectedChartTrade) {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === 'Escape') {
        if (selectedChartTrade) setSelectedChartTrade(null);
        if (document.activeElement === searchInputRef.current) {
          setSearchQuery('');
          searchInputRef.current.blur();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedChartTrade]);

  const allSignals = screenerData?.signals || [];

  // Filter signals based on search, strategy, and quickFilter
  const filteredSignals = useMemo(() => {
    return allSignals.filter(sig => {
      const matchesSearch = sig.symbol.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStrategy = strategyFilter === 'ALL' || sig.strategy === strategyFilter;

      let matchesQuick = true;
      if (quickFilter === 'OPTIMAL') {
        matchesQuick = sig.regime_status === 'OPTIMAL';
      } else if (quickFilter === 'HIGH_RR') {
        matchesQuick = (sig.risk_reward || 0) >= 2.0;
      } else if (quickFilter === 'HIGH_CONVICTION') {
        matchesQuick = (sig.confidence_score || 0) >= 80;
      }

      return matchesSearch && matchesStrategy && matchesQuick;
    });
  }, [allSignals, searchQuery, strategyFilter, quickFilter]);

  const optimalCount = allSignals.filter(s => s.regime_status === 'OPTIMAL').length;
  const avgRR = allSignals.length > 0 
    ? (allSignals.reduce((acc, s) => acc + (s.risk_reward || 0), 0) / allSignals.length).toFixed(1)
    : '2.1';

  // Copy Trade Setup Plan to Clipboard
  const handleCopySetup = (sig) => {
    const text = `🎯 [QUANTUM SWING SETUP: ${sig.symbol}]\n• Entry: ₹${sig.entry_price}\n• Stop-Loss: ₹${sig.stop_loss} (-${sig.risk_pct}%)\n• Target 1: ₹${sig.target_1}\n• Target 2: ₹${sig.target_2}\n• R:R Ratio: 1:${sig.risk_reward}\n• Strategy: ${sig.strategy_title}`;
    navigator.clipboard.writeText(text);
    setCopiedSymbol(sig.symbol);
    playTone('blip');
    showToast(`Copied ${sig.symbol} setup parameters to clipboard`, 'success');
    setTimeout(() => setCopiedSymbol(null), 2500);
  };

  return (
    <>
      {/* 3D Three.js Fluid Background */}
      <ThreeCanvas regime={regimeData?.regime} isScanning={loading} />

      {/* Cybernetic Custom Cursor */}
      <CustomCursor />

      {/* Floating HUD Toast */}
      {toast && (
        <CyberToast 
          message={toast.message} 
          type={toast.type} 
          onClose={() => setToast(null)} 
        />
      )}

      {/* Laser Scanning Beam when scan is in progress */}
      {loading && <div className="scan-beam" />}

      {/* Top Ticker Tape Marquee - Ultra Sharp & High Contrast */}
      <div className="ticker-tape-wrap">
        <div className="ticker-tape-content">
          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">NSE: NIFTY 50</span>
          <span className="ticker-val-cyan">₹{regimeData?.metrics?.nifty_close || '22,687.65'}</span>
          <span style={{ color: (regimeData?.metrics?.dist_20ema_pct >= 0) ? '#10b981' : '#f43f5e', marginLeft: '0.35rem', fontWeight: 700 }}>
            ({regimeData?.metrics?.dist_20ema_pct > 0 ? '+' : ''}{regimeData?.metrics?.dist_20ema_pct || '-0.8'}%)
          </span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">REGIME:</span>
          <span className="ticker-val-rose" style={{ color: regimeData?.color || '#f43f5e' }}>
            {regimeData?.title || 'Bearish Correction'}
          </span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">BREADTH:</span>
          <span className="ticker-val-green">{regimeData?.metrics?.breadth_above_50ema_pct || '48'}% STOCKS &gt; 50 EMA</span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">DEFENSIVE CASH:</span>
          <span className="ticker-val-amber">{100 - (regimeData?.max_capital_exposure_pct || 25)}% CASH TARGET</span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">TELEMETRY:</span>
          <span style={{ color: '#ffffff', fontWeight: 700 }}>MUMBAI EXCHANGE FAST-STREAM</span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">ALPHA ENGINE:</span>
          <span className="ticker-val-cyan">ACTIVE [4 QUANT MODELS]</span>

          <span className="ticker-diamond">◈</span>
          <span className="ticker-tag">NSE: NIFTY 50</span>
          <span className="ticker-val-cyan">₹{regimeData?.metrics?.nifty_close || '22,687.65'}</span>
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
              <div className="brand-sub">NSE QUANTITATIVE STUDIO v2.4 ULTRA</div>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <div className="nav-tabs">
            <button 
              className={`nav-tab-btn ${activeTab === 'screener' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('screener');
                playTone('click');
              }}
            >
              <Layers size={16} /> Cockpit ({filteredSignals.length})
            </button>
            <button 
              className={`nav-tab-btn ${activeTab === 'regime' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('regime');
                playTone('click');
              }}
            >
              <Compass size={16} /> Regime Matrix
            </button>
            <button 
              className={`nav-tab-btn ${activeTab === 'backtest' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('backtest');
                playTone('click');
              }}
            >
              <BarChart2 size={16} /> Backtest Lab
            </button>
          </div>

          {/* Right Action & Regime Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
            {/* Live Clock & Session Status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#e2e8f0', fontWeight: 600 }}>
              <span className="live-dot" style={{ background: isMarketOpen ? '#10b981' : '#f59e0b', width: 8, height: 8 }} />
              <span style={{ color: isMarketOpen ? '#10b981' : '#f59e0b', fontWeight: 700 }}>
                {isMarketOpen ? 'NSE LIVE' : 'AFTER HOURS'}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.25)' }}>|</span>
              <span style={{ color: '#f8fafc' }}>{currentTime}</span>
            </div>

            {/* Sound FX Toggle Button */}
            <button 
              onClick={toggleSound}
              className="btn-cyber-ghost"
              title={soundOn ? 'Sound FX Enabled' : 'Enable Cyber Sound FX'}
              style={{ padding: '0.45rem', borderRadius: '10px' }}
            >
              {soundOn ? <Volume2 size={16} color="#38bdf8" /> : <VolumeX size={16} color="#64748b" />}
            </button>

            {/* Live Regime Pill Button */}
            {regimeData && (
              <div 
                className="btn-cyber-ghost clickable" 
                onClick={() => {
                  setActiveTab('regime');
                  playTone('click');
                }}
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

            {/* Laser Scan NSE Button */}
            <button 
              onClick={() => runScreener(true)} 
              disabled={loading}
              className="btn-cyber-primary"
            >
              <RefreshCw size={15} className={loading ? 'live-dot' : ''} />
              {loading ? 'Scanning...' : 'Scan NSE'}
            </button>
          </div>
        </nav>

        {/* TAB 1: COCKPIT / SCREENER */}
        {activeTab === 'screener' && (
          <main style={{ animation: 'fadeInUp 0.3s ease' }}>
            {/* Lusion / Avant-Garde Editorial Hero Banner */}
            <div className="hero-editorial" style={{ marginBottom: '2rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#38bdf8', letterSpacing: '0.12em', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                  <Terminal size={14} />
                  <span>[01 // QUANTITATIVE ALPHA COCKPIT]</span>
                  <span>•</span>
                  <span>NIFTY 100 UNIVERSE</span>
                </div>
                <h1 className="hero-main-title" style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.4rem, 5vw, 4.2rem)', fontWeight: 900, letterSpacing: '-0.04em', lineHeight: 0.95, textTransform: 'uppercase' }}>
                  TACTICAL<br />CONVERGENCE
                </h1>
              </div>

              {/* 3 Executive HUD Metric Cards */}
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {/* HUD 1: Regime Capital Allocation */}
                <div style={{ 
                  background: 'rgba(10, 16, 28, 0.85)', 
                  border: '1px solid rgba(255,255,255,0.14)', 
                  borderRadius: '16px', 
                  padding: '1.25rem 1.5rem',
                  backdropFilter: 'blur(20px)',
                  minWidth: '220px',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: '#cbd5e1', fontWeight: 700 }}>
                    <span>REGIME CYCLE</span>
                    <span style={{ color: regimeData?.color || '#38bdf8', fontWeight: 'bold' }}>{regimeData?.regime || 'ACTIVE'}</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.9rem', fontWeight: 800, color: regimeData?.color || '#fff' }}>
                    {regimeData?.max_capital_exposure_pct || 25}% <span style={{ fontSize: '0.85rem', color: '#cbd5e1', fontWeight: 500 }}>CAPITAL</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.2rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    🛡 {100 - (regimeData?.max_capital_exposure_pct || 25)}% Protected in Cash
                  </div>
                </div>

                {/* HUD 2: Nifty 50 Health */}
                <div style={{ 
                  background: 'rgba(10, 16, 28, 0.85)', 
                  border: '1px solid rgba(255,255,255,0.14)', 
                  borderRadius: '16px', 
                  padding: '1.25rem 1.5rem',
                  backdropFilter: 'blur(20px)',
                  minWidth: '220px',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: '#cbd5e1', fontWeight: 700 }}>
                    <span>NIFTY 50 BENCHMARK</span>
                    <span style={{ color: (regimeData?.metrics?.dist_20ema_pct >= 0) ? '#10b981' : '#f43f5e', fontWeight: 'bold' }}>
                      {regimeData?.metrics?.dist_20ema_pct > 0 ? '+' : ''}{regimeData?.metrics?.dist_20ema_pct}% 20EMA
                    </span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.9rem', fontWeight: 800, color: '#fff' }}>
                    ₹{regimeData?.metrics?.nifty_close || '22,687'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#e2e8f0', marginTop: '0.2rem', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                    RSI: <b style={{ color: '#fff' }}>{regimeData?.metrics?.rsi_14 || '46.2'}</b> • ATR: <b style={{ color: '#38bdf8' }}>{regimeData?.metrics?.atr_pct || '1.1'}%</b>
                  </div>
                </div>

                {/* HUD 3: Confluence Setups Velocity */}
                <div style={{ 
                  background: 'rgba(10, 16, 28, 0.85)', 
                  border: '1px solid rgba(255,255,255,0.14)', 
                  borderRadius: '16px', 
                  padding: '1.25rem 1.5rem',
                  backdropFilter: 'blur(20px)',
                  minWidth: '220px',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: '#cbd5e1', fontWeight: 700 }}>
                    <span>CONFLUENCE SETUPS</span>
                    <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>AVG 1:{avgRR} R:R</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.9rem', fontWeight: 800, color: '#fff' }}>
                    {filteredSignals.length} <span style={{ fontSize: '0.9rem', color: '#cbd5e1', fontWeight: 500 }}>SIGNALS</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.2rem', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    ◈ {optimalCount} Optimal to Cycle
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive Controls & Filters Bar */}
            <div style={{ 
              background: 'rgba(8, 14, 26, 0.85)', 
              backdropFilter: 'blur(16px)', 
              border: '1px solid var(--border-glass)',
              borderRadius: '18px',
              padding: '1rem 1.5rem',
              marginBottom: '2rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '1.25rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
                {/* Search Bar */}
                <div className="search-input-wrap" style={{ width: '270px' }}>
                  <Search size={16} color="#64748b" />
                  <input 
                    ref={searchInputRef}
                    type="text" 
                    placeholder="Search ticker (press / to focus)..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="search-input"
                  />
                  {searchQuery && (
                    <button 
                      onClick={() => setSearchQuery('')}
                      style={{ background: 'none', border: 'none', color: '#64748b', display: 'flex' }}
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>

                {/* Strategy Dropdown */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <SlidersHorizontal size={15} color="#94a3b8" />
                  <select 
                    value={strategyFilter} 
                    onChange={(e) => {
                      setStrategyFilter(e.target.value);
                      playTone('click');
                    }}
                    className="select-dropdown"
                  >
                    <option value="ALL">All Strategies</option>
                    <option value="trend_pullback">Trend EMA Pullback</option>
                    <option value="relative_strength">Relative Strength Leader</option>
                    <option value="capitulation_reversal">Capitulation Oversold Bounce</option>
                    <option value="volatility_squeeze">Volatility Squeeze Expansion</option>
                  </select>
                </div>

                {/* Quick Filter Chips */}
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  <button 
                    className={`filter-chip ${quickFilter === 'ALL' ? 'active' : ''}`}
                    onClick={() => { setQuickFilter('ALL'); playTone('click'); }}
                  >
                    All ({allSignals.length})
                  </button>
                  <button 
                    className={`filter-chip ${quickFilter === 'OPTIMAL' ? 'active' : ''}`}
                    onClick={() => { setQuickFilter('OPTIMAL'); playTone('click'); }}
                  >
                    Optimal Only ({optimalCount})
                  </button>
                  <button 
                    className={`filter-chip ${quickFilter === 'HIGH_RR' ? 'active' : ''}`}
                    onClick={() => { setQuickFilter('HIGH_RR'); playTone('click'); }}
                  >
                    R:R &gt;= 2.0
                  </button>
                  <button 
                    className={`filter-chip ${quickFilter === 'HIGH_CONVICTION' ? 'active' : ''}`}
                    onClick={() => { setQuickFilter('HIGH_CONVICTION'); playTone('click'); }}
                  >
                    Conviction &gt;= 80%
                  </button>
                </div>
              </div>

              {/* View Switcher: Grid vs Table */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ display: 'flex', background: 'rgba(0,0,0,0.5)', padding: '0.2rem', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <button 
                    onClick={() => { setViewMode('grid'); playTone('click'); }}
                    style={{
                      background: viewMode === 'grid' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
                      border: viewMode === 'grid' ? '1px solid #38bdf8' : '1px solid transparent',
                      color: viewMode === 'grid' ? '#fff' : 'var(--text-dim)',
                      padding: '0.35rem 0.65rem',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)'
                    }}
                    title="Grid Card View"
                  >
                    <LayoutGrid size={14} /> Cards
                  </button>
                  <button 
                    onClick={() => { setViewMode('table'); playTone('click'); }}
                    style={{
                      background: viewMode === 'table' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
                      border: viewMode === 'table' ? '1px solid #38bdf8' : '1px solid transparent',
                      color: viewMode === 'table' ? '#fff' : 'var(--text-dim)',
                      padding: '0.35rem 0.65rem',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)'
                    }}
                    title="Terminal Table View"
                  >
                    <Table size={14} /> Table
                  </button>
                </div>

                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                  SYNC: {screenerData?.timestamp || 'LIVE'}
                </div>
              </div>
            </div>

            {/* Loading / Empty States */}
            {loading ? (
              <div className="glass-card empty-state" style={{ padding: '5rem 1rem' }}>
                <div className="live-dot" style={{ margin: '0 auto 1.5rem', width: 16, height: 16, background: '#38bdf8' }}></div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', letterSpacing: '0.05em', color: '#fff' }}>
                  SCANNING TELEMETRY & MULTI-TIMEFRAME INDICATORS...
                </div>
              </div>
            ) : filteredSignals.length === 0 ? (
              <div className="glass-card empty-state" style={{ padding: '4rem 1rem' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem', color: '#38bdf8' }}>◈</div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', marginBottom: '0.5rem' }}>
                  No Setup Confluences Found
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Adjust active filters or initiate a fresh scan of the NSE universe.
                </p>
              </div>
            ) : viewMode === 'grid' ? (
              /* CARD GRID VIEW */
              <div className="signals-grid">
                {filteredSignals.map((sig, idx) => {
                  const isOptimal = sig.regime_status === 'OPTIMAL';
                  const isPos = sig.change_pct >= 0;
                  const isCopied = copiedSymbol === sig.symbol;

                  return (
                    <TiltCard key={idx} className="signal-card">
                      <div>
                        {/* Top Header */}
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.45rem', fontWeight: 800, color: '#fff' }}>
                                {sig.symbol}
                              </span>
                              <span className={`change-pill ${isPos ? 'pos' : 'neg'}`}>
                                {isPos ? '+' : ''}{sig.change_pct}%
                              </span>
                            </div>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#cbd5e1', fontWeight: 600, marginTop: '0.2rem' }}>
                              LTP: <b style={{ color: '#fff' }}>₹{sig.current_price?.toFixed(2)}</b>
                            </div>
                          </div>

                          <span style={{ 
                            fontSize: '0.68rem',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 800,
                            letterSpacing: '0.08em',
                            padding: '0.25rem 0.65rem',
                            borderRadius: '9999px',
                            textTransform: 'uppercase',
                            background: isOptimal ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                            color: isOptimal ? '#10b981' : '#f59e0b',
                            border: `1px solid ${isOptimal ? 'rgba(16,185,129,0.35)' : 'rgba(245,158,11,0.35)'}`,
                            boxShadow: isOptimal ? '0 0 15px rgba(16,185,129,0.2)' : 'none'
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
                          marginBottom: '0.5rem'
                        }}>
                          {sig.strategy_title}
                        </div>

                        {/* Visual Risk-to-Reward Progress Bar */}
                        <RiskRewardBar 
                          entry={sig.entry_price} 
                          stopLoss={sig.stop_loss} 
                          target1={sig.target_1} 
                          target2={sig.target_2} 
                        />

                        {/* Trade Parameters Cockpit */}
                        <div className="trade-plan-cockpit">
                          <div>
                            <div className="cockpit-title">Target Entry</div>
                            <div className="cockpit-val" style={{ color: '#38bdf8' }}>₹{sig.entry_price}</div>
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
                      <div className="card-footer">
                        <div className="confidence-meter">
                          <span>CONVICTION:</span>
                          <span className="confidence-val">{sig.confidence_score}%</span>
                          <span style={{ color: '#64748b' }}>| R:R 1:{sig.risk_reward}</span>
                        </div>

                        <div style={{ display: 'flex', gap: '0.45rem' }}>
                          <button 
                            onClick={() => handleCopySetup(sig)}
                            className="btn-cyber-ghost"
                            title="Copy Trade Setup"
                            style={{ padding: '0.45rem', borderRadius: '8px' }}
                          >
                            {isCopied ? <Check size={14} color="#10b981" /> : <Copy size={14} color="#94a3b8" />}
                          </button>

                          <button 
                            onClick={() => {
                              setSelectedChartTrade(sig);
                              playTone('blip');
                            }}
                            className="btn-cyber-ghost"
                            style={{ padding: '0.4rem 0.85rem' }}
                          >
                            <BarChart2 size={13} color="#38bdf8" /> Hologram Chart
                          </button>
                        </div>
                      </div>
                    </TiltCard>
                  );
                })}
              </div>
            ) : (
              /* INSTITUTIONAL TERMINAL TABLE VIEW */
              <div className="glass-card" style={{ padding: '1rem' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table className="terminal-table">
                    <thead>
                      <tr>
                        <th>TICKER</th>
                        <th>LTP</th>
                        <th>CHG %</th>
                        <th>STRATEGY</th>
                        <th>CONVICTION</th>
                        <th>ENTRY ₹</th>
                        <th>STOP LOSS ₹</th>
                        <th>TARGET (2R) ₹</th>
                        <th>R:R</th>
                        <th>REGIME</th>
                        <th style={{ textAlign: 'right' }}>ACTIONS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSignals.map((sig, idx) => {
                        const isOptimal = sig.regime_status === 'OPTIMAL';
                        const isPos = sig.change_pct >= 0;
                        return (
                          <tr key={idx}>
                            <td style={{ fontWeight: 800, color: '#fff' }}>{sig.symbol}</td>
                            <td>₹{sig.current_price?.toFixed(2)}</td>
                            <td style={{ color: isPos ? '#10b981' : '#f43f5e', fontWeight: 700 }}>
                              {isPos ? '+' : ''}{sig.change_pct}%
                            </td>
                            <td style={{ color: 'var(--text-muted)' }}>{sig.strategy_title}</td>
                            <td style={{ color: '#38bdf8', fontWeight: 700 }}>{sig.confidence_score}%</td>
                            <td style={{ color: '#fff' }}>₹{sig.entry_price}</td>
                            <td style={{ color: '#f43f5e' }}>₹{sig.stop_loss}</td>
                            <td style={{ color: '#10b981' }}>₹{sig.target_2}</td>
                            <td>1:{sig.risk_reward}</td>
                            <td>
                              <span style={{
                                fontSize: '0.65rem',
                                padding: '0.15rem 0.5rem',
                                borderRadius: '999px',
                                background: isOptimal ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                                color: isOptimal ? '#10b981' : '#f59e0b',
                                border: `1px solid ${isOptimal ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`
                              }}>
                                {sig.regime_status}
                              </span>
                            </td>
                            <td style={{ textAlign: 'right' }}>
                              <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                                <button
                                  onClick={() => handleCopySetup(sig)}
                                  className="btn-cyber-ghost"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.72rem' }}
                                  title="Copy Setup"
                                >
                                  <Copy size={12} />
                                </button>
                                <button
                                  onClick={() => {
                                    setSelectedChartTrade(sig);
                                    playTone('blip');
                                  }}
                                  className="btn-cyber-ghost"
                                  style={{ padding: '0.25rem 0.65rem', fontSize: '0.72rem' }}
                                >
                                  <BarChart2 size={12} color="#38bdf8" /> Chart
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
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
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#38bdf8', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
                    [TELEMETRY BLUEPRINT // {selectedChartTrade.strategy_title}]
                  </div>
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.75rem', fontWeight: 800, color: '#fff' }}>
                    {selectedChartTrade.symbol} — Execution Blueprint
                  </h3>
                </div>
                <button className="close-btn" onClick={() => setSelectedChartTrade(null)}>
                  <X size={20} />
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
              <div style={{ marginTop: '1rem', background: 'rgba(0,0,0,0.45)', border: '1px solid var(--border-subtle)', padding: '1rem 1.25rem', borderRadius: '14px' }}>
                <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#38bdf8', marginBottom: '0.45rem', textTransform: 'uppercase', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
                  Technical Confluence Pillars
                </div>
                <ul style={{ paddingLeft: '1.2rem', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.65' }}>
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
