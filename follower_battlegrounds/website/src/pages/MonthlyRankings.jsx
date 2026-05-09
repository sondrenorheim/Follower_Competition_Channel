import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { loadIndex, getMonthlyLeaderboard, getAllTimeLeaderboardData, normalizeResultPlatform } from '../utils/dataLoader';
import LeaderboardTable from '../components/LeaderboardTable';
import SearchBar from '../components/SearchBar';
import PlatformTabs from '../components/PlatformTabs';

/**
 * MonthlyRankings Page
 * View all-time and monthly leaderboards
 */
export default function MonthlyRankings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPlatform = normalizeResultPlatform(searchParams.get('platform'));
  const [viewMode, setViewMode] = useState('all-time'); // 'all-time', 'monthly', or 'top-stats'
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Starting');
  const [currentPage, setCurrentPage] = useState(1);
  const [availableMonths, setAvailableMonths] = useState([]);
  const [selectedStatCategory, setSelectedStatCategory] = useState('points');
  const [gameTypeFilter, setGameTypeFilter] = useState('all'); // 'all' or specific game_type
  const [gameTypes, setGameTypes] = useState([]);
  const [indexReady, setIndexReady] = useState(false);
  const [previewLimit, setPreviewLimit] = useState(null);
  const [allTimeMeta, setAllTimeMeta] = useState({
    totalPlayers: 0,
    isPreview: false,
    previewLimit: null,
    totalResults: 0
  });
  const [monthlyMeta, setMonthlyMeta] = useState({
    totalPlayers: 0,
    isPreview: false,
    previewLimit: null,
    totalResults: 0
  });
  const [forceFullAllTime, setForceFullAllTime] = useState(false);
  const [forceFullMonthly, setForceFullMonthly] = useState(false);

  // Current month/year
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());

  const handlePlatformChange = React.useCallback((platform) => {
    const next = normalizeResultPlatform(platform);
    setSearchParams((params) => {
      const updated = new URLSearchParams(params);
      updated.set('platform', next);
      return updated;
    });
    setGameTypeFilter('all');
    setSearchQuery('');
    setCurrentPage(1);
    setForceFullAllTime(false);
    setForceFullMonthly(false);
  }, [setSearchParams]);

  // Load available months and game types from the index
  useEffect(() => {
    let isMounted = true;

    async function loadIndexData() {
      let shouldStopLoading = true;
      setLoading(true);
      setLoadingProgress(5);
        setLoadingMessage('Loading index');
      try {
        setIndexReady(false);
        const index = await loadIndex(selectedPlatform);
        if (!index || !isMounted) return;

        setPreviewLimit(index.results_preview_limit || 200);

        const months = (index.available_months || []).map((key) => {
          const [year, month] = key.split('-').map(Number);
          return {
            month,
            year,
            label: new Date(year, month - 1, 1).toLocaleDateString('en-US', {
              month: 'long',
              year: 'numeric'
            })
          };
        });

        months.sort((a, b) => {
          if (a.year !== b.year) return b.year - a.year;
          return b.month - a.month;
        });

        setAvailableMonths(months);
        setLoadingProgress(30);
        setLoadingMessage('Preparing filters');

        if (months.length > 0) {
          setSelectedMonth(months[0].month);
          setSelectedYear(months[0].year);
        }

        const types = (index.types_metadata || []).map((t) => ({
          type: t.type,
          displayName: t.type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
          count: t.games
        }));
        setGameTypes(types);
        setIndexReady(true);
        setLoadingProgress(40);
        setLoadingMessage('Index ready');
        shouldStopLoading = false;
      } catch (error) {
        console.error('Error loading index:', error);
      } finally {
        if (isMounted && shouldStopLoading) {
          setLoading(false);
        }
      }
    }

    loadIndexData();
    return () => {
      isMounted = false;
    };
  }, [selectedPlatform]);

  useEffect(() => {
    if (!searchQuery) return;
    if (viewMode === 'monthly' && monthlyMeta.isPreview && !forceFullMonthly) {
      setForceFullMonthly(true);
    }
    if (viewMode !== 'monthly' && allTimeMeta.isPreview && !forceFullAllTime) {
      setForceFullAllTime(true);
    }
  }, [searchQuery, viewMode, monthlyMeta.isPreview, allTimeMeta.isPreview, forceFullMonthly, forceFullAllTime]);

  // Load leaderboard data
  useEffect(() => {
    if (!indexReady) return;

    let isMounted = true;

    async function loadData() {
      setLoading(true);
      setLoadingProgress(50);
      setLoadingMessage('Loading leaderboard');
      try {
        if (viewMode === 'monthly') {
          if (!selectedMonth || !selectedYear) {
            setLeaderboardData([]);
            return;
          }
          setLoadingProgress(70);
          setLoadingMessage('Loading monthly results');
          const { entries, meta } = await getMonthlyLeaderboard(
            selectedYear,
            selectedMonth,
            null,
            gameTypeFilter,
            { preview: !forceFullMonthly, platform: selectedPlatform }
          );
          if (!isMounted) return;
          setLeaderboardData(entries);
          setMonthlyMeta(meta);
          setLoadingProgress(100);
          setLoadingMessage('Done');
        } else {
          setLoadingProgress(70);
          setLoadingMessage('Loading all-time stats');
          const usePreview = viewMode === 'all-time' && !forceFullAllTime;
          const { entries, meta } = await getAllTimeLeaderboardData({ preview: usePreview, platform: selectedPlatform });
          if (!isMounted) return;
          setAllTimeMeta(meta);

          setLoadingProgress(90);
          setLoadingMessage('Sorting results');
          const data = [...entries];
          if (viewMode === 'top-stats') {
            data.sort((a, b) => {
              switch (selectedStatCategory) {
                case 'points':
                  return b.points - a.points;
                case 'kills':
                  return b.totalKills - a.totalKills;
                case 'wins':
                  return b.wins - a.wins;
                case 'top3':
                  return b.top3Finishes - a.top3Finishes;
                case 'top10pct':
                  return b.top10PctFinishes - a.top10PctFinishes;
                case 'avgPlacement':
                  return parseFloat(a.avgPlacement) - parseFloat(b.avgPlacement);
                case 'games':
                  return b.games - a.games;
                default:
                  return b.points - a.points;
              }
            });
          }

          if (!isMounted) return;
          setLeaderboardData(data);
          setLoadingProgress(100);
          setLoadingMessage('Done');
        }
      } catch (error) {
        console.error('Error loading leaderboard:', error);
        setLoadingProgress(100);
        setLoadingMessage('Loading failed');
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [indexReady, viewMode, selectedMonth, selectedYear, selectedStatCategory, gameTypeFilter, forceFullMonthly, forceFullAllTime, selectedPlatform]);

  // Keep game type filter limited to monthly view
  useEffect(() => {
    if (viewMode !== 'monthly' && gameTypeFilter !== 'all') {
      setGameTypeFilter('all');
    }
  }, [viewMode, gameTypeFilter]);



  // Filter by search query but keep original ranks from the full sorted set
  const filteredData = React.useMemo(() => {
    const base = leaderboardData.map((player, index) => ({
      ...player,
      calculatedRank: index + 1
    }));
    if (!searchQuery) return base;
    const q = searchQuery.toLowerCase();
    return base.filter((player) => player.username.toLowerCase().includes(q));
  }, [leaderboardData, searchQuery]);

  // Use available months only
  const monthOptions = availableMonths;
  const gameTypeOptions = [
    { type: 'all', displayName: 'All Games' },
    ...gameTypes
  ];

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-dark-bg-primary">
        <div className="text-6xl animate-bounce-slow mb-4">📊</div>
        <div className="text-2xl font-bold text-primary animate-pulse">Loading Rankings...</div>
        <div className="mt-4 flex gap-2">
          <div className="w-3 h-3 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-3 h-3 bg-secondary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-3 h-3 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
        <div className="mt-6 w-64 max-w-xs">
          <div className="h-2 rounded-full bg-dark-bg-tertiary overflow-hidden border border-slate-600">
            <div
              className="h-full bg-gradient-to-r from-primary via-secondary to-accent transition-all duration-300"
              style={{ width: `${loadingProgress}%` }}
            ></div>
          </div>
          <div className="mt-3 text-sm text-text-muted">
            {loadingMessage} {loadingProgress}%
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        {/* Page Header */}
        <div className="mb-8 text-center animate-fade-in">
          <h2 className="text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent mb-6 tracking-tight">
            Monthly Rankings
          </h2>
          <p className="text-lg text-text-secondary max-w-3xl mx-auto font-medium leading-relaxed mb-4">
            Every day each daily follower race count towards points. At the end of the month,
            the top 10% ranked followers qualify for the monthly medal race to crown the monthly winner!
            Unfollowers will not qualify.
          </p>
        </div>

        {/* Controls */}
        <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-5 sm:p-8 mb-8">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[260px]">
              <PlatformTabs value={selectedPlatform} onChange={handlePlatformChange} />
            </div>

            {/* View Mode Toggle */}
            <div className="flex bg-dark-surface/50 rounded-xl p-1.5 border-2 border-slate-600">
              <button
                onClick={() => {
                  setViewMode('all-time');
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className={`px-8 py-4 rounded-lg font-bold transition-all duration-200 ${
                  viewMode === 'all-time'
                    ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary border-accent scale-105'
                    : 'text-text-muted hover:text-text-primary hover:bg-dark-surface/70 hover:scale-105'
                }`}
              >
                🏆 All-Time
              </button>
              <button
                onClick={() => {
                  setViewMode('monthly');
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className={`px-8 py-4 rounded-lg font-bold transition-all duration-200 ${
                  viewMode === 'monthly'
                    ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary border-accent scale-105'
                    : 'text-text-muted hover:text-text-primary hover:bg-dark-surface/70 hover:scale-105'
                }`}
              >
                📅 Monthly
              </button>
              <button
                onClick={() => {
                  setViewMode('top-stats');
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className={`px-8 py-4 rounded-lg font-bold transition-all duration-200 ${
                  viewMode === 'top-stats'
                    ? 'bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary border-accent scale-105'
                    : 'text-text-muted hover:text-text-primary hover:bg-dark-surface/70 hover:scale-105'
                }`}
              >
                📊 Top Stats
              </button>
            </div>

            {/* Month Selector (only for monthly view) */}
            {viewMode === 'monthly' && (
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <select
                    value={`${selectedYear}-${selectedMonth}`}
                    onChange={(e) => {
                      const [year, month] = e.target.value.split('-').map(Number);
                      setSelectedYear(year);
                      setSelectedMonth(month);
                      setCurrentPage(1);
                    }}
                    className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none"
                  >
                    {monthOptions.map((option) => (
                      <option key={`${option.year}-${option.month}`} value={`${option.year}-${option.month}`} className="bg-dark-bg-secondary text-text-primary">
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                    <svg className="h-5 w-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            )}

            {/* Game Type Selector */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <select
                  value={gameTypeFilter}
                  onChange={(e) => {
                    setGameTypeFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  disabled={viewMode !== 'monthly'}
                  className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {gameTypeOptions.map((gameType) => (
                    <option key={gameType.type} value={gameType.type} className="bg-dark-bg-secondary text-text-primary">
                      {gameType.displayName}
                    </option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  <svg className="h-5 w-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              {viewMode !== 'monthly' && (
                <p className="mt-2 text-xs text-text-muted">Game type filter is available in monthly view.</p>
              )}
            </div>

            {/* Category Selector (only for top stats view) */}
            {viewMode === 'top-stats' && (
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <select
                    value={selectedStatCategory}
                    onChange={(e) => {
                      setSelectedStatCategory(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none"
                  >
                    <option value="points" className="bg-dark-bg-secondary text-text-primary">Most Points</option>
                    <option value="kills" className="bg-dark-bg-secondary text-text-primary">Most Kills</option>
                    <option value="wins" className="bg-dark-bg-secondary text-text-primary">Most Wins</option>
                    <option value="top3" className="bg-dark-bg-secondary text-text-primary">Most Top 3 Finishes</option>
                    <option value="top10pct" className="bg-dark-bg-secondary text-text-primary">Most Top 10% Finishes</option>
                    <option value="avgPlacement" className="bg-dark-bg-secondary text-text-primary">Best Average Placement</option>
                    <option value="games" className="bg-dark-bg-secondary text-text-primary">Most Games Played</option>
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                    <svg className="h-5 w-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            )}

            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Search players..." trackingSource="monthly_rankings" />
            </div>
          </div>
        </div>

        {/* Leaderboard Table */}
        {filteredData.length > 0 ? (
          <LeaderboardTable
            data={filteredData}
            columns={
              viewMode === 'top-stats'
                ? selectedStatCategory === 'kills'
                  ? ['rank', 'username', 'kills', 'points', 'games']
                  : selectedStatCategory === 'wins'
                    ? ['rank', 'username', 'wins', 'points', 'games']
                    : selectedStatCategory === 'top3'
                      ? ['rank', 'username', 'top3', 'points', 'games']
                      : selectedStatCategory === 'top10pct'
                        ? ['rank', 'username', 'top10pct', 'points', 'games']
                        : selectedStatCategory === 'avgPlacement'
                          ? ['rank', 'username', 'avg', 'points', 'games']
                          : selectedStatCategory === 'games'
                            ? ['rank', 'username', 'games', 'points', 'wins']
                            : ['rank', 'username', 'points', 'games', 'wins', 'avg']
                : ['rank', 'username', 'points', 'games', 'wins', 'avg']
            }
            currentPage={currentPage}
            onPageChange={setCurrentPage}
            trackingSource="monthly_rankings"
            playerPlatform={selectedPlatform}
          />
        ) : (
          <div className="text-center py-20 bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-dashed border-slate-600 animate-fade-in">
            <div className="text-6xl mb-4 animate-bounce-slow">
              {searchQuery ? '🔍' : '📊'}
            </div>
            <p className="text-2xl font-bold text-text-primary mb-2">
              {searchQuery ? 'No Players Found' : 'No Data Available'}
            </p>
            <p className="text-text-muted mb-6">
              {searchQuery ? 'Try a different search term' : 'Rankings will appear after games are played'}
            </p>
            <div className="flex justify-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-secondary rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></div>
              <div className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></div>
            </div>
          </div>
        )}

        {viewMode === 'monthly' && monthlyMeta.isPreview && (
          <div className="mt-6 bg-dark-bg-secondary border-2 border-slate-700 rounded-card p-6 shadow-card-dark flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="text-text-secondary text-sm">
              Showing top {monthlyMeta.previewLimit || previewLimit || 200} of{' '}
              {monthlyMeta.totalResults || monthlyMeta.totalPlayers || filteredData.length} players.
            </div>
            <button
              onClick={() => setForceFullMonthly(true)}
              className="px-4 py-2 rounded-lg font-bold bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary hover:scale-105 transition-transform"
            >
              Load full monthly results
            </button>
          </div>
        )}

        {viewMode !== 'monthly' && allTimeMeta.isPreview && (
          <div className="mt-6 bg-dark-bg-secondary border-2 border-slate-700 rounded-card p-6 shadow-card-dark flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="text-text-secondary text-sm">
              Showing top {allTimeMeta.previewLimit || previewLimit || 200} of{' '}
              {allTimeMeta.totalResults || allTimeMeta.totalPlayers || filteredData.length} players.
            </div>
            <button
              onClick={() => setForceFullAllTime(true)}
              className="px-4 py-2 rounded-lg font-bold bg-gradient-to-r from-primary to-secondary text-white shadow-glow-primary hover:scale-105 transition-transform"
            >
              Load full all-time results
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
