import React, { useState, useEffect, useRef } from 'react';

export default function StockChart({ symbol, tradePlan }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    fetch(`/api/chart/${symbol}`)
      .then(res => res.json())
      .then(json => {
        setData(json.candles || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load chart data", err);
        setLoading(false);
      });
  }, [symbol]);

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
        <div className="live-dot" style={{ margin: '0 auto 1rem', background: '#38bdf8', width: 12, height: 12 }}></div>
        Loading candlestick & indicator telemetry for {symbol}...
      </div>
    );
  }

  if (!data || data.length === 0) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>No chart data available for {symbol}</div>;
  }

  // Chart dimensions
  const width = 820;
  const height = 360;
  const padding = { top: 20, right: 60, bottom: 80, left: 10 };
  const rsiHeight = 60;
  const mainChartHeight = height - padding.bottom;

  // Price Extents
  const minPrice = Math.min(...data.map(d => d.low)) * 0.99;
  const maxPrice = Math.max(...data.map(d => d.high)) * 1.01;
  const priceRange = maxPrice - minPrice || 1;

  // Coordinate mappers
  const candleWidth = Math.max(3, (width - padding.left - padding.right) / data.length);
  const getX = (idx) => padding.left + (idx * candleWidth) + (candleWidth / 2);
  const getY = (val) => padding.top + (1 - (val - minPrice) / priceRange) * (mainChartHeight - padding.top);
  const getRsiY = (rsiVal) => height - padding.bottom + 20 + (1 - (rsiVal / 100)) * rsiHeight;

  // Generate EMA paths
  const ema20Points = data
    .map((d, i) => d.ema20 ? `${getX(i)},${getY(d.ema20)}` : null)
    .filter(Boolean)
    .join(' ');

  const ema50Points = data
    .map((d, i) => d.ema50 ? `${getX(i)},${getY(d.ema50)}` : null)
    .filter(Boolean)
    .join(' ');

  const rsiPoints = data
    .map((d, i) => d.rsi ? `${getX(i)},${getRsiY(d.rsi)}` : null)
    .filter(Boolean)
    .join(' ');

  const activeCandle = hoveredCandle || data[data.length - 1];

  return (
    <div ref={containerRef} style={{ width: '100%', overflowX: 'auto' }}>
      {/* Chart Top Info Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
        <div style={{ display: 'flex', gap: '1rem', fontFamily: 'var(--font-mono)' }}>
          <span><b style={{ color: '#fff' }}>{symbol}</b> (NSE Daily)</span>
          <span>O: <span style={{ color: '#fff' }}>₹{activeCandle?.open}</span></span>
          <span>H: <span style={{ color: '#fff' }}>₹{activeCandle?.high}</span></span>
          <span>L: <span style={{ color: '#fff' }}>₹{activeCandle?.low}</span></span>
          <span>C: <span style={{ color: activeCandle?.close >= activeCandle?.open ? '#10b981' : '#f43f5e' }}>₹{activeCandle?.close}</span></span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: '#38bdf8' }}>— 20 EMA: ₹{activeCandle?.ema20 || '-'}</span>
          <span style={{ color: '#f59e0b' }}>— 50 EMA: ₹{activeCandle?.ema50 || '-'}</span>
          <span style={{ color: '#a855f7' }}>— RSI(14): {activeCandle?.rsi || '-'}</span>
        </div>
      </div>

      <svg 
        viewBox={`0 0 ${width} ${height}`} 
        style={{ width: '100%', height: 'auto', background: '#090d16', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}
        onMouseLeave={() => setHoveredCandle(null)}
      >
        <defs>
          <linearGradient id="rsiGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a855f7" stopOpacity="0.3"/>
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0"/>
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
          const y = padding.top + pct * (mainChartHeight - padding.top);
          const p = maxPrice - pct * priceRange;
          return (
            <g key={i}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
              <text x={width - padding.right + 8} y={y + 4} fill="#64748b" fontSize="10" fontFamily="var(--font-mono)">
                ₹{p.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* Trade Plan Price Lines (If provided) */}
        {tradePlan && (
          <>
            {/* Target Line */}
            {tradePlan.target_1 && (
              <g>
                <line 
                  x1={padding.left} 
                  y1={getY(tradePlan.target_1)} 
                  x2={width - padding.right} 
                  y2={getY(tradePlan.target_1)} 
                  stroke="#10b981" 
                  strokeDasharray="4 2" 
                  strokeWidth="1.5" 
                />
                <text x={width - padding.right + 8} y={getY(tradePlan.target_1) + 4} fill="#10b981" fontSize="10" fontWeight="bold">
                  TGT ₹{tradePlan.target_1}
                </text>
              </g>
            )}
            {/* Entry Line */}
            {tradePlan.entry_price && (
              <g>
                <line 
                  x1={padding.left} 
                  y1={getY(tradePlan.entry_price)} 
                  x2={width - padding.right} 
                  y2={getY(tradePlan.entry_price)} 
                  stroke="#38bdf8" 
                  strokeWidth="1.5" 
                />
                <text x={width - padding.right + 8} y={getY(tradePlan.entry_price) + 4} fill="#38bdf8" fontSize="10" fontWeight="bold">
                  ENTRY ₹{tradePlan.entry_price}
                </text>
              </g>
            )}
            {/* Stop Loss Line */}
            {tradePlan.stop_loss && (
              <g>
                <line 
                  x1={padding.left} 
                  y1={getY(tradePlan.stop_loss)} 
                  x2={width - padding.right} 
                  y2={getY(tradePlan.stop_loss)} 
                  stroke="#f43f5e" 
                  strokeDasharray="4 2" 
                  strokeWidth="1.5" 
                />
                <text x={width - padding.right + 8} y={getY(tradePlan.stop_loss) + 4} fill="#f43f5e" fontSize="10" fontWeight="bold">
                  SL ₹{tradePlan.stop_loss}
                </text>
              </g>
            )}
          </>
        )}

        {/* Candlesticks */}
        {data.map((d, i) => {
          const isGreen = d.close >= d.open;
          const color = isGreen ? '#10b981' : '#f43f5e';
          const x = getX(i);
          const yOpen = getY(d.open);
          const yClose = getY(d.close);
          const yHigh = getY(d.high);
          const yLow = getY(d.low);

          const bodyTop = Math.min(yOpen, yClose);
          const bodyHeight = Math.max(2, Math.abs(yClose - yOpen));
          const w = Math.max(2, candleWidth - 2);

          return (
            <g 
              key={i} 
              onMouseEnter={() => setHoveredCandle(d)}
              style={{ cursor: 'crosshair' }}
            >
              {/* High / Low Wick */}
              <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth="1.2" />
              {/* Body */}
              <rect 
                x={x - w / 2} 
                y={bodyTop} 
                width={w} 
                height={bodyHeight} 
                fill={color} 
                rx="1"
              />
            </g>
          );
        })}

        {/* 20 EMA Line */}
        {ema20Points && (
          <polyline fill="none" stroke="#38bdf8" strokeWidth="1.8" points={ema20Points} opacity="0.9" />
        )}

        {/* 50 EMA Line */}
        {ema50Points && (
          <polyline fill="none" stroke="#f59e0b" strokeWidth="1.8" points={ema50Points} opacity="0.85" />
        )}

        {/* --- RSI SUB-CHART (BOTTOM) --- */}
        <line x1={padding.left} y1={height - padding.bottom + 15} x2={width - padding.right} y2={height - padding.bottom + 15} stroke="rgba(255,255,255,0.1)" />
        {/* RSI 70 Line */}
        <line x1={padding.left} y1={getRsiY(70)} x2={width - padding.right} y2={getRsiY(70)} stroke="rgba(244,63,94,0.3)" strokeDasharray="2 2" />
        <text x={width - padding.right + 8} y={getRsiY(70) + 3} fill="#f43f5e" fontSize="9" opacity="0.7">70</text>
        {/* RSI 30 Line */}
        <line x1={padding.left} y1={getRsiY(30)} x2={width - padding.right} y2={getRsiY(30)} stroke="rgba(16,185,129,0.3)" strokeDasharray="2 2" />
        <text x={width - padding.right + 8} y={getRsiY(30) + 3} fill="#10b981" fontSize="9" opacity="0.7">30</text>
        {/* RSI Wave */}
        {rsiPoints && (
          <polyline fill="none" stroke="#a855f7" strokeWidth="1.6" points={rsiPoints} />
        )}
      </svg>
    </div>
  );
}
