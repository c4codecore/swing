import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { History, RefreshCw, Search } from 'lucide-react';
import { formatINR, formatPercent } from '../utils/formatters';

function price(value) {
  return formatINR(value);
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

export default function SignalHistoryView({ onRefresh, onSelectStock }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [dateFilter, setDateFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [query, setQuery] = useState('');
  const [historyType, setHistoryType] = useState('swing');

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

  const swingRecords = data?.records || [];
  const intradayRecords = (data?.market_records || []).filter(record => record.market_type === 'intraday');
  const optionsRecords = (data?.market_records || []).filter(record => record.market_type === 'options');
  const currentRecords = historyType === 'swing' ? swingRecords : (historyType === 'intraday' ? intradayRecords : optionsRecords).map(record => ({
    ...record, ...record.snapshot, signal_date: record.signal_date, captured_at: record.captured_at,
    id: `${record.market_type}-${record.id}`,
  }));
  const dates = useMemo(() => [...new Set(currentRecords.map(record => record.signal_date))], [currentRecords]);
  const filtered = useMemo(() => {
    const needle = query.trim().toUpperCase();
    return currentRecords.filter(record => {
      const dateMatch = dateFilter === 'ALL' || record.signal_date === dateFilter;
      const statusValue = historyType === 'intraday' ? record.direction : historyType === 'options' ? record.status : record.outcome;
      const statusMatch = statusFilter === 'ALL' || statusValue === statusFilter;
      const searchMatch = !needle || String(record.symbol || '').toUpperCase().includes(needle) || String(record.strategy_title || record.strategy || '').toUpperCase().includes(needle);
      return dateMatch && statusMatch && searchMatch;
    });
  }, [currentRecords, historyType, dateFilter, statusFilter, query]);
  const grouped = useMemo(() => filtered.reduce((groups, record) => {
    (groups[record.signal_date] ||= []).push(record);
    return groups;
  }, {}), [filtered]);

  return <section className="module-page signal-history-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">MARKETVOICE · YOUR WATCHLIST</div><h1>History</h1><p>Shares found in market scans stay here while we watch their price and record what happens next.</p></div>
      <button className="secondary-button" onClick={() => { load(true); onRefresh?.(); }} disabled={refreshing}><RefreshCw size={14} className={refreshing ? 'spin' : ''} />{refreshing ? 'Checking prices' : 'Update results'}</button>
    </div>

    <div className="history-market-tabs" role="tablist" aria-label="History category">
      <button type="button" role="tab" aria-selected={historyType === 'swing'} className={historyType === 'swing' ? 'active' : ''} onClick={() => { setHistoryType('swing'); setStatusFilter('ALL'); setDateFilter('ALL'); }}>Swing trading <b>{swingRecords.length}</b></button>
      <button type="button" role="tab" aria-selected={historyType === 'intraday'} className={historyType === 'intraday' ? 'active' : ''} onClick={() => { setHistoryType('intraday'); setStatusFilter('ALL'); setDateFilter('ALL'); }}>Intraday <b>{intradayRecords.length}</b></button>
      <button type="button" role="tab" aria-selected={historyType === 'options'} className={historyType === 'options' ? 'active' : ''} onClick={() => { setHistoryType('options'); setStatusFilter('ALL'); setDateFilter('ALL'); }}>Futures &amp; options <b>{optionsRecords.length}</b></button>
    </div>

    {historyType === 'swing' ? <div className="history-summary">
      <article><span>RECORDED SETUPS</span><strong>{data?.count ?? '—'}</strong></article>
      <article className="history-open"><span>STILL TRACKING</span><strong>{data?.open_count ?? '—'}</strong></article>
      <article className="history-target"><span>TARGET PRICE REACHED</span><strong>{data?.target_count ?? '—'}</strong></article>
      <article className="history-stop"><span>LOSS LIMIT REACHED</span><strong>{data?.stop_count ?? '—'}</strong></article>
      <article className="history-time"><span>TIME LIMIT ENDED</span><strong>{data?.time_exit_count ?? '—'}</strong></article>
    </div> : <div className="history-summary">
      <article><span>RECORDED SETUPS</span><strong>{currentRecords.length}</strong></article>
      {historyType === 'intraday' ? <>
        <article className="history-open"><span>BULLISH SETUPS</span><strong>{currentRecords.filter(record => record.direction === 'BULLISH').length}</strong></article>
        <article className="history-stop"><span>BEARISH SETUPS</span><strong>{currentRecords.filter(record => record.direction === 'BEARISH').length}</strong></article>
        <article className="history-target"><span>LAST SCAN DATE</span><strong>{currentRecords[0]?.signal_date || '—'}</strong></article>
      </> : <>
        <article className="history-open"><span>PLAN READY</span><strong>{currentRecords.filter(record => record.status === 'SETUP_READY').length}</strong></article>
        <article className="history-stop"><span>WAITING / UNAVAILABLE</span><strong>{currentRecords.filter(record => record.status !== 'SETUP_READY').length}</strong></article>
        <article className="history-target"><span>LAST PLAN DATE</span><strong>{currentRecords[0]?.signal_date || '—'}</strong></article>
      </>}
    </div>}

    <div className="history-filters">
      <label className="history-search"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a share" /></label>
      <label><span>Found on</span><select value={dateFilter} onChange={event => setDateFilter(event.target.value)}><option value="ALL">Any date</option>{dates.map(date => <option value={date} key={date}>{displayDate(date)}</option>)}</select></label>
      <label><span>{historyType === 'swing' ? 'What happened' : historyType === 'intraday' ? 'Direction' : 'Plan status'}</span><select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}><option value="ALL">Everything</option>{historyType === 'swing' ? <><option value="OPEN">Still tracking</option><option value="TARGET_HIT">Target price reached</option><option value="STOP_LOSS">Loss limit reached</option><option value="TIME_EXIT">Time limit ended</option></> : historyType === 'intraday' ? <><option value="BULLISH">Bullish</option><option value="BEARISH">Bearish</option></> : <><option value="SETUP_READY">Plan ready</option><option value="WAIT">Waiting</option><option value="UNAVAILABLE">Unavailable</option><option value="NO_TRADE">No trade</option></>}</select></label>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong><button className="text-action" onClick={() => load(true)}>Try again</button></div>}
    {loading ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Loading signal history</strong><span>Updating open setups from completed daily candles…</span></div>
      : !filtered.length ? <div className="empty-panel"><div className="empty-icon"><History size={19} /></div><strong>{currentRecords.length ? 'No history matches these filters' : historyType === 'swing' ? 'No swing history yet' : historyType === 'intraday' ? 'No intraday history yet' : 'No futures & options history yet'}</strong><span>{currentRecords.length ? 'Clear a filter or search for another symbol.' : historyType === 'swing' ? 'Run a scan in Swing Trading. Matching setups will be saved here automatically.' : historyType === 'intraday' ? 'Run an Intraday scan. Its setups will be saved here automatically.' : 'Open Futures & Options to save the latest plan for this market day.'}</span></div>
        : historyType === 'swing' ? <div className="history-date-groups">{Object.entries(grouped).map(([date, records]) => <section className="history-date-group" key={date}>
          <div className="history-date-heading"><div><span>{displayDate(date)}</span><strong>{records.length} {records.length === 1 ? 'setup' : 'setups'}</strong></div></div>
      <div className="history-table-wrap"><table className="history-table"><thead><tr><th>STOCK / WHY IT WAS FOUND</th><th>PRICE WHEN FOUND</th><th>LOSS LIMIT</th><th>TARGET PRICE</th><th>PRICE NOW / EXIT</th><th>WHAT HAPPENED</th><th>PRICE CHANGE</th></tr></thead><tbody>
            {records.map(record => {
              const resultPrice = record.exit_price ?? record.last_price;
              const returnClass = record.return_pct == null ? '' : record.return_pct >= 0 ? 'positive' : 'negative';
              return <tr key={record.id}>
                <td><button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ ...record, source: 'history' })} aria-label={`View ${record.symbol} stock research`}>{record.symbol}</button><details className="history-more-details"><summary>Why it was found</summary><small>{record.strategy_title.replace('Trend EMA Pullback', 'Buy a dip in a rising share').replace('Relative Strength Leader', 'Shares doing better than Nifty').replace('Capitulation Oversold Bounce', 'Possible bounce after a sharp fall').replace('Volatility Squeeze Expansion', 'Breakout after a quiet period').replace('Multi-Factor Confluence', 'Several positive checks agree')}</small></details></td>
                <td>{price(record.entry_price)}</td><td className="negative">{price(record.stop_loss)}</td><td className="positive">{price(record.target_1)}</td>
                <td>{price(resultPrice)}<small>{record.exit_date ? displayDate(record.exit_date) : `Checked ${record.last_checked_date || 'pending'}`}</small></td>
                <td><span className={`history-outcome ${record.outcome.toLowerCase()}`}>{statusLabel(record)}</span><small className="history-progress">Watched for {record.holding_sessions} of {record.max_holding_days} market days</small></td>
                <td className={returnClass}>{formatPercent(record.return_pct, { signed: true })}</td>
              </tr>;
            })}
          </tbody></table></div>
        </section>)}</div>
        : historyType === 'intraday' ? <div className="history-date-groups">{Object.entries(grouped).map(([date, records]) => <section className="history-date-group" key={date}>
          <div className="history-date-heading"><div><span>{displayDate(date)}</span><strong>{records.length} {records.length === 1 ? 'setup' : 'setups'}</strong></div></div>
          <div className="history-table-wrap"><table className="history-table"><thead><tr><th>STOCK / STRATEGY</th><th>DIRECTION</th><th>ENTRY</th><th>STOP LOSS</th><th>TARGET 1</th><th>TARGET 2</th><th>R:R</th><th>SCORE</th><th>LAST UPDATED</th></tr></thead><tbody>
            {records.map(record => <tr key={record.id}>
              <td><button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ ...record, source: 'intraday' })} aria-label={`View ${record.symbol} stock research`}>{record.symbol}</button><small>{record.strategy_title || record.strategy}</small></td>
              <td><span className={`history-outcome ${String(record.direction || '').toLowerCase()}`}>{record.direction || '—'}</span></td>
              <td>{price(record.entry_price)}</td><td className="negative">{price(record.stop_loss)}</td><td className="positive">{price(record.target_1)}</td><td>{price(record.target_2)}</td>
              <td>{record.risk_reward == null ? '—' : `${record.risk_reward} to 1`}</td><td>{record.confidence_score == null ? '—' : `${record.confidence_score}%`}</td>
              <td>{record.captured_at ? new Date(record.captured_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) : '—'} IST</td>
            </tr>)}
          </tbody></table></div>
        </section>)}</div>
        : <div className="history-date-groups">{Object.entries(grouped).map(([date, records]) => <section className="history-date-group" key={date}>
          <div className="history-date-heading"><div><span>{displayDate(date)}</span><strong>{records.length} {records.length === 1 ? 'plan' : 'plans'}</strong></div></div>
          <div className="history-table-wrap"><table className="history-table"><thead><tr><th>UNDERLYING / STRUCTURE</th><th>STATUS</th><th>BIAS</th><th>EXPIRY</th><th>OPTION LEGS</th><th>NET DEBIT</th><th>MAX LOSS · 1 LOT</th><th>MAX GAIN · 1 LOT</th><th>LAST UPDATED</th></tr></thead><tbody>
            {records.map(record => <tr key={record.id}>
              <td><strong>{record.symbol}</strong><small>{record.strategy_title || record.strategy || 'NIFTY options spread'}</small></td>
              <td><span className={`history-outcome ${String(record.status || '').toLowerCase()}`}>{String(record.status || '—').replaceAll('_', ' ')}</span></td>
              <td>{String(record.bias || '—').replaceAll('_', ' ')}</td><td>{record.expiry || '—'}</td>
              <td>{(record.legs || []).map(leg => `${leg.side} ${leg.symbol}`).join(' · ') || record.reason || 'No option legs saved'}</td>
              <td>{price(record.net_debit)}</td><td className="negative">{price(record.max_loss_one_lot)}</td><td className="positive">{price(record.max_profit_one_lot)}</td>
              <td>{record.captured_at ? new Date(record.captured_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) : '—'} IST</td>
            </tr>)}
          </tbody></table></div>
        </section>)}</div>}

    <p className="history-disclaimer">{historyType === 'swing' ? 'We check swing setups against completed daily candles. Prices are not live and may update with a delay.' : historyType === 'intraday' ? 'Intraday records keep the latest saved version of each stock and strategy for that market day. They are research signals, not live prices.' : 'Futures & options records keep the latest plan snapshot for each market day. Premiums and risk values can change quickly; verify live quotes before acting.'}</p>
  </section>;
}
