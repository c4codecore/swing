import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, CandlestickChart, Check,
  Copy, LayoutDashboard, RefreshCw, Search, ShieldAlert, Sparkles,
  Table2, Target, TrendingUp, X, Zap
} from 'lucide-react';
import { formatINR, formatPercent } from '../utils/formatters';

let intradayScreenerSnapshot = null;
let intradayScreenerRequest = null;

function price(value) {
  return formatINR(value);
}

function candleTime(signal) {
  if (!signal.last_candle_at) return 'Candle time unavailable';
  const time = new Date(signal.last_candle_at).toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short', hour12: true
  });
  return `${signal.stale ? 'STALE · ' : ''}5m · ${time} IST · ${Math.floor((signal.data_delay_seconds || 0) / 60)}m delay`;
}

const STRATEGY_LABELS = {
  vwap_opening_drive: 'Gap + Volume Drive',
  orb_prebreakout: 'Breakout Setup',
  momentum_ignition: 'Momentum Ignition',
  mean_reversion: 'Mean Reversion Bounce',
  rs_surge: 'Relative Strength Surge',
  opening_range_breakout: '15-Min Opening Range Breakout',
  vwap_reclaim: 'VWAP Reclaim / Breakdown',
  trend_pullback: 'Trend Pullback Bounce',
};

const STRATEGY_ICONS = {
  vwap_opening_drive: '🚀',
  orb_prebreakout: '💎',
  momentum_ignition: '⚡',
  mean_reversion: '🔄',
  rs_surge: '💪',
  opening_range_breakout: '🎯',
  vwap_reclaim: '↗️',
  trend_pullback: '🌊',
};

