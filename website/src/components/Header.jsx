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
    <header className="bg-gradient-to-r from-primary to-secondary shadow-2xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Title */}
        <div className="py-8 text-center">
          <h1 className="text-5xl font-black text-white tracking-tight mb-2 drop-shadow-lg">
            The Follower Games
          </h1>
          <p className="text-white text-sm opacity-90 font-medium">Compete. Survive. Dominate.</p>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex justify-center space-x-2 pb-0">
          {tabs.map((tab) => (
            <Link
              key={tab.path}
              to={tab.path}
              className={`px-8 py-4 text-sm font-bold rounded-t-xl transition-all ${
                isActive(tab.path)
                  ? 'bg-white text-primary shadow-lg scale-105'
                  : 'bg-white/10 text-white hover:bg-white/20 backdrop-blur-sm'
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
