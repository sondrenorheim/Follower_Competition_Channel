import React from 'react';
import { getGameTypeInfo } from '../utils/formatters';

/**
 * GameFilter Component
 * Dropdown filter for selecting game type
 */
export default function GameFilter({
  value,
  onChange,
  gameTypes = [],
  disabled = false,
  helperText = ''
}) {
  const allGameTypes = [
    { type: 'all', displayName: 'All Games', count: gameTypes.reduce((sum, g) => sum + g.count, 0) },
    ...gameTypes
  ];

  return (
    <div className="relative group">
      <label htmlFor="game-filter" className="block text-sm font-bold text-text-primary mb-2 flex items-center gap-2">
        <span>🎮</span>
        <span>Game Type</span>
      </label>
      <div className="relative">
        <select
          id="game-filter"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {allGameTypes.map((gameType) => {
            return (
              <option
                key={gameType.type}
                value={gameType.type}
                className="bg-dark-bg-secondary text-text-primary"
              >
                {gameType.displayName}
              </option>
            );
          })}
        </select>
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          <svg className="h-5 w-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {helperText ? (
        <p className="mt-2 text-xs text-text-muted">{helperText}</p>
      ) : null}
    </div>
  );
}
