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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Daily Results</h2>
        <p className="text-gray-600">
          View the top performers from each daily follower race or use the search bar to find your result.
          The top 50k followers are awarded points each day.
        </p>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Game Type Filter */}
        <GameFilter
          value={selectedGameType}
          onChange={setSelectedGameType}
          gameTypes={gameTypes}
        />

        {/* Day/Episode Selector */}
        <div>
          <label htmlFor="game-selector" className="block text-sm font-medium text-gray-700 mb-1">
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
            className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md bg-white"
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
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
        </div>
      </div>

      {/* Results Table */}
      {selectedGame ? (
        <div>
          <div className="mb-4 p-4 bg-red-50 border-l-4 border-primary rounded">
            <h3 className="font-semibold text-gray-900">
              {selectedGame.game_display_name} - Day {selectedGame.day_number}
            </h3>
            <p className="text-sm text-gray-600">
              {new Date(selectedGame.timestamp).toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
              })}
              {' • '}
              {selectedGame.total_participants} participants
            </p>
          </div>

          <LeaderboardTable
            data={filteredResults}
            columns={['rank', 'username', 'points', 'survivalTime', 'kills']}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
          />
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          No games available for this filter
        </div>
      )}
    </div>
  );
}
