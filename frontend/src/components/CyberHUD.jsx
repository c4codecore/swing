import React, { useEffect, useState } from 'react';

export function CustomCursor() {
  const [pos, setPos] = useState({ x: -100, y: -100 });
  const [trailerPos, setTrailerPos] = useState({ x: -100, y: -100 });
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    const handleMove = (e) => {
      setPos({ x: e.clientX, y: e.clientY });
    };

    const handleMouseOver = (e) => {
      if (e.target.closest('button, a, input, select, .signal-card, .clickable')) {
        setHovered(true);
      } else {
        setHovered(false);
      }
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseover', handleMouseOver);

    // Smooth trailer loop
    let animId;
    let curX = -100;
    let curY = -100;

    const loop = () => {
      curX += (pos.x - curX) * 0.15;
      curY += (pos.y - curY) * 0.15;
      setTrailerPos({ x: curX, y: curY });
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);

    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseover', handleMouseOver);
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
          width: '6px',
          height: '6px',
          background: '#38bdf8',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 9999,
          boxShadow: '0 0 10px #38bdf8'
        }}
      />
      {/* Ethereal Glow Follower */}
      <div 
        style={{
          position: 'fixed',
          top: trailerPos.y,
          left: trailerPos.x,
          width: hovered ? '64px' : '36px',
          height: hovered ? '64px' : '36px',
          border: '1px solid rgba(56, 189, 248, 0.4)',
          background: hovered ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          zIndex: 9998,
          transition: 'width 0.25s ease, height 0.25s ease, background 0.25s ease',
          backdropFilter: hovered ? 'blur(2px)' : 'none',
          boxShadow: hovered ? '0 0 25px rgba(56, 189, 248, 0.3)' : 'none'
        }}
      />
    </>
  );
}

// 3D Tilt Card wrapper (Awwwards Studio Signature)
export function TiltCard({ children, className, style, onClick }) {
  const [transform, setTransform] = useState('');
  const [glare, setGlare] = useState({ x: 50, y: 50, opacity: 0 });

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -7;
    const rotateY = ((x - centerX) / centerX) * 7;

    setTransform(`perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(8px)`);
    setGlare({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
      opacity: 0.15
    });
  };

  const handleMouseLeave = () => {
    setTransform('perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)');
    setGlare({ x: 50, y: 50, opacity: 0 });
  };

  return (
    <div 
      className={className}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        ...style,
        transform: transform,
        transition: 'transform 0.15s ease-out, border-color 0.25s ease, box-shadow 0.25s ease',
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
          background: `radial-gradient(circle at ${glare.x}% ${glare.y}%, rgba(255,255,255,${glare.opacity}) 0%, transparent 60%)`,
          pointerEvents: 'none',
          transition: 'opacity 0.2s ease',
          zIndex: 10
        }}
      />
      {children}
    </div>
  );
}
