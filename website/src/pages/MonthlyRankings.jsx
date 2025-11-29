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
      <div className="flex flex-col justify-center items-center min-h-screen bg-dark-bg-primary">
        <div className="text-6xl animate-bounce-slow mb-4">📊</div>
        <div className="text-2xl font-bold text-primary animate-pulse">Loading Rankings...</div>
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
            Monthly Rankings
          </h2>
          <p className="text-lg text-text-secondary max-w-3xl mx-auto font-medium leading-relaxed mb-4">
            The top 50k places from each daily follower race are awarded points. At the end of the month,
            the top 1000 ranked followers qualify for the monthly medal race to crown the monthly winner!
            Unfollowers will not qualify.
          </p>
        </div>

        {/* Controls */}
        <div className="bg-dark-bg-secondary rounded-card shadow-card-dark border-2 border-slate-700 p-8 mb-8">
          <div className="flex flex-wrap items-center gap-4">
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

            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <SearchBar value={searchQuery} onChange={setSearchQuery} placeholder="Search players..." />
            </div>
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
      </div>
    </div>
  );
}
