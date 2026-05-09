import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { loadHallOfFame, getDataBasePath, normalizeResultPlatform } from '../utils/dataLoader';
import { formatPoints, formatDate } from '../utils/formatters';
import PlatformTabs from '../components/PlatformTabs';

function formatMonthKey(monthKey) {
  if (!monthKey) return '';
  const [year, month] = monthKey.split('-').map(Number);
  if (!year || !month) return monthKey;
  const date = new Date(year, month - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

function resolveAssetUrl(basePath, path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  const trimmed = path.replace(/^\/+/, '');
  return `${basePath}${trimmed}`;
}

function Avatar({ username, avatarUrl, sizeClass = 'w-16 h-16' }) {
  const [failed, setFailed] = useState(false);
  const initials = useMemo(() => {
    if (!username) return '?';
    const cleaned = username.replace(/[^a-z0-9]/gi, '');
    return cleaned.slice(0, 2).toUpperCase() || username.slice(0, 2).toUpperCase();
  }, [username]);

  if (!avatarUrl || failed) {
    return (
      <div className={`${sizeClass} rounded-full bg-gradient-to-br from-primary/40 to-secondary/40 border-2 border-slate-600 flex items-center justify-center text-text-primary font-bold`}>
        {initials}
      </div>
    );
  }

  return (
    <img
      src={avatarUrl}
      alt={username}
      className={`${sizeClass} rounded-full object-cover border-2 border-slate-600 shadow-card-dark`}
      onError={() => setFailed(true)}
      loading="lazy"
    />
  );
}

export default function HallOfFame() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPlatform = normalizeResultPlatform(searchParams.get('platform'));
  const [loading, setLoading] = useState(true);
  const [dailyChampions, setDailyChampions] = useState([]);
  const [monthlyChampions, setMonthlyChampions] = useState([]);
  const [error, setError] = useState('');

  const handlePlatformChange = React.useCallback((platform) => {
    const next = normalizeResultPlatform(platform);
    setSearchParams((params) => {
      const updated = new URLSearchParams(params);
      updated.set('platform', next);
      return updated;
    });
  }, [setSearchParams]);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setLoading(true);
      try {
        const data = await loadHallOfFame(selectedPlatform);
        if (!mounted) return;
        const daily = Array.isArray(data?.daily_champions) ? data.daily_champions : [];
        const monthly = Array.isArray(data?.monthly_champions) ? data.monthly_champions : [];
        setDailyChampions(daily);
        setMonthlyChampions(monthly);
        setError('');
      } catch (err) {
        console.error('Failed to load hall of fame:', err);
        if (mounted) {
          setError('Hall of Fame data not available yet.');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, [selectedPlatform]);

  const basePath = getDataBasePath();

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-dark-bg-primary">
        <div className="text-2xl font-bold text-primary animate-pulse">Loading Hall of Fame...</div>
        <div className="mt-4 flex gap-2">
          <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-3 h-3 bg-secondary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-3 h-3 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="mb-10 text-center animate-fade-in">
          <h2 className="text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent mb-6 tracking-tight">
            Hall of Fame
          </h2>
          <p className="text-lg text-text-secondary max-w-3xl mx-auto font-medium leading-relaxed">
            Daily and monthly champions with the most points across all games.
          </p>
        </div>

        <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-5 sm:p-8 mb-8">
          <PlatformTabs value={selectedPlatform} onChange={handlePlatformChange} />
        </div>

        {error ? (
          <div className="text-center py-16 bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-dashed border-slate-600">
            <p className="text-text-muted">{error}</p>
          </div>
        ) : (
          <>
            <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-8 mb-10">
              <h3 className="text-2xl font-bold text-text-primary mb-6">Monthly Champions</h3>
              {monthlyChampions.length === 0 ? (
                <p className="text-text-muted">Monthly champions will appear here once a month completes.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {monthlyChampions.map((champ) => {
                    const avatarUrl = resolveAssetUrl(basePath, champ.avatar);
                    return (
                      <div key={`${champ.month}-${champ.username}`} className="bg-dark-bg-tertiary/60 border-2 border-slate-600 rounded-card p-6 flex items-center gap-4">
                        <Avatar username={champ.username} avatarUrl={avatarUrl} sizeClass="w-16 h-16" />
                        <div>
                          <p className="text-sm uppercase tracking-widest text-text-muted">
                            {formatMonthKey(champ.month)}
                          </p>
                          <p className="text-xl font-bold text-text-primary">@{champ.username}</p>
                          <p className="text-sm text-text-secondary">
                            {formatPoints(champ.points)} points
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-8">
              <h3 className="text-2xl font-bold text-text-primary mb-6">Daily Champions</h3>
              {dailyChampions.length === 0 ? (
                <p className="text-text-muted">Daily champions will appear here after the first results are posted.</p>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {dailyChampions.map((champ, index) => {
                    const avatarUrl = resolveAssetUrl(basePath, champ.avatar);
                    const isLatest = index === 0;
                    return (
                      <div
                        key={`day-${champ.day}-${champ.username}`}
                        className={`flex items-center gap-4 rounded-card border-2 p-6 shadow-card-dark ${
                          isLatest
                            ? 'bg-gradient-to-r from-primary/20 via-secondary/20 to-accent/20 border-primary/40'
                            : 'bg-dark-bg-tertiary/50 border-slate-600'
                        }`}
                      >
                        <Avatar username={champ.username} avatarUrl={avatarUrl} sizeClass="w-20 h-20" />
                        <div>
                          <p className="text-sm uppercase tracking-widest text-text-muted">Day {champ.day}</p>
                          <p className="text-2xl font-bold text-text-primary">@{champ.username}</p>
                          <p className="text-sm text-text-secondary">
                            {formatPoints(champ.points)} points
                          </p>
                          {champ.timestamp ? (
                            <p className="text-xs text-text-muted mt-1">
                              {formatDate(champ.timestamp)}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
