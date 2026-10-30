import React from 'react';
import { Eye, Moon, Contrast, Sparkles } from 'lucide-react';

const DIM_LEVELS = ['normal', 'dim', 'extra'];

export default function AppearanceControls({ theme, setTheme, dim, setDim, grayscale, setGrayscale, motion, setMotion, compact = false }) {
  const cycleDim = () => setDim(DIM_LEVELS[(DIM_LEVELS.indexOf(dim) + 1) % DIM_LEVELS.length]);
  const dimLabel = dim === 'extra' ? 'Extra dim' : dim === 'dim' ? 'Dim' : 'Normal brightness';
  return <div className={`appearance-controls ${compact ? 'appearance-controls-compact' : ''}`}>
    <button type="button" className="appearance-quick" onClick={cycleDim} aria-label={`Brightness: ${dimLabel}. Activate to change brightness`}>
      <Contrast size={20} aria-hidden="true" /><span>{dimLabel}</span>
    </button>
    <details className="appearance-menu">
      <summary className="appearance-trigger"><span>Display options</span></summary>
      <div className="appearance-panel">
      <label className="setting-field">
        <span>Theme</span>
        <select value={theme} onChange={event => setTheme(event.target.value)}>
          <option value="dark">Dark low-glare</option>
          <option value="light">Light high-contrast</option>
          <option value="auto">Auto</option>
        </select>
      </label>
      <p className="setting-hint"><Moon size={18} aria-hidden="true" /> Use brightness button: {dimLabel}</p>
      <button type="button" className={`setting-button ${grayscale ? 'setting-active' : ''}`} aria-pressed={grayscale} onClick={() => setGrayscale(!grayscale)}>
        <Eye size={18} aria-hidden="true" /><span>Grayscale preview {grayscale ? 'on' : 'off'}</span>
      </button>
      <button type="button" className={`setting-button ${motion ? 'setting-active' : ''}`} aria-pressed={motion} onClick={() => setMotion(!motion)}>
        <Sparkles size={18} aria-hidden="true" /><span>Decorative motion {motion ? 'on' : 'off'}</span>
      </button>
      </div>
    </details>
  </div>;
}
