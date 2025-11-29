import React from 'react';
import { getGameTypeInfo } from '../utils/formatters';

/**
 * GameFilter Component
 * Dropdown filter for selecting game type
 */
export default function GameFilter({ value, onChange, gameTypes = [] }) {
  const allGameTypes = [
    { type: 'all', displayName: 'All Games', count: gameTypes.reduce((sum, g) => sum + g.count, 0) },
    ...gameTypes
  ];

  return (
    <div className="relative">
      <label htmlFor="game-filter" className="block text-sm font-semibold text-gray-700 mb-2">
        Game Type
      </label>
      <select
        id="game-filter"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full pl-3 pr-10 py-2.5 text-base border-2 border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent rounded-lg bg-white hover:border-gray-300 transition-colors"
      >
        {allGameTypes.map((gameType) => {
          const info = getGameTypeInfo(gameType.type);
          return (
            <option key={gameType.type} value={gameType.type}>
              {info.name} {gameType.count ? `(${gameType.count})` : ''}
            </option>
          );
        })}
      </select>
    </div>
  );
}
