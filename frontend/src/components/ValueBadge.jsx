import React from 'react';

export default function ValueBadge({ positive, children, unit = '', context = 'change', className = '' }) {
  const isPositive = Boolean(positive);
  return <span className={`value-badge ${isPositive ? 'gain' : 'loss'} ${className}`.trim()}>
    <span className="value-symbol" aria-hidden="true">{isPositive ? '▲' : '▼'}</span>
    <span className="value-label">{isPositive ? 'GAIN' : 'LOSS'}</span>
    <span className="value-number">{isPositive ? '+' : '−'}{children}{unit}</span>
    <span className="visually-hidden">{context}</span>
  </span>;
}
