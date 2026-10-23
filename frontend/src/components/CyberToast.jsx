import React from 'react';
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export default function CyberToast({ message, type = 'info', onClose }) {
  if (!message) return null;

  const iconMap = {
    success: <CheckCircle2 size={16} color="#10b981" />,
    info: <Info size={16} color="#38bdf8" />,
    warning: <AlertTriangle size={16} color="#f59e0b" />
  };

  const borderColor = type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#38bdf8';

  return (
    <div 
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 99999,
        background: 'rgba(8, 14, 26, 0.92)',
        border: `1px solid ${borderColor}`,
        boxShadow: `0 10px 35px rgba(0,0,0,0.8), 0 0 20px ${borderColor}33`,
        borderRadius: '12px',
        padding: '0.75rem 1.25rem',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        animation: 'toastSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.82rem',
        color: '#f8fafc'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {iconMap[type] || iconMap.info}
      </div>
      <div style={{ letterSpacing: '0.02em' }}>{message}</div>
      {onClose && (
        <button 
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-dim)',
            padding: '2px',
            marginLeft: '0.5rem',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
