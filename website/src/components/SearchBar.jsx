import React from 'react';

/**
 * SearchBar Component
 * Search input with clear button
 */
export default function SearchBar({ value, onChange, placeholder = 'Search username...' }) {
  return (
    <div className="relative group">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <svg
          className={`h-5 w-5 transition-colors duration-200 ${
            value ? 'text-accent' : 'text-text-muted group-hover:text-primary'
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full pl-10 pr-10 py-3 border-2 border-slate-600 rounded-xl leading-5 bg-dark-bg-tertiary placeholder-text-muted text-text-primary focus:outline-none focus:placeholder-text-secondary focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent hover:border-primary/50 transition-all duration-200 sm:text-sm font-medium shadow-inner-subtle"
        placeholder={placeholder}
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute inset-y-0 right-0 pr-3 flex items-center group/clear"
        >
          <svg
            className="h-5 w-5 text-text-muted hover:text-danger transition-all duration-200 group-hover/clear:rotate-90"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
