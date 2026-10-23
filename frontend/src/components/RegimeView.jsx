import React from 'react';
import { Compass, ShieldAlert, CheckCircle2, XCircle, Info, BarChart2, Zap } from 'lucide-react';

export default function RegimeView({ regimeData, onSelectStrategy }) {
  if (!regimeData) {
    return <div className="empty-state">Loading Market Regime Intelligence...</div>;
  }

  const { regime, title, color, description, recommended_action, max_capital_exposure_pct, allowed_strategies, metrics } = regimeData;

  const allStrategies = [
    { id: "trend_pullback", name: "Trend EMA Pullback", desc: "Uptrend dip buying (High win rate in Bull markets, prone to whipsaws in Bear)." },
    { id: "relative_strength", name: "Relative Strength Leader", desc: "Outperforming stocks making highs while Nifty is weak (Super effective in Bear/Choppy)." },
    { id: "capitulation_reversal", name: "Capitulation Oversold Bounce", desc: "Deep RSI < 25 snapback bounce (Essential for Bearish market crashes)." },
    { id: "volatility_squeeze", name: "Volatility Squeeze Expansion", desc: "Energy compression breakout (Best in Sideways to Bullish transition)." }
  ];

  return (
    <div>
      {/* Hero Overview */}
      <div className="glass-card" style={{ marginBottom: '1.5rem', borderLeft: `6px solid ${color}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <span className="live-dot" style={{ background: color }}></span>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>{title}</h2>
              <span style={{ 
                background: `${color}20`, 
                color: color, 
                border: `1px solid ${color}50`,
                padding: '0.2rem 0.6rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: 700
              }}>
                {regime}
              </span>
            </div>
            <p style={{ color: 'var(--text-muted)', maxWidth: '780px', fontSize: '0.95rem', lineHeight: '1.6' }}>
              {description}
            </p>
          </div>

          <div style={{ 
            background: 'rgba(0,0,0,0.3)', 
            border: '1px solid var(--border-subtle)', 
            borderRadius: '12px', 
            padding: '1rem 1.5rem',
            textAlign: 'center',
            minWidth: '200px'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Recommended Exposure
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2rem', fontWeight: 800, color: color }}>
              {max_capital_exposure_pct}%
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Keep {100 - max_capital_exposure_pct}% Capital in Cash
            </div>
          </div>
        </div>

        {/* Action Directive */}
        <div className="action-guidance-card" style={{ borderLeftColor: color }}>
          <div className="action-guidance-title">Daily Execution Directive</div>
          <div className="action-guidance-text">{recommended_action}</div>
        </div>
      </div>

      {/* Metrics & Strategy Matrix Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem' }}>
        
        {/* Nifty 50 Health Matrix */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart2 size={18} color="#38bdf8" /> Nifty 50 Technical Vitals
          </h3>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Current Nifty Close</div>
              <div className="metric-val">₹{metrics?.nifty_close}</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">14-Day RSI</div>
              <div className="metric-val" style={{ color: (metrics?.rsi_14 < 35 || metrics?.rsi_14 > 65) ? '#f59e0b' : '#10b981' }}>
                {metrics?.rsi_14}
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-label">20 Day EMA</div>
              <div className="metric-val">₹{metrics?.ema_20}</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">50 Day EMA</div>
              <div className="metric-val">₹{metrics?.ema_50}</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Distance from 20 EMA</div>
              <div className="metric-val" style={{ color: metrics?.dist_20ema_pct >= 0 ? '#10b981' : '#f43f5e' }}>
                {metrics?.dist_20ema_pct > 0 ? '+' : ''}{metrics?.dist_20ema_pct}%
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-label">Volatility (Daily ATR %)</div>
              <div className="metric-val">{metrics?.atr_pct}%</div>
            </div>
          </div>

          {/* Market Breadth Indicator */}
          <div className="allocation-box" style={{ marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Market Breadth (% Stocks &gt; 50 EMA)</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: metrics?.breadth_above_50ema_pct >= 60 ? '#10b981' : '#f43f5e' }}>
                {metrics?.breadth_above_50ema_pct}%
              </span>
            </div>
            <div className="allocation-bar-bg">
              <div 
                className="allocation-bar-fill" 
                style={{ 
                  width: `${metrics?.breadth_above_50ema_pct || 50}%`,
                  background: metrics?.breadth_above_50ema_pct >= 60 ? '#10b981' : '#f43f5e'
                }} 
              />
            </div>
          </div>
        </div>

        {/* Strategy Permitted Radar */}
        <div className="glass-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={18} color="#a855f7" /> Strategy Permission Matrix
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            To protect your capital, only strategies engineered for the current market state are enabled.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {allStrategies.map(s => {
              const isAllowed = allowed_strategies?.some(allowed => 
                allowed.toLowerCase().includes(s.id.replace('_', '')) || s.id.includes(allowed.toLowerCase())
              );

              return (
                <div 
                  key={s.id} 
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    borderRadius: '10px',
                    background: isAllowed ? 'rgba(16,185,129,0.06)' : 'rgba(244,63,94,0.05)',
                    border: `1px solid ${isAllowed ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.15)'}`
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                      {isAllowed ? (
                        <CheckCircle2 size={16} color="#10b981" />
                      ) : (
                        <XCircle size={16} color="#f43f5e" />
                      )}
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: isAllowed ? '#fff' : 'var(--text-dim)' }}>
                        {s.name}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {s.desc}
                    </div>
                  </div>

                  <span style={{ 
                    fontSize: '0.7rem', 
                    fontWeight: 700, 
                    padding: '0.2rem 0.5rem', 
                    borderRadius: '4px',
                    textTransform: 'uppercase',
                    background: isAllowed ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)',
                    color: isAllowed ? '#10b981' : '#f43f5e',
                    alignSelf: 'center',
                    whiteSpace: 'nowrap'
                  }}>
                    {isAllowed ? 'ACTIVE' : 'BLOCKED'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
