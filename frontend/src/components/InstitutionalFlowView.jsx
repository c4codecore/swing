import React, { useCallback, useEffect, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, RefreshCw, Volume2 } from 'lucide-react';

const money = value => value == null ? '—' : `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
const crore = value => value == null ? '—' : `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 1 })} Cr`;

function FlowTable({ title, rows, direction }) {
  const positive = direction === 'up';
  const MoveIcon = positive ? ArrowUpRight : ArrowDownRight;
  return <section className={`flow-panel ${positive ? 'flow-buying' : 'flow-selling'}`}>
    <div className="flow-panel-heading">
      <div><span className="flow-panel-icon"><MoveIcon size={17} /></span><div><h2>{title}</h2><p>{positive ? 'More buying pressure in recent trades' : 'More selling pressure in recent trades'}</p></div></div>
      <span className="flow-panel-count">{rows?.length || 0} stocks</span>
    </div>
    {!rows?.length ? <div className="flow-empty">No shares showed a clear buying or selling direction in this period.</div> : <div className="flow-table-wrap"><table className="flow-table">
      <thead><tr><th>STOCK</th><th>ESTIMATED ACTIVITY · 20 DAYS</th><th>PRICE PRESSURE</th><th>TRADING VS USUAL</th><th>PRICE NOW</th></tr></thead>
      <tbody>{rows.map((stock, index) => <tr key={stock.symbol}>
        <td><span className="flow-rank">{index + 1}</span><span className="flow-stock-name"><strong>{stock.symbol}</strong><small title={stock.company_name}>{stock.company_name}</small></span></td>
        <td className={positive ? 'positive' : 'negative'}><strong>{stock.flow_proxy_20d_cr > 0 ? '+' : ''}{crore(stock.flow_proxy_20d_cr)}</strong><small>Last 5 days: {stock.flow_proxy_5d_cr > 0 ? '+' : ''}{crore(stock.flow_proxy_5d_cr)}</small></td>
        <td className={positive ? 'positive' : 'negative'}><strong>{stock.pressure_20d_pct > 0 ? '+' : ''}{stock.pressure_20d_pct}%</strong><small>Last 5 days: {stock.pressure_5d_pct > 0 ? '+' : ''}{stock.pressure_5d_pct}%</small></td>
        <td><strong>{stock.volume_ratio_20d.toFixed(2)}× usual</strong><small>Average daily trades: {crore(stock.average_turnover_daily_cr)}</small></td>
        <td>{money(stock.close)}<small className={Number(stock.change_pct) >= 0 ? 'positive' : 'negative'}>{Number(stock.change_pct) > 0 ? '+' : ''}{stock.change_pct}% today</small></td>
      </tr>)}</tbody>
    </table></div>}
  </section>;
}

export default function InstitutionalFlowView() {
  const [limit, setLimit] = useState(10);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (refresh = false) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/flow-watchlist?limit=${limit}${refresh ? '&refresh=true' : ''}`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Volume flow scan could not be loaded.');
      setData(result);
      setError('');
    } catch (loadError) {
      setError(loadError.message || 'Volume flow scan could not be loaded.');
    } finally { setLoading(false); }
  }, [limit]);

  useEffect(() => { load(); }, [load]);

  return <section className="module-page flow-watch-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">MARKETVOICE · SHARE ACTIVITY</div><h1>Buying and selling activity</h1><p>See which shares have had more buying or selling pressure than usual.</p></div>
      <div className="flow-controls"><label>Show<select value={limit} onChange={event => setLimit(Number(event.target.value))}><option value={10}>Top 10</option><option value={20}>Top 20</option></select></label><button className="secondary-button" onClick={() => load(true)} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''} />{loading ? 'Checking shares' : 'Refresh list'}</button></div>
    </div>

    <div className="flow-method-strip"><Volume2 size={17} /><span><strong>{data?.scored_count ?? '—'} of {data?.universe_count ?? '50'} shares checked</strong><small>{data?.as_of ? `Prices through ${data.as_of}` : 'Using the latest completed market day'} · only shares traded worth at least ₹5 Cr/day</small></span><i>{data?.cached ? 'Updated within 5 minutes' : 'Looking back 20 market days'}</i></div>
    {error && <div className="portfolio-notice"><strong>{error}</strong><button className="text-action" onClick={() => load(true)}>Try again</button></div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking share activity</strong><span>Comparing recent prices and trading across liquid NSE shares…</span></div> : <div className="flow-panels">
      <FlowTable title="More buying activity" rows={data?.accumulation} direction="up" />
      <FlowTable title="More selling activity" rows={data?.distribution} direction="down" />
    </div>}
    <div className="flow-disclaimer"><strong>What these numbers mean</strong><p>We estimate buying or selling pressure from where the share price closed each day and how much it was traded. The rupee amount is only a rough estimate. It does not tell us who bought or sold, or prove that large investors were involved. Check company news and exchange reports before making a decision.</p></div>
  </section>;
}
