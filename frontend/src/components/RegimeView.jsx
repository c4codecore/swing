import React from 'react';
import { Compass, ShieldAlert, CheckCircle2, XCircle, AlertCircle, BarChart2, Zap, ArrowRight, Shield, Layers, TrendingUp } from 'lucide-react';
import { playTone } from '../utils/soundFx';

export default function RegimeView({ regimeData, onSelectStrategy }) {
  if (!regimeData) {
    return (
      <div className="glass-card empty-state" style={{ padding: '4rem 1rem' }}>
        <div className="live-dot" style={{ margin: '0 auto 1.5rem', width: 14, height: 14, background: '#38bdf8' }} />
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem' }}>
          DECODING MULTI-FACTOR MARKET REGIME TELEMETRY...
        </div>
      </div>
    );
  }

  const { regime, title, color, description, recommended_action, max_capital_exposure_pct, allowed_strategies, metrics } = regimeData;

  const marketPhases = [
    { key: 'ACCUMULATION_BASE', label: 'Accumulation Base', desc: 'Smart money buying stealthily after panic crash.' },
    { key: 'BULLISH_EXPANSION', label: 'Bullish Expansion', desc: 'Sustained markup with high momentum & high breadth.' },
    { key: 'BLOW_OFF_TOP', label: 'Blow-Off Top', desc: 'Parabolic climax with excessive retail participation.' },
    { key: 'DISTRIBUTION', label: 'Distribution', desc: 'Institutions selling into strength, range volatility.' },
    { key: 'BEARISH_CORRECTION', label: 'Bearish Correction', desc: 'Active downtrend, breakouts fail, cash is king.' },
    { key: 'CAPITULATION_PANIC', label: 'Capitulation Panic', desc: 'Deep RSI oversold snapback opportunities.' }
  ];

  const allStrategies = [
    { 
      id: "trend_pullback", 
      name: "Trend EMA Pullback", 
      target: ["BULLISH_EXPANSION"],
      bestRegime: "Bullish Expansion",
      desc: "Dip buying into 20/50 EMA in established institutional uptrends. High win rate in bull cycles; high whipsaw risk in corrections."
    },
    { 
      id: "relative_strength", 
      name: "Relative Strength Leader", 
      target: ["BEARISH_CORRECTION", "DISTRIBUTION", "BULLISH_EXPANSION"],
      bestRegime: "All Regimes / Bear Correction",
      desc: "Stocks making fresh 20-day highs while Nifty is making lower lows. The #1 hedge strategy during market downturns."
    },
    { 
      id: "capitulation_reversal", 
      name: "Capitulation Oversold Bounce", 
      target: ["CAPITULATION_PANIC", "BEARISH_CORRECTION"],
      bestRegime: "Panic Capitulation",
      desc: "Deep RSI < 25 + Bollinger lower band pierce. Exploits extreme panic selling for rapid 2R-3R mean reversion bounces."
    },
    { 
      id: "volatility_squeeze", 
      name: "Volatility Squeeze Expansion", 
      target: ["ACCUMULATION_BASE", "BULLISH_EXPANSION"],
      bestRegime: "Accumulation / Consolidation",
      desc: "Bollinger Bands contracting inside Keltner Channels. Massive kinetic energy release when momentum breaks out."
    }
  ];

  const isCurrentPhase = (phaseKey) => {
    if (!regime) return false;
    return regime.toUpperCase().includes(phaseKey.replace('_', '')) || regime === phaseKey;
  };

  return (
    <div style={{ animation: 'fadeInUp 0.35s ease' }}>
      {/* Hero Overview Banner */}
      <div 
        className="glass-card regime-summary" 
        style={{ 
          marginBottom: '2rem', 
          borderLeft: `6px solid ${color}`,
          background: 'linear-gradient(135deg, rgba(8, 14, 26, 0.85) 0%, rgba(12, 18, 32, 0.6) 100%)',
          boxShadow: `0 20px 50px rgba(0,0,0,0.6), 0 0 35px ${color}1a`
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ flex: '1 1 500px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              <span className="live-dot" style={{ background: color, width: 9, height: 9 }}></span>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.75rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em' }}>
                {title}
              </h2>
              <span style={{ 
                background: `${color}18`, 
                color: color, 
                border: `1px solid ${color}45`,
                padding: '0.25rem 0.75rem',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                letterSpacing: '0.05em'
              }}>
                [REGIME: {regime}]
              </span>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: '1.65', maxWidth: '820px' }}>
              {description}
            </p>
          </div>

          {/* Capital Exposure Cockpit Card */}
          <div className="exposure-card" style={{ 
            background: 'rgba(0,0,0,0.45)', 
            border: '1px solid rgba(255,255,255,0.08)', 
            borderRadius: '16px', 
            padding: '1.25rem 1.75rem',
            textAlign: 'center',
            minWidth: '220px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.4)'
          }}>
            <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.35rem' }}>
              Recommended Capital Exposure
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2.4rem', fontWeight: 900, color: color, lineHeight: 1.1 }}>
              {max_capital_exposure_pct}%
            </div>
            <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.35rem', fontFamily: 'var(--font-mono)' }}>
              🛡 Preserve {100 - max_capital_exposure_pct}% in Protective Cash
            </div>
          </div>
        </div>

        {/* Daily Execution Directive */}
        <div className="execution-directive" style={{ 
          background: `${color}0d`, 
          borderLeft: `4px solid ${color}`,
          borderTop: '1px solid rgba(255,255,255,0.06)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '12px',
          padding: '1rem 1.25rem'
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 800, color: color, textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)', marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Zap size={14} /> Tactical Execution Directive
          </div>
          <div style={{ fontSize: '0.92rem', color: '#f8fafc', fontWeight: 500, lineHeight: '1.5' }}>
            {recommended_action}
          </div>
        </div>
      </div>

      {/* Market Cycle Progression Roadmap */}
      <div className="glass-card phase-roadmap" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: '#38bdf8', letterSpacing: '0.1em' }}>
              [MACRO CYCLE TELEMETRY]
            </div>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 800 }}>
              6-Phase Market Regime Roadmap
            </h3>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Active Stage Highlighted
          </div>
        </div>

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
          gap: '0.75rem',
          position: 'relative'
        }}>
          {marketPhases.map((phase, idx) => {
            const active = isCurrentPhase(phase.key);
            return (
              <div 
                key={phase.key}
                className={`phase-tile ${active ? 'is-active' : ''}`}
                style={{
                  background: active ? `${color}18` : 'rgba(0,0,0,0.3)',
                  border: active ? `1.5px solid ${color}` : '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '12px',
                  padding: '1rem',
                  boxShadow: active ? `0 0 25px ${color}33` : 'none',
                  transition: 'all 0.3s ease',
                  position: 'relative'
                }}
              >
                {active && (
                  <span style={{ 
                    position: 'absolute', 
                    top: '-9px', 
                    right: '12px', 
                    background: color, 
                    color: '#000', 
                    fontSize: '0.62rem', 
                    fontFamily: 'var(--font-mono)', 
                    fontWeight: 800, 
                    padding: '0.1rem 0.45rem', 
                    borderRadius: '999px',
                    letterSpacing: '0.05em'
                  }}>
                    ACTIVE NOW
                  </span>
                )}
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: active ? color : 'var(--text-dim)', marginBottom: '0.25rem' }}>
                  STAGE 0{idx + 1}
                </div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem', fontWeight: 700, color: active ? '#fff' : 'var(--text-muted)', marginBottom: '0.4rem' }}>
                  {phase.label}
                </div>
                <div style={{ fontSize: '0.72rem', color: active ? 'var(--text-main)' : 'var(--text-dim)', lineHeight: '1.4' }}>
                  {phase.desc}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Metrics & Strategy Matrix Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.75rem' }}>
        
        {/* Nifty 50 Technical Vitals Deck */}
        <div className="glass-card vitals-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart2 size={18} color="#38bdf8" /> Nifty 50 Technical Vitals
            </h3>
            <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              LIVE BENCHMARK
            </span>
          </div>
          
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-label">Current Nifty Close</div>
              <div className="metric-val" style={{ color: '#fff' }}>₹{metrics?.nifty_close}</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">14-Day RSI (Momentum)</div>
              <div className="metric-val" style={{ color: (metrics?.rsi_14 < 35 || metrics?.rsi_14 > 65) ? '#f59e0b' : '#10b981' }}>
                {metrics?.rsi_14}
              </div>
            </div>
            <div className="metric-item">
              <div className="metric-label">20 Day Trend EMA</div>
              <div className="metric-val">₹{metrics?.ema_20}</div>
            </div>
            <div className="metric-item">
              <div className="metric-label">50 Day Baseline EMA</div>
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
              <div className="metric-val" style={{ color: '#38bdf8' }}>{metrics?.atr_pct}%</div>
            </div>
          </div>

          {/* Market Breadth Indicator Progress */}
          <div className="breadth-panel" style={{ marginTop: '1.5rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Market Breadth (% Stocks &gt; 50 EMA)</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, color: metrics?.breadth_above_50ema_pct >= 50 ? '#10b981' : '#f43f5e' }}>
                {metrics?.breadth_above_50ema_pct}%
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' }}>
              <div 
                style={{
                  width: `${Math.min(100, Math.max(0, metrics?.breadth_above_50ema_pct || 0))}%`,
                  height: '100%',
                  background: metrics?.breadth_above_50ema_pct >= 50 
                    ? 'linear-gradient(90deg, #10b981, #34d399)' 
                    : 'linear-gradient(90deg, #f43f5e, #fb7185)',
                  borderRadius: '999px',
                  transition: 'width 1s ease'
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.35rem', fontFamily: 'var(--font-mono)' }}>
              <span>0% (Extreme Weakness)</span>
              <span>50% (Equilibrium)</span>
              <span>100% (Broad Market Rally)</span>
            </div>
          </div>
        </div>

        {/* Strategy Synergy Compatibility Matrix */}
        <div className="glass-card strategy-matrix-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Layers size={18} color="#a855f7" /> Strategy Activation Matrix
            </h3>
            <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              REGIME SYNERGY
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {allStrategies.map((strat) => {
              const isAllowed = strat.target.some(t => regime?.includes(t) || t === regime);
              const badgeBg = isAllowed ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.1)';
              const badgeColor = isAllowed ? '#10b981' : '#94a3b8';
              const badgeBorder = isAllowed ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.08)';

              return (
                <div 
                  key={strat.id}
                  className={`strategy-row ${isAllowed ? 'is-allowed' : 'is-muted'}`}
                  style={{
                    background: isAllowed ? 'rgba(16,185,129,0.04)' : 'rgba(0,0,0,0.3)',
                    border: `1px solid ${isAllowed ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.06)'}`,
                    borderRadius: '12px',
                    padding: '0.9rem 1.1rem',
                    transition: 'all 0.25s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {isAllowed ? <CheckCircle2 size={15} color="#10b981" /> : <AlertCircle size={15} color="#64748b" />}
                      <span style={{ fontFamily: 'var(--font-body)', fontWeight: 700, fontSize: '0.9rem', color: isAllowed ? '#fff' : 'var(--text-muted)' }}>
                        {strat.name}
                      </span>
                    </div>

                    <span style={{
                      fontSize: '0.65rem',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 800,
                      padding: '0.2rem 0.55rem',
                      borderRadius: '999px',
                      background: badgeBg,
                      color: badgeColor,
                      border: `1px solid ${badgeBorder}`
                    }}>
                      {isAllowed ? 'ACTIVATED' : 'CAUTION / MUTED'}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.45', marginBottom: '0.65rem' }}>
                    {strat.desc}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.5rem' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      Prime Cycle: {strat.bestRegime}
                    </span>

                    {onSelectStrategy && (
                      <button 
                        onClick={() => {
                          playTone('click');
                          onSelectStrategy(strat.id);
                        }}
                        className="btn-cyber-ghost"
                        style={{ padding: '0.25rem 0.65rem', fontSize: '0.72rem' }}
                      >
                        View Setups <ArrowRight size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
}