const STRATEGY_LEARNING = {
  vwap_opening_drive: {
    intro: 'Market khulte hi kisi share ka price pichhle din se upar ya neeche khul sakta hai. App opening gap ya din ke move ke saath us waqt ke hisaab se volume aur VWAP ki position check karta hai.',
    checks: ['Opening gap ya din ka noticeable move', 'Us waqt ke hisaab se normal ya zyada volume (RVOL)', 'Price VWAP ke upar ya neeche hai', '5-minute RSI se move ki direction ka basic check'],
    example: 'Maan lijiye share pichhle close se upar khula, volume active hai aur price VWAP ke upar tik raha hai. App ise possible upward drive ke liye review list mein rakh sakta hai.',
    caution: 'Opening ke baad gap reverse bhi ho sakta hai. Gap khud continuation ki guarantee nahi hota; price, volume aur risk levels alag se check karein.',
  },
  orb_prebreakout: {
    intro: 'Yeh setup un shares ko dhoondhta hai jo haal ke price high (resistance) ke paas hain ya kuch samay se chhoti range mein chal rahe hain. Aisi jagah se price bahar nikle to tez move ho sakta hai, par breakout fail bhi ho sakta hai.',
    checks: ['5-day ya 20-day high ke paas price', 'Ya din ki range normal se chhoti (tight squeeze)', 'Volume, VWAP aur RSI se confirmation'],
    example: 'Agar share kuch din se ₹500 ke aas-paas ruk raha hai aur aaj us level ke kareeb volume ke saath pahunchta hai, to app ise breakout ke liye dekhne layak maan sakta hai.',
    caution: 'Resistance ke paas pahunchna breakout ho jaana nahi hai. Is strategy ka naam “pre-breakout” hai; level ke upar tikna alag se verify karein.',
  },
  momentum_ignition: {
    intro: 'Iska simple matlab hai: share mein aaj strong upward move ho, trading volume bhi saath de, aur price din ki range ke upper hisse mein ho. App daily trend aur momentum indicators se extra check karta hai.',
    checks: ['Din ka positive price move', 'Us waqt ke hisaab se higher volume', 'Price daily EMA20 ke upar', 'Session range mein price upper side par aur RSI strong'],
    example: 'Share dheere-dheere nahi balki volume ke saath upar ja raha ho aur din ke high ke paas bana rahe, to yeh momentum setup ho sakta hai.',
    caution: 'Bahut tez move ke baad price palat sakta hai. Late entry ka risk hota hai; current price aur stop level zaroor dekhein.',
  },
  mean_reversion: {
    intro: 'Kabhi share bahut girne ke baad apne average zone ki taraf wapas aata hai. Mean reversion bounce isi possible sambhalne ko dhoondhta hai; girawat ke beech sirf sasta dikhna kaafi nahi.',
    checks: ['Price lower Bollinger Band ke paas aaya ho', '5-minute RSI kamzor zone se recover kar raha ho', 'Price VWAP ke upar wapas aaya ho', 'Latest candle mein bounce ka sanket'],
    example: 'Agar share din mein girkar lower band tak gaya, phir candle green hui aur price VWAP ke upar aaya, to app possible bounce ko flag kar sakta hai.',
    caution: 'Girawat jaari reh sakti hai. Support tootne par bounce nahi aata; is setup ko reversal ki pakki khabar na samjhein.',
  },
  rs_surge: {
    intro: 'Yeh share ke move ko NIFTY 500 benchmark ke move se compare karta hai. Agar share broad market se behtar chal raha ho aur volume/trend checks bhi pass hon, to use relative strength kehte hain.',
    checks: ['Share ka intraday percent move Nifty se compare hota hai', 'Share Nifty se kam-se-kam 0.8 percentage point behtar ho', 'Volume, VWAP, EMA20 aur RSI confirmation'],
    example: 'Agar Nifty 0.2% gira ho par koi share 0.7% upar ho, to woh Nifty ke muqable mein behtar perform kar raha hai.',
    caution: 'Nifty ko beat karna profit ki guarantee nahi. Market-wide girawat mein strong share bhi neeche aa sakta hai.',
  },
  opening_range_breakout: {
    intro: 'Market ke pehle 15 minute ka high aur low ek chhoti opening range banate hain. Us range se baad mein volume ke saath bahar nikalna possible breakout ya breakdown hota hai.',
    checks: ['Pehle 15 minute ka high/low tay ho chuka ho', 'Completed 5-minute candle range ke bahar close kare', 'VWAP, volume aur RSI us direction ko support kare'],
    example: 'Agar pehle 15 minute ka high ₹250 hai aur baad ki candle VWAP ke upar volume ke saath ₹250 se upar close kare, to upward breakout setup ban sakta hai.',
    caution: 'Price range ke bahar jaakar turant andar laut sakta hai (false breakout). Candle close aur risk level check karein.',
  },
  vwap_reclaim: {
    intro: 'VWAP aaj ke trades ka volume ke hisaab se average price hai. Price neeche rehne ke baad VWAP ke upar close kare to “reclaim”; upar rehne ke baad neeche close kare to “breakdown” kaha jata hai.',
    checks: ['Pichhli completed 5-minute candle VWAP ki ek side ho', 'Nayi completed candle VWAP cross karke doosri side close kare', 'Volume aur RSI se cross ka basic confirmation'],
    example: 'Share VWAP se neeche chal raha tha. Nayi 5-minute candle VWAP ke upar close hui aur volume bhi normal se zyada raha—yeh VWAP reclaim ka example hai.',
    caution: 'VWAP ke aas-paas price baar-baar cross kar sakta hai. Ek cross akela trend badalne ka proof nahi hota.',
  },
  trend_pullback: {
    intro: 'Uptrend mein share kabhi thoda neeche aakar rukta ya sambhalta hai. Trend pullback setup aise pause ko dekhta hai—app daily trend, VWAP ke paas price aur latest candle ki direction check karta hai.',
    checks: ['Daily EMA20, EMA50 se upar ho (short-term uptrend)', 'Price EMA20 aur VWAP ke aas-paas support le raha ho', 'Latest 5-minute candle sambhalne ka sanket de', 'Volume bahut kam na ho'],
    example: 'Share ka daily trend upar hai; price VWAP ke paas halka neeche aaya aur phir green candle bani. Yeh possible pullback bounce hai.',
    caution: 'Pullback kabhi full reversal ban sakta hai. Trend aur stop level ko saath mein samjhein; sirf green candle par bharosa na karein.',
  },
};

