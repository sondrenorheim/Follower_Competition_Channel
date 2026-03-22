import React from 'react';
import { Link, useLocation } from 'react-router-dom';

/**
 * Header Component
 * Main navigation header with tabs
 */
export default function Header() {
  const location = useLocation();
  const isMemberClub = location.pathname.startsWith('/member-club');

  const tabs = [
    { name: 'Daily Results', path: '/' },
    { name: 'Monthly Rankings', path: '/monthly' },
    { name: 'Hall of Fame', path: '/hall-of-fame' },
    { name: 'The Member Club', path: '/member-club' }
  ];

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <header
      className={
        isMemberClub
          ? 'bg-[radial-gradient(circle_at_top,_#3a2a10_0%,_#0d0b09_45%,_#060504_100%)] border-b border-amber-300/30 shadow-[0_0_30px_rgba(255,200,90,0.25)]'
          : 'bg-gradient-to-r from-dark-bg-secondary via-dark-bg-tertiary to-dark-bg-secondary border-b-2 border-slate-700 shadow-2xl shadow-black/50'
      }
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Title */}
        <div className="py-10 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className={`text-5xl ${isMemberClub ? 'text-amber-200' : 'animate-bounce-slow'}`}>🏆</span>
            <h1
              className={
                isMemberClub
                  ? 'text-4xl md:text-5xl font-black text-amber-100 tracking-[0.12em] drop-shadow-[0_0_18px_rgba(255,200,90,0.35)]'
                  : 'text-5xl font-black text-white tracking-tight drop-shadow-lg animate-fade-in'
              }
            >
              {isMemberClub ? 'The Member Club' : 'The Follower Battles'}
            </h1>
            <span className={`text-5xl ${isMemberClub ? 'text-amber-200' : 'animate-bounce-slow'}`}>🏆</span>
          </div>
          <p
            className={
              isMemberClub
                ? 'text-amber-200/80 text-sm font-semibold tracking-[0.35em] uppercase mb-4'
                : 'text-text-secondary text-sm font-medium tracking-wide mb-4'
            }
          >
            {isMemberClub ? 'Member-only access · Celebrated every day' : 'Compete. Survive. Dominate.'}
          </p>

          {/* Social Media Follow Banner */}
          <div className="mt-6 max-w-2xl mx-auto">
            <div
              className={
                isMemberClub
                  ? 'bg-gradient-to-r from-amber-900/60 via-yellow-900/40 to-amber-900/60 border border-amber-300/40 rounded-xl p-4 shadow-[0_0_25px_rgba(255,200,90,0.2)]'
                  : 'bg-gradient-to-r from-purple-900/50 via-pink-900/50 to-purple-900/50 border-2 border-accent/50 rounded-xl p-4 shadow-glow-accent'
              }
            >
              <p className={`font-bold text-sm mb-3 ${isMemberClub ? 'text-amber-100' : 'text-white'}`}>
                {isMemberClub
                  ? '🏅 Thank you for being part of the Club. Your support keeps FBG alive.'
                  : '📣 Join our other media channels'}
              </p>
              <div
                className={
                  isMemberClub
                    ? 'flex flex-nowrap items-center justify-center gap-3'
                    : 'grid grid-cols-3 gap-3 max-w-3xl mx-auto'
                }
              >
                {isMemberClub ? (
                  <a
                    href="https://buymeacoffee.com/followerbattlegrounds/membership"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-8 py-3 rounded-full text-sm font-extrabold uppercase tracking-[0.25em] text-[#120b03] bg-gradient-to-r from-amber-200 via-amber-400 to-amber-300 shadow-[0_0_18px_rgba(255,200,90,0.45)] hover:shadow-[0_0_26px_rgba(255,200,90,0.7)] hover:-translate-y-0.5 transition-all duration-200 border border-amber-100/60"
                  >
                    Join The Club
                  </a>
                ) : (
                  <>
                    <a
                      href="https://www.instagram.com/followerbattlegrounds/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-1 row-start-1 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                      </svg>
                      Instagram
                    </a>
                    <a
                      href="https://www.tiktok.com/@followerbattlegro"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-2 row-start-1 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-cyan-600 to-pink-600 hover:from-cyan-500 hover:to-pink-500 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
                      </svg>
                      TikTok
                    </a>
                    <a
                      href="https://www.youtube.com/@FollowerBattlegrounds"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-3 row-start-1 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                      </svg>
                      YouTube
                    </a>
                    <a
                      href="https://discord.gg/ugNqrD2y"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-1 row-start-2 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/>
                      </svg>
                      Discord
                    </a>
                    <a
                      href="https://www.facebook.com/profile.php?id=61582195167989"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-2 row-start-2 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M22.675 0h-21.35C.595 0 0 .595 0 1.326v21.348C0 23.405.595 24 1.326 24h11.495v-9.294H9.692V11.09h3.129V8.413c0-3.1 1.893-4.788 4.659-4.788 1.325 0 2.463.099 2.795.143v3.24l-1.918.001c-1.504 0-1.794.715-1.794 1.763v2.313h3.587l-.467 3.616h-3.12V24h6.116C23.406 24 24 23.405 24 22.674V1.326C24 .595 23.406 0 22.675 0z"/>
                      </svg>
                      Facebook
                    </a>
                    <a
                      href="https://x.com/FBattlegro85184"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-3 row-start-2 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-slate-800 to-black hover:from-slate-700 hover:to-slate-900 text-white font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M18.901 1.153h3.68l-8.04 9.188L24 22.847h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.153h7.594l5.243 6.932 6.064-6.932Zm-1.291 19.492h2.04L6.486 3.24H4.298L17.61 20.645Z"/>
                      </svg>
                      X
                    </a>
                    <a
                      href="https://buymeacoffee.com/followerbattlegrounds/membership"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="col-start-2 row-start-3 flex items-center justify-center gap-2 w-full px-3 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-[#120b03] font-bold rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg text-xs sm:text-sm whitespace-nowrap"
                    >
                      👑 The Club
                    </a>
                  </>
                )}
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
                tab.path === '/member-club'
                  ? isActive(tab.path)
                    ? 'bg-gradient-to-r from-amber-200 via-amber-300 to-amber-200 text-[#120b03] border-amber-200 shadow-[0_0_18px_rgba(255,200,90,0.6)] scale-105 -translate-y-1'
                    : 'bg-gradient-to-r from-amber-900/40 via-amber-700/30 to-amber-900/40 text-amber-100 border-amber-400/50 hover:border-amber-300 hover:text-amber-50 hover:shadow-[0_0_16px_rgba(255,200,90,0.35)] hover:scale-105'
                  : isActive(tab.path)
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
