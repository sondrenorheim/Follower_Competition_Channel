import React from 'react';
import { RESULT_PLATFORMS, normalizeResultPlatform } from '../utils/dataLoader';

const PLATFORM_STYLES = {
  instagram: {
    dot: 'bg-gradient-to-br from-[#f58529] via-[#dd2a7b] to-[#8134af]',
    button: 'border-[#dd2a7b]/70 bg-[#dd2a7b]/15 text-[#ffd7ec] shadow-[0_0_24px_rgba(221,42,123,0.22)]',
    option: 'hover:border-[#dd2a7b]/50 hover:bg-[#dd2a7b]/12'
  },
  youtube: {
    dot: 'bg-[#ff0033]',
    button: 'border-[#ff0033]/75 bg-[#ff0033]/15 text-[#ffd6dd] shadow-[0_0_24px_rgba(255,0,51,0.24)]',
    option: 'hover:border-[#ff0033]/50 hover:bg-[#ff0033]/12'
  },
  facebook: {
    dot: 'bg-[#1877f2]',
    button: 'border-[#1877f2]/75 bg-[#1877f2]/15 text-[#d7e8ff] shadow-[0_0_24px_rgba(24,119,242,0.22)]',
    option: 'hover:border-[#1877f2]/50 hover:bg-[#1877f2]/12'
  }
};

export default function PlatformTabs({ value = 'instagram', onChange = () => {}, counts = {} }) {
  const active = normalizeResultPlatform(value);
  const [open, setOpen] = React.useState(false);
  const dropdownRef = React.useRef(null);
  const fieldId = React.useId();
  const labelId = `${fieldId}-label`;
  const valueId = `${fieldId}-value`;
  const activePlatform = RESULT_PLATFORMS.find((platform) => platform.id === active) || RESULT_PLATFORMS[0];
  const activeStyle = PLATFORM_STYLES[active] || PLATFORM_STYLES.instagram;

  React.useEffect(() => {
    if (!open) return undefined;

    const handlePointerDown = (event) => {
      if (!dropdownRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const selectPlatform = (platformId) => {
    onChange(platformId);
    setOpen(false);
  };

  return (
    <div className="w-full max-w-xs" ref={dropdownRef}>
      <label id={labelId} className="block text-sm font-bold text-text-primary mb-2">
        Platform Results
      </label>
      <div className="relative">
        <button
          type="button"
          className={`flex min-h-[3.25rem] w-full items-center justify-between gap-3 rounded-xl border-2 px-4 py-3 text-left transition-all duration-200 ${activeStyle.button}`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-labelledby={`${labelId} ${valueId}`}
          onClick={() => setOpen((current) => !current)}
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className={`h-3 w-3 shrink-0 rounded-full ${activeStyle.dot}`} />
            <span className="min-w-0">
              <span id={valueId} className="block truncate text-sm font-black">
                {activePlatform.label}
              </span>
              {counts?.[active] !== undefined ? (
                <span className="block truncate text-xs font-semibold text-current/70">
                  {counts[active]} {Number(counts[active]) === 1 ? 'game' : 'games'}
                </span>
              ) : null}
            </span>
          </span>
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            className={`h-5 w-5 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {open ? (
          <div
            className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border-2 border-slate-600 bg-dark-bg-secondary shadow-card-dark"
            role="listbox"
            aria-labelledby={labelId}
          >
            <div className="p-1.5">
              {RESULT_PLATFORMS.map((platform) => {
                const selected = platform.id === active;
                const count = counts?.[platform.id];
                const style = PLATFORM_STYLES[platform.id] || PLATFORM_STYLES.instagram;
                return (
                  <button
                    key={platform.id}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => selectPlatform(platform.id)}
                    className={`flex w-full items-center justify-between gap-3 rounded-lg border border-transparent px-3 py-2.5 text-left text-sm font-bold transition-colors duration-150 ${style.option} ${
                      selected ? 'bg-dark-surface text-text-primary' : 'text-text-muted'
                    }`}
                  >
                    <span className="flex min-w-0 items-center gap-3">
                      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} />
                      <span className="truncate">{platform.label}</span>
                    </span>
                    {count !== undefined ? (
                      <span className="shrink-0 text-xs font-semibold text-text-muted">{count}</span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
      <div className="sr-only" aria-live="polite">
        Showing {activePlatform.label} results
      </div>
    </div>
  );
}
