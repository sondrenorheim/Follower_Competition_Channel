/**
 * Data Loader Utilities
 * Fetches and caches game statistics and history data
 */

const DATA_BASE_PATH = '/'; // Serve from root (works in both dev and production)

// Cache for loaded data
let cachedPlayerStats = null;
let cachedGameHistory = null;

/**
 * Load player statistics from JSON file
 * @returns {Promise<Object>} Player statistics data
 */
export async function loadPlayerStats() {
  if (cachedPlayerStats) {
    return cachedPlayerStats;
  }

  const primaryPaths = [
    `${DATA_BASE_PATH}player_statistics_web.json`,
    `${DATA_BASE_PATH}player_statistics.json`,
  ];

  for (const path of primaryPaths) {
    try {
      const response = await fetch(path);
      if (!response.ok) continue;
      const data = await response.json();
      cachedPlayerStats = data;
      return data;
    } catch (err) {
      // try next
    }
  }

  console.error('Error loading player statistics (all sources failed)');
  // Return mock data for development
  return {
    last_updated: new Date().toISOString(),
    total_games_recorded: 0,
    players: {}
  };
}

/**
 * Load game history from JSON file
 * @returns {Promise<Object>} Game history data
 */
export async function loadGameHistory() {
  if (cachedGameHistory) {
    return cachedGameHistory;
  }

  const primaryPaths = [
    `${DATA_BASE_PATH}game_history_web.json`,
    `${DATA_BASE_PATH}game_history.json`,
  ];

  for (const path of primaryPaths) {
    try {
      const response = await fetch(path);
      if (!response.ok) continue;
      const data = await response.json();
      cachedGameHistory = data;
      return data;
    } catch (err) {
      // try next
    }
  }

  console.error('Error loading game history (all sources failed)');
  // Return mock data for development
  return {
    games: []
  };
}

/**
 * Get all games of a specific type
 * @param {string} gameType - Game type identifier (e.g., "battle_royale")
 * @returns {Promise<Array>} Array of game records
 */
export async function getGamesByType(gameType) {
  const history = await loadGameHistory();

  if (gameType === 'all') {
    return history.games || [];
  }

  return (history.games || []).filter(game => game.game_type === gameType);
}

/**
 * Get a specific game by ID
 * @param {string} gameId - Unique game identifier
 * @returns {Promise<Object|null>} Game record or null if not found
 */
export async function getGameById(gameId) {
  const history = await loadGameHistory();
  return (history.games || []).find(game => game.game_id === gameId) || null;
}

/**
 * Get player statistics for a specific username
 * @param {string} username - Player username
 * @returns {Promise<Object|null>} Player stats or null if not found
 */
export async function getPlayerStats(username) {
  const stats = await loadPlayerStats();
  return stats.players?.[username] || null;
}

/**
 * Get all-time leaderboard sorted by total points
 * @param {number} limit - Number of top players to return
 * @returns {Promise<Array>} Array of {username, stats} objects
 */
export async function getAllTimeLeaderboard(limit = 10) {
  const stats = await loadPlayerStats();

  const players = Object.entries(stats.players || {}).map(([username, playerData]) => {
    const statsArray = playerData.stats || playerData;
    const totalPoints = Array.isArray(statsArray) ? statsArray[0] : 0;

    return {
      username,
      totalPoints,
      stats: statsArray,
      gameBreakdown: playerData.game_breakdown || {},
      recentGames: playerData.recent_games || []
    };
  });

  players.sort((a, b) => b.totalPoints - a.totalPoints);

  return players.slice(0, limit);
}

/**
 * Get monthly leaderboard for a specific month
 * @param {number} year - Year
 * @param {number} month - Month (1-12)
 * @param {number} limit - Number of top players to return
 * @returns {Promise<Array>} Array of player rankings for the month
 */
export async function getMonthlyLeaderboard(year, month, limit = 1000) {
  const history = await loadGameHistory();

  // Filter games from the specified month
  const monthGames = (history.games || []).filter(game => {
    const gameDate = new Date(game.timestamp);
    return gameDate.getFullYear() === year && gameDate.getMonth() === month - 1;
  });

  // Aggregate player stats for the month
  const monthlyStats = {};

  monthGames.forEach(game => {
    game.results.forEach(result => {
      if (!monthlyStats[result.username]) {
        monthlyStats[result.username] = {
          username: result.username,
          points: 0,
          games: 0,
          wins: 0,
          bestPlacement: Infinity,
          totalKills: 0
        };
      }

      const player = monthlyStats[result.username];
      player.points += result.points;
      player.games += 1;
      if (result.placement === 1) player.wins += 1;
      if (result.placement < player.bestPlacement) player.bestPlacement = result.placement;
      player.totalKills += result.kills || 0;
    });
  });

  const leaderboard = Object.values(monthlyStats);
  leaderboard.sort((a, b) => b.points - a.points);

  return leaderboard.slice(0, limit);
}

/**
 * Get game history for a specific player
 * @param {string} username - Player username
 * @param {number} limit - Number of recent games to return
 * @returns {Promise<Array>} Array of game records where player participated
 */
export async function getPlayerGameHistory(username, limit = 10) {
  const history = await loadGameHistory();
  const playerGames = [];

  for (const game of history.games || []) {
    const playerResult = game.results.find(r => r.username === username);
    if (playerResult) {
      playerGames.push({
        gameId: game.game_id,
        gameType: game.game_type,
        gameDisplayName: game.game_display_name,
        dayNumber: game.day_number,
        timestamp: game.timestamp,
        ...playerResult
      });
    }
  }

  // Sort by timestamp, most recent first
  playerGames.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  return playerGames.slice(0, limit);
}

/**
 * Clear cached data (useful for forcing refresh)
 */
export function clearCache() {
  cachedPlayerStats = null;
  cachedGameHistory = null;
}

/**
 * Get list of available game types
 * @returns {Promise<Array>} Array of {type, displayName, count} objects
 */
export async function getGameTypes() {
  const history = await loadGameHistory();
  const typeCounts = {};

  (history.games || []).forEach(game => {
    if (!typeCounts[game.game_type]) {
      typeCounts[game.game_type] = {
        type: game.game_type,
        displayName: game.game_display_name,
        count: 0
      };
    }
    typeCounts[game.game_type].count += 1;
  });

  return Object.values(typeCounts);
}
