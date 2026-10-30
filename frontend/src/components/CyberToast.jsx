import React from 'react';
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export default function CyberToast({ message, type = 'info', onClose }) {
  if (!message) return null;

  const iconMap = {
    success: <CheckCircle2 size={16} color="#10b981" />,
    info: <Info size={16} color="#38bdf8" />,
    warning: <AlertTriangle size={16} color="#f59e0b" />
  };

  const statusLabel = type === 'success' ? 'Success' : type === 'warning' ? 'Warning' : 'Information';

  return (
    <div className={`cyber-toast toast-${type}`}>
      <div className="cyber-toast-icon">
        {iconMap[type] || iconMap.info}
      </div>
      <div className="cyber-toast-copy"><span className="cyber-toast-status">{statusLabel}</span><span>{message}</span></div>
      {onClose && (
        <button 
          onClick={onClose}
          aria-label="Dismiss notification"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
