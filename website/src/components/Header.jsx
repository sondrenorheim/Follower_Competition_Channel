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
    <header className="bg-gradient-to-r from-dark-bg-secondary via-dark-bg-tertiary to-dark-bg-secondary border-b-2 border-slate-700 shadow-2xl shadow-black/50">
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
          <p className="text-text-secondary text-sm font-medium tracking-wide mb-4">
            Compete. Survive. Dominate.
          </p>

          {/* Social Media Follow Banner */}
          <div className="mt-6 max-w-2xl mx-auto">
            <div className="bg-gradient-to-r from-purple-900/50 via-pink-900/50 to-purple-900/50 border-2 border-accent/50 rounded-xl p-4 shadow-glow-accent">
              <p className="text-white font-bold text-sm mb-3">
                🎯 Follow on both platforms to double your chances of winning! 🎯
              </p>
              <div className="flex items-center justify-center gap-4">
                <a
                  href="https://www.instagram.com/followerbattlegrounds/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                  </svg>
                  Follow on Instagram
                </a>
                <a
                  href="https://www.tiktok.com/@followerbattlegro"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-cyan-600 to-pink-600 hover:from-cyan-500 hover:to-pink-500 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
                  </svg>
                  Follow on TikTok
                </a>
              </div>
            </div>
          </div>
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
