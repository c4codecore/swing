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
const REGIME_MARKS = {
  EXTREME_PANIC_OVERSOLD: '‼',
  BEARISH_CORRECTION: '▼',
  STRONG_BULL: '▲',
  PULLBACK_BULL: '↗',
  SIDEWAYS_CHOPPY: '↔',
  TRANSITION: '◇',
};
const stateClass = value => String(value || '').toLowerCase().replaceAll('_', '-');

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

  return <div className="regime-view">
    <section className="glass-card regime-summary">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <div className="regime-kicker">Confirmed market regime</div>
          <h2 className={`regime-badge state-${stateClass(confirmed)}`}><span aria-hidden="true">{REGIME_MARKS[confirmed] || '◇'}</span>{LABELS[confirmed] || confirmed}</h2>
          <div className="regime-description">{regimeData.description}</div>
        </div>
        <div className="exposure-card">
          <div className="regime-kicker">Risk scaling weight</div>
          <strong>{Math.round((regimeData.sizing_weight ?? 0) * 100)}%</strong>
          <div>Default, not a tested optimum</div>
        </div>
      </div>
      <p>{regimeData.recommended_action}</p>
      <small>{regimeData.sizing_weight_note}</small>
      <div className="regime-tags">
        <span className="strategy-tag">Raw today: {LABELS[regimeData.raw_regime] || regimeData.raw_regime}</span>
        <span className="strategy-tag">Matched: {regimeData.classification_source === 'catch_all' ? 'catch-all rule' : 'defined rule'} · {regimeData.matching_rule}</span>
        <span className="strategy-tag">Confirmed for {regimeData.days_in_state} daily close{regimeData.days_in_state === 1 ? '' : 's'}</span>
        {regimeData.pending_regime && <span className={`regime-badge pending state-${stateClass(regimeData.pending_regime)}`}>
          <span aria-hidden="true">◇</span>Pending change to {LABELS[regimeData.pending_regime] || regimeData.pending_regime} · {regimeData.pending_days}/{regimeData.pending_required_days} closes
        </span>}
      </div>
    </section>

    {regimeData.warnings?.map((warning, index) => <div className="portfolio-notice status-warning" role="status" key={index}>
      <AlertCircle size={16} /> <strong>{warning}</strong>
    </div>)}

    <div className="regime-columns">
      <section className="glass-card vitals-card">
        <h3><BarChart2 size={18} aria-hidden="true" /> Regime inputs</h3>
        <div className="metrics-grid">
          {metricRows.map(([label, value, suffix]) => <div className="metric-item" key={label}>
            <div className="metric-label">{label}</div>
            <div className="metric-val">{suffix === '₹' ? '₹' : ''}{display(value)}{suffix && suffix !== '₹' && value != null ? suffix : ''}</div>
          </div>)}
        </div>
        <div className="breadth-panel">
          <div className="breadth-heading">
            <strong>Liquidity-filtered market breadth</strong>
            <span>{breadth.universe_size ?? 0} symbols · {regimeData.universe?.mode || 'configured universe'} · minimum {breadth.minimum_universe_size ?? 200}</span>
          </div>
          <div>Above EMA20: {breadth.pct_above_20ema == null ? 'Unavailable' : `${breadth.pct_above_20ema}%`} · Above EMA50: {breadth.pct_above_50ema == null ? 'Unavailable' : `${breadth.pct_above_50ema}%`}</div>
          {breadth.warning && <div className="status-warning">Warning: {breadth.warning}</div>}
        </div>
      </section>

      <section className="glass-card strategy-matrix-card">
        <h3><Layers size={18} aria-hidden="true" /> Strategy gating</h3>
        <p>Gating is {regimeData.strategy_gating_enabled ? 'on' : 'off'} for the confirmed regime.</p>
        <div className="strategy-status-group">
          <strong><CheckCircle2 size={18} aria-hidden="true" /> Active strategies</strong>
          {active.length ? active.map(id => <div key={id} className="strategy-status-row">{STRATEGY_NAMES[id] || id}{onSelectStrategy && <button className="secondary-button" onClick={() => onSelectStrategy(id)}>View</button>}</div>) : <div>No strategies are active.</div>}
        </div>
        <div>
          <strong><AlertCircle size={18} aria-hidden="true" /> Skipped strategies</strong>
          {skipped.length ? skipped.map(item => <div key={item.id} className="strategy-status-row"><b>{STRATEGY_NAMES[item.id] || item.id}</b><small>{item.reason}</small></div>) : <div>None.</div>}
        </div>
      </section>
    </div>

    <section className="glass-card regime-history">
      <h3><Zap size={18} aria-hidden="true" /> Last 30 daily regimes</h3>
      <p>{regimeData.catch_all_days_last_30 ?? 0} of the last {history.length} days used the catch-all.</p>
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
