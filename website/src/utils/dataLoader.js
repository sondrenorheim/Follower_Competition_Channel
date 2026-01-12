/**
 * Data Loader Utilities - Updated for Partitioned API
 * Fetches and caches game statistics and history data from partitioned endpoints
 *
 * This version prioritizes the new partitioned API structure:
 * - api/index.json - Master index
 * - api/days/{day}.json - Day summaries
 * - api/games/{game_id}.json - Individual game files
 * - api/types/{game_type}.json - Game type indexes
 * - api/players/{letter}.json - Player stats by first letter
 * - api/player_history/{letter}.json - Player game history by first letter
 */

const runtimeApiBase =
  typeof window !== 'undefined' && window.__API_BASE_URL__
    ? window.__API_BASE_URL__
    : '';
const apiBase = (import.meta.env.VITE_API_BASE_URL || runtimeApiBase || '').replace(/\/$/, '');
const DATA_BASE_PATH = apiBase ? `${apiBase}/` : '/'; // Serve from root (works in dev/prod)

// Cache for partitioned data
let cachedIndex = null;
let cachedDays = new Map(); // Map of day_number -> day_data
let cachedGames = new Map(); // Map of game_id -> game_data
let cachedTypes = new Map(); // Map of game_type -> type_index
let cachedPlayerLetters = new Map(); // Map of letter -> player_data
let cachedPlayerIndex = null;
let cachedMonthlyLeaderboards = new Map(); // Map of YYYY-MM -> leaderboard_data
let cachedPlayerHistoryIndex = null;
let cachedPlayerHistoryLetters = new Map(); // Map of letter -> player history data
let cachedGamePreviews = new Map(); // Map of game_id -> preview game data
let cachedDayAggregatePreviews = new Map(); // Map of day_number -> aggregate preview
let cachedDayAggregates = new Map(); // Map of day_number -> aggregate full data

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
};
const GAME_CODE_MAP_REVERSE = Object.fromEntries(Object.entries(GAME_CODE_MAP).map(([k, v]) => [v, k]));

/**
 * Load the partitioned index file (master index)
 * @returns {Promise<Object>} Index data with available days and types
 */
export async function loadIndex() {
  if (cachedIndex) {
    return cachedIndex;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/index.json`);
    if (!response.ok) {
      console.error('Failed to load index.json');
      return null;
    }
    const data = await response.json();
    cachedIndex = data;
    console.log(`✅ Loaded index: ${data.total_games} games, ${data.total_days} days`);
    return data;
  } catch (err) {
    console.error('Error loading index:', err);
    return null;
  }
}

/**
 * Load data for a specific day (partitioned)
 * @param {number} dayNumber - Day number to load
 * @returns {Promise<Object>} Day data with game summaries
 */
export async function loadDay(dayNumber) {
  // Check cache first
  if (cachedDays.has(dayNumber)) {
    return cachedDays.get(dayNumber);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/days/${dayNumber}.json`);
    if (!response.ok) {
      console.warn(`Day ${dayNumber} not found`);
      return null;
    }
    const data = await response.json();
    cachedDays.set(dayNumber, data);
    return data;
  } catch (err) {
    console.error(`Error loading day ${dayNumber}:`, err);
    return null;
  }
}

/**
 * Load aggregated "All Games" results for a specific day.
 * @param {number} dayNumber - Day number to load
 * @param {Object} options
 * @param {boolean} options.preview - When true, loads the top-N preview file
 * @returns {Promise<Object>} Aggregated day results
 */
