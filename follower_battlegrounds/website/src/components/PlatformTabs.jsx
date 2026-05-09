import React from 'react';
import { RESULT_PLATFORMS, normalizeResultPlatform } from '../utils/dataLoader';

export default function PlatformTabs({ value = 'instagram', onChange = () => {}, counts = {} }) {
  const active = normalizeResultPlatform(value);

  return (
    <div className="w-full">
      <label className="block text-sm font-bold text-text-primary mb-2">Platform Results</label>
      <div className="flex flex-wrap gap-2 rounded-xl border-2 border-slate-600 bg-dark-surface/50 p-1.5">
        {RESULT_PLATFORMS.map((platform) => {
          const selected = platform.id === active;
          const count = counts?.[platform.id];
          return (
            <button
              key={platform.id}
              type="button"
              onClick={() => onChange(platform.id)}
              className={`min-w-[7.5rem] flex-1 rounded-lg px-4 py-3 text-sm font-bold transition-all duration-200 ${
                selected
                  ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary'
                  : 'text-text-muted hover:text-text-primary hover:bg-dark-surface/70'
              }`}
              aria-pressed={selected}
            >
              <span>{platform.label}</span>
              {count !== undefined ? (
                <span className={`ml-2 text-xs ${selected ? 'text-white/80' : 'text-text-muted'}`}>
                  {count}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
