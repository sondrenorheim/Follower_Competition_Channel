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
  const [games, setGames] = useState([]);
  const [gameTypes, setGameTypes] = useState([]);
  const [selectedGameType, setSelectedGameType] = useState('all');
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

        const allGames = await getGamesByType('all');
        setGames(allGames);

        // Select most recent game by default
        if (allGames.length > 0) {
          const sortedGames = [...allGames].sort(
            (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
          );
          setSelectedGame(sortedGames[0]);
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

      // Auto-select most recent game of selected type
      if (filtered.length > 0) {
        const sortedGames = [...filtered].sort(
          (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
        );
        setSelectedGame(sortedGames[0]);
      } else {
        setSelectedGame(null);
      }
    }
    filterGames();
  }, [selectedGameType]);

  // Filter results by search query
  const filteredResults = selectedGame
    ? selectedGame.results.filter((result) =>
        result.username.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8 text-center">
          <h2 className="text-4xl font-extrabold text-gray-900 mb-3 tracking-tight">
            Daily Results
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            View the top performers from each daily follower race or use the search bar to find your result.
            The top 50k followers are awarded points each day.
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Game Type Filter */}
            <GameFilter
              value={selectedGameType}
              onChange={setSelectedGameType}
              gameTypes={gameTypes}
            />

            {/* Day/Episode Selector */}
            <div>
              <label htmlFor="game-selector" className="block text-sm font-semibold text-gray-700 mb-2">
                Episode
              </label>
              <select
                id="game-selector"
                value={selectedGame?.game_id || ''}
                onChange={(e) => {
                  const game = games.find((g) => g.game_id === e.target.value);
                  setSelectedGame(game);
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                className="block w-full pl-3 pr-10 py-2.5 text-base border-2 border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent rounded-lg bg-white hover:border-gray-300 transition-colors"
              >
                {games.length === 0 ? (
                  <option>No games available</option>
                ) : (
                  games
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                    .map((game) => (
                      <option key={game.game_id} value={game.game_id}>
                        Day {game.day_number} - {game.game_display_name} ({game.total_participants} players)
                      </option>
                    ))
                )}
              </select>
            </div>

            {/* Search Bar */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Search Players
              </label>
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
            </div>
          </div>
        </div>

        {/* Results Table */}
        {selectedGame ? (
          <div>
            <div className="mb-6 p-6 bg-gradient-to-r from-primary to-secondary rounded-xl shadow-lg text-white">
              <h3 className="text-2xl font-bold mb-2">
                {selectedGame.game_display_name} - Day {selectedGame.day_number}
              </h3>
              <div className="flex items-center gap-4 text-sm opacity-90">
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  {selectedGame.total_participants} participants
                </span>
              </div>
            </div>

            <LeaderboardTable
              data={filteredResults}
              columns={['rank', 'username', 'points', 'survivalTime', 'kills']}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          </div>
        ) : (
          <div className="text-center py-16 bg-white rounded-xl shadow-lg">
            <div className="text-gray-400 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-xl font-semibold text-gray-600 mb-2">No Games Available</p>
            <p className="text-gray-500">Try selecting a different game type filter</p>
          </div>
        )}
      </div>
    </div>
  );
}
