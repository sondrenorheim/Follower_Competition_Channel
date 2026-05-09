import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { loadIndex, getPlayerStats, getPlayerGameHistory, getGameTypes, normalizeResultPlatform } from '../utils/dataLoader';
import { formatPoints, formatDate, getPlacementSuffix, getGameTypeInfo } from '../utils/formatters';
import GameFilter from '../components/GameFilter';
import PlatformTabs from '../components/PlatformTabs';

/**
 * PlayerProfile Page
 * Detailed statistics for a specific player
 */
export default function PlayerProfile() {
  const { username } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPlatform = normalizeResultPlatform(searchParams.get('platform'));
  const [playerData, setPlayerData] = useState(null);
  const [gameHistory, setGameHistory] = useState([]);
  const [allGameHistory, setAllGameHistory] = useState([]);
  const [gameTypes, setGameTypes] = useState([]);
  const [selectedGameType, setSelectedGameType] = useState('all');
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Starting');
  const [historyHasMore, setHistoryHasMore] = useState(false);

  const handlePlatformChange = React.useCallback((platform) => {
    const next = normalizeResultPlatform(platform);
    setSearchParams((params) => {
      const updated = new URLSearchParams(params);
      updated.set('platform', next);
      return updated;
    });
    setSelectedGameType('all');
  }, [setSearchParams]);

  useEffect(() => {
    async function loadPlayerData() {
      setLoading(true);
      setLoadingProgress(10);
      setLoadingMessage('Loading player stats');
      try {
        const index = await loadIndex(selectedPlatform);
        const previewLimit = index?.results_preview_limit || 200;

        const [data, history, types] = await Promise.all([
          getPlayerStats(username, selectedPlatform),
          getPlayerGameHistory(username, previewLimit, selectedPlatform),
          getGameTypes(selectedPlatform)
        ]);

        setLoadingProgress(80);
        setLoadingMessage('Finalizing');

        setPlayerData(data);
        setAllGameHistory(history);
        setGameHistory(history);
        setGameTypes(types);
        const totalGames = data?.stats?.[1] || 0;
        setHistoryHasMore(totalGames > history.length);
        setLoadingProgress(100);
        setLoadingMessage('Done');
      } catch (error) {
        console.error('Error loading player data:', error);
        setLoadingProgress(100);
        setLoadingMessage('Loading failed');
      } finally {
        setLoading(false);
      }
    }
    loadPlayerData();
  }, [username, selectedPlatform]);

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
    const statsList = playerData?.stats || [];
    const totalPoints = statsList[0] || 0;
    const gamesPlayed = statsList[1] || 0;
    const bestPlacement = statsList[2] || 0;
    const totalPlacement = statsList[3] || 0;
    const wins = statsList[4] || 0;
    const top3 = statsList[5] || 0;
    const top10Pct = statsList[6] || 0;
    const firstEliminations = statsList[8] || 0;
    const bestHotStreak = statsList[10] || 0;
    const totalKills = statsList[11] || 0;
    const avgPlacement = gamesPlayed > 0 ? (totalPlacement / gamesPlayed).toFixed(1) : '0.0';

    return {
      totalPoints,
      gamesPlayed,
      bestPlacement,
      avgPlacement,
      wins,
      top3Finishes: top3,
      top10PctFinishes: top10Pct,
      totalKills,
      bestHotStreak,
      firstEliminations
    };
  }, [playerData]);

  const loadFullHistory = async () => {
    if (historyLoading) return;
    setHistoryLoading(true);
    try {
      const fullHistory = await getPlayerGameHistory(username, null, selectedPlatform);
      setAllGameHistory(fullHistory);
      setHistoryHasMore(false);
    } catch (error) {
      console.error('Error loading full history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="flex flex-col items-center">
          <div className="text-xl text-gray-600">Loading...</div>
          <div className="mt-4 w-64 max-w-xs">
            <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300"
                style={{ width: `${loadingProgress}%` }}
              ></div>
            </div>
            <div className="mt-2 text-sm text-gray-500">
              {loadingMessage} {loadingProgress}%
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!playerData) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <PlatformTabs value={selectedPlatform} onChange={handlePlatformChange} />
        </div>
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Player Not Found</h2>
          <p className="text-gray-600 mb-4">No statistics found for username: {username}</p>
          <Link to={`/?platform=${encodeURIComponent(selectedPlatform)}`} className="text-primary hover:underline">
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
          to={`/?platform=${encodeURIComponent(selectedPlatform)}`}
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

        <div className="mb-6 grid grid-cols-1 md:grid-cols-[minmax(260px,1fr)_minmax(220px,320px)] gap-4">
          <PlatformTabs value={selectedPlatform} onChange={handlePlatformChange} />
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
        {historyHasMore && (
          <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
            <span>
              Showing the most recent {allGameHistory.length} of {playerData?.stats?.[1] || allGameHistory.length} games.
            </span>
            <button
              onClick={loadFullHistory}
              disabled={historyLoading}
              className="px-4 py-2 rounded-md bg-primary text-white font-semibold hover:bg-secondary transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {historyLoading ? 'Loading full history...' : 'Load full history'}
            </button>
          </div>
        )}

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