export async function loadDayAggregate(dayNumber, { preview = false } = {}) {
  const cache = preview ? cachedDayAggregatePreviews : cachedDayAggregates;
  if (cache.has(dayNumber)) {
    return cache.get(dayNumber);
  }

  const suffix = preview ? "_aggregate_top" : "_aggregate";
  try {
    const response = await fetch(`${DATA_BASE_PATH}api/days/${dayNumber}${suffix}.json`);
    if (!response.ok) {
      if (preview) {
        return await loadDayAggregate(dayNumber, { preview: false });
      }
      console.warn(`Aggregate for day ${dayNumber} not found`);
      return null;
    }
    const data = await response.json();
    if (preview) {
      data._isPreview = true;
    }
    cache.set(dayNumber, data);
    return data;
  } catch (err) {
    console.error(`Error loading aggregate for day ${dayNumber}:`, err);
    return null;
  }
}

/**
 * Load a specific game by ID
 * @param {string} gameId - Game ID to load
 * @returns {Promise<Object>} Full game data with results
 */
export async function loadGame(gameId) {
  // Check cache first
  if (cachedGames.has(gameId)) {
    return cachedGames.get(gameId);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/games/${gameId}.json`);
    if (!response.ok) {
      console.warn(`Game ${gameId} not found`);
      return null;
    }
    const data = await response.json();
    cachedGames.set(gameId, data);
    return data;
  } catch (err) {
    console.error(`Error loading game ${gameId}:`, err);
    return null;
  }
}

/**
 * Load a preview version of a game (top-N results)
 * @param {string} gameId - Game ID to load
 * @returns {Promise<Object>} Preview game data
 */
export async function loadGamePreview(gameId) {
  if (cachedGamePreviews.has(gameId)) {
    return cachedGamePreviews.get(gameId);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/games/${gameId}_top.json`);
    if (!response.ok) {
      return await loadGame(gameId);
    }
    const data = await response.json();
    data._isPreview = true;
    cachedGamePreviews.set(gameId, data);
    return data;
  } catch (err) {
    console.error(`Error loading preview for game ${gameId}:`, err);
    return await loadGame(gameId);
  }
}

/**
 * Load game type index
 * @param {string} gameType - Game type to load
 * @returns {Promise<Object>} Type index with game list
 */
export async function loadGameType(gameType) {
  // Check cache first
  if (cachedTypes.has(gameType)) {
    return cachedTypes.get(gameType);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/types/${gameType}.json`);
    if (!response.ok) {
      console.warn(`Game type ${gameType} not found`);
      return null;
    }
    const data = await response.json();
    cachedTypes.set(gameType, data);
    return data;
  } catch (err) {
    console.error(`Error loading game type ${gameType}:`, err);
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
    if (!response.ok) {
      console.error('Failed to load player index');
      return null;
    }
    const data = await response.json();
    cachedPlayerIndex = data;
    console.log(`✅ Loaded player index: ${data.total_players} players`);
    return data;
  } catch (err) {
    console.error('Error loading player index:', err);
    return null;
  }
}

/**
 * Load player history index (compact per-player game history).
 * @returns {Promise<Object>} Player history index data
 */
export async function loadPlayerHistoryIndex() {
  if (cachedPlayerHistoryIndex) {
    return cachedPlayerHistoryIndex;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/player_history/index.json`);
    if (!response.ok) {
      console.warn('Player history index not found');
      return null;
    }
    const data = await response.json();
    cachedPlayerHistoryIndex = data;
    return data;
  } catch (err) {
    console.error('Error loading player history index:', err);
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
    if (!response.ok) {
      console.warn(`Player letter ${letter} not found`);
      return null;
    }
    const data = await response.json();
    cachedPlayerLetters.set(letter, data);
    return data;
  } catch (err) {
    console.error(`Error loading players for letter ${letter}:`, err);
    return null;
  }
}

/**
 * Load player history for a specific letter group (partitioned)
 * @param {string} letter - Letter to load (a-z, 0)
 * @returns {Promise<Object>} Player history data for that letter
 */
