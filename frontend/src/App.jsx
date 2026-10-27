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
import TradingStrategiesView from './components/TradingStrategiesView';
import { playTone, setSoundEnabled } from './utils/soundFx';

const navigation = [
  { id: 'screener', label: 'Overview', icon: LayoutDashboard, section: 'WORKSPACE' },
  { id: 'regime', label: 'Market regime', icon: Compass },
  { id: 'backtest', label: 'Strategy lab', icon: BarChart3 },
  { id: 'portfolio', label: 'Portfolio', icon: Wallet },
];
const marketNavigation = [
  { id: 'intraday', label: 'Intraday', icon: CandlestickChart },
  { id: 'options', label: 'Options', icon: Activity },
];
const MANUAL_PORTFOLIO_KEY = 'swing-trading-manual-portfolio-v1';
let liveStatusRequest = null;

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
    const saved = JSON.parse(window.localStorage.getItem(MANUAL_PORTFOLIO_KEY) || '[]');
    return Array.isArray(saved) ? saved.filter(item => item && typeof item.symbol === 'string' && Number(item.quantity) > 0 && Number(item.average_price) > 0) : [];
  } catch {
    return [];
  }
}

function formatPrice(value, fallback = '—') {
  if (value === undefined || value === null || value === '') return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : value;
}

function formatCompact(value) {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? '—' : new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 2 }).format(number);
}

function formatPercent(value, providerUsesPercent = false) {
  const number = Number(value);
  if (value == null || !Number.isFinite(number)) return '—';
  return `${(providerUsesPercent ? number : number * 100).toFixed(2)}%`;
}

function formatDividendYield(value) {
  const number = Number(value);
  if (value == null || !Number.isFinite(number)) return '—';
  // Yahoo's dividendYield is normally fractional, but some NSE records return percent units.
  return `${(Math.abs(number) > 0.25 ? number : number * 100).toFixed(2)}%`;
}

function formatMoney(value, currency = 'INR') {
  const number = Number(value);
  if (value == null || !Number.isFinite(number)) return '—';
  const safeCurrency = /^[A-Z]{3}$/.test(currency || '') ? currency : 'INR';
  try {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: safeCurrency, notation: 'compact', maximumFractionDigits: 2 }).format(number);
  } catch {
    return `${safeCurrency} ${formatCompact(number)}`;
  }
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
    if (label === 'EMA 20 / 50 / 200') {
      if (raw.ema20 == null || raw.ema50 == null || raw.ema200 == null || raw.close == null) return 'neutral';
      if (raw.close > raw.ema20 && raw.ema20 > raw.ema50 && raw.ema50 > raw.ema200) return 'good';
      return raw.close < raw.ema50 ? 'bad' : 'neutral';
    }
    if (label === 'RSI (14)') return number >= 45 && number <= 65 ? 'good' : number > 70 || number < 35 ? 'bad' : 'neutral';
    if (label === 'ADX (14)') return number >= 25 ? 'good' : number < 15 ? 'watch' : 'neutral';
    if (label === 'ATR (14)') return raw.atr14_pct >= 5 ? 'watch' : 'neutral';
    if (label === 'Volume / 20-day avg') return raw.volume_ratio20 >= 1.5 ? 'good' : raw.volume_ratio20 < 0.7 ? 'watch' : 'neutral';
    if (label === 'Return (20 / 63 sessions)') {
      const returns = String(value).match(/-?\d+(?:\.\d+)?/g)?.map(Number) || [];
      return returns.length === 2 && returns.every((item) => item > 0) ? 'good' : returns.length === 2 && returns.every((item) => item < 0) ? 'bad' : 'neutral';
    }
    if (label === 'Mansfield RS vs Nifty') return number > 0 ? 'good' : number < 0 ? 'bad' : 'neutral';
  }

  if (section === 'fundamental') {
    if (['EPS (TTM)', 'Revenue growth', 'Earnings growth', 'Profit margin', 'Operating margin', 'Free cash flow'].includes(label)) {
      const rawValue = label === 'EPS (TTM)' ? raw.eps_ttm
        : label === 'Revenue growth' ? raw.revenue_growth
          : label === 'Earnings growth' ? raw.earnings_growth
            : label === 'Profit margin' ? raw.profit_margin
              : label === 'Operating margin' ? raw.operating_margin : raw.free_cash_flow;
      return rawValue > 0 ? 'good' : rawValue < 0 ? 'bad' : 'neutral';
    }
    if (label === 'Return on equity') return raw.return_on_equity >= 0.15 ? 'good' : raw.return_on_equity < 0 ? 'bad' : 'neutral';
    if (label === 'Debt / equity (reported %)') return raw.debt_to_equity <= 100 ? 'good' : raw.debt_to_equity > 200 ? 'bad' : 'watch';
    if (label === 'Current ratio') return raw.current_ratio >= 1.5 ? 'good' : raw.current_ratio < 1 ? 'bad' : 'neutral';
  }
  return 'neutral';
}

