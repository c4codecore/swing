import React from 'react';

const SCALE_STEPS = [100, 115, 130, 150, 175];

export default function FontScaleControls({ value, onChange, compact = false }) {
  const current = Math.max(0, SCALE_STEPS.indexOf(Number(value)));
  const change = next => onChange(SCALE_STEPS[Math.max(0, Math.min(SCALE_STEPS.length - 1, next))]);
  return <div className={`font-scale-controls ${compact ? 'font-scale-compact' : ''}`} aria-label="Text size">
    <span className="font-scale-label">Text size: {SCALE_STEPS[current]}%</span>
    <div className="font-scale-buttons">
      <button type="button" onClick={() => change(current - 1)} disabled={current === 0} aria-label="Make text smaller">A−</button>
      <button type="button" onClick={() => change(0)} aria-label="Reset text size to 100%">A</button>
      <button type="button" onClick={() => change(current + 1)} disabled={current === SCALE_STEPS.length - 1} aria-label="Make text larger">A+</button>
    </div>
  </div>;
}
