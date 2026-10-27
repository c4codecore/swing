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
    ? data?.status === 'SETUP_READY' ? 'DEFINED-RISK SPREAD' : data?.status === 'WAIT' ? 'WAIT FOR SIGNAL' : data?.status === 'NO_TRADE' ? 'NO TRADE' : 'OPTIONS DATA UNAVAILABLE'
    : data?.signal === 'LONG_CALL_BIAS' ? 'BULLISH · CALL BIAS' : data?.signal === 'LONG_PUT_BIAS' ? 'BEARISH · PUT BIAS' : 'WAIT · NO CONFIRMED BREAK';
  const signalTone = directional ? (isOptions || data?.signal === 'LONG_CALL_BIAS' ? 'positive' : 'negative') : 'neutral';

  return <section className="module-page trading-strategy-page">
    <div className="module-heading">
      <div><div className="eyebrow subtle-eyebrow">IIFL LIVE · READ-ONLY RESEARCH</div><h1>{isOptions ? 'Options strategies' : 'Intraday strategies'}</h1><p>{isOptions ? 'NIFTY debit spreads from the live intraday bias and IIFL option premiums.' : 'NIFTY 15-minute opening-range breakout with VWAP trend confirmation.'}</p></div>
      <div className="trading-module-actions"><span className={`portfolio-connection ${connected ? 'connected' : ''}`}><i />{connected ? 'IIFL connected' : 'IIFL login needed'}</span><button className="secondary-button" onClick={() => setRefreshKey(key => key + 1)}><RefreshCw size={14} />Refresh</button></div>
    </div>

    {error && <div className="portfolio-notice"><strong>{error}</strong>{!connected && <button className="text-action" onClick={onConnect}>Connect IIFL <ArrowUpRight size={14} /></button>}</div>}
    {loading && !data ? <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Reading IIFL market data</strong><span>Calculating a rule-based setup…</span></div>
      : data && <>
        <div className="trading-signal-banner">
          <div className={`trading-signal-icon ${signalTone}`}>{isOptions ? <Activity size={19} /> : <CandlestickChart size={19} />}</div>
          <div className="trading-signal-copy"><span>{isOptions ? 'NIFTY OPTIONS · NEXT AVAILABLE EXPIRY' : `${data.strategy} · ${data.session_date || 'RECENT SESSION'}`}</span><strong className={signalTone}>{statusText}</strong><small>{isOptions ? data.strategy || data.reason : (data.reasons || []).join(' ')}</small></div>
          <div className="trading-spot"><span>NIFTY SPOT</span><strong>{price(data.spot)}</strong><small>{data.quote_at ? `Tick ${new Date(data.quote_at).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : data.candles_as_of ? `Candle ${new Date(data.candles_as_of).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST` : 'Waiting for quote'}</small></div>
        </div>

        {!isOptions && <>
          <div className="trading-metrics-grid">
            <article><span>OPENING RANGE HIGH</span><strong>{price(data.opening_range_high)}</strong></article>
            <article><span>OPENING RANGE LOW</span><strong>{price(data.opening_range_low)}</strong></article>
            <article><span>VWAP</span><strong>{price(data.vwap)}</strong></article>
            <article><span>EMA 9 / 20</span><strong>{price(data.ema9)} / {price(data.ema20)}</strong></article>
          </div>
          {data.entry != null && <div className="intraday-plan-grid"><article><span>SPOT ENTRY REFERENCE</span><strong>{price(data.entry)}</strong></article><article><span>INVALIDATION / STOP</span><strong>{price(data.stop)}</strong></article><article><span>2R TARGET REFERENCE</span><strong>{price(data.target_2r)}</strong></article><article><span>SPOT RISK</span><strong>{data.risk_points} points</strong></article></div>}
          <div className="trading-rationale"><strong>Signal checks</strong><ul>{(data.reasons || []).map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>
        </>}

        {isOptions && data.status === 'SETUP_READY' && <>
          <div className="options-spread-summary"><article><span>EXPIRY</span><strong>{data.expiry}</strong></article><article><span>LOT SIZE</span><strong>{data.lot_size}</strong></article><article><span>NET DEBIT / SHARE</span><strong>{price(data.net_debit)}</strong></article><article><span>BREAKEVEN AT EXPIRY</span><strong>{price(data.breakeven)}</strong></article></div>
          <div className="options-legs"><div className="options-legs-heading"><strong>{data.strategy}</strong><span>{data.spread_width} point spread</span></div><div className="options-legs-table"><div className="options-leg-row options-leg-header"><span>LEG</span><span>CONTRACT</span><span>STRIKE</span><span>LIVE PREMIUM</span></div>{data.legs.map((leg, index) => <div className="options-leg-row" key={`${leg.instrument_id}-${index}`}><span className={leg.side === 'BUY' ? 'positive' : 'negative'}>{leg.side}</span><span>{leg.symbol}</span><span>{price(leg.strike)}</span><span>{price(leg.premium)}</span></div>)}</div><div className="options-payoff-row"><div><span>MAX LOSS · 1 LOT</span><strong className="negative">{price(data.max_loss_one_lot)}</strong></div><div><span>MAX PROFIT · 1 LOT</span><strong className="positive">{price(data.max_profit_one_lot)}</strong></div></div></div>
          <div className="trading-rationale"><strong>Why this structure</strong><ul><li>{data.reason}</li><li>Maximum loss shown is the estimated net debit for one lot, before fees, taxes and slippage.</li></ul></div>
        </>}
        {isOptions && data.status !== 'SETUP_READY' && <div className="empty-panel options-wait-state"><div className="empty-icon"><ShieldAlert size={19} /></div><strong>{statusText}</strong><span>{data.reason || 'Wait for a fresh NIFTY directional setup.'}</span></div>}

        <p className="trading-disclaimer">{data.disclaimer || 'Research scenario only. Not personalized financial advice. Verify IIFL prices and your risk limit; this app never places orders.'} {isOptions && 'SEBI reports high loss rates among individual equity F&O traders; use extra caution.'}</p>
        <div className="trading-data-foot"><span className={data.fresh === false ? 'stale' : 'fresh'}><i />{data.fresh === false ? 'LAST SESSION / STALE' : 'UPDATING EVERY 30 SECONDS'}</span><span>{data.data_source}</span></div>
      </>}
  </section>;
}
