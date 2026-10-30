import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, CandlestickChart, Check, ChevronDown,
  Copy, Filter, LayoutDashboard, RefreshCw, Search, ShieldAlert, Sparkles,
  Table2, Target, TrendingUp, X, Zap
} from 'lucide-react';

function price(value) {
  const number = Number(value);
  return value == null || value === '' || !Number.isFinite(number)
    ? '—'
    : `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

const STRATEGY_LABELS = {
  vwap_opening_drive: 'Gap + Volume Drive',
  orb_prebreakout: 'Breakout Setup',
  momentum_ignition: 'Momentum Ignition',
  mean_reversion: 'Mean Reversion Bounce',
  rs_surge: 'Relative Strength Surge',
};

const STRATEGY_ICONS = {
  vwap_opening_drive: '🚀',
  orb_prebreakout: '💎',
  momentum_ignition: '⚡',
  mean_reversion: '🔄',
  rs_surge: '💪',
};

function IntradayScreenerView({ connected, onConnect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [directionFilter, setDirectionFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table');
  const [copiedSymbol, setCopiedSymbol] = useState(null);

  const loadScreener = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const url = forceRefresh ? '/api/intraday/screener?force_refresh=true' : '/api/intraday/screener';
      const response = await fetch(url, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Intraday scan failed.');
      setData(result);
    } catch (loadError) {
      setError(loadError.message || 'Intraday scan could not be completed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadScreener(false); }, []);

  const allSignals = data?.signals || [];
  const filteredSignals = useMemo(() => allSignals.filter(signal => {
    const matchesSearch = !searchQuery || signal.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStrategy = strategyFilter === 'ALL' || signal.strategy === strategyFilter;
    const matchesDirection = directionFilter === 'ALL' || signal.direction === directionFilter;
    return matchesSearch && matchesStrategy && matchesDirection;
  }), [allSignals, searchQuery, strategyFilter, directionFilter]);

  const summary = data?.scan_summary || {};
  const stratDist = data?.strategy_distribution || {};

  const handleCopy = signal => {
    const text = `INTRADAY SETUP · ${signal.symbol}\nStrategy: ${signal.strategy_title}\nDirection: ${signal.direction}\nEntry: ₹${signal.entry_price}\nStop: ₹${signal.stop_loss}\nTarget 1: ₹${signal.target_1}\nTarget 2: ₹${signal.target_2}\nR:R: 1:${signal.risk_reward}\nConfidence: ${signal.confidence_score}%`;
    navigator.clipboard?.writeText(text);
    setCopiedSymbol(signal.symbol);
    window.setTimeout(() => setCopiedSymbol(null), 2500);
  };

  return <section className="module-page trading-strategy-page">
    <div className="module-heading">
      <div>
        <div className="eyebrow subtle-eyebrow">INTRADAY STOCK SCREENER · MULTI-SIGNAL</div>
        <h1>Intraday setups</h1>
        <p>Stocks filtered using 5 world-class intraday strategies — Gap Drive, Breakout Squeeze, Momentum Ignition, Mean Reversion, and Relative Strength Surge.</p>
      </div>
      <div className="trading-module-actions">
        <button className="scan-button" onClick={() => loadScreener(true)} disabled={loading}>
          {loading ? <RefreshCw size={14} className="spin" /> : <Sparkles size={14} />}
          {loading ? 'Scanning…' : 'Run scan'}
        </button>
      </div>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong></div>}

    {loading && !data ? (
      <div className="empty-panel">
        <div className="loader-orb"><RefreshCw size={20} /></div>
        <strong>Scanning NSE stocks for intraday setups</strong>
        <span>Analyzing 50 stocks across 5 strategies — this may take a moment…</span>
      </div>
    ) : data && <>
      {/* Summary Strip */}
      <section className="market-strip" aria-label="Intraday scan summary">
        <article className="metric-card tone-mint">
          <div className="metric-top"><span>STOCKS FOUND</span><span className="metric-icon"><Target size={16} /></span></div>
          <div className="metric-value">{filteredSignals.length}</div>
          <div className="metric-bottom"><span>{summary.total_setups || 0} total setups from scan</span></div>
        </article>
        <article className="metric-card tone-lilac">
          <div className="metric-top"><span>BULLISH SETUPS</span><span className="metric-icon"><TrendingUp size={16} /></span></div>
          <div className="metric-value">{summary.bullish || 0}</div>
          <div className="metric-bottom"><span className="metric-change positive"><ArrowUpRight size={14} />Upside momentum</span></div>
        </article>
        <article className="metric-card tone-peach">
          <div className="metric-top"><span>BEARISH SETUPS</span><span className="metric-icon"><ArrowDownRight size={16} /></span></div>
          <div className="metric-value">{summary.bearish || 0}</div>
          <div className="metric-bottom"><span className="metric-change negative"><ArrowDownRight size={14} />Downside setups</span></div>
        </article>
        <article className="metric-card tone-mint">
          <div className="metric-top"><span>SCAN STATUS</span><span className="metric-icon"><Zap size={16} /></span></div>
          <div className="metric-value">{summary.succeeded || 0}/{summary.requested || 0}</div>
          <div className="metric-bottom"><span>Stocks scanned successfully</span></div>
        </article>
      </section>

      {/* Strategy Distribution */}
      {Object.keys(stratDist).length > 0 && <div className="intraday-strat-dist">
        {(data.strategies_available || []).map(s => <button
          key={s.id}
          className={`intraday-strat-chip ${strategyFilter === s.id ? 'active' : ''} ${!stratDist[s.id] ? 'empty' : ''}`}
          onClick={() => setStrategyFilter(strategyFilter === s.id ? 'ALL' : s.id)}
          title={s.description}
        >
          <span>{STRATEGY_ICONS[s.id] || '📊'}</span>
          <span>{STRATEGY_LABELS[s.id] || s.title}</span>
          <b>{stratDist[s.id] || 0}</b>
        </button>)}
      </div>}

      {/* Filters */}
      <div className="intraday-filter-row">
        <label className="search-box">
          <Search size={16} />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Find a stock" />
          {searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear"><X size={14} /></button>}
        </label>
        <select className="strategy-select" value={strategyFilter} onChange={e => setStrategyFilter(e.target.value)} aria-label="Filter by strategy">
          <option value="ALL">All strategies</option>
          {(data.strategies_available || []).map(s => <option key={s.id} value={s.id}>{STRATEGY_LABELS[s.id] || s.title} ({stratDist[s.id] || 0})</option>)}
        </select>
        <select className="strategy-select" value={directionFilter} onChange={e => setDirectionFilter(e.target.value)} aria-label="Filter by direction">
          <option value="ALL">All directions</option>
          <option value="BULLISH">Bullish only</option>
          <option value="BEARISH">Bearish only</option>
        </select>
        <div className="view-toggle">
          <button onClick={() => setViewMode('table')} className={viewMode === 'table' ? 'active' : ''} aria-label="Table view"><Table2 size={16} /></button>
          <button onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'active' : ''} aria-label="Card view"><LayoutDashboard size={16} /></button>
        </div>
      </div>

      {/* Results */}
      {filteredSignals.length === 0 ? (
        <div className="empty-panel">
          <div className="empty-icon"><Search size={19} /></div>
          <strong>{allSignals.length ? 'No stocks match these filters' : 'No intraday setups found right now'}</strong>
          <span>{allSignals.length ? 'Try a different filter or search.' : 'The market may not have strong setups today. Run a fresh scan to check again.'}</span>
          {!allSignals.length && <button className="text-action" onClick={() => loadScreener(true)}>Scan again <ArrowUpRight size={14} /></button>}
        </div>
      ) : viewMode === 'table' ? (
        <div className="table-shell">
          <div className="table-scroll">
            <table className="setups-table">
              <thead><tr>
                <th>STOCK</th>
                <th>STRATEGY</th>
                <th>DIRECTION</th>
                <th>PRICE CHANGE</th>
                <th>ENTRY PRICE</th>
                <th>STOP LOSS</th>
                <th>TARGET 1</th>
                <th>TARGET 2</th>
                <th>R:R</th>
                <th>SCORE</th>
                <th aria-label="Actions" />
              </tr></thead>
              <tbody>{filteredSignals.map((signal, index) => {
                const positive = signal.change_pct >= 0;
                const isBullish = signal.direction === 'BULLISH';
                const isCopied = copiedSymbol === signal.symbol;
                return <tr key={`${signal.symbol}-${index}`} className="setup-row">
                  <td>
                    <div className="instrument">
                      <span className={`instrument-token ${isBullish ? '' : 'bearish-token'}`}>{signal.symbol.slice(0, 1)}</span>
                      <span><b>{signal.symbol}</b><small>{signal.strategy_title}</small></span>
                    </div>
                  </td>
                  <td><span className="strategy-tag">{STRATEGY_ICONS[signal.strategy] || '📊'} {STRATEGY_LABELS[signal.strategy] || signal.strategy_title}</span></td>
                  <td><span className={`direction-badge ${isBullish ? 'bullish' : 'bearish'}`}>{isBullish ? '▲ BULL' : '▼ BEAR'}</span></td>
                  <td><span className={`move-value ${positive ? 'positive' : 'negative'}`}>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{positive ? '+' : ''}{signal.change_pct}%</span></td>
                  <td className="numeric-cell">{price(signal.entry_price)}</td>
                  <td className="numeric-cell stop-value">{price(signal.stop_loss)}</td>
                  <td className="numeric-cell target-value">{price(signal.target_1)}</td>
                  <td className="numeric-cell target-value">{price(signal.target_2)}</td>
                  <td><span className="rr-badge">{signal.risk_reward} to 1</span></td>
                  <td>
                    <div className="confidence">
                      <span className="confidence-track"><i style={{ width: `${Math.min(100, signal.confidence_score || 0)}%` }} /></span>
                      <b>{signal.confidence_score ?? '—'}%</b>
                    </div>
                  </td>
                  <td><button className="row-action" title="Copy setup" onClick={() => handleCopy(signal)}>{isCopied ? <Check size={15} /> : <Copy size={15} />}</button></td>
                </tr>;
              })}</tbody>
            </table>
          </div>
          <div className="table-footer">
            <span><b>{filteredSignals.length}</b> intraday setups shown</span>
            <span>Based on daily price analysis · prices may differ intraday</span>
          </div>
        </div>
      ) : (
        <div className="setup-grid">{filteredSignals.map((signal, index) => {
          const isBullish = signal.direction === 'BULLISH';
          return <article className="setup-card" key={`${signal.symbol}-${index}`}>
            <div className="setup-card-top">
              <span className={`instrument-token large-token ${isBullish ? '' : 'bearish-token'}`}>{signal.symbol.slice(0, 1)}</span>
              <span className={`direction-badge ${isBullish ? 'bullish' : 'bearish'}`}>{isBullish ? '▲ BULLISH' : '▼ BEARISH'}</span>
            </div>
            <h3>{signal.symbol}</h3>
            <p className="setup-strategy">{STRATEGY_ICONS[signal.strategy]} {STRATEGY_LABELS[signal.strategy] || signal.strategy_title}</p>
            <div className="card-prices">
              <div><span>ENTRY</span><b>{price(signal.entry_price)}</b></div>
              <div><span>STOP LOSS</span><b className="stop-value">{price(signal.stop_loss)}</b></div>
              <div><span>TARGET 1</span><b className="target-value">{price(signal.target_1)}</b></div>
              <div><span>TARGET 2</span><b className="target-value">{price(signal.target_2)}</b></div>
            </div>
            <div className="intraday-card-reasons">
              <strong>Why this setup</strong>
              <ul>{(signal.reasons || []).slice(0, 3).map((reason, i) => <li key={i}>{reason}</li>)}</ul>
            </div>
            <div className="card-end">
              <span className="rr-badge">{signal.risk_reward} to 1 · Risk {signal.risk_pct}%</span>
              <div className="confidence">
                <span className="confidence-track"><i style={{ width: `${Math.min(100, signal.confidence_score || 0)}%` }} /></span>
                <b>{signal.confidence_score}%</b>
              </div>
              <button className="text-action" onClick={() => handleCopy(signal)}><Copy size={14} /> Copy</button>
            </div>
          </article>;
        })}</div>
      )}

      <p className="trading-disclaimer">{data.disclaimer || 'Intraday setups based on daily data analysis. Not personalized advice. No orders placed. Verify prices, slippage and risk before acting.'}</p>
      <div className="trading-data-foot">
        <span className={data.cached ? 'stale' : 'fresh'}><i />{data.cached ? 'CACHED RESULT' : 'FRESH SCAN'}</span>
        <span>Updated {data.timestamp || 'just now'} · {summary.succeeded || 0} stocks scanned</span>
      </div>
    </>}
  </section>;
}


function NiftyIntradayView({ connected, onConnect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    let busy = false;
    const load = async (showLoader = false) => {
      if (busy) return;
      busy = true;
      if (showLoader && active) setLoading(true);
      try {
        const response = await fetch('/api/intraday', { cache: 'no-store' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'IIFL strategy data could not be loaded.');
        if (active) { setData(result); setError(null); }
      } catch (loadError) {
        if (active) setError(loadError.message || 'IIFL strategy data could not be loaded.');
      } finally {
        busy = false;
        if (active && showLoader) setLoading(false);
      }
    };
    load(true);
    const timer = window.setInterval(() => load(false), 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [refreshKey]);

  const directional = ['LONG_CALL_BIAS', 'LONG_PUT_BIAS'].includes(data?.signal);
  const statusText = data?.signal === 'LONG_CALL_BIAS' ? 'Nifty may rise' : data?.signal === 'LONG_PUT_BIAS' ? 'Nifty may fall' : 'Wait · no clear price move';
  const signalTone = directional ? (data?.signal === 'LONG_CALL_BIAS' ? 'positive' : 'negative') : 'neutral';

  return <>
    <div className="nifty-intraday-heading">
      <h2>NIFTY 50 check</h2>
      <div className="trading-module-actions">
        <span className={`portfolio-connection ${connected ? 'connected' : ''}`}><i />{connected ? 'IIFL connected' : 'IIFL login needed'}</span>
        <button className="secondary-button" onClick={() => setRefreshKey(key => key + 1)}><RefreshCw size={14} />Refresh</button>
      </div>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
    {loading && !data ? <div className="empty-panel compact-empty"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking Nifty</strong></div>
      : data && <>
        <div className="trading-signal-banner">
          <div className={`trading-signal-icon ${signalTone}`}><CandlestickChart size={19} /></div>
          <div className="trading-signal-copy">
            <span>{`TODAY'S NIFTY MOVE · ${data.session_date || 'LATEST SESSION'}`}</span>
            <strong className={signalTone}>{statusText}</strong>
            <small>{(data.reasons || []).join(' ')}</small>
          </div>
          <div className="trading-spot"><span>NIFTY PRICE</span><strong>{price(data.spot)}</strong>
            <small>{data.quote_at ? `Updated ${new Date(data.quote_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : data.candles_as_of ? `Latest price ${new Date(data.candles_as_of).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : 'Waiting for price'}</small>
          </div>
        </div>
        <div className="trading-metrics-grid">
          <article><span>HIGH IN FIRST 15 MIN</span><strong>{price(data.opening_range_high)}</strong></article>
          <article><span>LOW IN FIRST 15 MIN</span><strong>{price(data.opening_range_low)}</strong></article>
          <article><span>AVERAGE PRICE TODAY</span><strong>{price(data.vwap)}</strong></article>
          <article><span>SHORT-TERM AVERAGES</span><strong>{price(data.ema9)} / {price(data.ema20)}</strong></article>
        </div>
        {data.entry != null && <div className="intraday-plan-grid">
          <article><span>PRICE TO REVIEW</span><strong>{price(data.entry)}</strong></article>
          <article><span>EXIT IF PRICE FALLS TO</span><strong>{price(data.stop)}</strong></article>
          <article><span>POSSIBLE GAIN PRICE</span><strong>{price(data.target_2r)}</strong></article>
          <article><span>POSSIBLE LOSS SIZE</span><strong>{data.risk_points} points</strong></article>
        </div>}
      </>}
  </>;
}


