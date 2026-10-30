import React from 'react';
import { AlertCircle, BarChart2, CheckCircle2, Layers, Zap } from 'lucide-react';

const LABELS = {
  EXTREME_PANIC_OVERSOLD: 'Extreme panic',
  BEARISH_CORRECTION: 'Bearish correction',
  STRONG_BULL: 'Strong bull',
  PULLBACK_BULL: 'Bull pullback',
  SIDEWAYS_CHOPPY: 'Sideways / choppy',
};
const STRATEGY_NAMES = {
  trend_pullback: 'Buy a dip in a rising share',
  relative_strength: 'Shares doing better than Nifty',
  capitulation_reversal: 'Possible bounce after a sharp fall',
  volatility_squeeze: 'Breakout after a quiet period',
  multi_factor: 'Several positive checks agree',
};
const display = value => value == null || Number.isNaN(Number(value)) ? 'Unavailable' : `${value}`;

export default function RegimeView({ regimeData, onSelectStrategy }) {
  if (!regimeData) {
    return <div className="glass-card empty-state" style={{ padding: '4rem 1rem' }}>
      <div className="live-dot" style={{ margin: '0 auto 1.5rem', width: 14, height: 14, background: '#38bdf8' }} />
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>Checking the latest completed market close…</div>
    </div>;
  }

  const confirmed = regimeData.confirmed_regime || regimeData.regime;
  const metrics = regimeData.metrics || {};
  const breadth = regimeData.breadth || {};
  const history = regimeData.regime_history || [];
  const active = regimeData.active_strategies || regimeData.allowed_strategies || [];
  const skipped = regimeData.skipped_strategies || [];
  const metricRows = [
    ['NIFTY close', metrics.nifty_close, '₹'],
    ['EMA 20', metrics.ema_20, '₹'],
    ['EMA 50', metrics.ema_50, '₹'],
    ['EMA 200', metrics.ema_200, '₹'],
    ['20-day return', metrics.return_20d_pct, '%'],
    ['50-day return', metrics.return_50d_pct, '%'],
    ['RSI (14)', metrics.rsi_14, ''],
    ['Bollinger width', metrics.bollinger_width_pct, '%'],
    ['Width · 20-day mean', metrics.bollinger_width_20d_mean_pct, '%'],
    ['Width · 20-day std dev', metrics.bollinger_width_20d_std_pct, '%'],
    [`50 EMA slope · ${metrics.ema_50_slope_lookback || 5} days`, metrics.ema_50_slope_5d_pct, '%'],
    ['ATR (14)', metrics.atr_pct, '%'],
  ];

  return <div style={{ animation: 'fadeInUp 0.35s ease' }}>
    <section className="glass-card regime-summary" style={{ marginBottom: '1.5rem', borderLeft: `6px solid ${regimeData.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '.08em' }}>CONFIRMED MARKET REGIME</div>
          <h2 style={{ color: regimeData.color, margin: '.3rem 0', fontSize: '1.6rem' }}>{LABELS[confirmed] || confirmed}</h2>
          <div style={{ color: 'var(--text-muted)' }}>{regimeData.description}</div>
        </div>
        <div className="exposure-card" style={{ padding: '1rem 1.4rem', textAlign: 'center', minWidth: 170 }}>
          <div style={{ fontSize: '.7rem', color: 'var(--text-dim)' }}>RISK SCALING WEIGHT</div>
          <strong style={{ color: regimeData.color, fontSize: '2rem' }}>{Math.round((regimeData.sizing_weight ?? 0) * 100)}%</strong>
          <div style={{ fontSize: '.68rem', color: 'var(--text-muted)' }}>Default, not a tested optimum</div>
        </div>
      </div>
      <p style={{ margin: '1rem 0 0', color: 'var(--text-muted)' }}>{regimeData.recommended_action}</p>
      <small style={{ color: 'var(--text-dim)' }}>{regimeData.sizing_weight_note}</small>
      <div style={{ display: 'flex', gap: '.6rem', flexWrap: 'wrap', marginTop: '1rem' }}>
        <span className="strategy-tag">Raw today: {LABELS[regimeData.raw_regime] || regimeData.raw_regime}</span>
        <span className="strategy-tag">Matched: {regimeData.classification_source === 'catch_all' ? 'catch-all rule' : 'defined rule'} · {regimeData.matching_rule}</span>
        <span className="strategy-tag">Confirmed for {regimeData.days_in_state} daily close{regimeData.days_in_state === 1 ? '' : 's'}</span>
        {regimeData.pending_regime && <span className="strategy-tag" style={{ color: '#f59e0b', borderColor: '#f59e0b' }}>
          Pending change: {LABELS[regimeData.pending_regime] || regimeData.pending_regime} · {regimeData.pending_days}/{regimeData.pending_required_days} closes
        </span>}
      </div>
    </section>

    {regimeData.warnings?.map((warning, index) => <div className="portfolio-notice" role="status" key={index} style={{ marginBottom: '.8rem' }}>
      <AlertCircle size={16} /> <strong>{warning}</strong>
    </div>)}

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(330px, 1fr))', gap: '1.25rem' }}>
      <section className="glass-card vitals-card">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginTop: 0 }}><BarChart2 size={18} color="#38bdf8" /> Regime inputs</h3>
        <div className="metrics-grid">
          {metricRows.map(([label, value, suffix]) => <div className="metric-item" key={label}>
            <div className="metric-label">{label}</div>
            <div className="metric-val">{suffix === '₹' ? '₹' : ''}{display(value)}{suffix && suffix !== '₹' && value != null ? suffix : ''}</div>
          </div>)}
        </div>
        <div className="breadth-panel" style={{ marginTop: '1rem', padding: '1rem', borderRadius: 12, background: 'rgba(0,0,0,.25)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '.5rem', flexWrap: 'wrap' }}>
            <strong>Liquidity-filtered market breadth</strong>
            <span>{breadth.universe_size ?? 0} symbols · {regimeData.universe?.mode || 'configured universe'} · minimum {breadth.minimum_universe_size ?? 200}</span>
          </div>
          <div style={{ marginTop: '.5rem' }}>Above EMA20: {breadth.pct_above_20ema == null ? 'Unavailable' : `${breadth.pct_above_20ema}%`} · Above EMA50: {breadth.pct_above_50ema == null ? 'Unavailable' : `${breadth.pct_above_50ema}%`}</div>
          {breadth.warning && <div style={{ marginTop: '.5rem', color: '#fbbf24' }}>{breadth.warning}</div>}
        </div>
      </section>

      <section className="glass-card strategy-matrix-card">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginTop: 0 }}><Layers size={18} color="#a855f7" /> Strategy gating</h3>
        <p style={{ color: 'var(--text-muted)' }}>Gating is {regimeData.strategy_gating_enabled ? 'on' : 'off'} for the confirmed regime.</p>
        <div style={{ marginBottom: '1rem' }}>
          <strong><CheckCircle2 size={15} color="#10b981" /> Active</strong>
          {active.length ? active.map(id => <div key={id} style={{ margin: '.4rem 0' }}>{STRATEGY_NAMES[id] || id}{onSelectStrategy && <button className="btn-cyber-ghost" style={{ marginLeft: '.5rem', padding: '.2rem .5rem' }} onClick={() => onSelectStrategy(id)}>View</button>}</div>) : <div style={{ color: 'var(--text-muted)', marginTop: '.4rem' }}>No strategies are active.</div>}
        </div>
        <div>
          <strong><AlertCircle size={15} color="#f59e0b" /> Skipped</strong>
          {skipped.length ? skipped.map(item => <div key={item.id} style={{ margin: '.4rem 0' }}><b>{STRATEGY_NAMES[item.id] || item.id}</b><small style={{ display: 'block', color: 'var(--text-dim)' }}>{item.reason}</small></div>) : <div style={{ color: 'var(--text-muted)', marginTop: '.4rem' }}>None.</div>}
        </div>
      </section>
    </div>

    <section className="glass-card" style={{ marginTop: '1.25rem' }}>
      <h3 style={{ display: 'flex', alignItems: 'center', gap: '.5rem', marginTop: 0 }}><Zap size={17} color="#f59e0b" /> Last 30 daily regimes</h3>
      <p style={{ color: 'var(--text-muted)' }}>{regimeData.catch_all_days_last_30 ?? 0} of the last {history.length} days used the catch-all.</p>
      {history.length ? <div className="table-scroll"><table className="setups-table"><thead><tr><th>DATE</th><th>RAW</th><th>RULE</th><th>CONFIRMED</th><th>DAYS IN STATE</th><th>PENDING</th><th>WEIGHT</th></tr></thead><tbody>
        {history.map(item => <tr key={item.evaluated_on}>
          <td>{item.evaluated_on}</td><td>{LABELS[item.raw_regime] || item.raw_regime}</td><td>{item.classification_source === 'catch_all' ? 'Catch-all' : (item.matching_rule || '—')}</td><td>{LABELS[item.confirmed_regime] || item.confirmed_regime}</td><td>{item.days_in_state}</td>
          <td>{item.pending_regime ? `${LABELS[item.pending_regime] || item.pending_regime} ${item.pending_days}/${item.pending_required_days}` : '—'}</td><td>{Math.round(item.sizing_weight * 100)}%</td>
        </tr>)}
      </tbody></table></div> : <div style={{ color: 'var(--text-muted)' }}>No persisted regime history yet.</div>}
      {regimeData.evaluation_date && <small style={{ display: 'block', marginTop: '.75rem', color: 'var(--text-dim)' }}>Based on completed daily close {regimeData.evaluation_date} · saved in {regimeData.storage_backend}.</small>}
    </section>
  </div>;
}
