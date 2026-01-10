import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPlayerStats, getPlayerGameHistory, getGameTypes } from '../utils/dataLoader';
import { formatPoints, formatDate, getPlacementSuffix, getGameTypeInfo } from '../utils/formatters';
import GameFilter from '../components/GameFilter';

/**
 * PlayerProfile Page
 * Detailed statistics for a specific player
 */
export default function PlayerProfile() {
  const { username } = useParams();
  const [playerData, setPlayerData] = useState(null);
  const [gameHistory, setGameHistory] = useState([]);
  const [allGameHistory, setAllGameHistory] = useState([]);
  const [gameTypes, setGameTypes] = useState([]);
  const [selectedGameType, setSelectedGameType] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPlayerData() {
      setLoading(true);
      try {
        const data = await getPlayerStats(username);
        const history = await getPlayerGameHistory(username, null);
        const types = await getGameTypes();

        setPlayerData(data);
        setAllGameHistory(history);
        setGameHistory(history);
        setGameTypes(types);
      } catch (error) {
        console.error('Error loading player data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadPlayerData();
  }, [username]);

  // Filter game history when game type changes
  useEffect(() => {
    if (selectedGameType === 'all') {
      setGameHistory(allGameHistory);
    } else {
      const filtered = allGameHistory.filter(game => game.gameType === selectedGameType);
      setGameHistory(filtered);
    }
  }, [selectedGameType, allGameHistory]);

  // Calculate stats from filtered game history (memoized)
  const stats = React.useMemo(() => {
    if (gameHistory.length === 0) {
      return {
        totalPoints: 0,
        gamesPlayed: 0,
        bestPlacement: 0,
        avgPlacement: 0,
        wins: 0,
        top3Finishes: 0,
        top10PctFinishes: 0,
        totalKills: 0,
        bestHotStreak: 0,
        firstEliminations: 0
      };
    }

    const totalPoints = gameHistory.reduce((sum, g) => sum + (g.points || 0), 0);
    const totalKills = gameHistory.reduce((sum, g) => sum + (g.kills || 0), 0);
    const wins = gameHistory.filter(g => g.placement === 1).length;
    const top3 = gameHistory.filter(g => g.placement <= 3).length;
    const bestPlacement = Math.min(...gameHistory.map(g => g.placement || Infinity));
    const avgPlacement = gameHistory.reduce((sum, g) => sum + (g.placement || 0), 0) / gameHistory.length;

    const top10Pct = gameHistory.filter(g => g.placement <= 40).length;
    const firstEliminations = gameHistory.filter(g => (g.placement || 0) === 0 || (g.placement || 0) === 1).length;

    let currentStreak = 0;
    let bestStreak = 0;
    gameHistory.forEach(g => {
      if (g.placement <= 40) {
        currentStreak++;
        bestStreak = Math.max(bestStreak, currentStreak);
      } else {
        currentStreak = 0;
      }
    });

    return {
      totalPoints,
      gamesPlayed: gameHistory.length,
      bestPlacement,
      avgPlacement: avgPlacement.toFixed(1),
      wins,
      top3Finishes: top3,
      top10PctFinishes: top10Pct,
      totalKills,
      bestHotStreak: bestStreak,
      firstEliminations
    };
  }, [gameHistory]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!playerData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Player Not Found</h2>
          <p className="text-gray-600 mb-4">No statistics found for username: {username}</p>
          <Link to="/" className="text-primary hover:underline">
            ← Back to Daily Results
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button */}
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-primary hover:text-secondary font-medium mb-6 transition-colors group"
        >
          <svg className="w-5 h-5 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to results
        </Link>

        {/* Player Header */}
        <div className="bg-gradient-to-r from-primary to-secondary rounded-xl shadow-xl p-8 mb-6 text-white">
          <h1 className="text-4xl font-extrabold mb-3">@{username}</h1>
          <p className="text-lg opacity-90">
            View your best and worst results and all-time stats below. Track your progress and see how your
            performance stacks up over time.
          </p>
        </div>

        {/* Game Filter */}
        <div className="mb-6 max-w-xs">
          <GameFilter
            value={selectedGameType}
            onChange={setSelectedGameType}
            gameTypes={gameTypes}
          />
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Points" value={formatPoints(stats.totalPoints)} />
        <StatCard label="Games Played" value={stats.gamesPlayed} />
        <StatCard label="Best Result" value={getPlacementSuffix(stats.bestPlacement)} />
        <StatCard label="Average Result" value={getPlacementSuffix(parseInt(stats.avgPlacement))} />
        <StatCard label="Wins" value={stats.wins} />
        <StatCard label="Top 3 Finishes" value={stats.top3Finishes} />
        <StatCard label="Top 10% Finishes" value={stats.top10PctFinishes} />
          <StatCard label="Total Kills" value={stats.totalKills} />
        </div>

        {/* Streaks & Unlucky */}
        {(stats.bestHotStreak > 0 || stats.firstEliminations > 0) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {stats.bestHotStreak > 0 && (
            <div className="bg-orange-50 border-l-4 border-orange-500 p-4 rounded">
              <div className="flex items-center">
                <span className="text-2xl mr-2">🔥</span>
                <div>
                  <h3 className="font-semibold text-gray-900">Best Hot Streak</h3>
                  <p className="text-gray-600">
                    {stats.bestHotStreak} consecutive top 10% finishes
                  </p>
                </div>
              </div>
            </div>
          )}
          {stats.firstEliminations > 0 && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
              <div className="flex items-center">
                <span className="text-2xl mr-2">💀</span>
                <div>
                  <h3 className="font-semibold text-gray-900">Most Unlucky</h3>
                  <p className="text-gray-600">
                    Eliminated first {stats.firstEliminations} time{stats.firstEliminations > 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            </div>
            )}
          </div>
        )}

        {/* Game Breakdown */}
        {playerData.game_breakdown && Object.keys(playerData.game_breakdown).length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Game Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(playerData.game_breakdown).map(([gameType, count]) => {
              const info = getGameTypeInfo(gameType);
              return (
                <div key={gameType} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${info.color}`}></div>
                  <span className="text-gray-700">
                    {info.name}: <span className="font-semibold">{count}</span>
                  </span>
                </div>
              );
              })}
            </div>
          </div>
        )}

        {/* Recent Game History */}
        <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Game History</h2>

        {gameHistory.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Game</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Points</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Kills</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {gameHistory.map((game, index) => {
                  const info = getGameTypeInfo(game.gameType);
                  return (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-600">{formatDate(game.timestamp)}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`font-medium ${info.textColor}`}>{info.name}</span>
                        <span className="text-gray-500 ml-1">Day {game.dayNumber}</span>
                      </td>
                      <td className="px-4 py-3 text-sm font-medium">{getPlacementSuffix(game.rank)}</td>
                      <td className="px-4 py-3 text-sm">{formatPoints(game.points)}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{game.kills || 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          ) : (
            <p className="text-gray-500">No game history available</p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-5 hover:shadow-xl transition-shadow border-l-4 border-primary">
      <div className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">{label}</div>
      <div className="text-3xl font-extrabold text-gray-900">{value}</div>
    </div>
  );
}
