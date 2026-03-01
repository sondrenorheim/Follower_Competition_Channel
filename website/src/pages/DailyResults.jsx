import React, { useState, useEffect, useRef } from 'react';
import { loadDay, loadIndex, loadDayAggregate, loadGame, loadGamePreview } from '../utils/dataLoader';
import LeaderboardTable from '../components/LeaderboardTable';
import SearchBar from '../components/SearchBar';
import GameFilter from '../components/GameFilter';

const ITEMS_PER_PAGE = 50;

/**
 * DailyResults Page
 * Browse individual game episode results
 */
export default function DailyResults() {
  const [gameTypes, setGameTypes] = useState([]);
  const [daysMetadata, setDaysMetadata] = useState([]);
  const [availableDays, setAvailableDays] = useState([]);
  const [selectedGameType, setSelectedGameType] = useState('all');
  const [selectedDayNumber, setSelectedDayNumber] = useState(null);
  const [selectedGame, setSelectedGame] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Starting');
  const [currentPage, setCurrentPage] = useState(1);
  const [indexLoaded, setIndexLoaded] = useState(false);
  const [isLoadingFullResults, setIsLoadingFullResults] = useState(false);
  const initialLoadRef = useRef(true);
  const fullResultsLoadingRef = useRef(false);

  // Load index + metadata on mount
  useEffect(() => {
    let isMounted = true;

    async function loadIndexData() {
      setLoading(true);
      setLoadingProgress(5);
      setLoadingMessage('Loading index');
      try {
        const index = await loadIndex();
        if (!isMounted) return;

        const types = (index?.types_metadata || []).map((t) => ({
          type: t.type,
          displayName: t.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          count: t.games
        }));
        setGameTypes(types);

        const days = index?.available_days || [];
        const meta = index?.days_metadata || [];
        setAvailableDays(days);
        setDaysMetadata(meta);

        if (days.length === 0) {
          setSelectedDayNumber(null);
          setSelectedGame(null);
          setLoadingProgress(100);
          setLoadingMessage('No days available');
          setLoading(false);
          initialLoadRef.current = false;
          return;
        }

        setLoadingProgress(35);
        setLoadingMessage('Preparing latest day');
        const maxDay = Math.max(...days);
        setSelectedDayNumber(maxDay);
        setLoadingProgress(60);
        setLoadingMessage('Loading results');
      } catch (error) {
        console.error('Error loading index:', error);
        setLoadingProgress(100);
        setLoadingMessage('Loading failed');
        setLoading(false);
        initialLoadRef.current = false;
      } finally {
        if (isMounted) {
          setIndexLoaded(true);
        }
      }
    }

    loadIndexData();
    return () => {
      isMounted = false;
    };
  }, []);

  const dayOptions = React.useMemo(() => {
    if (selectedGameType === 'all') {
      return availableDays;
    }

    return daysMetadata
      .filter((day) => Array.isArray(day.types) && day.types.includes(selectedGameType))
      .map((day) => day.day);
  }, [selectedGameType, availableDays, daysMetadata]);

  // Ensure selected day is valid for the chosen type
  useEffect(() => {
    if (!indexLoaded) {
      return;
    }
    if (!dayOptions || dayOptions.length === 0) {
      setSelectedDayNumber(null);
      setSelectedGame(null);
      return;
    }

    const maxDay = Math.max(...dayOptions);
    if (selectedDayNumber === null || !dayOptions.includes(selectedDayNumber)) {
      setSelectedDayNumber(maxDay);
    }
  }, [dayOptions, selectedDayNumber, indexLoaded]);

  useEffect(() => {
    setSearchQuery('');
    setCurrentPage(1);
  }, [selectedGameType]);

  useEffect(() => {
    setSearchQuery('');
    setCurrentPage(1);
  }, [selectedDayNumber]);

  // Load selected game when day or type changes
  useEffect(() => {
    let cancelled = false;

    async function loadSelection() {
      if (!indexLoaded) {
        return;
      }
      if (selectedDayNumber === null) {
        setSelectedGame(null);
        if (initialLoadRef.current) {
          setLoadingProgress(100);
          setLoadingMessage('No days available');
          setLoading(false);
          initialLoadRef.current = false;
        }
        return;
      }

      let game = null;
      if (selectedGameType === 'all') {
        game = await loadDayAggregate(selectedDayNumber, { preview: true });
      } else {
        const dayData = await loadDay(selectedDayNumber);
        if (dayData && dayData.games) {
          const matches = dayData.games.filter((g) => g.game_type === selectedGameType);
          if (matches.length > 0) {
            const latestGame = matches.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''))[0];
            game = await loadGamePreview(latestGame.game_id);
          }
        }
      }

      if (cancelled) return;
      setSelectedGame(game);
      setIsLoadingFullResults(false);

      if (initialLoadRef.current) {
        setLoadingProgress(100);
        setLoadingMessage('Done');
        setLoading(false);
        initialLoadRef.current = false;
      }
    }

    loadSelection();
    return () => {
      cancelled = true;
    };
  }, [selectedDayNumber, selectedGameType, indexLoaded]);

  const previewInfo = React.useMemo(() => {
    if (!selectedGame || !selectedGame._isPreview) return null;
    const previewLimit = selectedGame.preview_limit || selectedGame.results?.length || 0;
    const totalResults = selectedGame.total_results || selectedGame.total_participants || selectedGame.results?.length || 0;
    const previewPages = previewLimit ? Math.ceil(previewLimit / ITEMS_PER_PAGE) : 0;
    return {
      previewLimit,
      totalResults,
      previewPages
    };
  }, [selectedGame]);

  const loadFullResults = React.useCallback(async () => {
    if (!selectedGame || !selectedGame._isPreview) return;
    if (fullResultsLoadingRef.current) return;

    fullResultsLoadingRef.current = true;
    setIsLoadingFullResults(true);
    try {
      const fullGame = selectedGame.game_type === 'all'
        ? await loadDayAggregate(selectedGame.day_number, { preview: false })
        : await loadGame(selectedGame.game_id);
      if (fullGame) {
        setSelectedGame(fullGame);
      }
    } finally {
      fullResultsLoadingRef.current = false;
      setIsLoadingFullResults(false);
    }
  }, [selectedGame]);

  const handlePageChange = React.useCallback((page) => {
    setCurrentPage(page);
    if (!selectedGame || !selectedGame._isPreview || !previewInfo) {
      return;
    }
    if (previewInfo.previewPages > 0 && page >= previewInfo.previewPages) {
      loadFullResults();
    }
  }, [selectedGame, previewInfo, loadFullResults]);

  useEffect(() => {
    if (!selectedGame || !selectedGame._isPreview || !previewInfo) return;

    const needsFullResults = searchQuery.trim().length > 0 ||
      (previewInfo.previewPages > 0 && currentPage >= previewInfo.previewPages);
    if (!needsFullResults) return;

    loadFullResults();
  }, [searchQuery, currentPage, selectedGame, previewInfo, loadFullResults]);

  // For daily "All Games", load full results in the background so paging/search is never limited to preview data.
  useEffect(() => {
    if (!selectedGame || !selectedGame._isPreview) return;
    if (selectedGame.game_type !== 'all') return;
    loadFullResults();
  }, [selectedGame, loadFullResults]);

  // Sort all results and calculate ranks once per selection, then filter by search
  const rankedResults = React.useMemo(() => {
    if (!selectedGame || !Array.isArray(selectedGame.results)) return [];

    const sortedResults = [...selectedGame.results].sort((a, b) => {
      const pointsA = a.points || 0;
      const pointsB = b.points || 0;
      return pointsB - pointsA;
    });

    const ranks = new Array(sortedResults.length);
    let currentRank = 1;
    sortedResults.forEach((res, idx) => {
      if (idx > 0) {
        const prevPoints = sortedResults[idx - 1].points || 0;
        const points = res.points || 0;
        if (points < prevPoints) {
          currentRank = idx + 1;
        }
      }
      ranks[idx] = currentRank;
    });

    return sortedResults.map((result, idx) => ({
      ...result,
      calculatedRank: ranks[idx]
    }));
  }, [selectedGame]);

  const filteredResults = React.useMemo(() => {
    if (!rankedResults.length) return [];
    const q = searchQuery.toLowerCase();
    return rankedResults.filter((result) => result.username.toLowerCase().includes(q));
  }, [rankedResults, searchQuery]);

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-dark-bg-primary">
        <div className="text-6xl animate-bounce-slow mb-4"></div>
        <div className="text-2xl font-bold text-primary animate-pulse">Loading Games...</div>
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
      <div className="max-w-7xl mx-auto px-6 sm:px-6 lg:px-8 py-12">
        {/* Page Header */}
        <div className="mb-8 text-center animate-fade-in">
          <h2 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent mb-6 tracking-tight">
            Daily Results
          </h2>
          <p className="text-lg text-text-secondary max-w-3xl mx-auto font-medium leading-relaxed mb-4">
            View the top performers from each follower race or use the search bar to find your result.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-8 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Game Type Filter */}
            <GameFilter
              value={selectedGameType}
              onChange={setSelectedGameType}
              gameTypes={gameTypes}
            />

            {/* Day/Episode Selector */}
            <div className="group">
              <label htmlFor="day-selector" className="block text-sm font-bold text-text-primary mb-2 flex items-center gap-2">
                <span>Day</span>
              </label>
              <div className="relative">
                <select
                  id="day-selector"
                  value={selectedDayNumber || ''}
                  onChange={(e) => {
                    setSelectedDayNumber(Number(e.target.value));
                  }}
                  className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none"
                >
                  {dayOptions.length === 0 ? (
                    <option className="bg-dark-bg-secondary text-text-primary">No days available</option>
                  ) : (
                    [...new Set(dayOptions)]
                      .sort((a, b) => b - a)
                      .map((dayNum) => (
                        <option key={dayNum} value={dayNum} className="bg-dark-bg-secondary text-text-primary">
                          Day {dayNum}
                        </option>
                      ))
                  )}
                </select>
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  <svg className="h-5 w-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Search Bar */}
            <div>
              <label className="block text-sm font-bold text-text-primary mb-2 flex items-center gap-2">
                <span>Search Players</span>
              </label>
              <SearchBar value={searchQuery} onChange={setSearchQuery} trackingSource="daily_results" />
            </div>
          </div>
        </div>

        {/* Results Table */}
        {selectedGame ? (
          <div>
            <div className="mb-8 p-8 bg-gradient-to-r from-primary/20 via-secondary/20 to-accent/20 backdrop-blur-sm rounded-card shadow-card-dark border-2 border-primary/30">
              <h3 className="text-2xl font-bold mb-2 text-text-primary">
                {selectedGame.game_display_name} - Day {selectedGame.day_number}
              </h3>
              <div className="flex items-center gap-4 text-sm text-text-secondary">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {selectedGame.timestamp
                    ? new Date(selectedGame.timestamp).toLocaleDateString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit'
                    })
                    : 'Date TBD'}
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  {selectedGame.total_participants} participants
                </span>
              </div>
              {previewInfo && previewInfo.totalResults > previewInfo.previewLimit ? (
                <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-text-muted">
                  <span>
                    Showing top {previewInfo.previewLimit} of {previewInfo.totalResults} results.
                  </span>
                  <button
                    type="button"
                    onClick={loadFullResults}
                    disabled={isLoadingFullResults}
                    className="px-3 py-1.5 text-xs font-bold border border-accent/60 rounded-lg text-accent hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {isLoadingFullResults ? 'Loading full list...' : 'Load all results'}
                  </button>
                </div>
              ) : null}
              {isLoadingFullResults ? (
                <div className="mt-3 text-sm text-accent">Loading full results...</div>
              ) : null}
            </div>

            <LeaderboardTable
              data={filteredResults}
              columns={
                selectedGame.game_type === 'platformer_race' ||
                selectedGame.game_type === 'obstacle_course' ||
                selectedGame.game_type === 'all'
                  ? ['rank', 'username', 'points']
                  : selectedGame.game_type === 'fighter_arena'
                    ? ['rank', 'username', 'points', 'kills']
                    : selectedGame.game_type === 'team_battle'
                      ? ['rank', 'username', 'points', 'kills']
                      : selectedGame.game_type === 'snake_escape'
                        ? ['rank', 'username', 'points', 'survivalTime']
                        : ['rank', 'username', 'points', 'survivalTime', 'kills']
              }
              itemsPerPage={ITEMS_PER_PAGE}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              trackingSource="daily_results"
            />
          </div>
        ) : (
          <div className="text-center py-20 bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-dashed border-slate-600 animate-fade-in">
            <div className="text-6xl mb-4 animate-bounce-slow">dYZr</div>
            <p className="text-2xl font-bold text-text-primary mb-2">No Games Available</p>
            <p className="text-text-muted mb-6">Try selecting a different game type filter</p>
            <div className="flex justify-center gap-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-secondary rounded-full animate-pulse" style={{ animationDelay: '200ms' }}></div>
              <div className="w-2 h-2 bg-accent rounded-full animate-pulse" style={{ animationDelay: '400ms' }}></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