export async function loadPlayerHistoryLetter(letter) {
  letter = letter.toLowerCase();

  if (cachedPlayerHistoryLetters.has(letter)) {
    return cachedPlayerHistoryLetters.get(letter);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/player_history/${letter}.json`);
    if (!response.ok) {
      console.warn(`Player history letter ${letter} not found`);
      return null;
    }
    const data = await response.json();
    cachedPlayerHistoryLetters.set(letter, data);
    return data;
  } catch (err) {
    console.error(`Error loading player history for letter ${letter}:`, err);
    return null;
  }
}

/**
 * Get all games of a specific type
 * @param {string} gameType - Game type identifier (e.g., "battle_royale") or "all"
 * @returns {Promise<Array>} Array of game records with full data
 */
export async function getGamesByType(gameType) {
  const index = await loadIndex();
  if (!index) {
    return [];
  }

  if (gameType === 'all') {
    // Return all games from all days (metadata only for efficiency)
    const allGames = [];

    for (const dayNum of index.available_days || []) {
      const dayData = await loadDay(dayNum);
      if (dayData && dayData.games) {
        // For "all", we'll return metadata and lazy-load full data when needed
        dayData.games.forEach(gameSummary => {
          allGames.push({
            game_id: gameSummary.game_id,
            game_type: gameSummary.game_type,
            game_display_name: gameSummary.game_display_name,
            day_number: dayData.day_number,
            timestamp: gameSummary.timestamp,
            total_participants: gameSummary.total_participants,
            // Mark as summary - full data loaded on demand
            _isSummary: true,
          });
        });
      }
    }

    return allGames;
  }

  // Load type index for specific game type
  const typeIndex = await loadGameType(gameType);
  if (!typeIndex || !typeIndex.games) {
    return [];
  }

  // Return game summaries (full data loaded on demand)
  return typeIndex.games.map(g => ({
    game_id: g.game_id,
    game_type: typeIndex.game_type,
    game_display_name: typeIndex.game_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    day_number: g.day_number,
    timestamp: g.timestamp,
    total_participants: g.total_participants,
    _isSummary: true,
  }));
}

/**
 * Get a specific game by ID with full results
 * @param {string} gameId - Unique game identifier
 * @returns {Promise<Object|null>} Game record or null if not found
 */
export async function getGameById(gameId) {
  return await loadGame(gameId);
}

/**
 * Get a game with full results (load if summary)
 * @param {Object} game - Game object (may be summary or full)
 * @returns {Promise<Object>} Full game data with results
 */
export async function getGameWithResults(game) {
  if (!game) return null;

  // If already has results, return as-is
  if (game.results && !game._isSummary) {
    return game;
  }

  // Load full game data
  const fullGame = await loadGame(game.game_id);
  return fullGame;
}

/**
 * Get player statistics for a specific username
 * @param {string} username - Player username
 * @returns {Promise<Object|null>} Player stats or null if not found
 */
export async function getPlayerStats(username) {
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
 * Get all-time leaderboard sorted by total points
 * @param {number} limit - Number of top players to return
 * @returns {Promise<Array>} Array of {username, stats} objects
 */
export async function getAllTimeLeaderboard(limit = 10) {
  const playerIndex = await loadPlayerIndex();
  if (!playerIndex || !playerIndex.players) {
    return [];
  }

  // Index is already sorted by points descending
  const topPlayers = playerIndex.players.slice(0, limit);

  // Load full stats for top players
  const promises = topPlayers.map(async (p) => {
    const fullStats = await getPlayerStats(p.u);
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

/**
 * Get all players with full stats (all-time)
 * @returns {Promise<Array>} Array of {username, stats} objects
 */
export async function getAllPlayerStats() {
  const playerIndex = await loadPlayerIndex();
  if (!playerIndex || !playerIndex.letters) {
    return [];
  }

  const letterData = await Promise.all(
    playerIndex.letters.map((letter) => loadPlayerLetter(letter))
  );

  const players = [];
  letterData.forEach((data) => {
    if (!data || !data.players) return;
    Object.entries(data.players).forEach(([username, entry]) => {
      players.push({
        username,
        stats: entry.s || []
      });
    });
  });

  return players;
}

/**
 * Load pre-computed monthly leaderboard
 * @param {string} monthKey - Month key in YYYY-MM format
 * @returns {Promise<Object>} Monthly leaderboard data
 */
async function loadMonthlyLeaderboard(monthKey) {
  // Check cache first
  if (cachedMonthlyLeaderboards.has(monthKey)) {
    return cachedMonthlyLeaderboards.get(monthKey);
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/leaderboards/${monthKey}.json`);
    if (!response.ok) {
      console.warn(`Monthly leaderboard ${monthKey} not found`);
      return null;
    }
    const data = await response.json();
    cachedMonthlyLeaderboards.set(monthKey, data);
    return data;
  } catch (err) {
    console.error(`Error loading monthly leaderboard ${monthKey}:`, err);
    return null;
  }
}