function IntradayScreenerView({ onSelectStock }) {
  const [data, setData] = useState(() => intradayScreenerSnapshot);
  const [loading, setLoading] = useState(() => !intradayScreenerSnapshot);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [learnStrategyId, setLearnStrategyId] = useState(null);
  const [directionFilter, setDirectionFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table');
  const [copiedSymbol, setCopiedSymbol] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: 'confidence_score', direction: 'desc' });

  const loadScreener = async (forceRefresh = false) => {
    if (!forceRefresh && intradayScreenerSnapshot) {
      setData({ ...intradayScreenerSnapshot, cached: true });
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    let request = intradayScreenerRequest;
    if (forceRefresh || !request) {
      const url = forceRefresh ? '/api/intraday/screener?force_refresh=true' : '/api/intraday/screener';
      request = fetch(url, { cache: 'no-store' }).then(async response => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Intraday scan failed.');
        return result;
      });
      intradayScreenerRequest = request;
    }
    try {
      const result = await request;
      intradayScreenerSnapshot = result;
      setData(result);
    } catch (loadError) {
      setError(loadError.message || 'Intraday scan could not be completed.');
    } finally {
      if (intradayScreenerRequest === request) intradayScreenerRequest = null;
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScreener(false);
    const query = window.matchMedia('(max-width: 900px)');
    const useCards = () => { if (query.matches) setViewMode('grid'); };
    useCards();
    query.addEventListener?.('change', useCards);
    return () => query.removeEventListener?.('change', useCards);
  }, []);

  const allSignals = data?.signals || [];
  const filteredSignals = useMemo(() => allSignals.filter(signal => {
    const matchesSearch = !searchQuery || signal.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStrategy = strategyFilter === 'ALL' || signal.strategy === strategyFilter;
    const matchesDirection = directionFilter === 'ALL' || signal.direction === directionFilter;
    return matchesSearch && matchesStrategy && matchesDirection;
  }), [allSignals, searchQuery, strategyFilter, directionFilter]);
  const sortedSignals = useMemo(() => [...filteredSignals].sort((left, right) => {
    const a = left[sortConfig.key];
    const b = right[sortConfig.key];
    if (a == null && b == null) return 0;
    if (a == null) return 1;
    if (b == null) return -1;
    const numericKeys = new Set(['change_pct', 'entry_price', 'stop_loss', 'target_1', 'target_2', 'risk_reward', 'confidence_score', 'composite_score']);
    const comparison = numericKeys.has(sortConfig.key)
      ? Number(a) - Number(b)
      : String(a).localeCompare(String(b), 'en', { sensitivity: 'base' });
    return comparison * (sortConfig.direction === 'asc' ? 1 : -1);
  }), [filteredSignals, sortConfig]);
  const selectedStrategy = (data?.strategies_available || []).find(strategy => strategy.id === learnStrategyId);
  const learning = learnStrategyId ? STRATEGY_LEARNING[learnStrategyId] : null;

  useEffect(() => {
    if (!learnStrategyId) return undefined;
    const closeOnEscape = event => { if (event.key === 'Escape') setLearnStrategyId(null); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [learnStrategyId]);

  const requestSort = key => setSortConfig(previous => ({
    key,
    direction: previous.key === key && previous.direction === 'asc' ? 'desc' : 'asc',
  }));
  const sortHeader = (label, key) => <button type="button" className="intraday-sort-button" onClick={() => requestSort(key)}>
    <span>{label}</span><span className="intraday-sort-mark" aria-hidden="true">{sortConfig.key === key ? sortConfig.direction === 'asc' ? '↑' : '↓' : '↕'}</span>
  </button>;

  const summary = data?.scan_summary || {};
  const stratDist = data?.strategy_distribution || {};

  const handleCopy = signal => {
    const text = `INTRADAY SETUP · ${signal.symbol}\nStrategy: ${signal.strategy_title}\nDirection: ${signal.direction}\nEntry: ₹${signal.entry_price}\nStop: ₹${signal.stop_loss}\nTarget 1: ₹${signal.target_1}\nTarget 2: ₹${signal.target_2}\nR:R: 1:${signal.risk_reward}\nConfidence: ${signal.confidence_score}%`;
    navigator.clipboard?.writeText(text);
    setCopiedSymbol(signal.symbol);
    window.setTimeout(() => setCopiedSymbol(null), 2500);
  };

  return <section className="module-page trading-strategy-page">
    <div className="module-heading intraday-hero">
      <div className="intraday-hero-copy">
        <div className="eyebrow subtle-eyebrow"><span className="intraday-hero-mark"><CandlestickChart size={18} /></span> INTRADAY · MARKET SETUPS</div>
        <h1>Intraday setups</h1>
        <p>Market ke intraday setups, poore NSE EQ universe se.</p>
        <div className="intraday-hero-pills"><span><i className="intraday-status-dot" /> NIFTY 500 universe · {data?.scan_summary?.universe?.count ?? '500'} shares</span><span>8 strategies</span><span>Research view · No orders placed</span></div>
      </div>
      <div className="trading-module-actions">
        <button className="scan-button intraday-run-button" onClick={() => loadScreener(true)} disabled={loading}>
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
        <span>Scanning NSE-listed shares across 8 strategies. The first broad scan can take longer; daily market data is reused on follow-up scans.</span>
      </div>
    ) : data && <>
      {/* Scan summary */}
      <section className="market-strip" aria-label="Intraday scan summary">
        <article className="metric-card tone-mint">
          <div className="metric-top"><span>MATCHING STOCKS</span><span className="metric-icon"><Target size={16} /></span></div>
          <div className="metric-value">{filteredSignals.length}</div>
          <div className="metric-bottom"><span>From {summary.total_setups || 0} qualifying shares</span></div>
        </article>
        <article className="metric-card tone-lilac">
          <div className="metric-top"><span>BULLISH SETUPS</span><span className="metric-icon"><TrendingUp size={16} /></span></div>
          <div className="metric-value">{allSignals.filter(signal => signal.direction === 'BULLISH').length}</div>
          <div className="metric-bottom"><span className="metric-change positive"><ArrowUpRight size={14} />Upside momentum</span></div>
        </article>
        <article className="metric-card tone-peach">
          <div className="metric-top"><span>BEARISH SETUPS</span><span className="metric-icon"><ArrowDownRight size={16} /></span></div>
          <div className="metric-value">{allSignals.filter(signal => signal.direction === 'BEARISH').length}</div>
          <div className="metric-bottom"><span className="metric-change negative"><ArrowDownRight size={14} />Downside setups</span></div>
        </article>
        <article className="metric-card tone-mint">
          <div className="metric-top"><span>SCAN STATUS</span><span className="metric-icon"><Zap size={16} /></span></div>
          <div className="metric-value">{summary.succeeded || 0}/{summary.requested || 0}</div>
          <div className="metric-bottom"><span>Stocks scanned successfully</span></div>
        </article>
      </section>
      <details className="intraday-filter-details">
        <summary>Why some shares were left out</summary>
        <p>Price {data.filter_rejections?.min_price || 0} · Liquidity {data.filter_rejections?.avg_traded_value || 0} · History {data.filter_rejections?.insufficient_history || 0} · Stale data {data.filter_rejections?.stale_data || 0} · SME {data.filter_rejections?.sme || 0} · Price band {(data.filter_rejections?.circuit_band || 0) + (data.filter_rejections?.circuit_band_heuristic || 0)} · ASM/GSM {typeof data.filter_rejections?.asm_gsm === 'number' ? data.filter_rejections.asm_gsm : 0}</p>
      </details>

      {/* Strategy filters open a plain-language learning panel. */}
      {Object.keys(stratDist).length > 0 && <section className="intraday-strategy-guide" aria-label="Filter by strategy">
        <div className="intraday-strategy-guide-heading"><div><span className="eyebrow subtle-eyebrow">FILTER SETUPS</span><h2>Choose a strategy</h2></div><button className={`intraday-show-all ${strategyFilter === 'ALL' ? 'active' : ''}`} onClick={() => { setStrategyFilter('ALL'); setLearnStrategyId(null); }}>Show all</button></div>
        <div className="intraday-strat-dist">
        {(data.strategies_available || []).map(s => <button
          key={s.id}
          className={`intraday-strat-chip intraday-strategy-card ${strategyFilter === s.id ? 'active' : ''} ${!stratDist[s.id] ? 'empty' : ''}`}
          onClick={() => { setStrategyFilter(s.id); setLearnStrategyId(s.id); }}
          aria-pressed={strategyFilter === s.id}
        >
          <span className="intraday-strategy-card-top"><span className="intraday-strategy-icon" aria-hidden="true">{STRATEGY_ICONS[s.id] || '📊'}</span><b>{stratDist[s.id] || 0}</b></span>
          <strong>{STRATEGY_LABELS[s.id] || s.title}</strong>
          <span className="intraday-strategy-action">{strategyFilter === s.id ? 'Selected · learn more' : 'Select & learn'} <ArrowUpRight size={13} /></span>
        </button>)}
        </div>
      </section>}

      {/* Filters */}
      <div className="intraday-results-heading"><div><span className="eyebrow subtle-eyebrow">TODAY’S WATCHLIST</span><h2>Setups to review <b>{filteredSignals.length}</b></h2></div><span className="intraday-update-pill"><i />{data.cached ? 'Saved scan' : 'Latest scan'}</span></div>
      <div className="intraday-filter-row">
        <label className="search-box">
          <Search size={16} />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Find a stock" />
          {searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear"><X size={14} /></button>}
        </label>
        <select className="strategy-select" value={strategyFilter} onChange={e => { setStrategyFilter(e.target.value); setLearnStrategyId(e.target.value === 'ALL' ? null : e.target.value); }} aria-label="Filter by strategy">
          <option value="ALL">All strategies</option>
          {(data.strategies_available || []).map(s => <option key={s.id} value={s.id}>{STRATEGY_LABELS[s.id] || s.title} ({stratDist[s.id] || 0})</option>)}
        </select>
        <select className="strategy-select" value={directionFilter} onChange={e => setDirectionFilter(e.target.value)} aria-label="Filter by direction">
          <option value="ALL">All directions</option>
          <option value="BULLISH">Bullish only</option>
          <option value="BEARISH">Bearish only</option>
        </select>
        <div className="view-toggle">
          <button onClick={() => setViewMode(window.matchMedia('(max-width: 900px)').matches ? 'grid' : 'table')} className={viewMode === 'table' ? 'active' : ''} aria-label="Table view" aria-pressed={viewMode === 'table'}><Table2 size={16} /></button>
          <button onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'active' : ''} aria-label="Card view" aria-pressed={viewMode === 'grid'}><LayoutDashboard size={16} /></button>
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
            <table className="setups-table intraday-table">
              <thead><tr>
                <th aria-sort={sortConfig.key === 'symbol' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('STOCK', 'symbol')}</th>
                <th aria-sort={sortConfig.key === 'strategy_title' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('STRATEGY', 'strategy_title')}</th>
                <th aria-sort={sortConfig.key === 'direction' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('DIRECTION', 'direction')}</th>
                <th aria-sort={sortConfig.key === 'change_pct' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('PRICE CHANGE', 'change_pct')}</th>
                <th aria-sort={sortConfig.key === 'entry_price' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('ENTRY PRICE', 'entry_price')}</th>
                <th aria-sort={sortConfig.key === 'stop_loss' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('STOP LOSS', 'stop_loss')}</th>
                <th aria-sort={sortConfig.key === 'target_1' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('TARGET 1', 'target_1')}</th>
                <th aria-sort={sortConfig.key === 'target_2' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('TARGET 2', 'target_2')}</th>
                <th aria-sort={sortConfig.key === 'risk_reward' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('R:R', 'risk_reward')}</th>
                <th aria-sort={sortConfig.key === 'confidence_score' ? sortConfig.direction === 'asc' ? 'ascending' : 'descending' : 'none'}>{sortHeader('SCORE', 'confidence_score')}</th>
                <th aria-label="Actions" />
              </tr></thead>
              <tbody>{sortedSignals.map((signal, index) => {
                const positive = signal.change_pct >= 0;
                const isBullish = signal.direction === 'BULLISH';
                const isCopied = copiedSymbol === signal.symbol;
                return <tr key={`${signal.symbol}-${index}`} className="setup-row">
                  <td>
                    <div className="instrument">
                      <span className={`instrument-token ${isBullish ? '' : 'bearish-token'}`}>{signal.symbol.slice(0, 1)}</span>
                      <span><button type="button" className="intraday-stock-name" onClick={() => onSelectStock?.(signal)} aria-label={`View ${signal.symbol} stock research`}>{signal.symbol}</button><small className={`instrument-candle-time ${signal.stale ? 'stale' : ''}`}>{candleTime(signal)}</small></span>
                    </div>
                  </td>
                  <td><span className="strategy-tag">{STRATEGY_ICONS[signal.strategy] || '📊'} {STRATEGY_LABELS[signal.strategy] || signal.strategy_title}</span></td>
                  <td><span className={`direction-badge ${isBullish ? 'bullish' : 'bearish'}`}>{isBullish ? '▲ BULL' : '▼ BEAR'}</span></td>
                <td><span className={`move-value ${positive ? 'positive' : 'negative'}`}><span aria-hidden="true">{positive ? '▲' : '▼'}</span>{formatPercent(Math.abs(Number(signal.change_pct)) * (positive ? 1 : -1), { signed: positive })} <strong>{positive ? 'GAIN' : 'LOSS'}</strong></span></td>
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
            <span>Daily context + completed 5-minute bars · timestamps are IST</span>
          </div>
        </div>
      ) : (
        <div className="setup-grid">{sortedSignals.map((signal, index) => {
          const isBullish = signal.direction === 'BULLISH';
          return <article className="setup-card" key={`${signal.symbol}-${index}`}>
            <div className="setup-card-top">
              <span className={`instrument-token large-token ${isBullish ? '' : 'bearish-token'}`}>{signal.symbol.slice(0, 1)}</span>
              <span className={`direction-badge ${isBullish ? 'bullish' : 'bearish'}`}>{isBullish ? '▲ BULLISH' : '▼ BEARISH'}</span>
            </div>
            <h3><button type="button" className="intraday-stock-name" onClick={() => onSelectStock?.(signal)} aria-label={`View ${signal.symbol} stock research`}>{signal.symbol}</button></h3>
            <p className="setup-strategy">{STRATEGY_ICONS[signal.strategy]} {STRATEGY_LABELS[signal.strategy] || signal.strategy_title}</p>
            <div className="card-prices card-prices-4">
              <div><span>ENTRY</span><b>{price(signal.entry_price)}</b></div>
              <div><span>STOP LOSS</span><b className="stop-value">{price(signal.stop_loss)}</b></div>
              <div><span>TARGET 1</span><b className="target-value">{price(signal.target_1)}</b></div>
              <div><span>TARGET 2</span><b className="target-value">{price(signal.target_2)}</b></div>
            </div>
            <div className="intraday-card-reasons">
              <small className={signal.stale ? 'stale' : 'fresh'}>{candleTime(signal)}</small>
              <strong>Why this setup</strong>
              <ul>{(signal.reasons || []).slice(0, 3).map((reason, i) => <li key={i}>{reason}</li>)}</ul>
            </div>
            <div className="card-end">
              <span className="rr-badge">{signal.risk_reward} to 1 · Risk {formatPercent(signal.risk_pct, true)}</span>
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
        <span>Updated {data.timestamp || 'just now'} · {summary.succeeded || 0}/{summary.requested || 0} NIFTY 500 shares loaded · last full scan {summary.duration_seconds ?? '—'}s</span>
        {summary.timings_seconds && <span>Data fetch: daily {summary.timings_seconds.daily_data}s · 5-minute {summary.timings_seconds.five_minute_data}s · calculations {summary.timings_seconds.strategy_calculation}s</span>}
      </div>
    </>}
    {selectedStrategy && learning && <div className="intraday-learn-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setLearnStrategyId(null); }}>
      <section className="intraday-learn-modal" role="dialog" aria-modal="true" aria-labelledby="intraday-learn-title">
        <header className="intraday-learn-header">
          <span className="intraday-learn-icon" aria-hidden="true">{STRATEGY_ICONS[learnStrategyId] || '📊'}</span>
          <div><span className="eyebrow subtle-eyebrow">STRATEGY EXPLAINED · SIMPLE GUIDE</span><h2 id="intraday-learn-title">{STRATEGY_LABELS[learnStrategyId] || selectedStrategy.title}</h2></div>
          <button type="button" className="icon-button" onClick={() => setLearnStrategyId(null)} aria-label="Close strategy explanation"><X size={18} /></button>
        </header>
        <p className="intraday-learn-intro">{learning.intro}</p>
        <div className="intraday-learn-sections">
          <section><h3>App kya check karta hai</h3><ul>{learning.checks.map(item => <li key={item}>{item}</li>)}</ul></section>
          <section><h3>Ek simple example</h3><p>{learning.example}</p></section>
          <section className="intraday-learn-caution"><h3>Risk ko samjhein</h3><p>{learning.caution}</p></section>
        </div>
        <div className="intraday-learn-glossary"><strong>Chhote shabdon ka matlab</strong><span><b>VWAP</b> = aaj ke volume ke hisaab se average price</span><span><b>RSI</b> = recent price momentum ka indicator</span><span><b>RVOL</b> = iss waqt ka volume, aam volume ke muqable</span><span><b>EMA</b> = recent prices ko zyada weight dene wala average</span></div>
        <footer className="intraday-learn-footer"><small>Yeh setup sirf research signal hai—buy/sell ki guarantee nahi.</small><button type="button" className="primary-button" onClick={() => setLearnStrategyId(null)}>View {filteredSignals.length} matching stocks <ArrowUpRight size={16} /></button></footer>
      </section>
    </div>}
  </section>;
}


export default function TradingStrategiesView({ mode, connected, onConnect, onSelectStock }) {
  const isOptions = mode === 'options';

  // Options mode — keep original behavior
  if (isOptions) return <OptionsView connected={connected} onConnect={onConnect} onSelectStock={onSelectStock} />;

  // Intraday mode is a stock screener; NIFTY remains the relative-strength benchmark.
  return <IntradayScreenerView onSelectStock={onSelectStock} />;
}


function OptionsView({ connected, onConnect, onSelectStock }) {
  const [data, setData] = useState(null);
  const [stockScreen, setStockScreen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stockLoading, setStockLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stockError, setStockError] = useState(null);
  const [stockSearch, setStockSearch] = useState('');
  const [stockStrategy, setStockStrategy] = useState('ALL');
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

  useEffect(() => {
    let active = true;
    setStockLoading(true);
    setStockError(null);
    const url = refreshKey ? '/api/options/stocks?force_refresh=true' : '/api/options/stocks';
    fetch(url, { cache: 'no-store' })
      .then(async response => {
        const result = await response.json();
        if (response.status === 404) throw new Error('The backend is running an older version. Restart MarketVoice to load the F&O stock scan.');
        if (!response.ok) throw new Error(result.detail || 'F&O stock setups could not be loaded.');
        if (active) setStockScreen(result);
      })
      .catch(loadError => { if (active) setStockError(loadError.message || 'F&O stock setups could not be loaded.'); })
      .finally(() => { if (active) setStockLoading(false); });
    return () => { active = false; };
  }, [refreshKey]);

  const availableStockStrategies = stockScreen?.strategies_available?.length
    ? stockScreen.strategies_available
    : [...new Set((stockScreen?.signals || []).map(signal => signal.strategy).filter(Boolean))].map(id => ({ id, title: STRATEGY_LABELS[id] || id.replaceAll('_', ' ') }));
  const visibleStockSignals = (stockScreen?.signals || []).filter(signal => {
    const query = stockSearch.trim().toLowerCase();
    const matchesQuery = !query || `${signal.symbol || ''} ${signal.company_name || ''}`.toLowerCase().includes(query);
    return matchesQuery && (stockStrategy === 'ALL' || signal.strategy === stockStrategy);
  });

  const directional = data?.status === 'SETUP_READY';
  const statusText = data?.status === 'SETUP_READY' ? 'Example plan is ready' : data?.status === 'WAIT' ? 'Wait for a clearer move' : data?.status === 'NO_TRADE' ? 'No plan right now' : 'Option prices unavailable';
  const signalTone = directional ? 'positive' : 'neutral';

  return <section className="module-page trading-strategy-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">FUTURES &amp; OPTIONS · STOCK SETUPS</div><h1>Futures &amp; Options</h1><p>Optionable NIFTY 500 shares, filtered through eight intraday strategies.</p></div>
      <div className="trading-module-actions"><span className={`portfolio-connection ${connected ? 'connected' : ''}`}><i />{connected ? 'IIFL connected' : 'IIFL login needed'}</span><button className="secondary-button" onClick={() => setRefreshKey(key => key + 1)}><RefreshCw size={14} />Refresh</button></div>
    </div>

    <section className="options-stock-screen" aria-labelledby="options-stocks-title">
      <div className="options-stock-heading">
        <div><span className="eyebrow subtle-eyebrow">NIFTY 500 · OPTIONABLE SHARES</span><h2 id="options-stocks-title">Stock setups</h2><p>Shares with a current NSE stock-options listing and a completed-candle intraday signal.</p></div>
        <div className="options-stock-count"><strong>{stockScreen?.count ?? '—'}</strong><span>setups found</span></div>
      </div>
      <div className="options-stock-meta"><span>{stockScreen?.universe_count ?? '—'} optionable shares in scan</span><span>{stockScreen?.scanned_count ?? '—'} shares scanned</span><span>8 strategies checked</span></div>
      <div className="intraday-filter-row options-stock-filters">
        <label className="search-box"><Search size={16} /><input value={stockSearch} onChange={event => setStockSearch(event.target.value)} placeholder="Search company or symbol" aria-label="Search F&O stock setups" /></label>
        <select className="strategy-select" value={stockStrategy} onChange={event => setStockStrategy(event.target.value)} aria-label="Filter by strategy">
          <option value="ALL">All strategies</option>
          {availableStockStrategies.map(strategy => <option key={strategy.id} value={strategy.id}>{STRATEGY_LABELS[strategy.id] || strategy.title} ({stockScreen?.strategy_distribution?.[strategy.id] || 0})</option>)}
        </select>
      </div>
      {stockError && <div className="portfolio-notice"><strong>{stockError}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
      {stockLoading && !stockScreen ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Scanning F&amp;O shares</strong><span>Checking eligible shares for strategy signals…</span></div>
        : stockScreen && visibleStockSignals.length ? <div className="options-stock-grid">{visibleStockSignals.map(signal => <article className="options-stock-card" key={signal.symbol}>
          <div className="options-stock-card-top"><div><span className="options-stock-symbol">{signal.symbol}</span><small>{signal.company_name || signal.symbol}</small></div><div className="options-stock-badges"><span className={`options-direction ${signal.direction === 'BULLISH' ? 'positive' : 'negative'}`}>{signal.direction === 'BULLISH' ? '▲ Bullish' : '▼ Bearish'}</span>{signal.stale && <span className="options-stale-badge">Delayed</span>}</div></div>
          <div className="options-stock-strategy">{STRATEGY_ICONS[signal.strategy] || '✦'} {STRATEGY_LABELS[signal.strategy] || signal.strategy_title}</div>
          <div className="options-stock-prices"><div><span>PRICE NOW</span><b>{price(signal.current_price)}</b></div><div><span>ENTRY ZONE</span><b>{price(signal.entry_price)}</b></div><div><span>STOP LEVEL</span><b className="negative">{price(signal.stop_loss)}</b></div><div><span>TARGET 1</span><b className="positive">{price(signal.target_1)}</b></div></div>
          <div className="options-stock-footer"><span>Possible structure <b>{signal.options_structure}</b></span><button type="button" className="text-action" onClick={() => onSelectStock?.(signal, 'options')}>View stock details <ArrowUpRight size={14} /></button></div>
        </article>)}</div> : stockScreen && <div className="empty-panel"><div className="empty-icon"><Search size={19} /></div><strong>{stockScreen.count ? 'No shares match these filters' : 'No qualifying setups right now'}</strong><span>{stockScreen.count ? 'Try another name or strategy.' : stockScreen.reason || 'Refresh after fresh market data is available.'}</span></div>}
      <p className="trading-disclaimer">{stockScreen?.disclaimer || 'Underlying-stock signals only. Option premium, expiry-specific contract, Greeks and payoff are not calculated here. No orders are placed.'}</p>
    </section>

    {error && <div className="portfolio-notice"><strong>{error}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking live market prices</strong><span>Looking for a clear move before showing an example…</span></div>
      : data && <>
        <div className="trading-signal-banner">
          <div className={`trading-signal-icon ${signalTone}`}><Activity size={19} /></div>
          <div className="trading-signal-copy"><span>NIFTY OPTIONS · EXAMPLE PLAN</span><strong className={signalTone}>{statusText}</strong><small>{data.strategy || data.reason}</small></div>
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