function ResearchGrid({ items }) {
  const available = items.filter(([, value]) => value !== '—');
  if (!available.length) return <p className="research-empty">Provider did not return these fields.</p>;
  return <>
    <p className="research-signal-legend"><span className="signal-good">Green: supportive</span><span className="signal-bad">Red: caution</span><span>Grey: context only</span></p>
    <div className="research-grid">{available.map(([label, value, tone = 'neutral']) => <div className={`research-value signal-card-${tone}`} key={label}>
      <span>{label}</span><strong>{value}</strong><small className={`research-signal-label signal-${tone}`}>{tone === 'good' ? 'Supportive' : tone === 'bad' ? 'Caution' : tone === 'watch' ? 'Watch' : 'Context'}</small>
    </div>)}</div>
  </>;
}

function StockResearchDetails({ data, loading, error }) {
  if (loading) return <div className="research-loading"><RefreshCw size={15} /> Loading recent news, technicals and fundamentals…</div>;
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
    technicalValue('EMA 20 / 50 / 200', technical.ema20 != null ? `${formatPrice(technical.ema20)} / ${formatPrice(technical.ema50)} / ${formatPrice(technical.ema200)}` : '—'),
    technicalValue('RSI (14)', technical.rsi14 != null ? technical.rsi14.toFixed(1) : '—'),
    technicalValue('ADX (14)', technical.adx14 != null ? technical.adx14.toFixed(1) : '—'),
    technicalValue('ATR (14)', technical.atr14_pct != null ? `${technical.atr14_pct}% of price` : '—'),
    technicalValue('Volume / 20-day avg', technical.volume_ratio20 != null ? `${technical.volume_ratio20}×` : '—'),
    technicalValue('Return (20 / 63 sessions)', technical.return20_pct != null && technical.return63_pct != null ? `${technical.return20_pct}% / ${technical.return63_pct}%` : '—'),
    technicalValue('Mansfield RS vs Nifty', technical.mansfield_rs63 != null ? `${technical.mansfield_rs63 > 0 ? '+' : ''}${technical.mansfield_rs63}%` : '—'),
    technicalValue('Data date', technical.as_of || '—'),
  ];
  const currency = fundamentals.currency || 'INR';
  const fundamentalItems = [
    fundamentalValue('Market cap', formatMoney(fundamentals.market_cap, currency)),
    fundamentalValue('P/E (TTM)', fundamentals.trailing_pe != null ? fundamentals.trailing_pe.toFixed(2) : '—'),
    fundamentalValue('Forward P/E', fundamentals.forward_pe != null ? fundamentals.forward_pe.toFixed(2) : '—'),
    fundamentalValue('Price / book', fundamentals.price_to_book != null ? fundamentals.price_to_book.toFixed(2) : '—'),
    fundamentalValue('EPS (TTM)', formatMoney(fundamentals.eps_ttm, currency)),
    fundamentalValue('Dividend yield', formatDividendYield(fundamentals.dividend_yield)),
    fundamentalValue('Return on equity', formatPercent(fundamentals.return_on_equity)),
    fundamentalValue('Revenue growth', formatPercent(fundamentals.revenue_growth)),
    fundamentalValue('Earnings growth', formatPercent(fundamentals.earnings_growth)),
    fundamentalValue('Profit margin', formatPercent(fundamentals.profit_margin)),
    fundamentalValue('Operating margin', formatPercent(fundamentals.operating_margin)),
    fundamentalValue('Debt / equity (reported %)', formatPercent(fundamentals.debt_to_equity, true)),
    fundamentalValue('Current ratio', fundamentals.current_ratio != null ? fundamentals.current_ratio.toFixed(2) : '—'),
    fundamentalValue('Beta', fundamentals.beta != null ? fundamentals.beta.toFixed(2) : '—'),
    fundamentalValue('Total revenue', formatMoney(fundamentals.total_revenue, currency)),
    fundamentalValue('Free cash flow', formatMoney(fundamentals.free_cash_flow, currency)),
  ];

  const fetchedAt = data.retrieved_at ? new Date(data.retrieved_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) : 'now';
  return <div className="stock-research-details">
    <p className="research-data-stamp">Research snapshot fetched {fetchedAt} IST. Fundamentals are provider-reported and may be delayed.</p>
    <ResearchSection title="Recent company news" source={news.source || 'News provider'} status={news.status}>
      <p className="research-note">Last {news.lookback_hours || 72} hours · headline screening only; open stories and filings to verify context.</p>
      {news.event_risk && <div className="research-risk">Potential event-risk wording found. Review these stories before considering the setup.</div>}
      {news.headlines?.length ? <ul className="research-news-list">{news.headlines.map((item, index) => <li key={`${item.title}-${index}`}><div>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}</div><small>{[item.source, item.published_at ? new Date(item.published_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) : null].filter(Boolean).join(' · ')}</small></li>)}</ul> : <p className="research-empty">{news.status === 'unavailable' ? 'News could not be fetched. Check current company announcements manually.' : 'No recent headlines returned for this symbol.'}</p>}
    </ResearchSection>

    <ResearchSection title="Technical details" source={technical.source || 'Daily market data'} status={technical.status}>
      {technical.error && <p className="research-empty">{technical.error}</p>}
      <ResearchGrid items={technicalItems} />
    </ResearchSection>

    <ResearchSection title={fundamentals.company_name || 'Fundamentals'} source={fundamentals.source || 'Company data'} status={fundamentals.status}>
      {(fundamentals.sector || fundamentals.industry) && <p className="research-note">{[fundamentals.sector, fundamentals.industry].filter(Boolean).join(' · ')}</p>}
      {fundamentals.error && <p className="research-empty">{fundamentals.error}</p>}
      <ResearchGrid items={fundamentalItems} />
    </ResearchSection>
    {error && <p className="research-empty">Some research sections did not load: {error}</p>}
  </div>;
}

