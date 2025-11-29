import React, { useState, useEffect } from 'react';
import { getGamesByType, getGameTypes } from '../utils/dataLoader';
import LeaderboardTable from '../components/LeaderboardTable';
import SearchBar from '../components/SearchBar';
import GameFilter from '../components/GameFilter';

/**
 * DailyResults Page
 * Browse individual game episode results
 */
export default function DailyResults() {
  const [games, setGames] = useState([]); // Filtered games by type
  const [gameTypes, setGameTypes] = useState([]);
  const [selectedGameType, setSelectedGameType] = useState('all');
  const [selectedDayNumber, setSelectedDayNumber] = useState(null);
  const [selectedGame, setSelectedGame] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  // Load game types on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const types = await getGameTypes();
        setGameTypes(types);

        const loadedGames = await getGamesByType('all');
        setGames(loadedGames);

        // Find highest day number
        if (loadedGames.length > 0) {
          const maxDay = Math.max(...loadedGames.map(g => g.day_number));
          setSelectedDayNumber(maxDay);
        }
      } catch (error) {
        console.error('Error loading games:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Filter games when game type changes
  useEffect(() => {
    async function filterGames() {
      const filtered = await getGamesByType(selectedGameType);
      setGames(filtered);

      if (filtered.length > 0) {
        const availableDays = filtered.map(g => g.day_number);
        const maxDay = Math.max(...availableDays);

        // If no day selected or current day not available for this game type, use highest day
        if (selectedDayNumber === null || !availableDays.includes(selectedDayNumber)) {
          setSelectedDayNumber(maxDay);
        }
      }
    }
    filterGames();
  }, [selectedGameType, selectedDayNumber]);

  // Update selected game when day number or filtered games change
  useEffect(() => {
    if (selectedDayNumber !== null && games.length > 0) {
      // Find game matching both the selected game type and day number
      const matchingGame = games.find(g => g.day_number === selectedDayNumber);
      setSelectedGame(matchingGame || null);
    }
  }, [selectedDayNumber, games]);

  // Sort all results and calculate ranks, then filter by search
  const filteredResults = selectedGame
    ? (() => {
        // First, sort all results by points
        const sortedResults = [...selectedGame.results].sort((a, b) => {
          const pointsA = a.points || 0;
          const pointsB = b.points || 0;
          return pointsB - pointsA;
        });

        // Calculate ranks for all players (with tie handling)
        const resultsWithRanks = sortedResults.map((result) => {
          const pointValue = result.points || 0;
          let rank = 1;
          for (let i = 0; i < sortedResults.length; i++) {
            const otherPoints = sortedResults[i].points || 0;
            if (otherPoints > pointValue) {
              rank++;
            }
          }
          return { ...result, calculatedRank: rank };
        });

        // Then filter by search query
        return resultsWithRanks.filter((result) =>
          result.username.toLowerCase().includes(searchQuery.toLowerCase())
        );
      })()
    : [];

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-dark-bg-primary">
        <div className="text-6xl animate-bounce-slow mb-4">🏆</div>
        <div className="text-2xl font-bold text-primary animate-pulse">Loading Games...</div>
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
                <span>📅</span>
                <span>Day</span>
              </label>
              <div className="relative">
                <select
                  id="day-selector"
                  value={selectedDayNumber || ''}
                  onChange={(e) => {
                    setSelectedDayNumber(Number(e.target.value));
                    setSearchQuery('');
                    setCurrentPage(1);
                  }}
                  className="block w-full pl-4 pr-10 py-3 text-base border-2 border-slate-600 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent focus:shadow-glow-accent rounded-xl bg-dark-bg-tertiary text-text-primary hover:border-primary/50 transition-all duration-200 cursor-pointer font-medium shadow-card-dark appearance-none"
                >
                  {games.length === 0 ? (
                    <option className="bg-dark-bg-secondary text-text-primary">No days available</option>
                  ) : (
                    // Get unique day numbers, sort descending
                    [...new Set(games.map(g => g.day_number))]
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
                <span>🔍</span>
                <span>Search Players</span>
              </label>
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
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
                  {new Date(selectedGame.timestamp).toLocaleDateString('en-US', {
                    month: 'long',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  {selectedGame.total_participants} participants
                </span>
              </div>
            </div>

            <LeaderboardTable
              data={filteredResults}
              columns={
                selectedGame.game_type === 'platformer_race'
                  ? ['rank', 'username', 'points']
                  : ['rank', 'username', 'points', 'survivalTime', 'kills']
              }
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          </div>
        ) : (
          <div className="text-center py-20 bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-dashed border-slate-600 animate-fade-in">
            <div className="text-6xl mb-4 animate-bounce-slow">🎮</div>
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