/**
 * Get monthly leaderboard for a specific month (uses pre-computed files)
 * @param {number} year - Year
 * @param {number} month - Month (1-12)
 * @param {number} limit - Number of top players to return
 * @param {string} gameType - Game type identifier or "all"
 * @returns {Promise<Array>} Array of player rankings for the month
 */
export async function getMonthlyLeaderboard(year, month, limit = null, gameType = 'all') {
  // Build month key (YYYY-MM format)
  const monthKey = `${year}-${String(month).padStart(2, '0')}`;
  const leaderboardKey = gameType === 'all' ? monthKey : `${monthKey}_${gameType}`;

  // Load pre-computed monthly leaderboard (single request!)
  const monthData = await loadMonthlyLeaderboard(leaderboardKey);

  if (!monthData || !monthData.leaderboard) {
    console.warn(`No pre-computed leaderboard for ${leaderboardKey}`);
    return [];
  }

  // Convert compact format to expected format
  const leaderboard = monthData.leaderboard.map(entry => {
    const totalPlacement = entry.t || 0;
    return {
      username: entry.u,
      points: entry.p,
      games: entry.g,
      wins: entry.w,
      bestPlacement: entry.b || Infinity,
      totalKills: entry.k || 0,
      totalPlacement,
      avgPlacement: entry.g ? (totalPlacement / entry.g).toFixed(1) : '0.0',
      rank: entry.r
    };
  });

  const trimmed = limit === null || limit === undefined ? leaderboard : leaderboard.slice(0, limit);

  console.log(`?. Loaded monthly leaderboard ${leaderboardKey}: ${trimmed.length} players (1 request)`);
  return trimmed;
}


/**
 * Get game history for a specific player
 * @param {string} username - Player username
 * @param {number} limit - Number of recent games to return
 * @returns {Promise<Array>} Array of game records where player participated
 */