export default function TradingStrategiesView({ mode, connected, onConnect }) {
  const isOptions = mode === 'options';
  const isIntraday = mode === 'intraday';

  // Options mode — keep original behavior
  if (isOptions) return <OptionsView connected={connected} onConnect={onConnect} />;

  // Intraday mode — show the stock screener + Nifty check
  return <div>
    <IntradayScreenerView connected={connected} onConnect={onConnect} />
    <div className="intraday-nifty-section">
      <NiftyIntradayView connected={connected} onConnect={onConnect} />
    </div>
  </div>;
}


function OptionsView({ connected, onConnect }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    let busy = false;
    const load = async (showLoader = false) => {
      if (busy) return;
      busy = true;
      if (showLoader && active) setLoading(true);
      try {
        const response = await fetch('/api/options', { cache: 'no-store' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'IIFL strategy data could not be loaded.');
        if (active) { setData(result); setError(null); }
      } catch (loadError) {
        if (active) setError(loadError.message || 'IIFL strategy data could not be loaded.');
      } finally {
        busy = false;
        if (active && showLoader) setLoading(false);
      }
    };
    load(true);
    const timer = window.setInterval(() => load(false), 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [refreshKey]);

  const directional = data?.status === 'SETUP_READY';
  const statusText = data?.status === 'SETUP_READY' ? 'Example plan is ready' : data?.status === 'WAIT' ? 'Wait for a clearer move' : data?.status === 'NO_TRADE' ? 'No plan right now' : 'Option prices unavailable';
  const signalTone = directional ? 'positive' : 'neutral';

  return <section className="module-page trading-strategy-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">LIVE MARKET EXAMPLES · NO ORDERS PLACED</div><h1>Nifty options example</h1><p>Shows one example of how Nifty options could be combined, with the possible loss shown.</p></div>
      <div className="trading-module-actions"><span className={`portfolio-connection ${connected ? 'connected' : ''}`}><i />{connected ? 'IIFL connected' : 'IIFL login needed'}</span><button className="secondary-button" onClick={() => setRefreshKey(key => key + 1)}><RefreshCw size={14} />Refresh</button></div>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking live market prices</strong><span>Looking for a clear move before showing an example…</span></div>
      : data && <>
        <div className="trading-signal-banner">
          <div className={`trading-signal-icon ${signalTone}`}><Activity size={19} /></div>
          <div className="trading-signal-copy"><span>NIFTY OPTIONS · NEXT AVAILABLE DATE</span><strong className={signalTone}>{statusText}</strong><small>{data.strategy || data.reason}</small></div>
          <div className="trading-spot"><span>NIFTY PRICE</span><strong>{price(data.spot)}</strong><small>{data.quote_at ? `Updated ${new Date(data.quote_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : 'Waiting for price'}</small></div>
        </div>

        {data.status === 'SETUP_READY' && <>
          <div className="options-spread-summary"><article><span>LAST DATE FOR THIS OPTION</span><strong>{data.expiry}</strong></article><article><span>SHARES IN ONE BUNDLE</span><strong>{data.lot_size}</strong></article><article><span>AMOUNT PAID PER SHARE</span><strong>{price(data.net_debit)}</strong></article><article><span>PRICE NEEDED TO AVOID A LOSS</span><strong>{price(data.breakeven)}</strong></article></div>
          <div className="options-legs"><div className="options-legs-heading"><strong>{data.strategy}</strong><span>Difference between option prices: {data.spread_width} points</span></div><div className="options-legs-table"><div className="options-leg-row options-leg-header"><span>BUY OR SELL</span><span>OPTION</span><span>PRICE LEVEL</span><span>PRICE NOW</span></div>{data.legs.map((leg, index) => <div className="options-leg-row" key={`${leg.instrument_id}-${index}`}><span className={leg.side === 'BUY' ? 'positive' : 'negative'}>{leg.side === 'BUY' ? 'BUY' : 'SELL'}</span><span>{leg.symbol}</span><span>{price(leg.strike)}</span><span>{price(leg.premium)}</span></div>)}</div><div className="options-payoff-row"><div><span>HIGHEST POSSIBLE LOSS · 1 BUNDLE</span><strong className="negative">{price(data.max_loss_one_lot)}</strong></div><div><span>HIGHEST POSSIBLE GAIN · 1 BUNDLE</span><strong className="positive">{price(data.max_profit_one_lot)}</strong></div></div></div>
          <div className="trading-rationale"><strong>Why this example appears</strong><ul><li>{data.reason}</li><li>The loss shown is an estimate before fees and taxes. Option prices can change quickly.</li></ul></div>
        </>}
        {data.status !== 'SETUP_READY' && <div className="empty-panel options-wait-state"><div className="empty-icon"><ShieldAlert size={19} /></div><strong>{statusText}</strong><span>{data.reason || 'Wait for a fresh NIFTY directional setup.'}</span></div>}

        <p className="trading-disclaimer">{data.disclaimer || 'Research scenario only. Not personalized financial advice.'} SEBI reports high loss rates among individual equity F&O traders; use extra caution.</p>
        <div className="trading-data-foot"><span className={data.fresh === false ? 'stale' : 'fresh'}><i />{data.fresh === false ? 'LAST SESSION / STALE' : 'UPDATING EVERY 30 SECONDS'}</span><span>{data.data_source}</span></div>
      </>}
  </section>;
}
