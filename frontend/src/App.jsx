import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, AudioLines, BarChart3, BookOpen,
  CandlestickChart, Check, ChevronDown, Compass, Copy, LayoutDashboard,
  History, LineChart, Search, ShieldCheck,
  Settings, Sparkles, Table2, Volume2, VolumeX, Wallet, X, RefreshCw, Radio, WifiOff, Menu
} from 'lucide-react';
import appLogo from './assets/logo.png';
import StockChart from './components/StockChart';
import RegimeView from './components/RegimeView';
import BacktestLab from './components/BacktestLab';
import CyberToast from './components/CyberToast';
import TradingStrategiesView from './components/TradingStrategiesView';
import StockAnalysisView from './components/StockAnalysisView';
import SignalHistoryView from './components/SignalHistoryView';
import InstitutionalFlowView from './components/InstitutionalFlowView';
import AppearanceControls from './components/AppearanceControls';
import FontScaleControls from './components/FontScaleControls';
import ValueBadge from './components/ValueBadge';
import { playTone, setSoundEnabled } from './utils/soundFx';
import { formatINR, formatPercent as sharedFormatPercent } from './utils/formatters';

const DEFAULT_THEME = 'codecore';

function readAppearancePreference(key, fallback) {
  try { return window.localStorage.getItem(key) ?? fallback; }
  catch { return fallback; }
}

const navigation = [
  { id: 'screener', label: 'Overview', icon: LayoutDashboard, section: 'WORKSPACE' },
  { id: 'history', label: 'History', icon: History },
  { id: 'flow-watch', label: 'Buying & selling', icon: Volume2 },
  { id: 'stock-analysis', label: 'Stock analysis', icon: Search },
  { id: 'regime', label: 'Market mood', icon: Compass },
  { id: 'backtest', label: 'Test a strategy', icon: BarChart3 },
  { id: 'portfolio', label: 'Portfolio', icon: Wallet },
];
const marketNavigation = [
  { id: 'swing', label: 'Swing Trading', icon: LineChart },
  { id: 'intraday', label: 'Intraday', icon: CandlestickChart },
  { id: 'options', label: 'Options', icon: Activity },
];
const settingsNavigation = [{ id: 'settings', label: 'Settings', icon: Settings }];
const MANUAL_PORTFOLIO_KEY = 'marketvoice-manual-portfolio-v1';
const LEGACY_MANUAL_PORTFOLIO_KEY = 'swing-trading-manual-portfolio-v1';
const HISTORY_HOLDING_DAYS_KEY = 'marketvoice-history-holding-days-v1';
let liveStatusRequest = null;

function readHistoryHoldingDays() {
  try { return window.localStorage.getItem(HISTORY_HOLDING_DAYS_KEY) === '30' ? 30 : 15; }
  catch { return 15; }
}

function fetchLiveStatusOnce() {
  if (!liveStatusRequest) {
    liveStatusRequest = fetch('/api/market/live/status')
      .then(async response => {
        if (!response.ok) throw new Error(`Live status request failed (${response.status})`);
        return response.json();
      })
      .finally(() => { liveStatusRequest = null; });
  }
  return liveStatusRequest;
}

function readManualPortfolio() {
  try {
    const savedValue = window.localStorage.getItem(MANUAL_PORTFOLIO_KEY)
      ?? window.localStorage.getItem(LEGACY_MANUAL_PORTFOLIO_KEY)
      ?? '[]';
    const saved = JSON.parse(savedValue);
    return Array.isArray(saved) ? saved.filter(item => item && typeof item.symbol === 'string' && Number(item.quantity) > 0 && Number(item.average_price) > 0) : [];
  } catch {
    return [];
  }
}

function formatPrice(value, fallback = '—') {
  return formatINR(value, fallback);
}

function formatCompact(value) {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? '—' : new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 2 }).format(number);
}

function simpleStrategyName(strategy, fallback = '') {
  const names = {
    trend_pullback: 'Buy a dip in a rising share',
    relative_strength: 'Shares doing better than Nifty',
    capitulation_reversal: 'Possible bounce after a sharp fall',
    volatility_squeeze: 'Breakout after a quiet period',
    multi_factor: 'Several positive checks agree',
  };
  return names[strategy] || fallback || strategy || 'Share to review';
}

function simpleSignalStatus(status) {
  const labels = {
    REVIEW_NEWS_UNAVAILABLE: 'News could not be checked',
    AVOID_PENDING_EVENT_REVIEW: 'Read important news first',
    REVIEW_HEADLINES: 'Read recent news first',
    PENDING_NEWS_REVIEW: 'News check needed',
  };
  return labels[status] || status;
}

function formatPercent(value, providerUsesPercent = false) {
  return sharedFormatPercent(value, { fraction: !providerUsesPercent });
}

function formatDividendYield(value) {
  const number = Number(value);
  if (value == null || !Number.isFinite(number)) return '—';
  // Yahoo's dividendYield is normally fractional, but some NSE records return percent units.
  return sharedFormatPercent(Math.abs(number) > 0.25 ? number : number * 100);
}

