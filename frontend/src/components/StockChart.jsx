import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Layers, Activity, TrendingUp, Calendar, Zap } from 'lucide-react';
import { playTone } from '../utils/soundFx';

export default function StockChart({ symbol, tradePlan }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('6mo');
  const [hoverIndex, setHoverIndex] = useState(null);
  const [mouseY, setMouseY] = useState(null);
  const svgRef = useRef(null);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    fetch(`/api/chart/${symbol}?period=${period}`)
      .then(res => res.json())
      .then(json => {
        setData(json.candles || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load chart data", err);
        setLoading(false);
      });
  }, [symbol, period]);

  // Chart layout dimensions
  const width = 860;
  const height = 440;
  const padding = { top: 25, right: 75, bottom: 95, left: 15 };
  const rsiHeight = 65;
  const mainChartHeight = height - padding.bottom;
  const volumeHeight = 50;

  // Compute extents
  const { minPrice, maxPrice, priceRange, maxVol } = useMemo(() => {
    if (!data || data.length === 0) return { minPrice: 0, maxPrice: 100, priceRange: 1, maxVol: 1 };
    
    let prices = data.flatMap(d => [d.low, d.high]);
    if (tradePlan) {
      if (tradePlan.stop_loss) prices.push(tradePlan.stop_loss);
      if (tradePlan.target_2) prices.push(tradePlan.target_2);
      if (tradePlan.entry_price) prices.push(tradePlan.entry_price);
    }
    
    const minP = Math.min(...prices) * 0.99;
    const maxP = Math.max(...prices) * 1.01;
    const volMax = Math.max(...data.map(d => d.volume || 1), 1);
    
    return {
      minPrice: minP,
      maxPrice: maxP,
      priceRange: maxP - minP || 1,
      maxVol: volMax
    };
  }, [data, tradePlan]);

  if (loading) {
    return (
      <div style={{ padding: '4rem', textAlign: 'center', color: '#94a3b8' }}>
        <div className="live-dot" style={{ margin: '0 auto 1.25rem', background: '#38bdf8', width: 14, height: 14 }} />
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', letterSpacing: '0.05em' }}>
          STREAMING CANDLESTICKS & TELEMETRY FOR {symbol}...
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
        No historical candles available for {symbol}
      </div>
    );
  }

  // Coordinate mappers
  const chartInnerWidth = width - padding.left - padding.right;
  const candleStep = chartInnerWidth / data.length;
  const candleBarWidth = Math.max(2.5, Math.min(8, candleStep * 0.65));

  const getX = (idx) => padding.left + (idx * candleStep) + (candleStep / 2);
  const getY = (val) => padding.top + (1 - (val - minPrice) / priceRange) * (mainChartHeight - padding.top - volumeHeight);
  const getVolY = (vol) => mainChartHeight - ((vol / maxVol) * volumeHeight);
  const getRsiY = (rsiVal) => height - padding.bottom + 22 + (1 - (rsiVal / 100)) * rsiHeight;

  // Invert Y to price for crosshair
  const getPriceFromY = (yCoord) => {
    const ratio = 1 - (yCoord - padding.top) / (mainChartHeight - padding.top - volumeHeight);
    return minPrice + ratio * priceRange;
  };

  // EMA paths
  const ema20Points = data
    .map((d, i) => d.ema20 ? `${getX(i).toFixed(1)},${getY(d.ema20).toFixed(1)}` : null)
    .filter(Boolean)
    .join(' ');

  const ema50Points = data
    .map((d, i) => d.ema50 ? `${getX(i).toFixed(1)},${getY(d.ema50).toFixed(1)}` : null)
    .filter(Boolean)
    .join(' ');

  // RSI path
  const rsiPoints = data
    .map((d, i) => d.rsi != null ? `${getX(i).toFixed(1)},${getRsiY(d.rsi).toFixed(1)}` : null)
    .filter(Boolean)
    .join(' ');

  const activeCandle = hoverIndex !== null && data[hoverIndex] ? data[hoverIndex] : data[data.length - 1];
  const activePrice = activeCandle?.close;
  const isCandleGreen = activeCandle?.close >= activeCandle?.open;
  const candleChg = activeCandle ? (((activeCandle.close - activeCandle.open) / activeCandle.open) * 100).toFixed(2) : 0;

  // Mouse move handler for interactive crosshair
  const handleMouseMove = (e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    
    // Convert to SVG viewBox scale
    const scaleX = width / rect.width;
    const scaleY = height / rect.height;
    const svgX = clientX * scaleX;
    const svgY = clientY * scaleY;

    setMouseY(svgY);

    if (svgX >= padding.left && svgX <= width - padding.right) {
      const idx = Math.floor((svgX - padding.left) / candleStep);
      const clampedIdx = Math.max(0, Math.min(data.length - 1, idx));
      setHoverIndex(clampedIdx);
    }
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
    setMouseY(null);
  };

  const cursorX = hoverIndex !== null ? getX(hoverIndex) : null;
  const cursorPrice = mouseY !== null && mouseY >= padding.top && mouseY <= mainChartHeight - volumeHeight ? getPriceFromY(mouseY) : null;

  return (
    <div style={{ width: '100%' }}>
      {/* Chart Header Bar */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        flexWrap: 'wrap',
        gap: '0.75rem',
        padding: '0.85rem 1rem', 
        background: 'rgba(10, 16, 28, 0.85)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '14px',
        marginBottom: '0.75rem',
        backdropFilter: 'blur(12px)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', fontFamily: 'var(--font-mono)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>{symbol}</span>
            <span style={{ 
              fontSize: '0.75rem', 
              padding: '0.15rem 0.5rem', 
              borderRadius: '6px',
              background: isCandleGreen ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)',
              color: isCandleGreen ? '#10b981' : '#f43f5e',
              border: `1px solid ${isCandleGreen ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`
            }}>
              {isCandleGreen ? '+' : ''}{candleChg}%
            </span>
          </div>

          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', gap: '0.75rem' }}>
            <span>Open: <b style={{ color: '#fff' }}>₹{activeCandle?.open}</b></span>
            <span>High: <b style={{ color: '#fff' }}>₹{activeCandle?.high}</b></span>
            <span>Low: <b style={{ color: '#fff' }}>₹{activeCandle?.low}</b></span>
            <span>Close: <b style={{ color: isCandleGreen ? '#10b981' : '#f43f5e' }}>₹{activeCandle?.close}</b></span>
            {activeCandle?.volume && <span>Shares traded: <b style={{ color: '#94a3b8' }}>{(activeCandle.volume / 1000).toFixed(0)}k</b></span>}
          </div>
        </div>

        {/* Timeframe Selector Buttons */}
        <div style={{ display: 'flex', gap: '0.35rem', background: 'rgba(0,0,0,0.4)', padding: '0.2rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
          {['1mo', '3mo', '6mo', '1y'].map((p) => (
            <button
              key={p}
              onClick={() => {
                setPeriod(p);
                playTone('click');
              }}
              style={{
                background: period === p ? 'linear-gradient(135deg, rgba(56,189,248,0.25), rgba(168,85,247,0.2))' : 'transparent',
                border: period === p ? '1px solid #38bdf8' : '1px solid transparent',
                color: period === p ? '#fff' : 'var(--text-dim)',
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                padding: '0.25rem 0.65rem',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Main SVG Candlestick & Indicator Chart */}
      <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
        <svg 
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`} 
          style={{ 
            width: '100%', 
            height: 'auto', 
            background: 'linear-gradient(180deg, #070b14 0%, #03060c 100%)', 
            borderRadius: '16px', 
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 20px 40px rgba(0,0,0,0.6)'
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="rsiGradLine" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.4"/>
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0"/>
            </linearGradient>
            <linearGradient id="volGreenGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.5"/>
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.1"/>
            </linearGradient>
            <linearGradient id="volRedGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.5"/>
              <stop offset="100%" stopColor="#f43f5e" stopOpacity="0.1"/>
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0.2, 0.4, 0.6, 0.8].map((pct, i) => {
            const gridP = minPrice + pct * priceRange;
            const y = getY(gridP);
            return (
              <g key={i}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                <text x={width - padding.right + 6} y={y + 3} fill="#cbd5e1" fontSize="9.5" fontWeight="600" fontFamily="var(--font-mono)">
                  ₹{gridP.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Volume bars at bottom of price chart */}
          {data.map((d, i) => {
            if (!d.volume) return null;
            const x = getX(i) - candleBarWidth / 2;
            const y = getVolY(d.volume);
            const h = mainChartHeight - y;
            const isGreen = d.close >= d.open;
            return (
              <rect
                key={`vol-${i}`}
                x={x}
                y={y}
                width={candleBarWidth}
                height={Math.max(1, h)}
                fill={isGreen ? 'url(#volGreenGrad)' : 'url(#volRedGrad)'}
              />
            );
          })}

          {/* Trade Plan Price Guides (Target 2, Target 1, Entry, Stop Loss) */}
          {tradePlan?.target_2 && (
            <g>
              <line 
                x1={padding.left} 
                y1={getY(tradePlan.target_2)} 
                x2={width - padding.right} 
                y2={getY(tradePlan.target_2)} 
                stroke="#10b981" 
                strokeWidth="1.5" 
                strokeDasharray="6 3" 
              />
              <rect x={width - padding.right} y={getY(tradePlan.target_2) - 9} width="70" height="18" fill="#10b981" rx="4" />
              <text x={width - padding.right + 6} y={getY(tradePlan.target_2) + 3} fill="#000" fontSize="9" fontWeight="800" fontFamily="var(--font-mono)">
                TGT2 ₹{tradePlan.target_2}
              </text>
            </g>
          )}

          {tradePlan?.target_1 && (
            <g>
              <line 
                x1={padding.left} 
                y1={getY(tradePlan.target_1)} 
                x2={width - padding.right} 
                y2={getY(tradePlan.target_1)} 
                stroke="#34d399" 
                strokeWidth="1.2" 
                strokeDasharray="4 4" 
              />
              <rect x={width - padding.right} y={getY(tradePlan.target_1) - 8} width="66" height="16" fill="rgba(52, 211, 153, 0.85)" rx="3" />
              <text x={width - padding.right + 5} y={getY(tradePlan.target_1) + 3} fill="#000" fontSize="8.5" fontWeight="700" fontFamily="var(--font-mono)">
                TGT1 ₹{tradePlan.target_1}
              </text>
            </g>
          )}

          {tradePlan?.entry_price && (
            <g>
              <line 
                x1={padding.left} 
                y1={getY(tradePlan.entry_price)} 
                x2={width - padding.right} 
                y2={getY(tradePlan.entry_price)} 
                stroke="#38bdf8" 
                strokeWidth="1.8" 
              />
              <rect x={width - padding.right} y={getY(tradePlan.entry_price) - 9} width="70" height="18" fill="#38bdf8" rx="4" />
              <text x={width - padding.right + 6} y={getY(tradePlan.entry_price) + 3} fill="#000" fontSize="9" fontWeight="800" fontFamily="var(--font-mono)">
                ENTRY ₹{tradePlan.entry_price}
              </text>
            </g>
          )}

          {tradePlan?.stop_loss && (
            <g>
              <line 
                x1={padding.left} 
                y1={getY(tradePlan.stop_loss)} 
                x2={width - padding.right} 
                y2={getY(tradePlan.stop_loss)} 
                stroke="#f43f5e" 
                strokeWidth="1.5" 
                strokeDasharray="5 3" 
              />
              <rect x={width - padding.right} y={getY(tradePlan.stop_loss) - 9} width="66" height="18" fill="#f43f5e" rx="4" />
              <text x={width - padding.right + 6} y={getY(tradePlan.stop_loss) + 3} fill="#fff" fontSize="9" fontWeight="800" fontFamily="var(--font-mono)">
                SL ₹{tradePlan.stop_loss}
              </text>
            </g>
          )}

          {/* EMA Lines */}
          {ema50Points && <polyline points={ema50Points} fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeOpacity="0.85" />}
          {ema20Points && <polyline points={ema20Points} fill="none" stroke="#38bdf8" strokeWidth="2.0" strokeOpacity="0.95" />}

          {/* Candlesticks */}
          {data.map((d, i) => {
            const isGreen = d.close >= d.open;
            const x = getX(i);
            const highY = getY(d.high);
            const lowY = getY(d.low);
            const openY = getY(d.open);
            const closeY = getY(d.close);
            const topY = Math.min(openY, closeY);
            const barH = Math.max(1.5, Math.abs(closeY - openY));

            const isHovered = hoverIndex === i;
            const candleColor = isGreen ? '#10b981' : '#f43f5e';

            return (
              <g key={`candle-${i}`}>
                {/* Wick */}
                <line 
                  x1={x} 
                  y1={highY} 
                  x2={x} 
                  y2={lowY} 
                  stroke={candleColor} 
                  strokeWidth={isHovered ? '2' : '1.2'} 
                />
                {/* Body */}
                <rect 
                  x={x - candleBarWidth / 2} 
                  y={topY} 
                  width={candleBarWidth} 
                  height={barH} 
                  fill={isGreen ? '#10b981' : '#f43f5e'} 
                  stroke={isHovered ? '#fff' : candleColor}
                  strokeWidth={isHovered ? '1.5' : '0.5'}
                  rx="1"
                />
              </g>
            );
          })}

          {/* RSI Sub-Panel Divider & Guide lines */}
          <line x1={padding.left} y1={height - padding.bottom + 15} x2={width - padding.right} y2={height - padding.bottom + 15} stroke="rgba(255,255,255,0.12)" />
          
          {/* RSI Overbought 70 line */}
          <line x1={padding.left} y1={getRsiY(70)} x2={width - padding.right} y2={getRsiY(70)} stroke="rgba(244, 63, 94, 0.4)" strokeDasharray="3 3" />
          <text x={width - padding.right + 6} y={getRsiY(70) + 3} fill="#f43f5e" fontSize="8" fontFamily="var(--font-mono)">70 OB</text>

          {/* RSI Middle 50 line */}
          <line x1={padding.left} y1={getRsiY(50)} x2={width - padding.right} y2={getRsiY(50)} stroke="rgba(255, 255, 255, 0.08)" strokeDasharray="2 2" />

          {/* RSI Oversold 30 line */}
          <line x1={padding.left} y1={getRsiY(30)} x2={width - padding.right} y2={getRsiY(30)} stroke="rgba(16, 185, 129, 0.4)" strokeDasharray="3 3" />
          <text x={width - padding.right + 6} y={getRsiY(30) + 3} fill="#10b981" fontSize="8" fontFamily="var(--font-mono)">30 OS</text>

          {/* RSI Curve */}
          {rsiPoints && (
            <polyline 
              points={rsiPoints} 
              fill="none" 
              stroke="#a855f7" 
              strokeWidth="1.8" 
            />
          )}

          {/* Interactive Crosshair Cursor */}
          {cursorX !== null && (
            <g pointerEvents="none">
              {/* Vertical Crosshair Line */}
              <line 
                x1={cursorX} 
                y1={padding.top} 
                x2={cursorX} 
                y2={height - 20} 
                stroke="rgba(255, 255, 255, 0.4)" 
                strokeWidth="1" 
                strokeDasharray="4 4" 
              />

              {/* Date Badge on X-Axis */}
              <rect x={cursorX - 35} y={height - 18} width="70" height="16" fill="#1e293b" rx="3" stroke="rgba(255,255,255,0.2)" />
              <text x={cursorX} y={height - 6} fill="#f8fafc" fontSize="8.5" fontFamily="var(--font-mono)" textAnchor="middle">
                {activeCandle?.time}
              </text>
            </g>
          )}

          {mouseY !== null && cursorPrice !== null && (
            <g pointerEvents="none">
              {/* Horizontal Crosshair Line */}
              <line 
                x1={padding.left} 
                y1={mouseY} 
                x2={width - padding.right} 
                y2={mouseY} 
                stroke="rgba(255, 255, 255, 0.35)" 
                strokeWidth="1" 
                strokeDasharray="4 4" 
              />

              {/* Price Badge on Y-Axis */}
              <rect x={width - padding.right} y={mouseY - 8} width="66" height="16" fill="#38bdf8" rx="3" />
              <text x={width - padding.right + 6} y={mouseY + 3.5} fill="#040711" fontSize="9" fontWeight="800" fontFamily="var(--font-mono)">
                ₹{cursorPrice.toFixed(1)}
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* Chart Legend & Telemetry Indicators */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: '#cbd5e1', fontWeight: 600, flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 2, background: '#38bdf8', display: 'inline-block' }}></span>
            <span style={{ color: '#38bdf8' }}>20-day average price</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 2, background: '#f59e0b', display: 'inline-block' }}></span>
            <span style={{ color: '#f59e0b' }}>50-day average price</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: 12, height: 2, background: '#a855f7', display: 'inline-block' }}></span>
            <span style={{ color: '#a855f7' }}>Recent price strength: {activeCandle?.rsi ?? '-'}</span>
          </span>
        </div>
        <div>
          <span>Move over the chart to see the price for each date</span>
        </div>
      </div>
    </div>
  );
}
