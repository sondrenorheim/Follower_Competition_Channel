/**
 * Data Loader Utilities
 * Fetches and caches game statistics and history data
 */

const DATA_BASE_PATH = '/'; // Serve from root (works in both dev and production)

// Cache for loaded data
let cachedPlayerStats = null;
let cachedGameHistory = null;

// Cache for partitioned data
let cachedIndex = null;
let cachedDays = new Map(); // Map of day_number -> day_data
let cachedPlayerLetters = new Map(); // Map of letter -> player_data
let cachedPlayerIndex = null;

// Game code mapping for compact web stats
const GAME_CODE_MAP = {
  pr: 'platformer_race',
  oc: 'obstacle_course',
  br: 'battle_royale',
  fa: 'fighter_arena',
  se: 'snake_escape',
  tb: 'team_battle',
  gv: 'gorillas_vs_followers',
  sp: 'spleef',
  tr: 'platformer_race', // legacy code reuse
};
const GAME_CODE_MAP_REVERSE = Object.fromEntries(Object.entries(GAME_CODE_MAP).map(([k, v]) => [v, k]));

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
      const raw = await response.json();
      const data = normalizePlayerStats(raw);
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

// Normalize compact or full player stats into canonical shape
function normalizePlayerStats(raw) {
  // Canonical shape already
  if (raw && raw.players && raw.last_updated !== undefined) {
    return raw;
  }

  // Compact shape: {lu, tgr, p:{ username: {s:[...], gb:{code:count}, rg:[...] } } }
  if (raw && raw.p) {
    const out = {
      last_updated: raw.lu || null,
      total_games_recorded: raw.tgr || 0,
      players: {},
    };

    Object.entries(raw.p).forEach(([username, pdata]) => {
      const statsArr = pdata.s || [];
      const breakdown = {};
      const gb = pdata.gb || {};
      Object.entries(gb).forEach(([code, count]) => {
        const full = GAME_CODE_MAP[code] || code;
        breakdown[full] = count;
      });

      out.players[username] = {
        stats: statsArr,
        game_breakdown: breakdown,
        recent_games: pdata.rg || [],
      };
    });

    return out;
  }

  // Fallback
  return {
    last_updated: null,
    total_games_recorded: 0,
    players: {},
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
      const raw = await response.json();
      const data = normalizeGameHistory(raw);
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

// Normalize compact or full game history into canonical shape
function normalizeGameHistory(raw) {
  // Full shape already
  if (raw && raw.games) return raw;

  // Compact shape: {g:[{id,t,n,d,ts,r:[[u,pl,pts,k]]}]}
  if (raw && Array.isArray(raw.g)) {
    const games = raw.g.map((g) => {
      const gameType = GAME_CODE_MAP[g.t] || g.t || 'unknown';
      const results = (g.r || []).map((r) => ({
        username: r[0],
        placement: r[1],
        points: r[2],
        kills: r[3] || 0,
      }));
      return {
        game_id: g.id,
        game_type: gameType,
        game_display_name: g.n || gameType,
        day_number: g.d,
        timestamp: g.ts,
        results,
      };
    });
    return { games };
  }

  // Fallback
  return { games: [] };
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
  // Try partitioned data first
  const partitionedStats = await getPlayerStatsPartitioned(username);
  if (partitionedStats) {
    return partitionedStats;
  }

  // Fallback to monolithic file
  const stats = await loadPlayerStats();
  return stats.players?.[username] || null;
}

/**
 * Get all-time leaderboard sorted by total points
 * @param {number} limit - Number of top players to return
 * @returns {Promise<Array>} Array of {username, stats} objects
 */
export async function getAllTimeLeaderboard(limit = 10) {
  // Try partitioned player index first (much faster)
  const playerIndex = await loadPlayerIndex();
  if (playerIndex && playerIndex.players) {
    // Index already sorted by points
    const topPlayers = playerIndex.players.slice(0, limit);

    // Load full stats for top players
    const promises = topPlayers.map(async (p) => {
      const fullStats = await getPlayerStatsPartitioned(p.u);
      return {
        username: p.u,
        totalPoints: p.p,
        stats: fullStats?.stats || [],
        gameBreakdown: fullStats?.game_breakdown || {},
        recentGames: fullStats?.recent_games || []
      };
    });

    return Promise.all(promises);
  }

  // Fallback to old monolithic file
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
  cachedIndex = null;
  cachedDays.clear();
  cachedPlayerLetters.clear();
  cachedPlayerIndex = null;
}

/**
 * Load the partitioned index file
 * @returns {Promise<Object>} Index data with available days
 */
export async function loadIndex() {
  if (cachedIndex) {
    return cachedIndex;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/index.json`);
    if (!response.ok) return null;
    const data = await response.json();
    cachedIndex = data;
    return data;
  } catch (err) {
    console.error('Error loading index:', err);
    return null;
  }
}

/**
 * Load data for a specific day (partitioned)
 * @param {number} dayNumber - Day number to load
 * @returns {Promise<Object>} Day data with games
 */
export async function loadDay(dayNumber) {
  // Check cache first
  if (cachedDays.has(dayNumber)) {
    return cachedDays.get(dayNumber);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/days/${dayNumber}.json`);
    if (!response.ok) return null;
    const data = await response.json();
    cachedDays.set(dayNumber, data);
    return data;
  } catch (err) {
    console.error(`Error loading day ${dayNumber}:`, err);
    return null;
  }
}

/**
 * Load player index (list of all players with basic info)
 * @returns {Promise<Object>} Player index
 */
export async function loadPlayerIndex() {
  if (cachedPlayerIndex) {
    return cachedPlayerIndex;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/players/index.json`);
    if (!response.ok) return null;
    const data = await response.json();
    cachedPlayerIndex = data;
    return data;
  } catch (err) {
    console.error('Error loading player index:', err);
    return null;
  }
}

/**
 * Load players for a specific letter group (partitioned)
 * @param {string} letter - Letter to load (a-z, 0)
 * @returns {Promise<Object>} Players data for that letter
 */
export async function loadPlayerLetter(letter) {
  letter = letter.toLowerCase();

  // Check cache first
  if (cachedPlayerLetters.has(letter)) {
    return cachedPlayerLetters.get(letter);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/players/${letter}.json`);
    if (!response.ok) return null;
    const data = await response.json();
    cachedPlayerLetters.set(letter, data);
    return data;
  } catch (err) {
    console.error(`Error loading players for letter ${letter}:`, err);
    return null;
  }
}

/**
 * Get player stats using partitioned data
 * @param {string} username - Player username
 * @returns {Promise<Object|null>} Player stats or null if not found
 */
export async function getPlayerStatsPartitioned(username) {
  const firstLetter = username[0].toLowerCase();
  const letter = firstLetter.match(/[a-z]/) ? firstLetter : '0';

  const letterData = await loadPlayerLetter(letter);
  if (!letterData || !letterData.players) {
    return null;
  }

  const playerData = letterData.players[username];
  if (!playerData) {
    return null;
  }

  // Normalize compact format
  const statsArr = playerData.s || [];
  const breakdown = {};
  const gb = playerData.gb || {};
  Object.entries(gb).forEach(([code, count]) => {
    const full = GAME_CODE_MAP[code] || code;
    breakdown[full] = count;
  });

  return {
    stats: statsArr,
    game_breakdown: breakdown,
    recent_games: playerData.rg || [],
  };
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
