import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { History, RefreshCw, Search } from 'lucide-react';

function price(value) {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? '—' : `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function statusLabel(record) {
  if (record.outcome === 'TARGET_HIT') return 'Target price reached';
  if (record.outcome === 'STOP_LOSS') return 'Loss limit reached';
  if (record.outcome === 'TIME_EXIT') return `Time limit · ${record.max_holding_days} days`;
  return 'Still tracking';
}

function displayDate(value) {
  if (!value) return 'Date unavailable';
  return new Date(`${value}T12:00:00+05:30`).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: 'numeric', weekday: 'short' });
}

export default function SignalHistoryView({ onRefresh }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [dateFilter, setDateFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [query, setQuery] = useState('');

  const load = useCallback(async (showLoader = false) => {
    if (showLoader) setRefreshing(true);
    try {
      const response = await fetch('/api/history', { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'History could not be loaded.');
      setData(result);
      setError(null);
    } catch (loadError) {
      setError(loadError.message || 'History could not be loaded.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = window.setInterval(() => load(), 300000);
    return () => window.clearInterval(interval);
  }, [load]);

  const dates = useMemo(() => [...new Set((data?.records || []).map(record => record.signal_date))], [data]);
  const filtered = useMemo(() => {
    const needle = query.trim().toUpperCase();
    return (data?.records || []).filter(record => {
      const dateMatch = dateFilter === 'ALL' || record.signal_date === dateFilter;
      const statusMatch = statusFilter === 'ALL' || record.outcome === statusFilter;
      const searchMatch = !needle || record.symbol.includes(needle) || record.strategy_title.toUpperCase().includes(needle);
      return dateMatch && statusMatch && searchMatch;
    });
  }, [data, dateFilter, statusFilter, query]);
  const grouped = useMemo(() => filtered.reduce((groups, record) => {
    (groups[record.signal_date] ||= []).push(record);
    return groups;
  }, {}), [filtered]);

  return <section className="module-page signal-history-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">MARKETVOICE · YOUR WATCHLIST</div><h1>History</h1><p>Shares found in market scans stay here while we watch their price and record what happens next.</p></div>
      <button className="secondary-button" onClick={() => { load(true); onRefresh?.(); }} disabled={refreshing}><RefreshCw size={14} className={refreshing ? 'spin' : ''} />{refreshing ? 'Checking prices' : 'Update results'}</button>
    </div>

    <div className="history-summary">
      <article><span>RECORDED SETUPS</span><strong>{data?.count ?? '—'}</strong></article>
      <article className="history-open"><span>STILL TRACKING</span><strong>{data?.open_count ?? '—'}</strong></article>
      <article className="history-target"><span>TARGET PRICE REACHED</span><strong>{data?.target_count ?? '—'}</strong></article>
      <article className="history-stop"><span>LOSS LIMIT REACHED</span><strong>{data?.stop_count ?? '—'}</strong></article>
      <article className="history-time"><span>TIME LIMIT ENDED</span><strong>{data?.time_exit_count ?? '—'}</strong></article>
    </div>

    <div className="history-filters">
      <label className="history-search"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a share" /></label>
      <label><span>Found on</span><select value={dateFilter} onChange={event => setDateFilter(event.target.value)}><option value="ALL">Any date</option>{dates.map(date => <option value={date} key={date}>{displayDate(date)}</option>)}</select></label>
      <label><span>What happened</span><select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}><option value="ALL">Everything</option><option value="OPEN">Still tracking</option><option value="TARGET_HIT">Target price reached</option><option value="STOP_LOSS">Loss limit reached</option><option value="TIME_EXIT">Time limit ended</option></select></label>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong><button className="text-action" onClick={() => load(true)}>Try again</button></div>}
    {loading ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Loading signal history</strong><span>Updating open setups from completed daily candles…</span></div>
      : !filtered.length ? <div className="empty-panel"><div className="empty-icon"><History size={19} /></div><strong>{data?.count ? 'No history matches these filters' : 'No scan history yet'}</strong><span>{data?.count ? 'Clear a filter or search for another symbol.' : 'Run a scan in Overview. Matching setups will be saved here automatically.'}</span></div>
        : <div className="history-date-groups">{Object.entries(grouped).map(([date, records]) => <section className="history-date-group" key={date}>
          <div className="history-date-heading"><div><span>{displayDate(date)}</span><strong>{records.length} {records.length === 1 ? 'setup' : 'setups'}</strong></div></div>
      <div className="history-table-wrap"><table className="history-table"><thead><tr><th>STOCK / WHY IT WAS FOUND</th><th>PRICE WHEN FOUND</th><th>LOSS LIMIT</th><th>TARGET PRICE</th><th>PRICE NOW / EXIT</th><th>WHAT HAPPENED</th><th>PRICE CHANGE</th></tr></thead><tbody>
            {records.map(record => {
              const resultPrice = record.exit_price ?? record.last_price;
              const returnClass = record.return_pct == null ? '' : record.return_pct >= 0 ? 'positive' : 'negative';
              return <tr key={record.id}>
                <td><strong>{record.symbol}</strong><small>{record.strategy_title.replace('Trend EMA Pullback', 'Buy a dip in a rising share').replace('Relative Strength Leader', 'Shares doing better than Nifty').replace('Capitulation Oversold Bounce', 'Possible bounce after a sharp fall').replace('Volatility Squeeze Expansion', 'Breakout after a quiet period').replace('Multi-Factor Confluence', 'Several positive checks agree')}</small></td>
                <td>{price(record.entry_price)}</td><td className="negative">{price(record.stop_loss)}</td><td className="positive">{price(record.target_1)}</td>
                <td>{price(resultPrice)}<small>{record.exit_date ? displayDate(record.exit_date) : `Checked ${record.last_checked_date || 'pending'}`}</small></td>
                <td><span className={`history-outcome ${record.outcome.toLowerCase()}`}>{statusLabel(record)}</span><small className="history-progress">Watched for {record.holding_sessions} of {record.max_holding_days} market days</small></td>
                <td className={returnClass}>{record.return_pct == null ? '—' : `${record.return_pct > 0 ? '+' : ''}${record.return_pct}%`}</td>
              </tr>;
            })}
          </tbody></table></div>
        </section>)}</div>}

    <p className="history-disclaimer">We check the share’s daily prices after it was found. If the loss limit and target price were both crossed on the same day, we count the loss limit first. Prices are not live and may update with a delay.</p>
  </section>;
}
