import React, { useEffect, useState } from 'react';

export function CustomCursor() {
  const [pos, setPos] = useState({ x: -100, y: -100 });
  const [trailerPos, setTrailerPos] = useState({ x: -100, y: -100 });
  const [hovered, setHovered] = useState(false);
  const [isClicking, setIsClicking] = useState(false);

  useEffect(() => {
    const handleMove = (e) => {
      setPos({ x: e.clientX, y: e.clientY });
    };

    const handleMouseOver = (e) => {
      if (e.target.closest('button, a, input, select, .signal-card, .clickable, .tilt-interactive')) {
        setHovered(true);
      } else {
        setHovered(false);
      }
    };

    const handleMouseDown = () => setIsClicking(true);
    const handleMouseUp = () => setIsClicking(false);

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseover', handleMouseOver);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);

    // Smooth trailer loop
    let animId;
    let curX = -100;
    let curY = -100;

    const loop = () => {
      curX += (pos.x - curX) * 0.18;
      curY += (pos.y - curY) * 0.18;
      setTrailerPos({ x: curX, y: curY });
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);

    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseover', handleMouseOver);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      cancelAnimationFrame(animId);
    };
  }, [pos.x, pos.y]);

  return (
    <>
      {/* Precision Core Dot */}
      <div 
        style={{
          position: 'fixed',
          top: pos.y,
          left: pos.x,
          width: isClicking ? '4px' : '6px',
          height: isClicking ? '4px' : '6px',
          background: '#38bdf8',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 9999,
          boxShadow: '0 0 12px #38bdf8, 0 0 24px rgba(56, 189, 248, 0.6)'
        }}
      />
      {/* Ethereal Glow Follower Ring */}
      <div 
        style={{
          position: 'fixed',
          top: trailerPos.y,
          left: trailerPos.x,
          width: hovered ? '56px' : '32px',
          height: hovered ? '56px' : '32px',
          border: hovered ? '1.5px solid rgba(56, 189, 248, 0.7)' : '1px solid rgba(56, 189, 248, 0.35)',
          background: hovered ? 'rgba(56, 189, 248, 0.08)' : 'rgba(56, 189, 248, 0.02)',
          borderRadius: '50%',
          transform: `translate(-50%, -50%) scale(${isClicking ? 0.85 : 1})`,
          pointerEvents: 'none',
          zIndex: 9998,
          transition: 'width 0.22s cubic-bezier(0.16, 1, 0.3, 1), height 0.22s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, transform 0.15s ease',
          backdropFilter: hovered ? 'blur(1px)' : 'none',
          boxShadow: hovered ? '0 0 30px rgba(56, 189, 248, 0.35)' : 'none'
        }}
      />
    </>
  );
}

// 3D Tilt Card wrapper
export function TiltCard({ children, className, style, onClick }) {
  const [transform, setTransform] = useState('');
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -6;
    const rotateY = ((x - centerX) / centerX) * 6;

    setTransform(`perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(6px)`);
    setGlare({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.18
    });
  };

  const handleMouseLeave = () => {
    setTransform('perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)');
    setGlare({ x: 50, y: 50, opacity: 0 });
  };

  return (
    <div 
      className={`tilt-interactive ${className || ''}`}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        ...style,
        transform: transform,
        transition: 'transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease',
        transformStyle: 'preserve-3d',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Dynamic Glare Spotlight */}
      <div 
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(circle at ${glare.x}% ${glare.y}%, rgba(255,255,255,${glare.opacity}) 0%, transparent 55%)`,
          pointerEvents: 'none',
          transition: 'opacity 0.2s ease',
          zIndex: 10
        }}
      />
      {children}
    </div>
  );
}

// Visual Risk-to-Reward Progress Bar
export function RiskRewardBar({ entry, stopLoss, target1, target2 }) {
  if (!entry || !stopLoss || !target2) return null;

  const totalRange = target2 - stopLoss;
  if (totalRange <= 0) return null;

  const slPos = 0;
  const entryPos = Math.max(10, Math.min(60, ((entry - stopLoss) / totalRange) * 100));
  const t1Pos = target1 ? Math.max(entryPos + 10, Math.min(85, ((target1 - stopLoss) / totalRange) * 100)) : entryPos + 25;

  return (
    <div style={{ margin: '0.85rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: '0.35rem' }}>
        <span style={{ color: '#f43f5e' }}>SL ₹{stopLoss}</span>
        <span style={{ color: '#38bdf8' }}>ENTRY ₹{entry}</span>
        <span style={{ color: '#10b981' }}>TGT ₹{target2}</span>
      </div>
      <div style={{ position: 'relative', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px', overflow: 'hidden' }}>
        {/* Risk Zone (Stop to Entry) */}
        <div 
          style={{
            position: 'absolute',
            left: '0%',
            width: `${entryPos}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #f43f5e 0%, rgba(244, 63, 94, 0.4) 100%)',
            borderRadius: '999px 0 0 999px'
          }}
        />
        {/* Reward Zone (Entry to Target) */}
        <div 
          style={{
            position: 'absolute',
            left: `${entryPos}%`,
            width: `${100 - entryPos}%`,
            height: '100%',
            background: 'linear-gradient(90deg, rgba(16, 185, 129, 0.4) 0%, #10b981 100%)',
            borderRadius: '0 999px 999px 0'
          }}
        />
      </div>
    </div>
  );
}

// Circular Radial Gauge
export function RadialProgress({ value = 0, size = 64, strokeWidth = 5, color = '#38bdf8', label = '' }) {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference;

  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="none"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', textAlign: 'center', fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
        <div style={{ fontSize: size * 0.26, fontWeight: 700, color: '#fff' }}>{value}%</div>
        {label && <div style={{ fontSize: size * 0.14, color: 'var(--text-dim)', marginTop: 2 }}>{label}</div>}
      </div>
    </div>
  );
}
