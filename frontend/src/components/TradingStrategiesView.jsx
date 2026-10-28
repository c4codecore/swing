import React, { useEffect, useState } from 'react';
import { Activity, ArrowUpRight, CandlestickChart, RefreshCw, ShieldAlert } from 'lucide-react';

function price(value) {
  const number = Number(value);
  return value == null || value === '' || !Number.isFinite(number)
    ? '—'
    : `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

export default function TradingStrategiesView({ mode, connected, onConnect }) {
  const isOptions = mode === 'options';
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
        const response = await fetch(isOptions ? '/api/options' : '/api/intraday', { cache: 'no-store' });
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
  }, [isOptions, refreshKey]);

  const directional = isOptions ? data?.status === 'SETUP_READY' : ['LONG_CALL_BIAS', 'LONG_PUT_BIAS'].includes(data?.signal);
  const statusText = isOptions
    ? data?.status === 'SETUP_READY' ? 'Example plan is ready' : data?.status === 'WAIT' ? 'Wait for a clearer move' : data?.status === 'NO_TRADE' ? 'No plan right now' : 'Option prices unavailable'
    : data?.signal === 'LONG_CALL_BIAS' ? 'Nifty may rise' : data?.signal === 'LONG_PUT_BIAS' ? 'Nifty may fall' : 'Wait · no clear price move';
  const signalTone = directional ? (isOptions || data?.signal === 'LONG_CALL_BIAS' ? 'positive' : 'negative') : 'neutral';

  return <section className="module-page trading-strategy-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">LIVE MARKET EXAMPLES · NO ORDERS PLACED</div><h1>{isOptions ? 'Nifty options example' : 'Today’s Nifty check'}</h1><p>{isOptions ? 'Shows one example of how Nifty options could be combined, with the possible loss shown.' : 'Checks whether Nifty moves beyond its first 15-minute high or low, with today’s average price for context.'}</p></div>
      <div className="trading-module-actions"><span className={`portfolio-connection ${connected ? 'connected' : ''}`}><i />{connected ? 'IIFL connected' : 'IIFL login needed'}</span><button className="secondary-button" onClick={() => setRefreshKey(key => key + 1)}><RefreshCw size={14} />Refresh</button></div>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Checking live market prices</strong><span>Looking for a clear move before showing an example…</span></div>
      : data && <>
        <div className="trading-signal-banner">
          <div className={`trading-signal-icon ${signalTone}`}>{isOptions ? <Activity size={19} /> : <CandlestickChart size={19} />}</div>
          <div className="trading-signal-copy"><span>{isOptions ? 'NIFTY OPTIONS · NEXT AVAILABLE DATE' : `TODAY’S NIFTY MOVE · ${data.session_date || 'LATEST SESSION'}`}</span><strong className={signalTone}>{statusText}</strong><small>{isOptions ? data.strategy || data.reason : (data.reasons || []).join(' ')}</small></div>
          <div className="trading-spot"><span>NIFTY PRICE</span><strong>{price(data.spot)}</strong><small>{data.quote_at ? `Updated ${new Date(data.quote_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : data.candles_as_of ? `Latest price ${new Date(data.candles_as_of).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : 'Waiting for price'}</small></div>
        </div>

        {!isOptions && <>
          <div className="trading-metrics-grid">
            <article><span>HIGH IN FIRST 15 MINUTES</span><strong>{price(data.opening_range_high)}</strong></article>
            <article><span>LOW IN FIRST 15 MINUTES</span><strong>{price(data.opening_range_low)}</strong></article>
            <article><span>AVERAGE PRICE TODAY</span><strong>{price(data.vwap)}</strong></article>
            <article><span>SHORT-TERM AVERAGE PRICES</span><strong>{price(data.ema9)} / {price(data.ema20)}</strong></article>
          </div>
          {data.entry != null && <div className="intraday-plan-grid"><article><span>PRICE TO REVIEW</span><strong>{price(data.entry)}</strong></article><article><span>EXIT IF PRICE FALLS TO</span><strong>{price(data.stop)}</strong></article><article><span>POSSIBLE GAIN PRICE</span><strong>{price(data.target_2r)}</strong></article><article><span>POSSIBLE LOSS SIZE</span><strong>{data.risk_points} points</strong></article></div>}
          <div className="trading-rationale"><strong>What we checked</strong><ul>{(data.reasons || []).map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>
        </>}

        {isOptions && data.status === 'SETUP_READY' && <>
          <div className="options-spread-summary"><article><span>LAST DATE FOR THIS OPTION</span><strong>{data.expiry}</strong></article><article><span>SHARES IN ONE BUNDLE</span><strong>{data.lot_size}</strong></article><article><span>AMOUNT PAID PER SHARE</span><strong>{price(data.net_debit)}</strong></article><article><span>PRICE NEEDED TO AVOID A LOSS</span><strong>{price(data.breakeven)}</strong></article></div>
          <div className="options-legs"><div className="options-legs-heading"><strong>{data.strategy}</strong><span>Difference between option prices: {data.spread_width} points</span></div><div className="options-legs-table"><div className="options-leg-row options-leg-header"><span>BUY OR SELL</span><span>OPTION</span><span>PRICE LEVEL</span><span>PRICE NOW</span></div>{data.legs.map((leg, index) => <div className="options-leg-row" key={`${leg.instrument_id}-${index}`}><span className={leg.side === 'BUY' ? 'positive' : 'negative'}>{leg.side === 'BUY' ? 'BUY' : 'SELL'}</span><span>{leg.symbol}</span><span>{price(leg.strike)}</span><span>{price(leg.premium)}</span></div>)}</div><div className="options-payoff-row"><div><span>HIGHEST POSSIBLE LOSS · 1 BUNDLE</span><strong className="negative">{price(data.max_loss_one_lot)}</strong></div><div><span>HIGHEST POSSIBLE GAIN · 1 BUNDLE</span><strong className="positive">{price(data.max_profit_one_lot)}</strong></div></div></div>
          <div className="trading-rationale"><strong>Why this example appears</strong><ul><li>{data.reason}</li><li>The loss shown is an estimate before fees and taxes. Option prices can change quickly.</li></ul></div>
        </>}
        {isOptions && data.status !== 'SETUP_READY' && <div className="empty-panel options-wait-state"><div className="empty-icon"><ShieldAlert size={19} /></div><strong>{statusText}</strong><span>{data.reason || 'Wait for a fresh NIFTY directional setup.'}</span></div>}

        <p className="trading-disclaimer">{data.disclaimer || 'Research scenario only. Not personalized financial advice. Verify IIFL prices and your risk limit; this app never places orders.'} {isOptions && 'SEBI reports high loss rates among individual equity F&O traders; use extra caution.'}</p>
        <div className="trading-data-foot"><span className={data.fresh === false ? 'stale' : 'fresh'}><i />{data.fresh === false ? 'LAST SESSION / STALE' : 'UPDATING EVERY 30 SECONDS'}</span><span>{data.data_source}</span></div>
      </>}
  </section>;
}