export async function getPlayerGameHistory(username, limit = 10) {
  const resolvedLimit = limit === null || limit === undefined ? null : limit;

  // Try compact player history index first (fast path)
  const historyIndex = await loadPlayerHistoryIndex();
  if (historyIndex && Array.isArray(historyIndex.games)) {
    const firstLetter = username[0].toLowerCase();
    const letter = firstLetter.match(/[a-z]/) ? firstLetter : '0';
    const letterData = await loadPlayerHistoryLetter(letter);
    const entries = letterData?.players?.[username];

    if (Array.isArray(entries) && entries.length > 0) {
      const gamesMeta = historyIndex.games;
      const pointsScale = historyIndex.points_scale || 1;
      const count = resolvedLimit ? Math.min(resolvedLimit, entries.length) : entries.length;
      const playerGames = [];

      for (let i = 0; i < count; i += 1) {
        const entry = entries[i];
        const gameMeta = gamesMeta[entry[0]];
        if (!gameMeta) continue;

        const placement = entry[1] || 0;
        const points = (entry[2] || 0) / pointsScale;
        const kills = entry[3] || 0;

        playerGames.push({
          gameId: gameMeta[0],
          gameType: gameMeta[1],
          dayNumber: gameMeta[2],
          timestamp: gameMeta[3],
          placement,
          rank: placement,
          points,
          kills,
          damage: 0,
          survival_time: 0,
        });
      }

      return playerGames;
    }
  }

  // Fallback: use recent games list (fast) or scan all games (slow)
  const playerStats = await getPlayerStats(username);
  if (!playerStats || !playerStats.recent_games || playerStats.recent_games.length === 0) {
    const fallbackLimit = resolvedLimit === null ? 1000 : resolvedLimit;
    return await getPlayerGameHistoryFull(username, fallbackLimit);
  }

  const recentLimit = resolvedLimit === null ? playerStats.recent_games.length : resolvedLimit;
  const recentGameIds = playerStats.recent_games.slice(0, recentLimit);
  const playerGames = [];

  // Load each game and extract player's result
  for (const gameId of recentGameIds) {
    const game = await loadGame(gameId);
    if (!game || !game.results) continue;

    const playerResult = game.results.find(r => r.username === username);
    if (playerResult) {
      playerGames.push({
        gameId: game.game_id,
        gameType: game.game_type,
        gameDisplayName: game.game_display_name,
        dayNumber: game.day_number,
        timestamp: game.timestamp,
        placement: playerResult.placement,
        rank: playerResult.rank || playerResult.placement,
        points: playerResult.points,
        kills: playerResult.kills || 0,
        damage: playerResult.damage || 0,
        survival_time: playerResult.survival_time || 0,
      });
    }
  }

  return playerGames;
}


/**
 * Get full game history for a player (fallback method - searches all games)
 * @param {string} username - Player username
 * @param {number} limit - Number of recent games to return
 * @returns {Promise<Array>} Array of game records where player participated
 */
async function getPlayerGameHistoryFull(username, limit = 10) {
  const index = await loadIndex();
  if (!index) {
    return [];
  }

  const playerGames = [];

  // Search through all days (newest first)
  const sortedDays = [...(index.available_days || [])].sort((a, b) => b - a);

  for (const dayNum of sortedDays) {
    if (playerGames.length >= limit) break;

    const dayData = await loadDay(dayNum);
    if (!dayData || !dayData.games) continue;

    for (const gameSummary of dayData.games) {
      if (playerGames.length >= limit) break;

      const game = await loadGame(gameSummary.game_id);
      if (!game || !game.results) continue;

      const playerResult = game.results.find(r => r.username === username);
      if (playerResult) {
        playerGames.push({
          gameId: game.game_id,
          gameType: game.game_type,
          gameDisplayName: game.game_display_name,
          dayNumber: game.day_number,
          timestamp: game.timestamp,
          placement: playerResult.placement,
          rank: playerResult.rank || playerResult.placement,
          points: playerResult.points,
          kills: playerResult.kills || 0,
          damage: playerResult.damage || 0,
          survival_time: playerResult.survival_time || 0,
        });
      }
    }
  }

  return playerGames;
}

/**
 * Get list of available game types
 * @returns {Promise<Array>} Array of {type, displayName, count} objects
 */
export async function getGameTypes() {
  const index = await loadIndex();
  if (!index || !index.types_metadata) {
    return [];
  }

  return index.types_metadata.map(t => ({
    type: t.type,
    displayName: t.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    count: t.games
  }));
}

/**
 * Clear cached data (useful for forcing refresh)
 */
export function clearCache() {
  cachedIndex = null;
  cachedDays.clear();
  cachedGames.clear();
  cachedTypes.clear();
  cachedPlayerLetters.clear();
  cachedPlayerIndex = null;
  cachedMonthlyLeaderboards.clear();
  cachedPlayerHistoryIndex = null;
  cachedPlayerHistoryLetters.clear();
  cachedGamePreviews.clear();
  cachedDayAggregatePreviews.clear();
  cachedDayAggregates.clear();
  console.log('dY-`?,? Cache cleared');
}
