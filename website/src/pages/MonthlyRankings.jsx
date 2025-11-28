import React, { useState, useEffect } from 'react';
import { getAllTimeLeaderboard, getMonthlyLeaderboard } from '../utils/dataLoader';
import { parseStats } from '../utils/formatters';
import LeaderboardTable from '../components/LeaderboardTable';
import SearchBar from '../components/SearchBar';

/**
 * MonthlyRankings Page
 * View all-time and monthly leaderboards
 */
export default function MonthlyRankings() {
  const [viewMode, setViewMode] = useState('all-time'); // 'all-time' or 'monthly'
  const [leaderboardData, setLeaderboardData] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  // Current month/year
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());

  // Load leaderboard data
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        if (viewMode === 'all-time') {
          const data = await getAllTimeLeaderboard(1000);
          // Transform data for table
          const transformed = data.map((player) => {
            const stats = parseStats(player.stats);
            return {
              username: player.username,
              points: player.totalPoints,
              games: stats.gamesPlayed,
              wins: stats.wins,
              avgPlacement: stats.avgPlacement,
              totalKills: stats.totalKills
            };
          });
          setLeaderboardData(transformed);
        } else {
          const data = await getMonthlyLeaderboard(selectedYear, selectedMonth, 1000);
          setLeaderboardData(data);
        }
      } catch (error) {
        console.error('Error loading leaderboard:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [viewMode, selectedMonth, selectedYear]);

  // Filter by search query
  const filteredData = leaderboardData.filter((player) =>
    player.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Generate month options (last 12 months)
  const monthOptions = [];
  for (let i = 0; i < 12; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    monthOptions.push({
      month: date.getMonth() + 1,
      year: date.getFullYear(),
      label: date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    });
  }

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
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Monthly Rankings</h2>
        <p className="text-gray-600">
          The top 50k places from each daily follower race are awarded points. At the end of the month,
          the top 1000 ranked followers qualify for the monthly medal race to crown the monthly winner!
          Unfollowers will not qualify.
        </p>
      </div>

      {/* View Mode Toggle */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex bg-gray-200 rounded-lg p-1">
          <button
            onClick={() => {
              setViewMode('all-time');
              setSearchQuery('');
              setCurrentPage(1);
            }}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              viewMode === 'all-time'
                ? 'bg-white text-primary shadow-sm'
                : 'text-gray-700 hover:text-gray-900'
            }`}
          >
            All-Time
          </button>
          <button
            onClick={() => {
              setViewMode('monthly');
              setSearchQuery('');
              setCurrentPage(1);
            }}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              viewMode === 'monthly'
                ? 'bg-white text-primary shadow-sm'
                : 'text-gray-700 hover:text-gray-900'
            }`}
          >
            Monthly
          </button>
        </div>

        {/* Month Selector (only for monthly view) */}
        {viewMode === 'monthly' && (
          <div className="flex-1 min-w-[200px]">
            <select
              value={`${selectedYear}-${selectedMonth}`}
              onChange={(e) => {
                const [year, month] = e.target.value.split('-').map(Number);
                setSelectedYear(year);
                setSelectedMonth(month);
                setCurrentPage(1);
              }}
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md bg-white"
            >
              {monthOptions.map((option) => (
                <option key={`${option.year}-${option.month}`} value={`${option.year}-${option.month}`}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <SearchBar value={searchQuery} onChange={setSearchQuery} />
        </div>
      </div>

      {/* Leaderboard Table */}
      {filteredData.length > 0 ? (
        <LeaderboardTable
          data={filteredData}
          columns={['rank', 'username', 'points', 'games', 'wins', 'avg']}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
      ) : (
        <div className="text-center py-12 text-gray-500">
          {searchQuery ? 'No players found matching your search' : 'No data available'}
        </div>
      )}
    </div>
  );
}
