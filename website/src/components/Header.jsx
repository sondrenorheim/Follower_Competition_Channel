import React from 'react';
import { Link, useLocation } from 'react-router-dom';

/**
 * Header Component
 * Main navigation header with tabs
 */
export default function Header() {
  const location = useLocation();

  const tabs = [
    { name: 'Daily Results', path: '/' },
    { name: 'Monthly Rankings', path: '/monthly' }
  ];

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <header className="bg-gradient-to-r from-dark-bg-secondary via-dark-bg-tertiary to-dark-bg-secondary border-b-2 border-slate-700 shadow-2xl shadow-black/50 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Title */}
        <div className="py-10 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className="text-5xl animate-bounce-slow">🏆</span>
            <h1 className="text-5xl font-black text-white tracking-tight drop-shadow-lg animate-fade-in">
              The Follower Battles
            </h1>
            <span className="text-5xl animate-bounce-slow">🏆</span>
          </div>
          <p className="text-text-secondary text-sm font-medium tracking-wide">
            Compete. Survive. Dominate.
          </p>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex justify-center space-x-2 pb-0">
          {tabs.map((tab) => (
            <Link
              key={tab.path}
              to={tab.path}
              className={`px-8 py-4 text-sm font-bold rounded-t-xl transition-all duration-300 transform border-2 ${
                isActive(tab.path)
                  ? 'bg-gradient-to-r from-primary to-secondary text-white border-primary shadow-glow-primary scale-105 -translate-y-1'
                  : 'bg-dark-surface/50 text-text-muted border-slate-600 hover:bg-dark-surface hover:border-accent hover:shadow-glow-accent hover:text-text-primary hover:scale-105'
              }`}
            >
              {tab.name}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
