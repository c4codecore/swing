import React, { useCallback, useEffect, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, RefreshCw, Volume2 } from 'lucide-react';
import { formatINR, formatNumber, formatPercent } from '../utils/formatters';

const money = value => formatINR(value);
const crore = value => value == null ? '—' : `${formatINR(value)} Cr`;

function FlowTable({ title, rows, direction, days, onSelectStock }) {
  const positive = direction === 'up';
  const MoveIcon = positive ? ArrowUpRight : ArrowDownRight;
  const periodLabel = days === 1 ? 'market day' : 'market days';
  return <section className={`flow-panel ${positive ? 'flow-buying' : 'flow-selling'}`}>
    <div className="flow-panel-heading">
      <div><span className="flow-panel-icon"><MoveIcon size={17} /></span><div><h2>{title}</h2><p>{positive ? 'More buying pressure' : 'More selling pressure'} over the last {days} {periodLabel}</p></div></div>
      <span className="flow-panel-count">{rows?.length || 0} stocks</span>
    </div>
    {!rows?.length ? <div className="flow-empty">No shares showed a clear buying or selling direction in this period.</div> : <div className="flow-table-wrap"><table className="flow-table">
      <thead><tr><th>STOCK</th><th>ESTIMATED ACTIVITY · {days} {days === 1 ? 'DAY' : 'DAYS'}</th><th>PRICE PRESSURE · {days} {days === 1 ? 'DAY' : 'DAYS'}</th><th>TRADING VS USUAL</th><th>PRICE NOW</th></tr></thead>
      <tbody>{rows.map((stock, index) => { const period = stock.flow_periods?.[String(days)]; return <tr key={stock.symbol}>
        <td><span className="flow-rank">{index + 1}</span><span className="flow-stock-name"><button type="button" className="stock-name-button" onClick={() => onSelectStock?.({ symbol: stock.symbol, company_name: stock.company_name, source: 'flow' })} aria-label={`View ${stock.symbol} stock research`}>{stock.symbol}</button><small title={stock.company_name}>{stock.company_name}</small></span></td>
        <td className={positive ? 'positive' : 'negative'}><strong>{period?.flow_proxy_cr > 0 ? '+' : ''}{crore(period?.flow_proxy_cr)}</strong><small>Estimated activity · {days} {periodLabel}</small></td>
        <td className={positive ? 'positive' : 'negative'}><strong>{formatPercent(period?.pressure_pct, { signed: true })}</strong><small>Price pressure · {days} {periodLabel}</small></td>
        <td><strong>{formatNumber(stock.volume_ratio_20d)}× usual</strong><small>Average daily trades: {crore(stock.average_turnover_daily_cr)}</small></td>
        <td>{money(stock.close)}<small className={Number(stock.change_pct) >= 0 ? 'positive' : 'negative'}>{formatPercent(stock.change_pct, { signed: true })} today</small></td>
      </tr>; })}</tbody>
    </table></div>}
  </section>;
}

export default function InstitutionalFlowView({ onSelectStock }) {
  const [limit, setLimit] = useState(10);
  const [days, setDays] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (refresh = false) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/flow-watchlist?limit=${limit}&days=${days}${refresh ? '&refresh=true' : ''}`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Volume flow scan could not be loaded.');
      setData(result);
      setError('');
    } catch (loadError) {
      setError(loadError.message || 'Volume flow scan could not be loaded.');
    } finally { setLoading(false); }
  }, [limit, days]);

  useEffect(() => { load(); }, [load]);

  return <section className="module-page flow-watch-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">MARKETVOICE · SHARE ACTIVITY</div><h1>Buying and selling activity</h1><p>See which shares have had more buying or selling pressure than usual.</p></div>
      <div className="flow-controls"><label>Period<select value={days} onChange={event => setDays(Number(event.target.value))}><option value={1}>Last 1 market day</option><option value={2}>Last 2 market days</option><option value={5}>Last 5 market days</option><option value={10}>Last 10 market days</option><option value={20}>Last 20 market days</option></select></label><label>Show<select value={limit} onChange={event => setLimit(Number(event.target.value))}><option value={10}>Top 10</option><option value={20}>Top 20</option></select></label><button className="secondary-button" onClick={() => load(true)} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''} />{loading ? 'Checking shares' : 'Refresh list'}</button></div>
    </div>

    <div className="flow-method-strip"><Volume2 size={17} /><span><strong>{data?.scored_count ?? '—'} of {data?.universe_count ?? '500'} NIFTY 500 shares checked</strong><small>{data?.as_of ? `Prices through ${data.as_of}` : 'Using the latest completed market day'} · only shares traded worth at least ₹5 Cr/day</small></span><i>{data?.cached ? 'Cached result' : 'Activity window'} · Last {days} market {days === 1 ? 'day' : 'days'}</i></div>
    {error && <div className="portfolio-notice"><strong>{error}</strong><button className="text-action" onClick={() => load(true)}>Try again</button></div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking share activity</strong><span>Comparing recent prices and trading across liquid NSE shares…</span></div> : <div className="flow-panels">
      <FlowTable title="More buying activity" rows={data?.accumulation} direction="up" days={days} onSelectStock={onSelectStock} />
      <FlowTable title="More selling activity" rows={data?.distribution} direction="down" days={days} onSelectStock={onSelectStock} />
    </div>}
    <div className="flow-disclaimer"><strong>What these numbers mean</strong><p>We estimate buying or selling pressure from where the share price closed each day and how much it was traded. The rupee amount is only a rough estimate. It does not tell us who bought or sold, or prove that large investors were involved. Check company news and exchange reports before making a decision.</p></div>
  </section>;
}