function formatMoney(value, currency = 'INR') {
  const number = Number(value);
  if (value == null || !Number.isFinite(number)) return '—';
  const safeCurrency = /^[A-Z]{3}$/.test(currency || '') ? currency : 'INR';
  return safeCurrency === 'INR' ? formatINR(number) : new Intl.NumberFormat('en-IN', { style: 'currency', currency: safeCurrency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(number);
}

const SETUP_CHART_LABELS = {
  trend_pullback: 'Trend pullback',
  relative_strength: 'Relative strength',
  capitulation_reversal: 'Reversal',
  volatility_squeeze: 'Squeeze',
  multi_factor: 'Multi-factor',
};

function OverviewVisuals({ candles = [], breadthPct, signals = [], onOpenMood, onOpenSwing }) {
  const closes = candles.map(candle => Number(candle.close)).filter(Number.isFinite);
  const width = 760;
  const height = 230;
  const left = 12;
  const right = width - 12;
  const top = 14;
  const bottom = height - 24;
  const low = closes.length ? Math.min(...closes) : 0;
  const high = closes.length ? Math.max(...closes) : 1;
  const spread = high - low || 1;
  const points = closes.map((value, index) => {
    const x = left + (index / Math.max(1, closes.length - 1)) * (right - left);
    const y = bottom - ((value - low) / spread) * (bottom - top);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const linePath = points.map((point, index) => `${index ? 'L' : 'M'} ${point}`).join(' ');
  const areaPath = points.length ? `${linePath} L ${right} ${bottom} L ${left} ${bottom} Z` : '';
  const firstClose = closes[0];
  const lastClose = closes.at(-1);
  const periodChange = firstClose && lastClose ? ((lastClose - firstClose) / firstClose) * 100 : null;
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const chartDates = [candles[0]?.time, candles[Math.floor(candles.length / 2)]?.time, candles.at(-1)?.time]
    .map(value => value ? monthNames[Number(value.slice(5, 7)) - 1] || '' : '');
  const pct = breadthPct == null || !Number.isFinite(Number(breadthPct)) ? null : Math.max(0, Math.min(100, Number(breadthPct)));
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strategyCounts = signals.reduce((counts, signal) => {
    const id = signal.strategy || 'other';
    counts[id] = (counts[id] || 0) + 1;
    return counts;
  }, {});
  const setupRows = Object.entries(strategyCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const maxSetups = Math.max(1, ...setupRows.map(([, count]) => count));

  return <section className="dashboard-visuals" aria-label="Visual market dashboard">
    <article className="dashboard-chart-card nifty-trend-card">
      <div className="dashboard-chart-head"><div><span className="chart-kicker">NIFTY 50</span><h2>Market trend</h2></div><span className={`chart-change ${periodChange == null ? '' : periodChange >= 0 ? 'positive' : 'negative'}`}>{periodChange == null ? '—' : `${periodChange >= 0 ? '↗' : '↘'} ${formatPercent(periodChange, true)}`}</span></div>
      {closes.length > 1 ? <>
        <div className="nifty-chart-wrap"><svg className="nifty-trend-chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label={`Nifty 50 three month trend, from ${formatPrice(firstClose)} to ${formatPrice(lastClose)}`}>
          <defs><linearGradient id="niftyTrendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--chart-line)" stopOpacity=".32" /><stop offset="100%" stopColor="var(--chart-line)" stopOpacity="0" /></linearGradient></defs>
          {[.25, .5, .75].map(level => <line key={level} x1={left} x2={right} y1={top + (bottom - top) * level} y2={top + (bottom - top) * level} className="chart-grid-line" />)}
          <path d={areaPath} className="nifty-chart-area" />
          <path d={linePath} className="nifty-chart-line" />
          {points.length > 0 && <circle cx={points.at(-1).split(',')[0]} cy={points.at(-1).split(',')[1]} r="5" className="nifty-chart-dot" />}
        </svg></div>
        <div className="nifty-chart-dates"><span>{chartDates[0]}</span><span>{chartDates[1]}</span><span>{chartDates[2]}</span></div>
      </> : <div className="chart-empty-state"><span className="chart-loader-mark" />{candles.length ? 'Chart loading' : 'Chart unavailable'}</div>}
    </article>

    <button type="button" className="dashboard-chart-card breadth-chart-card" onClick={onOpenMood} aria-label="Open market mood details">
      <div className="dashboard-chart-head"><div><span className="chart-kicker">MARKET BREADTH</span><h2>Trend health</h2></div><ArrowUpRight size={18} /></div>
      <div className="breadth-chart-content">
        <svg className="breadth-donut" viewBox="0 0 150 150" role="img" aria-label={pct == null ? 'Market breadth unavailable' : `${pct.toFixed(0)} percent of tracked shares above their 50-day average`}>
          <circle className="breadth-donut-track" cx="75" cy="75" r={radius} />
          {pct != null && <circle className="breadth-donut-value" cx="75" cy="75" r={radius} strokeDasharray={`${circumference}`} strokeDashoffset={`${circumference * (1 - pct / 100)}`} />}
          <text x="75" y="73" className="breadth-donut-number">{pct == null ? '—' : `${pct.toFixed(0)}%`}</text>
          <text x="75" y="95" className="breadth-donut-label">above 50D</text>
        </svg>
        <div className="breadth-legend"><span><i className="breadth-legend-above" /> Above average</span><span><i className="breadth-legend-below" /> At or below</span><small>Tracked shares</small></div>
      </div>
    </button>

    <button type="button" className="dashboard-chart-card setup-mix-card" onClick={onOpenSwing} aria-label="Open swing trading setups">
      <div className="dashboard-chart-head"><div><span className="chart-kicker">SWING IDEAS</span><h2>Setup mix</h2></div><span className="setup-total-count">{signals.length}</span></div>
      {setupRows.length ? <div className="setup-mix-bars">{setupRows.map(([id, count], index) => <div className="setup-mix-row" key={id}>
        <div className="setup-mix-label"><span>{SETUP_CHART_LABELS[id] || 'Other'}</span><b>{count}</b></div>
        <span className="setup-mix-track"><i style={{ '--bar-scale': count / maxSetups, '--bar-delay': `${index * 90}ms` }} /></span>
      </div>)}</div> : <div className="chart-empty-state"><span className="chart-empty-ring" />No setups yet</div>}
    </button>
  </section>;
}

function ResearchSection({ title, source, status, children }) {
  return <section className="research-section">
    <div className="research-section-heading"><div><strong>{title}</strong><span>{source}</span></div>{status && <small>{status.replace(/_/g, ' ')}</small>}</div>
    {children}
  </section>;
}

function classifyMetric(section, label, value, raw = {}) {
  const number = Number(value);
  if (section === 'technical') {
    if (label === 'Trend') return /bullish|above ema/i.test(String(value)) ? 'good' : 'bad';
    if (label === 'Average price trend') {
      if (raw.ema20 == null || raw.ema50 == null || raw.ema200 == null || raw.close == null) return 'neutral';
      if (raw.close > raw.ema20 && raw.ema20 > raw.ema50 && raw.ema50 > raw.ema200) return 'good';
      return raw.close < raw.ema50 ? 'bad' : 'neutral';
    }
    if (label === 'Recent price strength') return number >= 45 && number <= 65 ? 'good' : number > 70 || number < 35 ? 'bad' : 'neutral';
    if (label === 'Trend strength') return number >= 25 ? 'good' : number < 15 ? 'watch' : 'neutral';
    if (label === 'Usual daily price movement') return raw.atr14_pct >= 5 ? 'watch' : 'neutral';
    if (label === 'Trading activity vs usual') return raw.volume_ratio20 >= 1.5 ? 'good' : raw.volume_ratio20 < 0.7 ? 'watch' : 'neutral';
    if (label === 'Price change over 1 and 3 months') {
      const returns = String(value).match(/-?\d+(?:\.\d+)?/g)?.map(Number) || [];
      return returns.length === 2 && returns.every((item) => item > 0) ? 'good' : returns.length === 2 && returns.every((item) => item < 0) ? 'bad' : 'neutral';
    }
    if (label === 'Performance vs Nifty') return number > 0 ? 'good' : number < 0 ? 'bad' : 'neutral';
  }

  if (section === 'fundamental') {
    if (['Earnings for each share', 'Revenue growth', 'Earnings growth', 'Profit left from sales', 'Operating margin', 'Cash left after spending'].includes(label)) {
      const rawValue = label === 'Earnings for each share' ? raw.eps_ttm
        : label === 'Revenue growth' ? raw.revenue_growth
          : label === 'Earnings growth' ? raw.earnings_growth
            : label === 'Profit left from sales' ? raw.profit_margin
              : label === 'Operating margin' ? raw.operating_margin : raw.free_cash_flow;
      return rawValue > 0 ? 'good' : rawValue < 0 ? 'bad' : 'neutral';
    }
    if (label === 'Profit earned on shareholder money') return raw.return_on_equity >= 0.15 ? 'good' : raw.return_on_equity < 0 ? 'bad' : 'neutral';
    if (label === 'Debt compared with shareholder money') return raw.debt_to_equity <= 100 ? 'good' : raw.debt_to_equity > 200 ? 'bad' : 'watch';
    if (label === 'Money available for near-term bills') return raw.current_ratio >= 1.5 ? 'good' : raw.current_ratio < 1 ? 'bad' : 'neutral';
  }
  return 'neutral';
}

function ResearchGrid({ items }) {
  const available = items.filter(([, value]) => value !== '—');
  if (!available.length) return <p className="research-empty">Provider did not return these fields.</p>;
  return <>
    <p className="research-signal-legend"><span className="signal-good">Green: looks good</span><span className="signal-bad">Red: needs care</span><span>Grey: extra information</span></p>
    <div className="research-grid">{available.map(([label, value, tone = 'neutral']) => <div className={`research-value signal-card-${tone}`} key={label}>
      <span>{label}</span><strong>{value}</strong><small className={`research-signal-label signal-${tone}`}>{tone === 'good' ? 'Looks good' : tone === 'bad' ? 'Needs care' : tone === 'watch' ? 'Keep an eye' : 'For information'}</small>
    </div>)}</div>
  </>;
}

function StockResearchDetails({ data, loading, error }) {
  if (loading) return <div className="research-loading"><RefreshCw size={15} /> Loading recent news, price trends and company details…</div>;
  if (error && !data) return <div className="setup-rationale research-error">Stock details could not load: {error}</div>;
  if (!data) return null;

  const technical = data.technical || {};
  const fundamentals = data.fundamentals || {};
  const news = data.news || {};
  const technicalValue = (label, value) => [label, value, classifyMetric('technical', label, value, technical)];
  const fundamentalValue = (label, value) => [label, value, classifyMetric('fundamental', label, value, fundamentals)];
  const technicalItems = [
    technicalValue('Last daily close', formatPrice(technical.close)),
    technicalValue('Trend', technical.trend || '—'),
    technicalValue('Average price trend', technical.ema20 != null ? `${formatPrice(technical.ema20)} / ${formatPrice(technical.ema50)} / ${formatPrice(technical.ema200)}` : '—'),
    technicalValue('Recent price strength', technical.rsi14 != null ? technical.rsi14.toFixed(2) : '—'),
    technicalValue('Trend strength', technical.adx14 != null ? technical.adx14.toFixed(2) : '—'),
    technicalValue('Usual daily price movement', technical.atr14_pct != null ? `${formatPercent(technical.atr14_pct, true)} of price` : '—'),
    technicalValue('Trading activity vs usual', technical.volume_ratio20 != null ? `${technical.volume_ratio20}×` : '—'),
    technicalValue('Price change over 1 and 3 months', technical.return20_pct != null && technical.return63_pct != null ? `${formatPercent(technical.return20_pct, true)} / ${formatPercent(technical.return63_pct, true)}` : '—'),
    technicalValue('Performance vs Nifty', technical.mansfield_rs63 != null ? formatPercent(technical.mansfield_rs63, true) : '—'),
    technicalValue('Data date', technical.as_of || '—'),
  ];
  const currency = fundamentals.currency || 'INR';
  const fundamentalItems = [
    fundamentalValue('Company size (market value)', formatMoney(fundamentals.market_cap, currency)),
    fundamentalValue('Share price vs past earnings', fundamentals.trailing_pe != null ? fundamentals.trailing_pe.toFixed(2) : '—'),
    fundamentalValue('Share price vs expected earnings', fundamentals.forward_pe != null ? fundamentals.forward_pe.toFixed(2) : '—'),
    fundamentalValue('Share price vs company assets', fundamentals.price_to_book != null ? fundamentals.price_to_book.toFixed(2) : '—'),
    fundamentalValue('Earnings for each share', formatMoney(fundamentals.eps_ttm, currency)),
    fundamentalValue('Dividend yield', formatDividendYield(fundamentals.dividend_yield)),
    fundamentalValue('Profit earned on shareholder money', formatPercent(fundamentals.return_on_equity)),
    fundamentalValue('Revenue growth', formatPercent(fundamentals.revenue_growth)),
    fundamentalValue('Earnings growth', formatPercent(fundamentals.earnings_growth)),
    fundamentalValue('Profit left from sales', formatPercent(fundamentals.profit_margin)),
    fundamentalValue('Operating margin', formatPercent(fundamentals.operating_margin)),
    fundamentalValue('Debt compared with shareholder money', formatPercent(fundamentals.debt_to_equity, true)),
    fundamentalValue('Money available for near-term bills', fundamentals.current_ratio != null ? fundamentals.current_ratio.toFixed(2) : '—'),
    fundamentalValue('Price movement compared with market', fundamentals.beta != null ? fundamentals.beta.toFixed(2) : '—'),
    fundamentalValue('Total revenue', formatMoney(fundamentals.total_revenue, currency)),
    fundamentalValue('Cash left after spending', formatMoney(fundamentals.free_cash_flow, currency)),
  ];

  const fetchedAt = data.retrieved_at ? new Date(data.retrieved_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) : 'now';
  return <div className="stock-research-details">
    <p className="research-data-stamp">Company and price information last checked {fetchedAt} IST. Some figures may be delayed.</p>
    <ResearchSection title="Recent company news" source={news.source || 'News provider'} status={news.status}>
      <p className="research-note">News from the last {news.lookback_hours || 72} hours. Headlines are a quick check; open the full story and company updates for context.</p>
      {news.event_risk && <div className="research-risk">A headline may describe an important event. Read the full story before deciding.</div>}
      {news.headlines?.length ? <ul className="research-news-list">{news.headlines.map((item, index) => <li key={`${item.title}-${index}`}><div>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}</div><small>{[item.source, item.published_at ? new Date(item.published_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) : null].filter(Boolean).join(' · ')}</small></li>)}</ul> : <p className="research-empty">{news.status === 'unavailable' ? 'News could not be fetched. Check current company announcements manually.' : 'No recent headlines returned for this symbol.'}</p>}
    </ResearchSection>

    <ResearchSection title="Price and trend checks" source={technical.source || 'Daily market data'} status={technical.status}>
      {technical.error && <p className="research-empty">{technical.error}</p>}
      <p className="research-note">These are clues from recent prices and trading activity, not predictions.</p>
      <ResearchGrid items={technicalItems} />
    </ResearchSection>

    <ResearchSection title={fundamentals.company_name || 'Company details'} source={fundamentals.source || 'Company data'} status={fundamentals.status}>
      {(fundamentals.sector || fundamentals.industry) && <p className="research-note">{[fundamentals.sector, fundamentals.industry].filter(Boolean).join(' · ')}</p>}
      {fundamentals.error && <p className="research-empty">{fundamentals.error}</p>}
      <ResearchGrid items={fundamentalItems} />
    </ResearchSection>
    {error && <p className="research-empty">Some research sections did not load: {error}</p>}
  </div>;
}

function PortfolioView({ data, loading, saving, storageStatus, saveError, error, onRefresh, onSaveHolding, onDeleteHolding, onSelectStock }) {
  const [entry, setEntry] = useState({ symbol: '', quantity: '', average_price: '' });
  const [editingSymbol, setEditingSymbol] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [symbolListLoaded, setSymbolListLoaded] = useState(false);
  const [symbolSearchOpen, setSymbolSearchOpen] = useState(false);
  const [symbolSearchError, setSymbolSearchError] = useState('');
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const holdings = data?.holdings || [];
  const totalValue = holdings.reduce((total, item) => total + (Number(item.current_value) || 0), 0);
  const totalInvestment = holdings.reduce((total, item) => total + (Number(item.invested_value) || 0), 0);
  const totalPnl = holdings.reduce((total, item) => total + (Number(item.unrealized_pnl) || 0), 0);
  const symbolQuery = entry.symbol.trim().toUpperCase().replace(/\.NS$/, '');
  const suggestions = useMemo(() => {
    if (!symbolQuery) return [];
    return stocks
      .filter(stock => stock.symbol.includes(symbolQuery) || (stock.name || '').toUpperCase().includes(symbolQuery))
      .sort((left, right) => {
        const leftPrefix = left.symbol.startsWith(symbolQuery) ? 0 : 1;
        const rightPrefix = right.symbol.startsWith(symbolQuery) ? 0 : 1;
        return leftPrefix - rightPrefix || left.symbol.localeCompare(right.symbol);
      })
      .slice(0, 8);
  }, [symbolQuery, stocks]);

  useEffect(() => {
    let active = true;
    fetch('/api/symbols')
      .then(async response => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Stock symbols could not be loaded.');
        if (active) setStocks(result.stocks || (result.symbols || []).map(symbol => ({ symbol, name: symbol })));
      })
      .catch(() => {})
      .finally(() => { if (active) setSymbolListLoaded(true); });
    return () => { active = false; };
  }, []);

  const selectStock = stock => {
    setEntry(current => ({ ...current, symbol: stock.symbol }));
    setSymbolSearchOpen(false);
    setSymbolSearchError('');
    setActiveSuggestion(-1);
  };

  const submitHolding = event => {
    event.preventDefault();
    const exactMatch = stocks.find(stock => stock.symbol === symbolQuery || (stock.name || '').trim().toUpperCase() === symbolQuery);
    if (symbolListLoaded && stocks.length && !exactMatch) {
      setSymbolSearchError('Type a ticker or company name, then choose a stock from the suggestions.');
      setSymbolSearchOpen(true);
      return;
    }
    const symbol = exactMatch?.symbol || symbolQuery;
    if (!symbol) return;
    onSaveHolding({ symbol, quantity: Number(entry.quantity), average_price: Number(entry.average_price) }, editingSymbol);
    setEntry({ symbol: '', quantity: '', average_price: '' });
    setEditingSymbol(null);
    setSymbolSearchError('');
  };
  const startEdit = item => {
    setEditingSymbol(item.symbol);
    setEntry({ symbol: item.symbol, quantity: String(item.quantity), average_price: String(item.average_price) });
    setSymbolSearchError('');
  };
  return <section className="module-page portfolio-page">
    <div className="module-heading portfolio-hero"><div className="portfolio-hero-copy"><div className="eyebrow subtle-eyebrow">YOUR SHARES · DAILY CHECK</div><h1>Your portfolio</h1><p>See your holdings, today’s estimated value and simple trend checks in one place.</p><div className="portfolio-hero-pills"><span>{holdings.length} {holdings.length === 1 ? 'share' : 'shares'} tracked</span><span>Prices can be delayed</span></div></div>
      <div className="portfolio-actions"><span className={`portfolio-connection ${storageStatus === 'saved' ? 'connected' : ''}`}><i />{storageStatus === 'saving' ? 'Saving changes…' : storageStatus === 'saved' ? 'Saved on this app' : storageStatus === 'loading' ? 'Loading saved portfolio…' : 'Browser copy only'}</span><button className="secondary-button" onClick={onRefresh} disabled={loading || saving}>{loading ? <RefreshCw size={14} className="spin" /> : <RefreshCw size={14} />}{loading ? 'Reviewing' : 'Refresh analysis'}</button></div>
    </div>
    {holdings.length > 0 && <div className="portfolio-summary"><article><span>SHARES HELD</span><strong>{holdings.length}</strong><small>Tracked investments</small></article><article><span>MONEY INVESTED · EST.</span><strong>{formatPrice(totalInvestment)}</strong><small>Based on your average buy price</small></article><article><span>VALUE TODAY · EST.</span><strong>{formatPrice(totalValue)}</strong><small>Using the latest available prices</small></article><article className={totalPnl >= 0 ? 'portfolio-total-gain' : 'portfolio-total-loss'}><span>GAIN OR LOSS · EST.</span><strong>{totalPnl >= 0 ? '+' : '−'}{formatPrice(Math.abs(totalPnl))}</strong><small>{totalPnl >= 0 ? 'Overall unrealized gain' : 'Overall unrealized loss'}</small></article></div>}
    <form className="portfolio-entry" onSubmit={submitHolding}>
      <div className="portfolio-entry-heading"><span className="portfolio-entry-icon"><Wallet size={19} /></span><div><span className="eyebrow subtle-eyebrow">PORTFOLIO ACTION</span><h2>{editingSymbol ? 'Update a holding' : 'Add a holding'}</h2><p>Enter the NSE stock, number of shares and your average purchase price.</p></div></div>
      <label className="portfolio-symbol-field">Stock symbol
        <input
          value={entry.symbol}
          onChange={event => { setEntry(current => ({ ...current, symbol: event.target.value })); setSymbolSearchOpen(true); setSymbolSearchError(''); setActiveSuggestion(-1); }}
          onFocus={() => setSymbolSearchOpen(true)}
          onBlur={() => setSymbolSearchOpen(false)}
          onKeyDown={event => {
            if (event.key === 'ArrowDown' && suggestions.length) { event.preventDefault(); setSymbolSearchOpen(true); setActiveSuggestion(index => index < 0 ? 0 : (index + 1) % suggestions.length); }
            else if (event.key === 'ArrowUp' && suggestions.length) { event.preventDefault(); setSymbolSearchOpen(true); setActiveSuggestion(index => index < 0 ? suggestions.length - 1 : (index - 1 + suggestions.length) % suggestions.length); }
            else if (event.key === 'Enter' && symbolSearchOpen && suggestions.length && !stocks.some(stock => stock.symbol === symbolQuery)) { event.preventDefault(); selectStock(stocks.find(stock => stock.symbol === symbolQuery || (stock.name || '').trim().toUpperCase() === symbolQuery) || suggestions[activeSuggestion] || suggestions[0]); }
            else if (event.key === 'Escape') setSymbolSearchOpen(false);
          }}
          placeholder="Search ticker or company, e.g. IRCTC"
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={symbolSearchOpen && suggestions.length > 0}
          aria-controls="portfolio-symbol-suggestions"
          required
          maxLength={30}
        />
        {symbolSearchOpen && symbolQuery && <div className="portfolio-symbol-suggestions" id="portfolio-symbol-suggestions" role="listbox">
          {suggestions.length ? suggestions.map((stock, index) => <button key={stock.symbol} type="button" role="option" aria-selected={index === activeSuggestion} className={index === activeSuggestion ? 'active' : ''} onMouseDown={event => event.preventDefault()} onClick={() => selectStock(stock)}>
            <strong>{stock.symbol}</strong><span>{stock.name || stock.symbol}</span>
          </button>) : <span className="portfolio-symbol-empty">{symbolListLoaded ? 'No NSE stock matches that search.' : 'Loading NSE stock list…'}</span>}
        </div>}
        {symbolSearchError && <small className="portfolio-symbol-error">{symbolSearchError}</small>}
      </label>
      <label>Quantity<input type="number" value={entry.quantity} onChange={event => setEntry(current => ({ ...current, quantity: event.target.value }))} min="0.000001" step="any" placeholder="Shares" required /></label>
      <label>Average buy price<input type="number" value={entry.average_price} onChange={event => setEntry(current => ({ ...current, average_price: event.target.value }))} min="0.01" step="any" placeholder="₹ per share" required /></label>
      <div className="portfolio-entry-actions"><button className="primary-button" type="submit" disabled={loading || saving}>{saving ? 'Saving…' : editingSymbol ? 'Save changes' : 'Add stock'}</button>{editingSymbol && <button className="secondary-button" type="button" disabled={saving} onClick={() => { setEditingSymbol(null); setEntry({ symbol: '', quantity: '', average_price: '' }); setSymbolSearchError(''); setSymbolSearchOpen(false); }}>Cancel</button>}</div>
    </form>
    {error && <div className="portfolio-notice"><strong>{error}</strong></div>}
    {saveError && <div className="portfolio-notice"><strong>{saveError}</strong></div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Reviewing your shares</strong><span>Calculating daily trend checks…</span></div>
      : holdings.length === 0 ? <div className="empty-panel"><div className="empty-icon"><Wallet size={19} /></div><strong>Add your first stock</strong><span>Enter its NSE symbol, quantity and average buy price above. Your list is saved with this app.</span></div>
        : <>
          <div className="portfolio-list">{holdings.map((item, index) => {
            const analysis = item.analysis || {};
            const actionLabel = analysis.action === 'REVIEW_SELL' ? 'Review this share' : analysis.action === 'HOLD' ? 'No exit warning' : 'Not enough information';
            const actionClass = analysis.action === 'REVIEW_SELL' ? 'review-sell' : analysis.action === 'HOLD' ? 'hold' : 'unknown';
            return <article className="portfolio-card" key={`${item.display_symbol || item.symbol}-${index}`}>
              <div className="portfolio-card-heading"><div><span className="instrument-token">{(item.display_symbol || item.symbol || '?').slice(0, 1)}</span><div><button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ symbol: item.symbol, source: 'portfolio' })} aria-label={`View ${item.display_symbol || item.symbol} stock research`}>{item.display_symbol || item.symbol}</button><small>Manual entry · Qty {item.quantity ?? '—'}</small></div></div><div className="portfolio-card-controls"><span className={`portfolio-action ${actionClass}`}>{actionLabel}</span><button type="button" disabled={saving} onClick={() => startEdit(item)}>Edit</button><button type="button" disabled={saving} onClick={() => onDeleteHolding(item.symbol)}>Remove</button></div></div>
              <div className="portfolio-values"><div><span>PRICE TODAY</span><b>{formatPrice(item.last_price)}</b></div><div><span>AVERAGE BUY PRICE</span><b>{formatPrice(item.average_price)}</b></div><div><span>SHARES</span><b>{item.quantity}</b></div><div><span>MONEY INVESTED · EST.</span><b>{formatPrice(item.invested_value)}</b></div><div><span>VALUE TODAY · EST.</span><b>{formatPrice(item.current_value)}</b></div><div><span>GAIN OR LOSS · EST.</span><ValueBadge positive={Number(item.unrealized_pnl) >= 0}>{formatPrice(Math.abs(Number(item.unrealized_pnl) || 0))}</ValueBadge></div></div>
              {analysis.action !== 'INSUFFICIENT_DATA' && <div className="portfolio-indicators"><span>20-day average price <b>{formatPrice(analysis.ema20)}</b></span><span>50-day average price <b>{formatPrice(analysis.ema50)}</b></span><span>Recent price strength <b>{analysis.rsi14 == null ? '—' : Number(analysis.rsi14).toFixed(2)}</b></span><span>Price change in 20 days <b className={Number(analysis.return20_pct) >= 0 ? 'positive' : 'negative'}>{formatPercent(analysis.return20_pct, true)}</b></span><small>Price date: {analysis.as_of || '—'}</small></div>}
              <ul className="portfolio-reasons">{(analysis.reasons || []).map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>
              <div className={`portfolio-verdict ${actionClass}`}><div><span>SIMPLE TAKEAWAY</span><strong>{actionLabel}</strong></div><p>{analysis.beginner_verdict || 'Is review me agla kadam samajhne ke liye abhi kaafi jaankari nahi hai.'}</p></div>
            </article>;
          })}</div>
          <p className="portfolio-disclaimer">{data?.disclaimer || 'Technical research screen only, not personalized financial advice.'} Price history comes from Yahoo Finance; signals may not account for your investment horizon, taxes, corporate actions, or personal risk limits.</p>
        </>}
  </section>;
}

export default function App() {
  const [theme, setTheme] = useState(() => readAppearancePreference('marketvoice-theme', DEFAULT_THEME));
  const [dim, setDim] = useState(() => readAppearancePreference('marketvoice-dim', 'normal'));
  const [grayscale, setGrayscale] = useState(() => readAppearancePreference('marketvoice-grayscale', 'false') === 'true');
  const [decorativeMotion, setDecorativeMotion] = useState(() => readAppearancePreference('marketvoice-motion-v2', 'true') === 'true');
  const [fontScale, setFontScale] = useState(() => Number(readAppearancePreference('marketvoice-font-scale', '100')) || 100);
  const [activeTab, setActiveTab] = useState('screener');
  const [regimeData, setRegimeData] = useState(null);
  const [liveStatus, setLiveStatus] = useState(null);
  const [liveQuote, setLiveQuote] = useState(null);
  const [liveQuoteError, setLiveQuoteError] = useState(null);
  const [screenerData, setScreenerData] = useState(null);
  const [niftyCandles, setNiftyCandles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [historyHoldingDays, setHistoryHoldingDays] = useState(readHistoryHoldingDays);
  const [strategyFilter, setStrategyFilter] = useState('ALL');
  const [quickFilter, setQuickFilter] = useState('ALL');
  const [viewMode, setViewMode] = useState('table');
  const [selectedChartTrade, setSelectedChartTrade] = useState(null);
  const [researchDetails, setResearchDetails] = useState(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState(null);
  const [soundOn, setSoundOn] = useState(false);
  const [toast, setToast] = useState(null);
  const [copiedSymbol, setCopiedSymbol] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState(null);
  const [manualHoldings, setManualHoldings] = useState(readManualPortfolio);
  const [portfolioInitialized, setPortfolioInitialized] = useState(false);
  const [portfolioSaving, setPortfolioSaving] = useState(false);
  const [portfolioStorageStatus, setPortfolioStorageStatus] = useState('loading');
  const [portfolioSaveError, setPortfolioSaveError] = useState(null);
  const [currentTime, setCurrentTime] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const searchInputRef = useRef(null);
  const openStockResearch = (stock, source = 'research') => {
    const details = typeof stock === 'string' ? { symbol: stock } : stock;
    if (!details?.symbol) return;
    setSelectedChartTrade({ ...details, source: details.source || source });
  };

  useEffect(() => {
    let active = true;
    fetch('/api/chart/%5ENSEI?period=3mo', { cache: 'no-store' })
      .then(async response => {
        if (!response.ok) throw new Error('Nifty chart data unavailable');
        return response.json();
      })
      .then(result => { if (active) setNiftyCandles(result.candles || []); })
      .catch(() => { if (active) setNiftyCandles([]); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.page = activeTab;
    root.dataset.dim = dim;
    root.dataset.grayscale = grayscale ? 'on' : 'off';
    root.dataset.decorativeMotion = decorativeMotion ? 'on' : 'off';
    root.dataset.fontScale = String(fontScale);
    const themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.content = theme === 'codecore' ? '#0d151e' : theme === 'light' ? '#ffffff' : theme === 'auto' && window.matchMedia('(prefers-color-scheme: light)').matches ? '#ffffff' : '#111318';
    try {
      window.localStorage.setItem('marketvoice-theme', theme);
      window.localStorage.setItem('marketvoice-dim', dim);
      window.localStorage.setItem('marketvoice-grayscale', String(grayscale));
      window.localStorage.setItem('marketvoice-motion-v2', String(decorativeMotion));
      window.localStorage.setItem('marketvoice-font-scale', String(fontScale));
    } catch { /* Preferences remain usable for this session when storage is unavailable. */ }
  }, [theme, activeTab, dim, grayscale, decorativeMotion, fontScale]);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return undefined;
    const updateKeyboardState = () => {
      document.documentElement.dataset.keyboardOpen = viewport.height < window.innerHeight * 0.72 ? 'true' : 'false';
    };
    viewport.addEventListener('resize', updateKeyboardState);
    updateKeyboardState();
    return () => viewport.removeEventListener('resize', updateKeyboardState);
  }, []);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 900px)');
    const syncCardView = () => { if (query.matches) setViewMode('grid'); };
    syncCardView();
    query.addEventListener?.('change', syncCardView);
    return () => query.removeEventListener?.('change', syncCardView);
  }, []);

  useEffect(() => {
    let active = true;
    const loadSavedPortfolio = async () => {
      try {
        const response = await fetch('/api/portfolio/manual', { cache: 'no-store' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Saved portfolio could not be loaded.');
        let holdings = result.holdings || [];
        if (!holdings.length && manualHoldings.length) {
          const migration = await fetch('/api/portfolio/manual', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ holdings: manualHoldings }),
          });
          const migrated = await migration.json();
          if (!migration.ok) throw new Error(migrated.detail || 'Existing browser portfolio could not be migrated.');
          holdings = migrated.holdings || manualHoldings;
        }
        if (active) {
          setManualHoldings(holdings);
          setPortfolioStorageStatus('saved');
          setPortfolioSaveError(null);
        }
      } catch (loadError) {
        if (active) {
          setPortfolioStorageStatus('local');
          setPortfolioSaveError(`Server storage is unavailable; using this browser's saved copy. ${loadError.message || ''}`);
        }
      } finally {
        if (active) setPortfolioInitialized(true);
      }
    };
    loadSavedPortfolio();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const updateTime = () => setCurrentTime(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isMarketOpen = useMemo(() => {
    if (typeof liveStatus?.market_open === 'boolean') return liveStatus.market_open;
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Kolkata', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date());
    const get = type => parts.find(part => part.type === type)?.value;
    const day = get('weekday');
    const time = Number(get('hour')) * 100 + Number(get('minute'));
    return day !== 'Sat' && day !== 'Sun' && time >= 915 && time <= 1530;
  }, [currentTime, liveStatus?.market_open]);

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
      try {
        const historyResponse = await fetch('/api/history/capture', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ signals: data.signals || [], max_holding_days: historyHoldingDays }),
        });
        const historyResult = await historyResponse.json();
        if (!historyResponse.ok) throw new Error(historyResult.detail || 'History save failed.');
        showToast(`Scan complete · ${data.signals?.length || 0} setups · ${historyResult.inserted} new saved to History`, 'success');
      } catch (historyError) {
        console.error('Unable to save scan results to history', historyError);
        showToast(`Scan complete · ${data.signals?.length || 0} setups · History save failed`, 'warning');
      }
    } catch (error) {
      console.error('Failed to run screener', error);
      playTone('alert');
      showToast('Market scan could not be completed', 'warning');
    } finally { setLoading(false); }
  };
  useEffect(() => {
    if (!portfolioInitialized) return;
    try { window.localStorage.setItem(MANUAL_PORTFOLIO_KEY, JSON.stringify(manualHoldings)); }
    catch (error) { console.warn('Could not save manual portfolio in this browser', error); }
  }, [manualHoldings, portfolioInitialized]);
  useEffect(() => {
    try { window.localStorage.setItem(HISTORY_HOLDING_DAYS_KEY, String(historyHoldingDays)); }
    catch (error) { console.warn('Could not save the history exit period in this browser', error); }
  }, [historyHoldingDays]);
  const loadPortfolio = async (_forceRefresh = false, rows = manualHoldings) => {
    setPortfolioLoading(true);
    setPortfolioError(null);
    if (!rows.length) {
      const todayIst = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
      setPortfolioData({ holdings: [], source: 'Manual entries', analysis_as_of: `${todayIst}T00:00:00+05:30`, disclaimer: 'Technical research screen only, not personalized financial advice.' });
      setPortfolioLoading(false);
      return;
    }
    try {
      const response = await fetch('/api/portfolio/manual-review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings: rows }),
        cache: 'no-store',
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Manual portfolio analysis could not be loaded.');
      setPortfolioData(data);
    } catch (error) {
      setPortfolioError(error.message || 'Manual portfolio analysis could not be loaded.');
    } finally { setPortfolioLoading(false); }
  };
  const saveManualHolding = (holding, oldSymbol = null) => {
    const next = manualHoldings.filter(item => item.symbol !== oldSymbol && item.symbol !== holding.symbol);
    next.push(holding);
    persistManualHoldings(next);
  };
  const persistManualHoldings = async rows => {
    setPortfolioSaving(true);
    setPortfolioStorageStatus('saving');
    setPortfolioSaveError(null);
    try {
      const response = await fetch('/api/portfolio/manual', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings: rows }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Portfolio changes could not be saved.');
      const saved = result.holdings || rows;
      setManualHoldings(saved);
      setPortfolioStorageStatus('saved');
      loadPortfolio(false, saved);
    } catch (saveError) {
      setManualHoldings(rows);
      setPortfolioStorageStatus('local');
      setPortfolioSaveError(`Changes remain saved in this browser, but server storage failed: ${saveError.message || 'unknown error'}`);
      loadPortfolio(false, rows);
    } finally { setPortfolioSaving(false); }
  };
  const deleteManualHolding = symbol => {
    const next = manualHoldings.filter(item => item.symbol !== symbol);
    persistManualHoldings(next);
  };
  useEffect(() => { loadRegime(); runScreener(false); }, []);
  useEffect(() => {
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
    const reviewedDate = portfolioData?.analysis_as_of?.slice(0, 10);
    if (activeTab === 'portfolio' && portfolioInitialized && !portfolioLoading && !portfolioError && (!portfolioData || reviewedDate !== today)) loadPortfolio(false);
  }, [activeTab, portfolioInitialized, portfolioData, portfolioLoading, portfolioError, currentTime]);
  useEffect(() => {
    let active = true;
    let timer;
    const refreshStatus = async () => {
      try {
        const status = await fetchLiveStatusOnce();
        if (active) {
          setLiveStatus(status);
          const untilNextOpen = status.market_open ? 5000 : status.next_market_open_at ? Date.parse(status.next_market_open_at) - Date.now() + 1000 : 60000;
          timer = window.setTimeout(refreshStatus, Math.max(1000, untilNextOpen));
          return;
        }
      } catch (error) { console.error('Unable to check IIFL feed status', error); }
      if (active) timer = window.setTimeout(refreshStatus, 30000);
    };
    refreshStatus();
    return () => { active = false; window.clearTimeout(timer); };
  }, []);
  useEffect(() => {
    if (!liveStatus?.authenticated) return undefined;
    let active = true;
    let timer;
    const refreshQuote = async () => {
      try {
        const response = await fetch('/api/market/live/nifty', { cache: 'no-store' });
        if (!response.ok) {
          if (response.status === 401 && active) {
            setLiveQuote(null);
            setLiveStatus(status => ({ ...status, authenticated: false }));
            setLiveQuoteError('IIFL session expired. Connect again to resume live quotes.');
          } else if (active) {
            const detail = await response.json().catch(() => ({}));
            setLiveQuoteError(detail.detail || `IIFL quote request failed (${response.status}).`);
          }
          return;
        }
        const quote = await response.json();
        if (active) {
          setLiveQuote(quote);
          setLiveQuoteError(null);
        }
      } catch (error) {
        console.error('Unable to refresh IIFL NIFTY quote', error);
        if (active) setLiveQuoteError('Could not reach the IIFL quote service. Retrying automatically.');
      } finally {
        // Schedule the next request after this one finishes so slow responses
        // cannot pile up or arrive out of order.
        if (active && isMarketOpen) timer = window.setTimeout(refreshQuote, 1000);
      }
    };
    refreshQuote();
    return () => { active = false; window.clearTimeout(timer); };
  }, [liveStatus?.authenticated, isMarketOpen]);
  useEffect(() => {
    if (!selectedChartTrade?.symbol) return undefined;
    let active = true;
    setResearchDetails(null);
    setResearchError(null);
    setResearchLoading(true);
    fetch(`/api/stock/${encodeURIComponent(selectedChartTrade.symbol)}/research`)
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Stock research data is unavailable');
        return data;
      })
      .then(data => { if (active) setResearchDetails(data); })
      .catch(error => { if (active) setResearchError(error.message); })
      .finally(() => { if (active) setResearchLoading(false); });
    return () => { active = false; };
  }, [selectedChartTrade?.symbol]);
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
    const matchesQuick = quickFilter === 'ALL' || (quickFilter === 'OPTIMAL' && signal.regime_status === 'OPTIMAL') || (quickFilter === 'HIGH_RR' && (signal.risk_reward || 0) >= 2) || (quickFilter === 'HIGH_CONVICTION' && (signal.overall_score ?? signal.confidence_score ?? 0) >= 80);
    return matchesSearch && matchesStrategy && matchesQuick;
  }), [allSignals, searchQuery, strategyFilter, quickFilter]);
  const optimalCount = allSignals.filter(signal => signal.regime_status === 'OPTIMAL').length;
  const metrics = regimeData?.metrics || {};
  const liveChange = liveQuote?.change_pct;
  const quoteFresh = liveQuote?.tick_at && Date.now() - Date.parse(liveQuote.tick_at) < 10000;
  const hasLiveQuote = liveQuote?.price != null && Number.isFinite(Number(liveQuote.price));
  const rangeLow = Number(liveQuote?.low);
  const rangeHigh = Number(liveQuote?.high);
  const hasSessionRange = liveQuote?.low != null && liveQuote?.high != null && Number.isFinite(rangeLow) && Number.isFinite(rangeHigh) && rangeHigh > rangeLow;
  const sessionRangePosition = hasLiveQuote && hasSessionRange
    ? Math.max(0, Math.min(100, ((Number(liveQuote.price) - rangeLow) / (rangeHigh - rangeLow)) * 100))
    : null;
  const liveQuoteTime = (liveQuote?.tick_at || liveQuote?.received_at)
    ? new Date(liveQuote.tick_at || liveQuote.received_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
    : null;
  const istToday = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
  const iiflQuoteIsToday = Boolean(liveQuote?.tick_at && liveQuote.tick_at.slice(0, 10) === istToday);
  const displayedNiftyPrice = isMarketOpen && hasLiveQuote ? liveQuote.price : iiflQuoteIsToday ? liveQuote.price : metrics.nifty_close ?? liveQuote?.price;
  const selectTab = id => {
    setActiveTab(id);
    setMobileMenuOpen(false);
    playTone('click');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const handleCopySetup = signal => {
    const text = `SWING SETUP · ${signal.symbol}\nStatus: ${signal.trade_status || 'Review setup'}\nEntry: ${formatPrice(signal.entry_price)}\nStop: ${formatPrice(signal.stop_loss)}\nTarget 1: ${formatPrice(signal.target_1)}\nTarget 2: ${formatPrice(signal.target_2)}\nRisk/reward: 1:${Number(signal.risk_reward || 0).toFixed(2)}\nStrategy: ${signal.strategy_title}`;
    navigator.clipboard?.writeText(text);
    setCopiedSymbol(signal.symbol);
    playTone('blip');
    showToast(`${signal.symbol} setup copied`, 'success');
    window.setTimeout(() => setCopiedSymbol(null), 2500);
  };

  return <div className="spatial-app">
    {toast && <CyberToast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    {mobileMenuOpen && <div className="mobile-drawer-backdrop" onClick={() => setMobileMenuOpen(false)} aria-hidden="true" />}
    
    <aside className={`side-rail ${mobileMenuOpen ? 'mobile-open' : ''}`}>
      <div className="side-rail-header">
        <button className="brand-mark" aria-label="MarketVoice home" onClick={() => selectTab('screener')}><span className="brand-orb"><img className="brand-logo" src={appLogo} alt="" /></span><span className="brand-wordmark">MarketVoice</span></button>
        <button className="icon-button mobile-drawer-close" onClick={() => setMobileMenuOpen(false)} aria-label="Close menu"><X size={18} /></button>
      </div>
      <div className="rail-divider" />
      <div className="nav-group-label">WORKSPACE</div>
      <nav className="side-nav" aria-label="Primary navigation">
        {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'selected' : ''}`} onClick={() => selectTab(id)} title={label}>
          <Icon size={22} strokeWidth={1.8} /><span>{label}</span>
        </button>)}
      </nav>
      <div className="rail-divider rail-lower" />
      <div className="nav-group-label">MARKETS</div>
      <nav className="side-nav">
        {marketNavigation.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'selected' : ''}`} onClick={() => selectTab(id)} title={label}>
          <Icon size={22} strokeWidth={1.8} /><span>{label}</span>{id === 'swing' && <i className="nav-count">{filteredSignals.length}</i>}
        </button>)}
      </nav>
      <div className="rail-divider rail-lower" />
      <nav className="side-nav" aria-label="Settings navigation">
        {settingsNavigation.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'selected' : ''}`} onClick={() => selectTab(id)} title={label}>
          <Icon size={22} strokeWidth={1.8} /><span>{label}</span>
        </button>)}
      </nav>
      <div className="rail-spacer" />
    </aside>

    <div className="workspace">
      <header className="topbar">
        <div className="topbar-left">
          <button className="mobile-menu-toggle" onClick={() => setMobileMenuOpen(true)} aria-label="Open navigation menu">
            <Menu size={20} />
          </button>
        </div>
        <div className="topbar-actions">
          <div className={`session-pill ${isMarketOpen ? 'session-open' : ''}`}><span className="session-state"><span className="session-indicator" /><span>{isMarketOpen ? 'NSE market open' : 'Market closed'}</span></span><span className="session-time">{currentTime} IST</span></div>
          <button className={`iifl-feed-button ${liveStatus?.authenticated ? 'connected' : 'disconnected'}`} onClick={() => liveStatus?.configured ? window.location.assign('/api/market/live/login') : showToast('Add rotated IIFL credentials and the NIFTY instrument ID in backend/.env', 'warning')} title={liveStatus?.authenticated ? 'IIFL live feed connected' : 'Connect the IIFL live market feed'} aria-label={liveStatus?.authenticated ? 'IIFL connected' : 'IIFL disconnected. Connect live feed'}>{liveStatus?.authenticated ? <Radio size={16} aria-hidden="true" /> : <WifiOff size={16} aria-hidden="true" />}<span className="iifl-feed-label">{liveStatus?.authenticated ? 'IIFL connected' : 'Connect IIFL'}</span></button>
        </div>
      </header>

      <main className="page-content">
        {activeTab === 'screener' && <>
          <section className="welcome-row feature-hero dashboard-hero">
            <div className="hero-copy">
              <div className="hero-copy-main">
                <div className="eyebrow">NSE MARKET DESK <span className="hero-index">/</span> YOUR DAILY VIEW</div>
                <h1>Know the market.<br /><em>Choose your next step.</em></h1>
                <p className="welcome-subtitle">A clear, shared view for both of you.</p>
                <div className="hero-actions"><button className="primary-button" onClick={() => selectTab('swing')}>Explore swing setups <ArrowUpRight size={16} /></button><button className="hero-secondary-action" onClick={() => selectTab('regime')}>Market mood</button></div>
              </div>
              <img className="dashboard-hero-art" src={appLogo} alt="" aria-hidden="true" />
              <div className="hero-meta"><span className={`market-open-label ${isMarketOpen ? 'is-open' : 'is-closed'}`}><i aria-hidden="true" />{isMarketOpen ? 'Market open' : 'Market closed'}</span><span className="hero-meta-divider" /><span>{currentTime} IST</span></div>
            </div>
            <button className="hero-feature-card" onClick={() => selectTab('regime')} aria-label="View Nifty live quote and market mood">
              <div className="hero-feature-top"><span><i className={quoteFresh && isMarketOpen ? 'connected' : ''} />NIFTY 50 <small>{!isMarketOpen ? iiflQuoteIsToday ? 'DAY-END · IIFL' : 'DAY-END CLOSE' : quoteFresh ? 'LIVE · IIFL' : liveStatus?.authenticated ? 'FEED CONNECTED' : 'DAILY DATA'}</small></span><ArrowUpRight size={16} /></div>
              <div className="hero-market-main">
                <div className="hero-market-price-row">
                  <strong>{displayedNiftyPrice != null ? formatPrice(displayedNiftyPrice) : 'Waiting for quote'}</strong>
                  {liveChange != null && hasLiveQuote && <ValueBadge positive={liveChange >= 0} unit="%" context="Nifty price change" className="hero-market-change">{Math.abs(Number(liveChange))}</ValueBadge>}
                </div>
                <span className="hero-market-subtitle">{!isMarketOpen ? iiflQuoteIsToday ? `Last IIFL quote · ${liveQuoteTime || 'time unavailable'} IST` : 'Latest available daily close' : liveQuoteError || liveStatus?.stream_error ? `${hasLiveQuote ? 'Feed issue · last quote' : 'Quote unavailable'}${liveQuoteTime ? ` · ${liveQuoteTime} IST` : ''}` : quoteFresh ? `Live quote · ${liveQuoteTime || 'time unavailable'} IST` : hasLiveQuote ? `Last quote · ${liveQuoteTime || 'time unavailable'} IST` : liveStatus?.authenticated ? 'Waiting for a live quote' : 'Connect IIFL for live prices'}</span>
                {isMarketOpen && hasLiveQuote && sessionRangePosition != null ? <div className="hero-session-range">
                  <div className="hero-range-head"><span>Today’s range</span><span>Price marker</span></div>
                  <div className="hero-range-track"><i style={{ left: `${sessionRangePosition}%` }} /></div>
                  <div className="hero-range-values"><span>LOW {formatPrice(rangeLow)}</span><span>HIGH {formatPrice(rangeHigh)}</span></div>
                </div> : <div className="hero-range-placeholder"><span className="market-mood-chip"><i aria-hidden="true" />{regimeData?.title || 'Checking market mood'}</span><span>{regimeData?.recommended_action || 'Your market summary appears here.'}</span></div>}
              </div>
            </button>
          </section>

          <OverviewVisuals candles={niftyCandles} breadthPct={metrics.breadth_above_50ema_pct} signals={allSignals} onOpenMood={() => selectTab('regime')} onOpenSwing={() => selectTab('swing')} />

          <section className="dashboard-shortcuts" aria-label="Trading workspaces">
            <div className="dashboard-shortcuts-heading"><div><div className="eyebrow subtle-eyebrow">YOUR WORKSPACES</div><h2>Where would you like to go?</h2></div></div>
            <div className="dashboard-shortcuts-grid">
              <button className="dashboard-shortcut swing-shortcut" onClick={() => selectTab('swing')}><span className="dashboard-shortcut-icon"><LineChart size={22} /></span><span className="dashboard-shortcut-copy"><strong>Swing Trading</strong><small>{allSignals.length} setups ready</small></span><ArrowUpRight size={18} /></button>
              <button className="dashboard-shortcut" onClick={() => selectTab('intraday')}><span className="dashboard-shortcut-icon"><CandlestickChart size={22} /></span><span className="dashboard-shortcut-copy"><strong>Intraday</strong><small>Today’s stock setups</small></span><ArrowUpRight size={18} /></button>
              <button className="dashboard-shortcut" onClick={() => selectTab('options')}><span className="dashboard-shortcut-icon"><Activity size={22} /></span><span className="dashboard-shortcut-copy"><strong>Options</strong><small>Nifty options view</small></span><ArrowUpRight size={18} /></button>
              <button className="dashboard-shortcut" onClick={() => selectTab('portfolio')}><span className="dashboard-shortcut-icon"><Wallet size={22} /></span><span className="dashboard-shortcut-copy"><strong>Portfolio</strong><small>Your tracked shares</small></span><ArrowUpRight size={18} /></button>
            </div>
          </section>
          <footer className="page-footer"><span><ShieldCheck size={14} /> Research tools for informed decisions</span><span>Data may be delayed. Verify before trading.</span></footer>
        </>}

        {activeTab === 'swing' && <section className="module-page swing-page">
          <div className="module-heading swing-hero">
            <div className="swing-hero-copy"><div className="eyebrow subtle-eyebrow">MULTI-DAY STOCK SCREENER</div><h1>Swing Trading</h1><p>Research stock ideas with clear entry, risk and target levels.</p><div className="swing-hero-pills"><span>Multi-day setups</span><span>Risk levels included</span><span>Research only · No orders placed</span></div></div>
            <div className="swing-hero-side"><div className="swing-hero-count"><strong>{filteredSignals.length}</strong><span>setups to review</span></div><button className="scan-button swing-scan-button" onClick={() => runScreener(true)} disabled={loading}>{loading ? <RefreshCw className="spin" size={16} /> : <Sparkles size={16} />}{loading ? 'Scanning stocks…' : 'Run a fresh scan'}</button><small className="swing-scan-updated">Updated {screenerData?.timestamp || 'just now'}</small></div>
          </div>
          <section className="setups-section">
            <div className="section-heading swing-results-heading"><div className="swing-results-copy"><div className="eyebrow subtle-eyebrow">STOCKS TO REVIEW <span className="heading-line" /></div><h2>Possible swing trades <span>{filteredSignals.length}</span></h2><p>Choose a stock to see its company details, chart and setup.</p>
              <details className="swing-filter-details"><summary>How many stocks were filtered out?</summary><small>Price: {screenerData?.filter_rejections?.min_price || 0} · Liquidity: {screenerData?.filter_rejections?.avg_traded_value || 0} · History: {screenerData?.filter_rejections?.insufficient_history || 0} · Stale data: {screenerData?.filter_rejections?.stale_data || 0} · SME: {screenerData?.filter_rejections?.sme || 0} · Price band: {(screenerData?.filter_rejections?.circuit_band || 0) + (screenerData?.filter_rejections?.circuit_band_heuristic || 0)} · ASM/GSM: {typeof screenerData?.filter_rejections?.asm_gsm === 'number' ? screenerData.filter_rejections.asm_gsm : 0}</small></details>
            </div><div className="setup-actions swing-search-actions"><label className="search-box"><Search size={16} /><input ref={searchInputRef} value={searchQuery} onChange={event => setSearchQuery(event.target.value)} placeholder="Find a stock" /><kbd>/</kbd>{searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear search"><X size={14} /></button>}</label><select className="strategy-select" value={strategyFilter} onChange={event => setStrategyFilter(event.target.value)} aria-label="Filter stock ideas"><option value="ALL">All stock ideas</option><option value="trend_pullback">Buy a dip in a rising share</option><option value="relative_strength">Shares doing better than Nifty</option><option value="capitulation_reversal">Possible bounce after a sharp fall</option><option value="volatility_squeeze">Breakout after a quiet period</option><option value="multi_factor">Several positive checks agree</option></select><div className="view-toggle"><button onClick={() => setViewMode('table')} className={viewMode === 'table' ? 'active' : ''} aria-label="Table view"><Table2 size={16} /></button><button onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'active' : ''} aria-label="Card view"><LayoutDashboard size={16} /></button></div></div></div>
            <div className="swing-toolbar"><div className="history-horizon-bar"><span>Track setups for</span><select value={historyHoldingDays} onChange={event => setHistoryHoldingDays(Number(event.target.value))} aria-label="Stop tracking after this many market days"><option value={15}>15 market days</option><option value={30}>30 market days</option></select></div>
            <div className="filter-row"><strong>SHOW</strong>{[['ALL', `All ${allSignals.length}`], ['OPTIMAL', `Fits market mood ${optimalCount}`], ['HIGH_RR', 'Possible gain is at least 2× the loss'], ['HIGH_CONVICTION', 'Many checks agree']].map(([id, label]) => <button key={id} className={`filter-pill ${quickFilter === id ? 'active' : ''}`} onClick={() => setQuickFilter(id)}>{quickFilter === id && <Check size={13} />}{label}</button>)}<span className="scan-time"><span className="scan-time-dot" />{screenerData?.timestamp || 'Ready to scan'}</span></div></div>

            {loading ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking shares</strong><span>Looking for shares that match your choices…</span></div> : filteredSignals.length === 0 ? <div className="empty-panel"><div className="empty-icon"><Search size={19} /></div><strong>{allSignals.length ? 'No shares match these choices' : 'No shares to show yet'}</strong><span>{allSignals.length ? 'Try a different name or choice.' : 'Check the market again to find shares.'}</span>{!allSignals.length && <button className="text-action" onClick={() => runScreener(true)}>Check market <ArrowUpRight size={14} /></button>}</div> : viewMode === 'table' ? <div className="table-shell"><div className="table-scroll"><table className="setups-table swing-table"><thead><tr><th>SHARE</th><th>WHY IT APPEARED</th><th>PRICE CHANGE</th><th>PRICE TO REVIEW</th><th>EXIT IF IT FALLS TO</th><th>POSSIBLE GAIN PRICE</th><th>POSSIBLE GAIN VS LOSS</th><th>CHECK SCORE</th><th aria-label="Actions" /></tr></thead><tbody>{filteredSignals.map((signal, index) => { const positive = signal.change_pct >= 0; const isCopied = copiedSymbol === signal.symbol; return <tr key={`${signal.symbol}-${index}`} className="setup-row"><td><button type="button" className="instrument-open" onClick={() => openStockResearch(signal, 'swing')}><span className="instrument-token">{signal.symbol.slice(0, 1)}</span><span><b>{signal.symbol}</b><small>{simpleSignalStatus(signal.trade_status) || (signal.regime_status === 'OPTIMAL' ? 'Fits the current market mood' : simpleStrategyName(signal.strategy, signal.strategy_title))}</small></span></button></td><td><span className="strategy-tag">{simpleStrategyName(signal.strategy, signal.strategy_title)}</span></td><td><span className={`move-value ${positive ? 'positive' : 'negative'}`}>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{formatPercent(signal.change_pct, true)} <strong>{positive ? 'GAIN' : 'LOSS'}</strong></span></td><td className="numeric-cell">{formatPrice(signal.entry_price)}</td><td className="numeric-cell stop-value">{formatPrice(signal.stop_loss)}</td><td className="numeric-cell target-value">{formatPrice(signal.target_1)}</td><td><span className="rr-badge">{signal.risk_reward} to 1</span></td><td><div className="confidence"><span className="confidence-track"><i style={{ width: `${Math.min(100, signal.confidence_score || 0)}%` }} /></span><b>{formatPercent(signal.confidence_score, true)}</b></div></td><td><button className="row-action" title="Copy setup" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}>{isCopied ? <Check size={15} /> : <Copy size={15} />}</button></td></tr>; })}</tbody></table></div><div className="table-footer"><span><b>{filteredSignals.length}</b> shares shown</span><span>Prices use the latest available market information</span></div></div> : <div className="setup-grid">{filteredSignals.map((signal, index) => <article className="setup-card" key={`${signal.symbol}-${index}`}><div className="setup-card-top"><span className="instrument-token large-token">{signal.symbol.slice(0, 1)}</span><span className={`move-value ${signal.change_pct >= 0 ? 'positive' : 'negative'}`}>{signal.change_pct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{formatPercent(signal.change_pct, true)} <strong>{signal.change_pct >= 0 ? 'GAIN' : 'LOSS'}</strong></span></div><h3><button type="button" className="stock-name-button" onClick={() => openStockResearch(signal, 'swing')} aria-label={`View ${signal.symbol} stock research`}>{signal.symbol}</button></h3><p className="setup-strategy">{simpleStrategyName(signal.strategy, signal.strategy_title)}</p><div className="card-prices"><div><span>PRICE TO REVIEW</span><b>{formatPrice(signal.entry_price)}</b></div><div><span>EXIT IF IT FALLS TO</span><b className="stop-value">{formatPrice(signal.stop_loss)}</b></div><div><span>POSSIBLE GAIN PRICE</span><b className="target-value">{formatPrice(signal.target_1)}</b></div></div><div className="card-score"><span>CHECK SCORE</span><strong>{formatPercent(signal.confidence_score, true)}</strong></div><details className="setup-card-details"><summary>More setup details</summary><p>{signal.regime_status === 'OPTIMAL' ? 'Fits the current market mood.' : 'Review the setup alongside current market conditions.'}</p><ul>{(signal.reasons || []).slice(0, 3).map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul></details><div className="card-end"><span className="rr-badge">{signal.risk_reward} to 1 possible gain vs loss</span><button type="button" className="secondary-button" onClick={() => openStockResearch(signal, 'swing')}>View setup</button><button className="text-action" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}><Copy size={14} /> Copy plan</button></div></article>)}</div>}
          </section>
          <footer className="page-footer"><span><ShieldCheck size={14} /> Research tools for informed decisions</span><span>Data may be delayed. Verify before trading.</span></footer>
        </section>}

        {activeTab === 'portfolio' && <PortfolioView data={portfolioData} loading={portfolioLoading} saving={portfolioSaving} storageStatus={portfolioStorageStatus} saveError={portfolioSaveError} error={portfolioError} onSaveHolding={saveManualHolding} onDeleteHolding={deleteManualHolding} onRefresh={() => loadPortfolio(true)} onSelectStock={openStockResearch} />}
        {activeTab === 'history' && <SignalHistoryView onSelectStock={openStockResearch} />}
        {activeTab === 'flow-watch' && <InstitutionalFlowView onSelectStock={openStockResearch} />}
        {activeTab === 'stock-analysis' && <StockAnalysisView onSelectStock={openStockResearch} />}
        {activeTab === 'intraday' && <TradingStrategiesView mode="intraday" connected={Boolean(liveStatus?.authenticated)} onConnect={() => window.location.assign('/api/market/live/login')} onSelectStock={stock => openStockResearch(stock, 'intraday')} />}
        {activeTab === 'options' && <TradingStrategiesView mode="options" connected={Boolean(liveStatus?.authenticated)} onConnect={() => window.location.assign('/api/market/live/login')} onSelectStock={stock => openStockResearch(stock, 'options')} />}
        {activeTab === 'regime' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">MARKET CONTEXT</div><h1>Market mood</h1><p>See whether the overall market looks strong, weak or mixed.</p></div><button className="secondary-button" onClick={() => selectTab('screener')}>Back to overview</button></div><RegimeView regimeData={regimeData} onSelectStrategy={id => { setStrategyFilter(id); selectTab('swing'); }} /></section>}
        {activeTab === 'backtest' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">LEARN FROM PAST PRICES</div><h1>Test a strategy</h1><p>See how a share-picking idea would have worked on older prices.</p></div><span className="research-badge"><BookOpen size={14} /> Learning tool</span></div><BacktestLab onSelectStock={openStockResearch} /></section>}
        {activeTab === 'settings' && <section className="module-page settings-page">
          <div className="module-heading"><div><div className="eyebrow subtle-eyebrow">PERSONALIZE MARKETVOICE</div><h1>Settings</h1><p>Adjust the theme, brightness, text size, and accessibility previews.</p></div></div>
          <div className="settings-grid">
            <section className="settings-card"><div className="settings-card-heading"><Settings size={20} /><div><h2>Appearance</h2><p>Choose a theme and tune display comfort.</p></div></div><AppearanceControls theme={theme} setTheme={setTheme} dim={dim} setDim={setDim} grayscale={grayscale} setGrayscale={setGrayscale} motion={decorativeMotion} setMotion={setDecorativeMotion} /></section>
            <section className="settings-card"><div className="settings-card-heading"><span className="settings-type-icon">A+</span><div><h2>Text size</h2><p>Increase the interface text in five steps.</p></div></div><FontScaleControls value={fontScale} onChange={setFontScale} /></section>
            <section className="settings-card"><div className="settings-card-heading"><Volume2 size={20} /><div><h2>Sound feedback</h2><p>Play a short sound for scans and key actions.</p></div></div><button type="button" className="setting-button sound-setting-button" aria-pressed={soundOn} onClick={toggleSound}>{soundOn ? <Volume2 size={17} /> : <VolumeX size={17} />}<span>{soundOn ? 'Sound is on' : 'Sound is off'}</span><strong>{soundOn ? 'Turn off' : 'Turn on'}</strong></button></section>
          </div>
        </section>}
      </main>

      <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
        <button className={`bottom-nav-item ${activeTab === 'screener' ? 'active' : ''}`} onClick={() => selectTab('screener')}>
          <LayoutDashboard size={19} />
          <span>Overview</span>
          {filteredSignals.length > 0 && <span className="bottom-nav-dot" />}
        </button>
        <button className={`bottom-nav-item ${activeTab === 'swing' ? 'active' : ''}`} onClick={() => selectTab('swing')}>
          <LineChart size={19} />
          <span>Swing</span>
        </button>
        <button className={`bottom-nav-item ${activeTab === 'intraday' ? 'active' : ''}`} onClick={() => selectTab('intraday')}>
          <CandlestickChart size={19} />
          <span>Intraday</span>
        </button>
        <button className={`bottom-nav-item ${activeTab === 'options' ? 'active' : ''}`} onClick={() => selectTab('options')}>
          <Activity size={19} />
          <span>Options</span>
        </button>
        <button className={`bottom-nav-item ${mobileMenuOpen || ['portfolio', 'history', 'flow-watch', 'stock-analysis', 'regime', 'backtest', 'settings'].includes(activeTab) ? 'active' : ''}`} onClick={() => setMobileMenuOpen(true)}>
          <Menu size={19} />
          <span>Menu</span>
        </button>
      </nav>
    </div>

    {selectedChartTrade && <div className="spatial-modal-backdrop" onClick={() => setSelectedChartTrade(null)}>
      <div className="spatial-modal" onClick={event => event.stopPropagation()}>
        <div className="modal-topline">
          <div><div className="eyebrow subtle-eyebrow">{selectedChartTrade.source === 'intraday' ? 'INTRADAY SETUP' : ['history', 'flow', 'portfolio', 'analysis', 'backtest', 'research', 'options'].includes(selectedChartTrade.source) ? 'STOCK RESEARCH' : 'SWING SETUP'}{selectedChartTrade.strategy_title ? ` · ${selectedChartTrade.strategy_title}` : ''}</div><h2>{selectedChartTrade.symbol} <span>{selectedChartTrade.entry_price != null ? 'Research setup' : 'Company research'}</span></h2></div>
          <div className="stock-research-modal-actions"><a className="secondary-button tradingview-modal-link" href={`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(`NSE:${selectedChartTrade.symbol}`)}`} target="_blank" rel="noopener noreferrer">TradingView chart <ArrowUpRight size={16} /></a><button className="icon-button" onClick={() => setSelectedChartTrade(null)} aria-label="Close"><X size={18} /></button></div>
        </div>
        <StockResearchDetails data={researchDetails} loading={researchLoading} error={researchError} />
        <StockChart symbol={selectedChartTrade.symbol} tradePlan={selectedChartTrade} />
        {(selectedChartTrade.entry_price != null || selectedChartTrade.stop_loss != null || selectedChartTrade.target_1 != null) && <div className="modal-metrics">
          <div><span>ENTRY</span><b>{formatPrice(selectedChartTrade.entry_price)}</b></div>
          <div><span>STOP LOSS</span><b className="stop-value">{formatPrice(selectedChartTrade.stop_loss)}</b></div>
          <div><span>TARGET 1</span><b className="target-value">{formatPrice(selectedChartTrade.target_1)}</b></div>
          <div><span>TARGET 2</span><b className="target-value">{formatPrice(selectedChartTrade.target_2)}</b></div>
          <div><span>RISK / SHARE</span><b>{formatPrice(selectedChartTrade.risk_per_share)} <small>({formatPercent(selectedChartTrade.risk_pct, true)})</small></b></div>
        </div>}
        {selectedChartTrade.score_label && <div className="setup-rationale"><span>SETUP SCORE</span><p>{selectedChartTrade.score_label}. This score is a checklist result, not a probability or guarantee.</p></div>}
        {selectedChartTrade.reasons?.length > 0 && <div className="setup-rationale"><span>WHY THIS SETUP</span><ul>{selectedChartTrade.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>}
      </div>
    </div>}
  </div>;
}
