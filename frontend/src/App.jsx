import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, AudioLines, BarChart3, Bell, BookOpen,
  CandlestickChart, Check, ChevronDown, CircleHelp, Compass, Copy, LayoutDashboard,
  LineChart, MoreHorizontal, Search, ShieldCheck,
  Sparkles, Table2, Target, Volume2, VolumeX, Wallet, X, RefreshCw, Radio
} from 'lucide-react';
import appLogo from './assets/logo.png';
import StockChart from './components/StockChart';
import RegimeView from './components/RegimeView';
import BacktestLab from './components/BacktestLab';
import CyberToast from './components/CyberToast';
import { playTone, setSoundEnabled } from './utils/soundFx';

const navigation = [
  { id: 'screener', label: 'Overview', icon: LayoutDashboard, section: 'WORKSPACE' },
  { id: 'regime', label: 'Market regime', icon: Compass },
  { id: 'backtest', label: 'Strategy lab', icon: BarChart3 },
];
const comingSoon = [
  { label: 'Intraday', icon: CandlestickChart },
  { label: 'Options', icon: Activity },
  { label: 'Portfolio', icon: Wallet },
];

function formatPrice(value, fallback = '—') {
  if (value === undefined || value === null || value === '') return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : value;
}

function Sparkline({ positive = true, seed = 1 }) {
  const points = useMemo(() => Array.from({ length: 24 }, (_, i) => {
    const drift = positive ? i * 0.38 : -i * 0.28;
    const wave = Math.sin((i + seed) * 0.76) * 3 + Math.cos((i + seed) * 0.31) * 2;
    return `${i * 5},${24 - drift - wave}`;
  }).join(' '), [positive, seed]);
  const color = positive ? '#88d5b1' : '#efaaa4';
  return <svg className="sparkline" viewBox="0 0 115 32" aria-hidden="true"><polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function MetricCard({ label, value, change, positive, icon: Icon, tone = 'mint', note }) {
  return <article className={`metric-card tone-${tone}`}>
    <div className="metric-top"><span>{label}</span><span className="metric-icon"><Icon size={16} /></span></div>
    <div className="metric-value">{value}</div>
    <div className="metric-bottom"><span className={`metric-change ${positive == null ? '' : positive ? 'positive' : 'negative'}`}>{positive === true ? <ArrowUpRight size={14} /> : positive === false ? <ArrowDownRight size={14} /> : null}{change}</span><span>{note}</span></div>
    <Sparkline positive={positive} seed={value.length} />
  </article>;
}

export default function App() {
  const [activeTab, setActiveTab] = useState('screener');
  const [regimeData, setRegimeData] = useState(null);
  const [liveStatus, setLiveStatus] = useState(null);
  const [liveQuote, setLiveQuote] = useState(null);
  const [screenerData, setScreenerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [quickFilter, setQuickFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table');
  const [selectedChartTrade, setSelectedChartTrade] = useState(null);
  const [soundOn, setSoundOn] = useState(false);
  const [toast, setToast] = useState(null);
  const [copiedSymbol, setCopiedSymbol] = useState(null);
  const [currentTime, setCurrentTime] = useState('');
  const searchInputRef = useRef(null);

  useEffect(() => {
    const updateTime = () => setCurrentTime(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isMarketOpen = useMemo(() => {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Kolkata', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date());
    const get = type => parts.find(part => part.type === type)?.value;
    const day = get('weekday');
    const time = Number(get('hour')) * 100 + Number(get('minute'));
    return day !== 'Sat' && day !== 'Sun' && time >= 915 && time <= 1530;
  }, [currentTime]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 3800);
  };
  const toggleSound = () => {
    const enabled = !soundOn;
    setSoundOn(enabled);
    setSoundEnabled(enabled);
    if (enabled) showToast('Sound feedback enabled', 'info');
  };
  const loadRegime = async () => {
    try {
      const response = await fetch('/api/regime');
      if (!response.ok) throw new Error('Unable to load market regime');
      setRegimeData(await response.json());
    } catch (error) { console.error('Failed to load regime', error); }
  };
  const runScreener = async (forceRefresh = false) => {
    setLoading(true);
    playTone('scan');
    try {
      const response = await fetch(forceRefresh ? '/api/screener/run?force_refresh=true' : '/api/screener/run');
      if (!response.ok) throw new Error('Unable to scan market');
      const data = await response.json();
      setScreenerData(data);
      if (data.regime) setRegimeData(data.regime);
      playTone('success');
      showToast(`Scan complete · ${data.signals?.length || 0} setups found`, 'success');
    } catch (error) {
      console.error('Failed to run screener', error);
      playTone('alert');
      showToast('Market scan could not be completed', 'warning');
    } finally { setLoading(false); }
  };
  useEffect(() => { loadRegime(); runScreener(false); }, []);
  useEffect(() => {
    let active = true;
    const refreshStatus = async () => {
      try {
        const response = await fetch('/api/market/live/status');
        if (response.ok && active) setLiveStatus(await response.json());
      } catch (error) { console.error('Unable to check IIFL feed status', error); }
    };
    refreshStatus();
    const timer = window.setInterval(refreshStatus, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  useEffect(() => {
    if (!liveStatus?.authenticated) return undefined;
    let active = true;
    const refreshQuote = async () => {
      try {
        const response = await fetch('/api/market/live/nifty');
        if (!response.ok) {
          if (response.status === 401 && active) {
            setLiveQuote(null);
            setLiveStatus(status => ({ ...status, authenticated: false }));
          }
          return;
        }
        const quote = await response.json();
        if (active) setLiveQuote(quote);
      } catch (error) { console.error('Unable to refresh IIFL NIFTY quote', error); }
    };
    refreshQuote();
    const timer = window.setInterval(refreshQuote, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [liveStatus?.authenticated]);
  useEffect(() => {
    const onKeyDown = event => {
      if (event.key === '/' && document.activeElement !== searchInputRef.current && !selectedChartTrade) { event.preventDefault(); searchInputRef.current?.focus(); }
      if (event.key === 'Escape') { setSelectedChartTrade(null); if (document.activeElement === searchInputRef.current) { setSearchQuery(''); searchInputRef.current.blur(); } }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedChartTrade]);

  const allSignals = screenerData?.signals || [];
  const filteredSignals = useMemo(() => allSignals.filter(signal => {
    const matchesSearch = signal.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStrategy = strategyFilter === 'ALL' || signal.strategy === strategyFilter;
    const matchesQuick = quickFilter === 'ALL' || (quickFilter === 'OPTIMAL' && signal.regime_status === 'OPTIMAL') || (quickFilter === 'HIGH_RR' && (signal.risk_reward || 0) >= 2) || (quickFilter === 'HIGH_CONVICTION' && (signal.confidence_score || 0) >= 80);
    return matchesSearch && matchesStrategy && matchesQuick;
  }), [allSignals, searchQuery, strategyFilter, quickFilter]);
  const optimalCount = allSignals.filter(signal => signal.regime_status === 'OPTIMAL').length;
  const avgRR = allSignals.length ? (allSignals.reduce((sum, signal) => sum + (signal.risk_reward || 0), 0) / allSignals.length).toFixed(1) : '—';
  const metrics = regimeData?.metrics || {};
  const liveChange = liveQuote?.change_pct;
  const quoteFresh = liveQuote && Date.now() - Date.parse(liveQuote.received_at) < 10000;
  const marketName = activeTab === 'screener' ? 'Overview' : activeTab === 'regime' ? 'Market regime' : 'Strategy lab';

  const selectTab = id => { setActiveTab(id); playTone('click'); };
  const handleCopySetup = signal => {
    const text = `SWING SETUP · ${signal.symbol}\nEntry: ₹${signal.entry_price}\nStop: ₹${signal.stop_loss}\nTarget 1: ₹${signal.target_1}\nTarget 2: ₹${signal.target_2}\nRisk/reward: 1:${signal.risk_reward}\nStrategy: ${signal.strategy_title}`;
    navigator.clipboard?.writeText(text);
    setCopiedSymbol(signal.symbol);
    playTone('blip');
    showToast(`${signal.symbol} setup copied`, 'success');
    window.setTimeout(() => setCopiedSymbol(null), 2500);
  };

  return <div className="spatial-app">
    {toast && <CyberToast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    <aside className="side-rail">
      <button className="brand-mark" aria-label="Aether home" onClick={() => selectTab('screener')}><span className="brand-orb"><img className="brand-logo" src={appLogo} alt="" /></span></button>
      <div className="rail-divider" />
      <div className="nav-group-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Primary navigation">
        {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'selected' : ''}`} onClick={() => selectTab(id)} title={label}>
          <Icon size={18} strokeWidth={1.8} /><span>{label}</span>{id === 'screener' && <i className="nav-count">{filteredSignals.length}</i>}
        </button>)}
      </nav>
      <div className="rail-divider rail-lower" />
      <div className="nav-group-label">MARKETS</div>
      <nav className="side-nav">
        {comingSoon.map(({ label, icon: Icon }) => <button key={label} className="side-nav-item future-item" title={`${label} · coming soon`} onClick={() => showToast(`${label} analysis is on the roadmap`, 'info')}>
          <Icon size={18} strokeWidth={1.8} /><span>{label}</span><span className="soon-dot">SOON</span>
        </button>)}
      </nav>
      <div className="rail-spacer" />
      <button className="side-nav-item support-item" onClick={() => showToast('Help center coming soon', 'info')}><CircleHelp size={18} /><span>Help & support</span></button>
      <button className="profile-button" aria-label="Account settings" onClick={() => showToast('Account settings coming soon', 'info')}><span className="avatar">A</span><span className="profile-copy"><b>Analyst</b><small>Personal workspace</small></span><MoreHorizontal size={17} /></button>
    </aside>

    <div className="workspace">
      <header className="topbar">
        <div className="breadcrumb"><span>Workspace</span><span className="crumb-slash">/</span><strong>{marketName}</strong></div>
        <div className="topbar-actions">
          <div className={`session-pill ${isMarketOpen ? 'session-open' : ''}`}><span className="session-indicator" /><span>{isMarketOpen ? 'NSE market open' : 'Market closed'}</span><i />{currentTime} IST</div>
          <button className={`iifl-feed-button ${liveStatus?.authenticated ? 'connected' : ''}`} onClick={() => liveStatus?.configured ? window.location.assign('/api/market/live/login') : showToast('Add rotated IIFL credentials and the NIFTY instrument ID in backend/.env', 'warning')} title="Connect the IIFL live market feed"><Radio size={14} /><span>{liveStatus?.authenticated ? 'IIFL live' : 'Connect IIFL'}</span></button>
          <button className="icon-button" title={soundOn ? 'Mute sound' : 'Enable sound'} onClick={toggleSound}>{soundOn ? <Volume2 size={17} /> : <VolumeX size={17} />}</button>
          <button className="icon-button notification-button" title="Notifications" onClick={() => showToast('You’re all caught up', 'info')}><Bell size={17} /><span /></button>
          <button className="scan-button" onClick={() => runScreener(true)} disabled={loading}>{loading ? <RefreshCw className="spin" size={16} /> : <Sparkles size={16} />}{loading ? 'Scanning' : 'Run scan'}</button>
        </div>
      </header>

      <main className="page-content">
        {activeTab === 'screener' && <>
          <section className="welcome-row feature-hero">
            <div className="hero-copy">
              <div className="eyebrow"><span className="eyebrow-mark"><AudioLines size={14} /></span> NSE MARKET DESK <span className="hero-index">/</span> SWING ANALYSIS</div>
              <h1>Read the market.<br /><em>Make your move.</em></h1>
              <p className="welcome-subtitle">Signals with context. Risk in view. Your next move, considered.</p>
              <div className="hero-meta"><span><i />{isMarketOpen ? 'MARKET IN SESSION' : 'LATEST MARKET SESSION'}</span><span className="hero-meta-divider" /><span>{currentTime} IST</span></div>
            </div>
            <button className="hero-feature-card" onClick={() => selectTab('regime')} aria-label="Explore current market regime">
              <div className="hero-art-glow" /><div className="hero-graphic"><span className="hero-graphic-ring ring-one" /><span className="hero-graphic-ring ring-two" /><span className="hero-graphic-core" /><i className="hero-star star-one" /><i className="hero-star star-two" /></div>
              <div className="hero-feature-top"><span>THE MARKET, RIGHT NOW</span><ArrowUpRight size={16} /></div>
              <div className="hero-feature-bottom"><small><i />REGIME READ</small><strong>{regimeData?.title || 'Building a market view'}</strong><span>{regimeData?.recommended_action || 'Your market context will appear here.'}</span></div>
              <div className="hero-feature-index">AETHER <b> / 01</b></div>
            </button>
          </section>

          <section className="market-strip" aria-label="Market snapshot">
            <MetricCard label="NIFTY 50" value={liveQuote?.price != null ? Number(liveQuote.price).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : metrics.nifty_close ? Number(metrics.nifty_close).toLocaleString('en-IN') : '—'} change={liveQuote ? `${liveChange > 0 ? '+' : ''}${liveChange}% today` : metrics.dist_20ema_pct == null ? '—' : `${metrics.dist_20ema_pct > 0 ? '+' : ''}${metrics.dist_20ema_pct}% vs EMA`} positive={liveQuote ? liveChange >= 0 : (metrics.dist_20ema_pct ?? 0) >= 0} icon={LineChart} note={liveQuote ? `${quoteFresh ? 'IIFL live' : 'IIFL last update'} · ${liveQuote.tick_time || liveQuote.received_at}` : liveStatus?.configured ? 'Daily close · connect live feed' : 'Daily close'} tone="lilac" />
            <MetricCard label="Market breadth" value={metrics.breadth_above_50ema_pct != null ? `${metrics.breadth_above_50ema_pct}%` : '—'} change={metrics.breadth_above_50ema_pct == null ? 'Unavailable' : metrics.breadth_above_50ema_pct >= 50 ? 'Broadening' : 'Narrow'} positive={metrics.breadth_above_50ema_pct == null ? null : metrics.breadth_above_50ema_pct >= 50} icon={Activity} note="above 50 day average" tone="mint" />
            <MetricCard label="Active setups" value={loading && !screenerData ? '…' : filteredSignals.length} change={`${optimalCount} high alignment`} positive={optimalCount > 0} icon={Target} note={`Average 1:${avgRR} risk / reward`} tone="peach" />
            <article className="regime-card" onClick={() => selectTab('regime')} role="button" tabIndex="0" onKeyDown={event => event.key === 'Enter' && selectTab('regime')}>
              <div className="regime-orbit"><span /><i /><b /></div><div className="regime-copy"><span className="regime-label">CURRENT REGIME</span><strong>{regimeData?.title || 'Reading the market'}</strong><small><span className="regime-dot" style={{ backgroundColor: regimeData?.color || '#aaa' }} />{regimeData?.recommended_action || 'Market conditions update with each scan'}</small></div><ArrowUpRight size={16} className="regime-link" />
            </article>
          </section>

          <section className="insight-banner">
            <div className="banner-glow" /><div className="banner-icon"><Sparkles size={18} /></div><div className="banner-copy"><span>MARKET PULSE <i /> {isMarketOpen ? 'LIVE SESSION' : 'LATEST SESSION'}</span><strong>{regimeData?.description || 'Your swing trading workspace is ready.'}</strong><small>Capital exposure guide <b>{regimeData?.max_capital_exposure_pct ?? '—'}%</b><span className="banner-separator">·</span>Nifty RSI <b>{metrics.rsi_14 ?? '—'}</b><span className="banner-separator">·</span>Daily ATR <b>{metrics.atr_pct != null ? `${metrics.atr_pct}%` : '—'}</b></small></div><button className="banner-action" onClick={() => selectTab('regime')}>Explore regime <ArrowUpRight size={15} /></button>
          </section>

          <section className="setups-section">
            <div className="section-heading"><div><div className="eyebrow subtle-eyebrow">SWING STRATEGIES <span className="heading-line" /></div><h2>Setups in focus <span>{filteredSignals.length}</span></h2><p>High-conviction opportunities across your watch universe.</p></div><div className="setup-actions"><label className="search-box"><Search size={16} /><input ref={searchInputRef} value={searchQuery} onChange={event => setSearchQuery(event.target.value)} placeholder="Search symbols" /><kbd>/</kbd>{searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear search"><X size={14} /></button>}</label><select className="strategy-select" value={strategyFilter} onChange={event => setStrategyFilter(event.target.value)} aria-label="Filter by strategy"><option value="ALL">All strategies</option><option value="trend_pullback">Trend EMA Pullback</option><option value="relative_strength">Relative Strength Leader</option><option value="capitulation_reversal">Capitulation Oversold Bounce</option><option value="volatility_squeeze">Volatility Squeeze Expansion</option></select><div className="view-toggle"><button onClick={() => setViewMode('table')} className={viewMode === 'table' ? 'active' : ''} aria-label="Table view"><Table2 size={16} /></button><button onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'active' : ''} aria-label="Card view"><LayoutDashboard size={16} /></button></div></div></div>
            <div className="filter-row"><span>QUICK FILTER</span>{[['ALL', `All ${allSignals.length}`], ['OPTIMAL', `In regime ${optimalCount}`], ['HIGH_RR', 'R:R above 2'], ['HIGH_CONVICTION', 'Conviction 80+']].map(([id, label]) => <button key={id} className={`filter-pill ${quickFilter === id ? 'active' : ''}`} onClick={() => setQuickFilter(id)}>{quickFilter === id && <Check size={13} />}{label}</button>)}<span className="scan-time"><span className="scan-time-dot" />Updated {screenerData?.timestamp || 'just now'}</span></div>

            {loading ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Reading the market</strong><span>Scanning for setups across your universe…</span></div> : filteredSignals.length === 0 ? <div className="empty-panel"><div className="empty-icon"><Search size={19} /></div><strong>{allSignals.length ? 'No setups match these filters' : 'No setups to show yet'}</strong><span>{allSignals.length ? 'Try a different symbol or filter.' : 'Run a fresh market scan to look for opportunities.'}</span>{!allSignals.length && <button className="text-action" onClick={() => runScreener(true)}>Scan market <ArrowUpRight size={14} /></button>}</div> : viewMode === 'table' ? <div className="table-shell"><div className="table-scroll"><table className="setups-table"><thead><tr><th>INSTRUMENT</th><th>STRATEGY</th><th>LAST MOVE</th><th>ENTRY</th><th>STOP</th><th>TARGET</th><th>RISK / REWARD</th><th>CONFIDENCE</th><th aria-label="Actions" /></tr></thead><tbody>{filteredSignals.map((signal, index) => { const positive = signal.change_pct >= 0; const isCopied = copiedSymbol === signal.symbol; return <tr key={`${signal.symbol}-${index}`} onClick={() => setSelectedChartTrade(signal)} className="setup-row"><td><div className="instrument"><span className="instrument-token">{signal.symbol.slice(0, 1)}</span><span><b>{signal.symbol}</b><small>{signal.regime_status === 'OPTIMAL' ? 'Aligned with regime' : signal.strategy_title || 'Swing setup'}</small></span></div></td><td><span className="strategy-tag">{signal.strategy_title || signal.strategy}</span></td><td><span className={`move-value ${positive ? 'positive' : 'negative'}`}>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{positive ? '+' : ''}{signal.change_pct}%</span></td><td className="numeric-cell">{formatPrice(signal.entry_price)}</td><td className="numeric-cell stop-value">{formatPrice(signal.stop_loss)}</td><td className="numeric-cell target-value">{formatPrice(signal.target_1)}</td><td><span className="rr-badge">1:{signal.risk_reward}</span></td><td><div className="confidence"><span className="confidence-track"><i style={{ width: `${Math.min(100, signal.confidence_score || 0)}%` }} /></span><b>{signal.confidence_score ?? '—'}%</b></div></td><td><button className="row-action" title="Copy setup" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}>{isCopied ? <Check size={15} /> : <Copy size={15} />}</button></td></tr>; })}</tbody></table></div><div className="table-footer"><span><b>{filteredSignals.length}</b> setups shown</span><span>Prices and signals reflect the latest available market data</span></div></div> : <div className="setup-grid">{filteredSignals.map((signal, index) => <article className="setup-card" key={`${signal.symbol}-${index}`} onClick={() => setSelectedChartTrade(signal)}><div className="setup-card-top"><span className="instrument-token large-token">{signal.symbol.slice(0, 1)}</span><span className={`move-value ${signal.change_pct >= 0 ? 'positive' : 'negative'}`}>{signal.change_pct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{signal.change_pct}%</span></div><h3>{signal.symbol}</h3><p className="setup-strategy">{signal.strategy_title}</p><div className="card-prices"><div><span>ENTRY</span><b>{formatPrice(signal.entry_price)}</b></div><div><span>STOP</span><b className="stop-value">{formatPrice(signal.stop_loss)}</b></div><div><span>TARGET</span><b className="target-value">{formatPrice(signal.target_1)}</b></div></div><div className="card-end"><span className="rr-badge">1:{signal.risk_reward} R/R</span><button className="text-action" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}><Copy size={14} /> Copy plan</button></div></article>)}</div>}
          </section>
          <footer className="page-footer"><span><ShieldCheck size={14} /> Research tools for informed decisions</span><span>Data may be delayed. Verify before trading.</span></footer>
        </>}

        {activeTab === 'regime' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">MARKET CONTEXT</div><h1>Market regime</h1><p>Understand the conditions shaping today’s opportunities.</p></div><button className="secondary-button" onClick={() => selectTab('screener')}>Back to overview</button></div><RegimeView regimeData={regimeData} onSelectStrategy={id => { setStrategyFilter(id); selectTab('screener'); }} /></section>}
        {activeTab === 'backtest' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">RESEARCH WORKSPACE</div><h1>Strategy lab</h1><p>Explore how your swing strategies have behaved across historical data.</p></div><span className="research-badge"><BookOpen size={14} /> Research mode</span></div><BacktestLab /></section>}
      </main>
    </div>

    {selectedChartTrade && <div className="spatial-modal-backdrop" onClick={() => setSelectedChartTrade(null)}><div className="spatial-modal" onClick={event => event.stopPropagation()}><div className="modal-topline"><div><div className="eyebrow subtle-eyebrow">SWING SETUP · {selectedChartTrade.strategy_title}</div><h2>{selectedChartTrade.symbol} <span>Execution plan</span></h2></div><button className="icon-button" onClick={() => setSelectedChartTrade(null)} aria-label="Close"><X size={18} /></button></div><StockChart symbol={selectedChartTrade.symbol} tradePlan={selectedChartTrade} /><div className="modal-metrics"><div><span>ENTRY</span><b>{formatPrice(selectedChartTrade.entry_price)}</b></div><div><span>STOP LOSS</span><b className="stop-value">{formatPrice(selectedChartTrade.stop_loss)}</b></div><div><span>TARGET 1</span><b className="target-value">{formatPrice(selectedChartTrade.target_1)}</b></div><div><span>TARGET 2</span><b className="target-value">{formatPrice(selectedChartTrade.target_2)}</b></div><div><span>RISK / SHARE</span><b>{formatPrice(selectedChartTrade.risk_per_share)} <small>({selectedChartTrade.risk_pct}%)</small></b></div></div>{selectedChartTrade.reasons?.length > 0 && <div className="setup-rationale"><span>WHY THIS SETUP</span><ul>{selectedChartTrade.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>}</div></div>}
  </div>;
}