function PortfolioView({ data, loading, error, onRefresh, onSaveHolding, onDeleteHolding }) {
  const [entry, setEntry] = useState({ symbol: '', quantity: '', average_price: '' });
  const [editingSymbol, setEditingSymbol] = useState(null);
  const holdings = data?.holdings || [];
  const totalValue = holdings.reduce((total, item) => total + (Number(item.current_value) || 0), 0);
  const totalInvestment = holdings.reduce((total, item) => total + (Number(item.invested_value) || 0), 0);
  const totalPnl = holdings.reduce((total, item) => total + (Number(item.unrealized_pnl) || 0), 0);
  const submitHolding = event => {
    event.preventDefault();
    const symbol = entry.symbol.trim().toUpperCase().replace(/\.NS$/, '');
    onSaveHolding({ symbol, quantity: Number(entry.quantity), average_price: Number(entry.average_price) }, editingSymbol);
    setEntry({ symbol: '', quantity: '', average_price: '' });
    setEditingSymbol(null);
  };
  const startEdit = item => {
    setEditingSymbol(item.symbol);
    setEntry({ symbol: item.symbol, quantity: String(item.quantity), average_price: String(item.average_price) });
  };
  return <section className="module-page portfolio-page">
    <div className="module-heading"><div><div className="eyebrow subtle-eyebrow">MANUAL PORTFOLIO · DAILY REVIEW</div><h1>Your portfolio</h1><p>Add your shares, quantity and average buy price for a daily technical review.</p></div>
      <div className="portfolio-actions"><span className="portfolio-connection connected"><i />Saved in this browser</span><button className="secondary-button" onClick={onRefresh} disabled={loading}>{loading ? <RefreshCw size={14} className="spin" /> : <RefreshCw size={14} />}{loading ? 'Reviewing' : 'Refresh analysis'}</button></div>
    </div>
    <form className="portfolio-entry" onSubmit={submitHolding}>
      <label>Stock symbol<input value={entry.symbol} onChange={event => setEntry(current => ({ ...current, symbol: event.target.value }))} placeholder="e.g. RELIANCE or TCS" required pattern="[A-Za-z0-9&._-]+" maxLength={30} /></label>
      <label>Quantity<input type="number" value={entry.quantity} onChange={event => setEntry(current => ({ ...current, quantity: event.target.value }))} min="0.000001" step="any" placeholder="Shares" required /></label>
      <label>Average buy price<input type="number" value={entry.average_price} onChange={event => setEntry(current => ({ ...current, average_price: event.target.value }))} min="0.01" step="any" placeholder="₹ per share" required /></label>
      <div className="portfolio-entry-actions"><button className="primary-button" type="submit" disabled={loading}>{editingSymbol ? 'Save changes' : 'Add stock'}</button>{editingSymbol && <button className="secondary-button" type="button" onClick={() => { setEditingSymbol(null); setEntry({ symbol: '', quantity: '', average_price: '' }); }}>Cancel</button>}</div>
    </form>
    {error && <div className="portfolio-notice"><strong>{error}</strong></div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Reviewing your shares</strong><span>Calculating daily trend checks…</span></div>
      : holdings.length === 0 ? <div className="empty-panel"><div className="empty-icon"><Wallet size={19} /></div><strong>Add your first stock</strong><span>Enter its NSE symbol, quantity and average buy price above. Your list is saved in this browser.</span></div>
        : <>
          <div className="portfolio-summary"><article><span>SHARES HELD</span><strong>{holdings.length}</strong></article><article><span>INVESTED · EST.</span><strong>{formatPrice(totalInvestment)}</strong></article><article><span>MARKET VALUE · EST.</span><strong>{formatPrice(totalValue)}</strong></article><article><span>UNREALIZED P&amp;L · EST.</span><strong className={totalPnl >= 0 ? 'positive' : 'negative'}>{formatPrice(totalPnl)}</strong></article></div>
          <div className="portfolio-list">{holdings.map((item, index) => {
            const analysis = item.analysis || {};
            const actionLabel = analysis.action === 'REVIEW_SELL' ? 'Review position' : analysis.action === 'HOLD' ? 'Hold' : 'Insufficient data';
            const actionClass = analysis.action === 'REVIEW_SELL' ? 'review-sell' : analysis.action === 'HOLD' ? 'hold' : 'unknown';
            return <article className="portfolio-card" key={`${item.display_symbol || item.symbol}-${index}`}>
              <div className="portfolio-card-heading"><div><span className="instrument-token">{(item.display_symbol || item.symbol || '?').slice(0, 1)}</span><div><strong>{item.display_symbol || item.symbol}</strong><small>Manual entry · Qty {item.quantity ?? '—'}</small></div></div><div className="portfolio-card-controls"><span className={`portfolio-action ${actionClass}`}>{actionLabel}</span><button type="button" onClick={() => startEdit(item)}>Edit</button><button type="button" onClick={() => onDeleteHolding(item.symbol)}>Remove</button></div></div>
              <div className="portfolio-values"><div><span>LAST PRICE</span><b>{formatPrice(item.last_price)}</b></div><div><span>AVG. BUY</span><b>{formatPrice(item.average_price)}</b></div><div><span>QUANTITY</span><b>{item.quantity}</b></div><div><span>INVESTED · EST.</span><b>{formatPrice(item.invested_value)}</b></div><div><span>MARKET VALUE · EST.</span><b>{formatPrice(item.current_value)}</b></div><div><span>UNREALIZED P&amp;L · EST.</span><b className={Number(item.unrealized_pnl) >= 0 ? 'positive' : 'negative'}>{formatPrice(item.unrealized_pnl)}</b></div></div>
              {analysis.action !== 'INSUFFICIENT_DATA' && <div className="portfolio-indicators"><span>EMA 20 <b>{formatPrice(analysis.ema20)}</b></span><span>EMA 50 <b>{formatPrice(analysis.ema50)}</b></span><span>RSI 14 <b>{analysis.rsi14 ?? '—'}</b></span><span>20-session return <b className={Number(analysis.return20_pct) >= 0 ? 'positive' : 'negative'}>{analysis.return20_pct == null ? '—' : `${analysis.return20_pct}%`}</b></span><small>Daily data: {analysis.as_of || '—'}</small></div>}
              <ul className="portfolio-reasons">{(analysis.reasons || []).map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>
              <div className={`portfolio-verdict ${actionClass}`}><div><span>AASAAN VERDICT · BEGINNER VIEW</span><strong>{actionLabel}</strong></div><p>{analysis.beginner_verdict || 'Is review me abhi agla step tay karne ke liye kaafi data nahi hai.'}</p></div>
            </article>;
          })}</div>
          <p className="portfolio-disclaimer">{data?.disclaimer || 'Technical research screen only, not personalized financial advice.'} Price history comes from Yahoo Finance; signals may not account for your investment horizon, taxes, corporate actions, or personal risk limits.</p>
        </>}
  </section>;
}

export default function App() {
  const [activeTab, setActiveTab] = useState('screener');
  const [regimeData, setRegimeData] = useState(null);
  const [liveStatus, setLiveStatus] = useState(null);
  const [liveQuote, setLiveQuote] = useState(null);
  const [liveQuoteError, setLiveQuoteError] = useState(null);
  const [screenerData, setScreenerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
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
  const [currentTime, setCurrentTime] = useState('');
  const searchInputRef = useRef(null);

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
      showToast(`Scan complete · ${data.signals?.length || 0} setups found`, 'success');
    } catch (error) {
      console.error('Failed to run screener', error);
      playTone('alert');
      showToast('Market scan could not be completed', 'warning');
    } finally { setLoading(false); }
  };
  useEffect(() => {
    try { window.localStorage.setItem(MANUAL_PORTFOLIO_KEY, JSON.stringify(manualHoldings)); }
    catch (error) { console.warn('Could not save manual portfolio in this browser', error); }
  }, [manualHoldings]);
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
    const next = [...manualHoldings];
    const existingIndex = next.findIndex(item => item.symbol === (oldSymbol || holding.symbol));
    if (existingIndex >= 0) next[existingIndex] = holding;
    else next.push(holding);
    setManualHoldings(next);
    loadPortfolio(false, next);
  };
  const deleteManualHolding = symbol => {
    const next = manualHoldings.filter(item => item.symbol !== symbol);
    setManualHoldings(next);
    loadPortfolio(false, next);
  };
  useEffect(() => { loadRegime(); runScreener(false); }, []);
  useEffect(() => {
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date());
    const reviewedDate = portfolioData?.analysis_as_of?.slice(0, 10);
    if (activeTab === 'portfolio' && !portfolioLoading && !portfolioError && (!portfolioData || reviewedDate !== today)) loadPortfolio(false);
  }, [activeTab, portfolioData, portfolioLoading, portfolioError, currentTime]);
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
  const avgRR = allSignals.length ? (allSignals.reduce((sum, signal) => sum + (signal.risk_reward || 0), 0) / allSignals.length).toFixed(1) : '—';
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
  const marketName = activeTab === 'screener' ? 'Overview' : activeTab === 'regime' ? 'Market regime' : activeTab === 'portfolio' ? 'Portfolio' : activeTab === 'intraday' ? 'Intraday' : activeTab === 'options' ? 'Options' : 'Strategy lab';

  const selectTab = id => { setActiveTab(id); playTone('click'); };
  const handleCopySetup = signal => {
    const text = `SWING SETUP · ${signal.symbol}\nStatus: ${signal.trade_status || 'Review setup'}\nEntry: ₹${signal.entry_price}\nStop: ₹${signal.stop_loss}\nTarget 1: ₹${signal.target_1}\nTarget 2: ₹${signal.target_2}\nRisk/reward: 1:${signal.risk_reward}\nStrategy: ${signal.strategy_title}`;
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
        {marketNavigation.map(({ id, label, icon: Icon }) => <button key={id} className={`side-nav-item ${activeTab === id ? 'selected' : ''}`} onClick={() => selectTab(id)} title={label}>
          <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
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
          {activeTab === 'screener' && <button className="scan-button" onClick={() => runScreener(true)} disabled={loading}>{loading ? <RefreshCw className="spin" size={16} /> : <Sparkles size={16} />}{loading ? 'Scanning' : 'Run scan'}</button>}
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
            <button className="hero-feature-card" onClick={() => selectTab('regime')} aria-label="View Nifty live quote and market regime">
              <div className="hero-feature-top"><span><i className={quoteFresh && isMarketOpen ? 'connected' : ''} />{!isMarketOpen ? iiflQuoteIsToday ? 'IIFL · DAY-END NIFTY 50' : 'NIFTY 50 · DAY-END CLOSE' : quoteFresh ? liveQuote.source === 'IIFL live market stream' ? 'IIFL · STREAM LIVE NIFTY 50' : 'IIFL · LIVE NIFTY 50' : liveStatus?.authenticated ? 'IIFL · FEED CONNECTED' : 'NIFTY 50 · DAILY DATA'}</span><ArrowUpRight size={16} /></div>
              <div className="hero-market-main">
                <div className="hero-market-price-row">
                  <strong>{displayedNiftyPrice != null ? formatPrice(displayedNiftyPrice) : 'Waiting for quote'}</strong>
                  {isMarketOpen && hasLiveQuote && liveChange != null && <span className={`hero-market-change ${liveChange >= 0 ? 'positive' : 'negative'}`}>{liveChange >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{liveChange > 0 ? '+' : ''}{liveChange}%</span>}
                </div>
                <span className="hero-market-subtitle">{!isMarketOpen ? iiflQuoteIsToday ? `Market closed · IIFL last quote ${liveQuoteTime || ''} IST` : 'Market closed · latest daily close from Yahoo Finance' : liveQuoteError || liveStatus?.stream_error ? `${liveQuoteError || liveStatus.stream_error}${hasLiveQuote ? ` · last tick ${liveQuoteTime || ''} IST` : ''}` : hasLiveQuote ? `${quoteFresh ? 'NIFTY 50 IIFL live spot' : 'IIFL quote delayed'} · tick ${liveQuoteTime || 'time unavailable'} IST` : liveStatus?.authenticated ? 'Waiting for IIFL quote · showing latest Yahoo daily bar' : 'Yahoo Finance daily bar · connect IIFL for live spot data'}</span>
                {isMarketOpen && hasLiveQuote && sessionRangePosition != null ? <div className="hero-session-range">
                  <div className="hero-range-head"><span>TODAY’S RANGE</span><span>MARKER = LIVE PRICE</span></div>
                  <div className="hero-range-track"><i style={{ left: `${sessionRangePosition}%` }} /></div>
                  <div className="hero-range-values"><span>LOW {formatPrice(rangeLow)}</span><span>HIGH {formatPrice(rangeHigh)}</span></div>
                </div> : <div className="hero-range-placeholder">{!isMarketOpen ? 'Intraday range hidden while market is closed' : hasLiveQuote ? 'Session high/low not supplied by the feed' : 'Live price range appears after IIFL quote connects'}</div>}
              </div>
              <div className="hero-regime-summary">
                <div><small><i style={{ background: regimeData?.color || '#d9f2a2' }} />MARKET REGIME</small><strong>{regimeData?.title || 'Waiting for market analysis'}</strong></div>
                <span title="Breadth and RSI use Yahoo Finance daily OHLCV data for the selected stock sample">{metrics.breadth_above_50ema_pct != null ? `YF breadth ${metrics.breadth_above_50ema_pct}% · ${metrics.breadth_valid_symbols ?? '—'} stocks > 50 EMA` : 'YF breadth unavailable'}<br />{metrics.rsi_14 != null ? `Nifty RSI ${metrics.rsi_14} · daily` : 'Nifty RSI —'}</span>
              </div>
            </button>
          </section>

          <section className="market-strip" aria-label="Market snapshot">
            <MetricCard label="NIFTY 50" value={displayedNiftyPrice != null ? Number(displayedNiftyPrice).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—'} change={isMarketOpen && liveQuote ? `${liveChange > 0 ? '+' : ''}${liveChange}% today` : 'Day-end close'} positive={isMarketOpen && liveQuote ? liveChange >= 0 : null} icon={LineChart} note={isMarketOpen ? liveQuote ? `${quoteFresh ? 'IIFL live' : 'IIFL last update'} · ${liveQuote.tick_time || liveQuote.received_at}` : 'Waiting for IIFL live quote' : iiflQuoteIsToday ? `IIFL last quote · ${liveQuoteTime || ''} IST` : 'Latest daily close · Yahoo Finance'} tone="lilac" />
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
            <div className="section-heading"><div><div className="eyebrow subtle-eyebrow">SWING STRATEGIES <span className="heading-line" /></div><h2>Setups in focus <span>{filteredSignals.length}</span></h2><p>Click any stock for its news, technicals and available fundamentals.</p></div><div className="setup-actions"><label className="search-box"><Search size={16} /><input ref={searchInputRef} value={searchQuery} onChange={event => setSearchQuery(event.target.value)} placeholder="Search symbols" /><kbd>/</kbd>{searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear search"><X size={14} /></button>}</label><select className="strategy-select" value={strategyFilter} onChange={event => setStrategyFilter(event.target.value)} aria-label="Filter by strategy"><option value="ALL">All strategies</option><option value="trend_pullback">Trend EMA Pullback</option><option value="relative_strength">Relative Strength Leader</option><option value="capitulation_reversal">Capitulation Oversold Bounce</option><option value="volatility_squeeze">Volatility Squeeze Expansion</option><option value="multi_factor">Multi-Factor Confluence</option></select><div className="view-toggle"><button onClick={() => setViewMode('table')} className={viewMode === 'table' ? 'active' : ''} aria-label="Table view"><Table2 size={16} /></button><button onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'active' : ''} aria-label="Card view"><LayoutDashboard size={16} /></button></div></div></div>
            <div className="filter-row"><span>QUICK FILTER</span>{[['ALL', `All ${allSignals.length}`], ['OPTIMAL', `In regime ${optimalCount}`], ['HIGH_RR', 'R:R above 2'], ['HIGH_CONVICTION', 'Setup score 80+']].map(([id, label]) => <button key={id} className={`filter-pill ${quickFilter === id ? 'active' : ''}`} onClick={() => setQuickFilter(id)}>{quickFilter === id && <Check size={13} />}{label}</button>)}<span className="scan-time"><span className="scan-time-dot" />Updated {screenerData?.timestamp || 'just now'}</span></div>

            {loading ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Reading the market</strong><span>Scanning for setups across your universe…</span></div> : filteredSignals.length === 0 ? <div className="empty-panel"><div className="empty-icon"><Search size={19} /></div><strong>{allSignals.length ? 'No setups match these filters' : 'No setups to show yet'}</strong><span>{allSignals.length ? 'Try a different symbol or filter.' : 'Run a fresh market scan to look for opportunities.'}</span>{!allSignals.length && <button className="text-action" onClick={() => runScreener(true)}>Scan market <ArrowUpRight size={14} /></button>}</div> : viewMode === 'table' ? <div className="table-shell"><div className="table-scroll"><table className="setups-table"><thead><tr><th>INSTRUMENT</th><th>STRATEGY</th><th>LAST MOVE</th><th>ENTRY</th><th>STOP</th><th>TARGET</th><th>RISK / REWARD</th><th>SETUP SCORE</th><th aria-label="Actions" /></tr></thead><tbody>{filteredSignals.map((signal, index) => { const positive = signal.change_pct >= 0; const isCopied = copiedSymbol === signal.symbol; return <tr key={`${signal.symbol}-${index}`} onClick={() => setSelectedChartTrade(signal)} className="setup-row"><td><div className="instrument"><span className="instrument-token">{signal.symbol.slice(0, 1)}</span><span><b>{signal.symbol}</b><small>{signal.trade_status || (signal.regime_status === 'OPTIMAL' ? 'Aligned with regime' : signal.strategy_title || 'Swing setup')}</small></span></div></td><td><span className="strategy-tag">{signal.strategy_title || signal.strategy}</span></td><td><span className={`move-value ${positive ? 'positive' : 'negative'}`}>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{positive ? '+' : ''}{signal.change_pct}%</span></td><td className="numeric-cell">{formatPrice(signal.entry_price)}</td><td className="numeric-cell stop-value">{formatPrice(signal.stop_loss)}</td><td className="numeric-cell target-value">{formatPrice(signal.target_1)}</td><td><span className="rr-badge">1:{signal.risk_reward}</span></td><td><div className="confidence"><span className="confidence-track"><i style={{ width: `${Math.min(100, signal.confidence_score || 0)}%` }} /></span><b>{signal.confidence_score ?? '—'}%</b></div></td><td><button className="row-action" title="Copy setup" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}>{isCopied ? <Check size={15} /> : <Copy size={15} />}</button></td></tr>; })}</tbody></table></div><div className="table-footer"><span><b>{filteredSignals.length}</b> setups shown</span><span>Prices and signals reflect the latest available market data</span></div></div> : <div className="setup-grid">{filteredSignals.map((signal, index) => <article className="setup-card" key={`${signal.symbol}-${index}`} onClick={() => setSelectedChartTrade(signal)}><div className="setup-card-top"><span className="instrument-token large-token">{signal.symbol.slice(0, 1)}</span><span className={`move-value ${signal.change_pct >= 0 ? 'positive' : 'negative'}`}>{signal.change_pct >= 0 ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{signal.change_pct >= 0 ? '+' : ''}{signal.change_pct}%</span></div><h3>{signal.symbol}</h3><p className="setup-strategy">{signal.strategy_title}</p><div className="card-prices"><div><span>ENTRY</span><b>{formatPrice(signal.entry_price)}</b></div><div><span>STOP</span><b className="stop-value">{formatPrice(signal.stop_loss)}</b></div><div><span>TARGET</span><b className="target-value">{formatPrice(signal.target_1)}</b></div></div><div className="card-end"><span className="rr-badge">1:{signal.risk_reward} R/R</span><button className="text-action" onClick={event => { event.stopPropagation(); handleCopySetup(signal); }}><Copy size={14} /> Copy plan</button></div></article>)}</div>}
          </section>
          <footer className="page-footer"><span><ShieldCheck size={14} /> Research tools for informed decisions</span><span>Data may be delayed. Verify before trading.</span></footer>
        </>}

        {activeTab === 'portfolio' && <PortfolioView data={portfolioData} loading={portfolioLoading} error={portfolioError} onSaveHolding={saveManualHolding} onDeleteHolding={deleteManualHolding} onRefresh={() => loadPortfolio(true)} />}
        {activeTab === 'intraday' && <TradingStrategiesView mode="intraday" connected={Boolean(liveStatus?.authenticated)} onConnect={() => window.location.assign('/api/market/live/login')} />}
        {activeTab === 'options' && <TradingStrategiesView mode="options" connected={Boolean(liveStatus?.authenticated)} onConnect={() => window.location.assign('/api/market/live/login')} />}
        {activeTab === 'regime' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">MARKET CONTEXT</div><h1>Market regime</h1><p>Understand the conditions shaping today’s opportunities.</p></div><button className="secondary-button" onClick={() => selectTab('screener')}>Back to overview</button></div><RegimeView regimeData={regimeData} onSelectStrategy={id => { setStrategyFilter(id); selectTab('screener'); }} /></section>}
        {activeTab === 'backtest' && <section className="module-page"><div className="module-heading"><div><div className="eyebrow subtle-eyebrow">RESEARCH WORKSPACE</div><h1>Strategy lab</h1><p>Explore how your swing strategies have behaved across historical data.</p></div><span className="research-badge"><BookOpen size={14} /> Research mode</span></div><BacktestLab /></section>}
      </main>
    </div>

    {selectedChartTrade && <div className="spatial-modal-backdrop" onClick={() => setSelectedChartTrade(null)}>
      <div className="spatial-modal" onClick={event => event.stopPropagation()}>
        <div className="modal-topline">
          <div><div className="eyebrow subtle-eyebrow">SWING SETUP · {selectedChartTrade.strategy_title}</div><h2>{selectedChartTrade.symbol} <span>Research setup</span></h2></div>
          <button className="icon-button" onClick={() => setSelectedChartTrade(null)} aria-label="Close"><X size={18} /></button>
        </div>
        <StockResearchDetails data={researchDetails} loading={researchLoading} error={researchError} />
        <StockChart symbol={selectedChartTrade.symbol} tradePlan={selectedChartTrade} />
        <div className="modal-metrics">
          <div><span>ENTRY</span><b>{formatPrice(selectedChartTrade.entry_price)}</b></div>
          <div><span>STOP LOSS</span><b className="stop-value">{formatPrice(selectedChartTrade.stop_loss)}</b></div>
          <div><span>TARGET 1</span><b className="target-value">{formatPrice(selectedChartTrade.target_1)}</b></div>
          <div><span>TARGET 2</span><b className="target-value">{formatPrice(selectedChartTrade.target_2)}</b></div>
          <div><span>RISK / SHARE</span><b>{formatPrice(selectedChartTrade.risk_per_share)} <small>({selectedChartTrade.risk_pct}%)</small></b></div>
        </div>
        {selectedChartTrade.score_label && <div className="setup-rationale"><span>SETUP SCORE</span><p>{selectedChartTrade.score_label}. This score is a checklist result, not a probability or guarantee.</p></div>}
        {selectedChartTrade.reasons?.length > 0 && <div className="setup-rationale"><span>WHY THIS SETUP</span><ul>{selectedChartTrade.reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>}
      </div>
    </div>}
  </div>;
}
