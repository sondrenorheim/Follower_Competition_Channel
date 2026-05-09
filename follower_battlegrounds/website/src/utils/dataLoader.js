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

export const RESULT_PLATFORMS = [
  { id: 'instagram', label: 'Instagram' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'facebook', label: 'Facebook' }
];

export function normalizeResultPlatform(platform = 'instagram') {
  const normalized = String(platform || 'instagram').toLowerCase();
  return RESULT_PLATFORMS.some((item) => item.id === normalized) ? normalized : 'instagram';
}

export function platformApiPath(path, platform = null) {
  const cleanPath = String(path || '').replace(/^\/+/, '');
  if (!platform) {
    return `${DATA_BASE_PATH}${cleanPath}`;
  }
  const normalized = normalizeResultPlatform(platform);
  return `${DATA_BASE_PATH}api/platforms/${normalized}/${cleanPath.replace(/^api\//, '')}`;
}

function cacheKey(key, platform = null) {
  return `${platform ? normalizeResultPlatform(platform) : 'global'}:${key}`;
}

function shouldFallbackToLegacy(platform) {
  return normalizeResultPlatform(platform) === 'instagram';
}

function legacyTypeForPlatform(gameType, platform) {
  const normalized = String(gameType || '').toLowerCase();
  const active = normalizeResultPlatform(platform);
  if (active === 'youtube' && normalized !== 'all') {
    return `youtube_${normalized}`;
  }
  if (active === 'facebook' && normalized !== 'all') {
    return `facebook_${normalized}`;
  }
  return normalized;
}

function normalizeLegacyType(gameType) {
  const normalized = String(gameType || '').toLowerCase();
  for (const prefix of ['youtube_followers_', 'facebook_', 'youtube_']) {
    if (normalized.startsWith(prefix)) {
      return normalized.slice(prefix.length);
    }
  }
  return normalized;
}

function includeLegacyTypeForPlatform(gameType, platform) {
  const raw = String(gameType || '').toLowerCase();
  const active = normalizeResultPlatform(platform);
  if (active === 'youtube') {
    return raw.startsWith('youtube_') && !raw.startsWith('youtube_followers_');
  }
  if (active === 'facebook') {
    return raw.startsWith('facebook_');
  }
  return !raw.startsWith('youtube_') && !raw.startsWith('facebook_') && !raw.startsWith('youtube_followers_');
}

function normalizeLegacyGameSummary(game, platform) {
  const rawType = String(game?.game_type || '').toLowerCase();
  return {
    ...game,
    raw_game_type: game?.raw_game_type || rawType,
    base_game_type: game?.base_game_type || normalizeLegacyType(rawType),
    game_type: normalizeLegacyType(rawType),
    result_platform: normalizeResultPlatform(platform)
  };
}

function derivePlatformIndexFromLegacy(globalIndex, platform) {
  if (!globalIndex) return null;
  const active = normalizeResultPlatform(platform);
  const typesMap = new Map();
  for (const item of globalIndex.types_metadata || []) {
    const rawType = String(item.type || '').toLowerCase();
    if (!includeLegacyTypeForPlatform(rawType, active)) continue;
    const baseType = normalizeLegacyType(rawType);
    const existing = typesMap.get(baseType) || { type: baseType, games: 0 };
    existing.games += Number(item.games || 0);
    typesMap.set(baseType, existing);
  }

  const daysMetadata = [];
  for (const day of globalIndex.days_metadata || []) {
    const types = (day.types || [])
      .filter((type) => includeLegacyTypeForPlatform(type, active))
      .map(normalizeLegacyType);
    const uniqueTypes = [...new Set(types)];
    if (uniqueTypes.length === 0) continue;
    daysMetadata.push({ ...day, types: uniqueTypes, games: uniqueTypes.length });
  }

  return {
    ...globalIndex,
    platform: active,
    platform_label: RESULT_PLATFORMS.find((item) => item.id === active)?.label || active,
    total_games: [...typesMap.values()].reduce((sum, item) => sum + item.games, 0),
    total_days: daysMetadata.length,
    available_days: daysMetadata.map((day) => day.day),
    days_metadata: daysMetadata,
    game_types: [...typesMap.keys()].sort(),
    types_metadata: [...typesMap.values()].sort((a, b) => a.type.localeCompare(b.type)),
    _legacyFallback: true
  };
}

// Cache for partitioned data
let cachedIndex = null;
let cachedPlatformIndexes = new Map();
let cachedDays = new Map(); // Map of day_number -> day_data
let cachedGames = new Map(); // Map of game_id -> game_data
let cachedTypes = new Map(); // Map of game_type -> type_index
let cachedPlayerLetters = new Map(); // Map of letter -> player_data
let cachedPlayerIndex = null;
let cachedMonthlyLeaderboards = new Map(); // Map of YYYY-MM -> leaderboard_data
let cachedAllTimeLeaderboard = null;
let cachedAllTimeLeaderboardPreview = null;
let cachedPlayerHistoryIndex = null;
let cachedPlayerHistoryLetters = new Map(); // Map of letter -> player history data
let cachedGamePreviews = new Map(); // Map of game_id -> preview game data
let cachedDayAggregatePreviews = new Map(); // Map of day_number -> aggregate preview
let cachedDayAggregates = new Map(); // Map of day_number -> aggregate full data
let cachedMediaKit = null;
let cachedHallOfFame = null;
let cachedClubMembers = null;
let cachedClubMemberStats = null;

export function getDataBasePath() {
  return DATA_BASE_PATH;
}

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
export async function loadIndex(platform = null) {
  if (platform) {
    const normalized = normalizeResultPlatform(platform);
    if (cachedPlatformIndexes.has(normalized)) {
      return cachedPlatformIndexes.get(normalized);
    }
    try {
      const response = await fetch(platformApiPath('index.json', normalized));
      if (!response.ok) {
        const fallback = await loadIndex();
        const data = derivePlatformIndexFromLegacy(fallback, normalized);
        if (data) {
          cachedPlatformIndexes.set(normalized, data);
          return data;
        }
        console.warn(`Platform index ${normalized} not found`);
        return null;
      }
      const data = await response.json();
      cachedPlatformIndexes.set(normalized, data);
      return data;
    } catch (err) {
      console.error(`Error loading ${normalized} index:`, err);
      return null;
    }
  }

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
export async function loadDay(dayNumber, { platform = null } = {}) {
  // Check cache first
  const key = cacheKey(dayNumber, platform);
  if (cachedDays.has(key)) {
    return cachedDays.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/days/${dayNumber}.json`, platform));
    if (!response.ok) {
      if (platform) {
        const fallback = await loadDay(dayNumber);
        if (fallback) {
          const games = (fallback.games || [])
            .filter((game) => includeLegacyTypeForPlatform(game.game_type, platform))
            .map((game) => normalizeLegacyGameSummary(game, platform));
          const data = {
            ...fallback,
            platform: normalizeResultPlatform(platform),
            total_games: games.length,
            games
          };
          cachedDays.set(key, data);
          return data;
        }
      }
      console.warn(`Day ${dayNumber} not found`);
      return null;
    }
    const data = await response.json();
    cachedDays.set(key, data);
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
export async function loadDayAggregate(dayNumber, { preview = false, platform = null } = {}) {
  const cache = preview ? cachedDayAggregatePreviews : cachedDayAggregates;
  const key = cacheKey(dayNumber, platform);
  if (cache.has(key)) {
    return cache.get(key);
  }

  const suffix = preview ? "_aggregate_top" : "_aggregate";
  try {
    const response = await fetch(platformApiPath(`api/days/${dayNumber}${suffix}.json`, platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadDayAggregate(dayNumber, { preview });
      }
      if (platform) {
        const fallbackDay = await loadDay(dayNumber, { platform });
        const summaries = fallbackDay?.games || [];
        const aggregated = new Map();
        let latestTimestamp = '';
        for (const summary of summaries) {
          const game = await loadGame(summary.game_id);
          if (!game || !Array.isArray(game.results)) continue;
          if ((game.timestamp || '') > latestTimestamp) {
            latestTimestamp = game.timestamp || '';
          }
          for (const result of game.results) {
            const username = String(result.username || '').trim();
            if (!username) continue;
            const entry = aggregated.get(username) || {
              username,
              points: 0,
              kills: 0,
              survival_time: 0,
              appearances: 0
            };
            entry.points += Number(result.points || 0);
            entry.kills += Number(result.kills || 0);
            entry.survival_time += Number(result.survival_time || 0);
            entry.appearances += 1;
            aggregated.set(username, entry);
          }
        }
        const results = [...aggregated.values()]
          .map((entry) => ({
            ...entry,
            points: Math.round(entry.points * 10) / 10,
            survival_time: Math.round(entry.survival_time * 10) / 10
          }))
          .sort((a, b) => (b.points || 0) - (a.points || 0) || a.username.localeCompare(b.username));
        const previewLimit = (await loadIndex(platform))?.results_preview_limit || 200;
        const data = {
          platform: normalizeResultPlatform(platform),
          game_id: `${normalizeResultPlatform(platform)}_all_day_${dayNumber}`,
          game_type: 'all',
          game_display_name: 'All Games',
          day_number: dayNumber,
          timestamp: latestTimestamp,
          total_participants: results.length,
          results: preview ? results.slice(0, previewLimit) : results,
          _isPreview: preview,
          is_preview: preview,
          preview_limit: previewLimit,
          total_results: results.length
        };
        cache.set(key, data);
        return data;
      }
      if (preview) {
        return await loadDayAggregate(dayNumber, { preview: false, platform });
      }
      console.warn(`Aggregate for day ${dayNumber} not found`);
      return null;
    }
    const data = await response.json();
    if (preview) {
      data._isPreview = true;
    }
    cache.set(key, data);
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
export async function loadGame(gameId, { platform = null } = {}) {
  // Check cache first
  const key = cacheKey(gameId, platform);
  if (cachedGames.has(key)) {
    return cachedGames.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/games/${gameId}.json`, platform));
    if (!response.ok) {
      if (platform) {
        const fallback = await loadGame(gameId);
        if (fallback) {
          const rawType = fallback.game_type;
          return includeLegacyTypeForPlatform(rawType, platform)
            ? normalizeLegacyGameSummary(fallback, platform)
            : null;
        }
      }
      console.warn(`Game ${gameId} not found`);
      return null;
    }
    const data = await response.json();
    cachedGames.set(key, data);
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
export async function loadGamePreview(gameId, { platform = null } = {}) {
  const key = cacheKey(gameId, platform);
  if (cachedGamePreviews.has(key)) {
    return cachedGamePreviews.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/games/${gameId}_top.json`, platform));
    if (!response.ok) {
      if (platform) {
        const fallback = await loadGamePreview(gameId);
        if (fallback) {
          const rawType = fallback.game_type;
          return includeLegacyTypeForPlatform(rawType, platform)
            ? { ...normalizeLegacyGameSummary(fallback, platform), _isPreview: !!fallback._isPreview }
            : null;
        }
      }
      return await loadGame(gameId, { platform });
    }
    const data = await response.json();
    data._isPreview = true;
    cachedGamePreviews.set(key, data);
    return data;
  } catch (err) {
    console.error(`Error loading preview for game ${gameId}:`, err);
    return await loadGame(gameId, { platform });
  }
}

/**
 * Load game type index
 * @param {string} gameType - Game type to load
 * @returns {Promise<Object>} Type index with game list
 */
export async function loadGameType(gameType, { platform = null } = {}) {
  // Check cache first
  const key = cacheKey(gameType, platform);
  if (cachedTypes.has(key)) {
    return cachedTypes.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/types/${gameType}.json`, platform));
    if (!response.ok) {
      if (platform) {
        const fallback = await loadGameType(legacyTypeForPlatform(gameType, platform));
        if (fallback) {
          const data = {
            ...fallback,
            platform: normalizeResultPlatform(platform),
            raw_game_type: fallback.game_type,
            game_type: normalizeLegacyType(fallback.game_type)
          };
          cachedTypes.set(key, data);
          return data;
        }
      }
      console.warn(`Game type ${gameType} not found`);
      return null;
    }
    const data = await response.json();
    cachedTypes.set(key, data);
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
export async function loadPlayerIndex(platform = null) {
  const key = platform ? normalizeResultPlatform(platform) : 'global';
  if (platform && cachedPlayerLetters.has(`player-index:${key}`)) {
    return cachedPlayerLetters.get(`player-index:${key}`);
  }
  if (!platform && cachedPlayerIndex) {
    return cachedPlayerIndex;
  }

  try {
    const response = await fetch(platformApiPath('api/players/index.json', platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadPlayerIndex();
      }
      console.error('Failed to load player index');
      return null;
    }
    const data = await response.json();
    if (platform) {
      cachedPlayerLetters.set(`player-index:${key}`, data);
    } else {
      cachedPlayerIndex = data;
    }
    console.log(`✅ Loaded player index: ${data.total_players} players`);
    return data;
  } catch (err) {
    console.error('Error loading player index:', err);
    return null;
  }
}

/**
 * Load media kit data
 * @returns {Promise<Object>} Media kit data
 */
export async function loadMediaKit() {
  if (cachedMediaKit) {
    return cachedMediaKit;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/media_kit.json`);
    if (!response.ok) {
      console.warn('Media kit data not found');
      return null;
    }
    const data = await response.json();
    cachedMediaKit = data;
    return data;
  } catch (err) {
    console.error('Error loading media kit:', err);
    return null;
  }
}

/**
 * Load Hall of Fame data (daily + monthly champions)
 * @returns {Promise<Object>} Hall of Fame data
 */
export async function loadHallOfFame(platform = null) {
  const key = platform ? `hall:${normalizeResultPlatform(platform)}` : 'hall:global';
  if (platform && cachedPlayerLetters.has(key)) {
    return cachedPlayerLetters.get(key);
  }
  if (!platform && cachedHallOfFame) {
    return cachedHallOfFame;
  }

  try {
    const response = await fetch(platformApiPath('api/hall_of_fame.json', platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadHallOfFame();
      }
      console.warn('Hall of fame data not found');
      return null;
    }
    const data = await response.json();
    if (platform) {
      cachedPlayerLetters.set(key, data);
    } else {
      cachedHallOfFame = data;
    }
    return data;
  } catch (err) {
    console.error('Error loading hall of fame:', err);
    return null;
  }
}

/**
 * Load club members list
 * @returns {Promise<Array>} Club members array
 */
export async function loadClubMembers() {
  if (cachedClubMembers) {
    return cachedClubMembers;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/club_members.json`);
    if (!response.ok) {
      console.warn('Club members data not found');
      return null;
    }
    const data = await response.json();
    cachedClubMembers = data;
    return data;
  } catch (err) {
    console.error('Error loading club members:', err);
    return null;
  }
}

/**
 * Load club members with precomputed stats
 * @returns {Promise<Array>} Club members stats array
 */
export async function loadClubMemberStats() {
  if (cachedClubMemberStats) {
    return cachedClubMemberStats;
  }

  try {
    const response = await fetch(`${DATA_BASE_PATH}api/club_members_stats.json`);
    if (!response.ok) {
      console.warn('Club members stats data not found');
      return null;
    }
    const data = await response.json();
    cachedClubMemberStats = data;
    return data;
  } catch (err) {
    console.error('Error loading club members stats:', err);
    return null;
  }
}
/**
 * Load player history index (compact per-player game history).
 * @returns {Promise<Object>} Player history index data
 */
export async function loadPlayerHistoryIndex(platform = null) {
  const key = platform ? `history-index:${normalizeResultPlatform(platform)}` : 'history-index:global';
  if (platform && cachedPlayerHistoryLetters.has(key)) {
    return cachedPlayerHistoryLetters.get(key);
  }
  if (!platform && cachedPlayerHistoryIndex) {
    return cachedPlayerHistoryIndex;
  }

  try {
    const response = await fetch(platformApiPath('api/player_history/index.json', platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadPlayerHistoryIndex();
      }
      console.warn('Player history index not found');
      return null;
    }
    const data = await response.json();
    if (platform) {
      cachedPlayerHistoryLetters.set(key, data);
    } else {
      cachedPlayerHistoryIndex = data;
    }
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
export async function loadPlayerLetter(letter, platform = null) {
  letter = letter.toLowerCase();

  // Check cache first
  const key = cacheKey(letter, platform);
  if (cachedPlayerLetters.has(key)) {
    return cachedPlayerLetters.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/players/${letter}.json`, platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadPlayerLetter(letter);
      }
      console.warn(`Player letter ${letter} not found`);
      return null;
    }
    const data = await response.json();
    cachedPlayerLetters.set(key, data);
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
export async function loadPlayerHistoryLetter(letter, platform = null) {
  letter = letter.toLowerCase();

  const key = cacheKey(letter, platform);
  if (cachedPlayerHistoryLetters.has(key)) {
    return cachedPlayerHistoryLetters.get(key);
  }

  try {
    const response = await fetch(platformApiPath(`api/player_history/${letter}.json`, platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadPlayerHistoryLetter(letter);
      }
      console.warn(`Player history letter ${letter} not found`);
      return null;
    }
    const data = await response.json();
    cachedPlayerHistoryLetters.set(key, data);
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
export async function getGamesByType(gameType, { platform = null } = {}) {
  const index = await loadIndex(platform);
  if (!index) {
    return [];
  }

  if (gameType === 'all') {
    // Return all games from all days (metadata only for efficiency)
    const allGames = [];

    for (const dayNum of index.available_days || []) {
      const dayData = await loadDay(dayNum, { platform });
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
  const typeIndex = await loadGameType(gameType, { platform });
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
export async function getGameById(gameId, { platform = null } = {}) {
  return await loadGame(gameId, { platform });
}

/**
 * Get a game with full results (load if summary)
 * @param {Object} game - Game object (may be summary or full)
 * @returns {Promise<Object>} Full game data with results
 */
export async function getGameWithResults(game, { platform = null } = {}) {
  if (!game) return null;

  // If already has results, return as-is
  if (game.results && !game._isSummary) {
    return game;
  }

  // Load full game data
  const fullGame = await loadGame(game.game_id, { platform });
  return fullGame;
}

/**
 * Get player statistics for a specific username
 * @param {string} username - Player username
 * @returns {Promise<Object|null>} Player stats or null if not found
 */
export async function getPlayerStats(username, platform = null) {
  const firstLetter = username[0].toLowerCase();
  const letter = firstLetter.match(/[a-z]/) ? firstLetter : '0';

  const letterData = await loadPlayerLetter(letter, platform);
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
export async function getAllTimeLeaderboard(limit = 10, platform = null) {
  const playerIndex = await loadPlayerIndex(platform);
  if (!playerIndex || !playerIndex.players) {
    return [];
  }

  // Index is already sorted by points descending
  const topPlayers = playerIndex.players.slice(0, limit);

  // Load full stats for top players
  const promises = topPlayers.map(async (p) => {
    const fullStats = await getPlayerStats(p.u, platform);
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
export async function getAllPlayerStats(platform = null) {
  const playerIndex = await loadPlayerIndex(platform);
  if (!playerIndex || !playerIndex.letters) {
    return [];
  }

  const letterData = await Promise.all(
    playerIndex.letters.map((letter) => loadPlayerLetter(letter, platform))
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
async function loadMonthlyLeaderboard(monthKey, { preview = false, platform = null } = {}) {
  const cacheKey = cacheKeySuffix(monthKey, preview, platform);
  if (cachedMonthlyLeaderboards.has(cacheKey)) {
    return cachedMonthlyLeaderboards.get(cacheKey);
  }

  const suffix = preview ? "_top" : "";

  try {
    const response = await fetch(platformApiPath(`api/leaderboards/${monthKey}${suffix}.json`, platform));
    if (!response.ok) {
      if (platform && shouldFallbackToLegacy(platform)) {
        return await loadMonthlyLeaderboard(monthKey, { preview });
      }
      if (platform && monthKey.includes('_')) {
        const [monthPart, ...typeParts] = monthKey.split('_');
        const fallbackKey = `${monthPart}_${legacyTypeForPlatform(typeParts.join('_'), platform)}`;
        const fallback = await loadMonthlyLeaderboard(fallbackKey, { preview });
        if (fallback) {
          return { ...fallback, platform: normalizeResultPlatform(platform), game_type: normalizeLegacyType(fallback.game_type) };
        }
      }
      if (preview) {
        return await loadMonthlyLeaderboard(monthKey, { preview: false, platform });
      }
      console.warn(`Monthly leaderboard ${monthKey} not found`);
      return null;
    }
    const data = await response.json();
    cachedMonthlyLeaderboards.set(cacheKey, data);
    return data;
  } catch (err) {
    console.error(`Error loading monthly leaderboard ${monthKey}:`, err);
    return null;
  }
}

function cacheKeySuffix(key, preview = false, platform = null) {
  return cacheKey(`${key}${preview ? ':preview' : ''}`, platform);
}

async function loadAllTimeLeaderboard({ preview = false, platform = null } = {}) {
  if (platform) {
    const key = cacheKeySuffix('all_time', preview, platform);
    if (cachedMonthlyLeaderboards.has(key)) {
      return cachedMonthlyLeaderboards.get(key);
    }
    const suffix = preview ? "_top" : "";
    try {
      const response = await fetch(platformApiPath(`api/leaderboards/all_time${suffix}.json`, platform));
      if (!response.ok) {
        if (shouldFallbackToLegacy(platform)) {
          return await loadAllTimeLeaderboard({ preview });
        }
        if (preview) {
          return await loadAllTimeLeaderboard({ preview: false, platform });
        }
        console.warn(`All-time leaderboard not found for ${platform}`);
        return null;
      }
      const data = await response.json();
      cachedMonthlyLeaderboards.set(key, data);
      return data;
    } catch (err) {
      console.error(`Error loading ${platform} all-time leaderboard:`, err);
      return null;
    }
  }

  const cache = preview ? cachedAllTimeLeaderboardPreview : cachedAllTimeLeaderboard;
  if (cache) {
    return cache;
  }

  const suffix = preview ? "_top" : "";
  try {
    const response = await fetch(`${DATA_BASE_PATH}api/leaderboards/all_time${suffix}.json`);
    if (!response.ok) {
      if (preview) {
        console.warn('All-time leaderboard not found');
        return null;
      }
      return await loadAllTimeLeaderboard({ preview: true });
    }
    const data = await response.json();
    if (preview) {
      cachedAllTimeLeaderboardPreview = data;
    } else {
      cachedAllTimeLeaderboard = data;
    }
    return data;
  } catch (err) {
    console.error('Error loading all-time leaderboard:', err);
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
export async function getMonthlyLeaderboard(year, month, limit = null, gameType = 'all', options = {}) {
  const { preview = false, platform = null } = options || {};
  // Build month key (YYYY-MM format)
  const monthKey = `${year}-${String(month).padStart(2, '0')}`;
  const leaderboardKey = gameType === 'all' ? monthKey : `${monthKey}_${gameType}`;

  // Load pre-computed monthly leaderboard (single request!)
  const monthData = await loadMonthlyLeaderboard(leaderboardKey, { preview, platform });

  if (!monthData || !monthData.leaderboard) {
    console.warn(`No pre-computed leaderboard for ${leaderboardKey}`);
    return {
      entries: [],
      meta: {
        month: monthKey,
        gameType: gameType,
        totalPlayers: 0,
        isPreview: false
      }
    };
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
  return {
    entries: trimmed,
    meta: {
      month: monthData.month || monthKey,
      gameType: monthData.game_type || gameType,
      totalPlayers: monthData.total_players ?? leaderboard.length,
      isPreview: !!monthData.is_preview,
      previewLimit: monthData.preview_limit ?? null,
      totalResults: monthData.total_results ?? monthData.total_players ?? leaderboard.length
    }
  };
}

/**
 * Get all-time leaderboard (compact file, preview or full).
 * @param {Object} options
 * @param {number|null} options.limit - Limit results after mapping
 * @param {boolean} options.preview - Load preview file when available
 * @returns {Promise<{entries: Array, meta: Object}>}
 */
export async function getAllTimeLeaderboardData({ limit = null, preview = false, platform = null } = {}) {
  const [playerIndex, index] = await Promise.all([loadPlayerIndex(platform), loadIndex(platform)]);
  const playerEntries = playerIndex?.players || [];
  const hasRichPlayerIndex = playerEntries.length > 0 &&
    ['w', 'b', 't', 'k', 't3', 't10'].every((key) => Object.prototype.hasOwnProperty.call(playerEntries[0], key));

  if (hasRichPlayerIndex) {
    const previewLimit = index?.results_preview_limit || null;
    const effectivePreview = preview && previewLimit && previewLimit > 0;
    const sliceLimit = effectivePreview ? previewLimit : null;

    const leaderboard = playerEntries.map((entry, indexPosition) => {
      const totalPlacement = entry.t || 0;
      return {
        username: entry.u,
        points: entry.p,
        games: entry.g,
        wins: entry.w || 0,
        bestPlacement: entry.b || Infinity,
        totalKills: entry.k || 0,
        totalPlacement,
        top3Finishes: entry.t3 || 0,
        top10PctFinishes: entry.t10 || 0,
        avgPlacement: entry.g ? (totalPlacement / entry.g).toFixed(1) : '0.0',
        rank: indexPosition + 1
      };
    });

    const previewTrimmed = sliceLimit ? leaderboard.slice(0, sliceLimit) : leaderboard;
    const trimmed = limit === null || limit === undefined ? previewTrimmed : previewTrimmed.slice(0, limit);
    return {
      entries: trimmed,
      meta: {
        totalPlayers: playerIndex?.total_players ?? leaderboard.length,
        isPreview: !!effectivePreview,
        previewLimit: previewLimit,
        totalResults: playerIndex?.total_players ?? leaderboard.length
      }
    };
  }

  const data = await loadAllTimeLeaderboard({ preview, platform });
  if (!data || !data.leaderboard) {
    return {
      entries: [],
      meta: {
        totalPlayers: 0,
        isPreview: false
      }
    };
  }

  const leaderboard = data.leaderboard.map((entry) => {
    const totalPlacement = entry.t || 0;
    return {
      username: entry.u,
      points: entry.p,
      games: entry.g,
      wins: entry.w,
      bestPlacement: entry.b || Infinity,
      totalKills: entry.k || 0,
      totalPlacement,
      top3Finishes: entry.t3 || 0,
      top10PctFinishes: entry.t10 || 0,
      avgPlacement: entry.g ? (totalPlacement / entry.g).toFixed(1) : '0.0',
      rank: entry.r
    };
  });

  const trimmed = limit === null || limit === undefined ? leaderboard : leaderboard.slice(0, limit);
  return {
    entries: trimmed,
    meta: {
      totalPlayers: data.total_players ?? leaderboard.length,
      isPreview: !!data.is_preview,
      previewLimit: data.preview_limit ?? null,
      totalResults: data.total_results ?? data.total_players ?? leaderboard.length
    }
  };
}


/**
 * Get game history for a specific player
 * @param {string} username - Player username
 * @param {number} limit - Number of recent games to return
 * @returns {Promise<Array>} Array of game records where player participated
 */
export async function getPlayerGameHistory(username, limit = 10, platform = null) {
  const resolvedLimit = limit === null || limit === undefined ? null : limit;

  // Try compact player history index first (fast path)
  const historyIndex = await loadPlayerHistoryIndex(platform);
  if (historyIndex && Array.isArray(historyIndex.games)) {
    const firstLetter = username[0].toLowerCase();
    const letter = firstLetter.match(/[a-z]/) ? firstLetter : '0';
    const letterData = await loadPlayerHistoryLetter(letter, platform);
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
  const playerStats = await getPlayerStats(username, platform);
  if (!playerStats || !playerStats.recent_games || playerStats.recent_games.length === 0) {
    const fallbackLimit = resolvedLimit === null ? 1000 : resolvedLimit;
    return await getPlayerGameHistoryFull(username, fallbackLimit, platform);
  }

  const recentLimit = resolvedLimit === null ? playerStats.recent_games.length : resolvedLimit;
  const recentGameIds = playerStats.recent_games.slice(0, recentLimit);
  const playerGames = [];

  // Load each game and extract player's result
  for (const gameId of recentGameIds) {
    const game = await loadGame(gameId, { platform });
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
async function getPlayerGameHistoryFull(username, limit = 10, platform = null) {
  const index = await loadIndex(platform);
  if (!index) {
    return [];
  }

  const playerGames = [];

  // Search through all days (newest first)
  const sortedDays = [...(index.available_days || [])].sort((a, b) => b - a);

  for (const dayNum of sortedDays) {
    if (playerGames.length >= limit) break;

    const dayData = await loadDay(dayNum, { platform });
    if (!dayData || !dayData.games) continue;

    for (const gameSummary of dayData.games) {
      if (playerGames.length >= limit) break;

      const game = await loadGame(gameSummary.game_id, { platform });
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
export async function getGameTypes(platform = null) {
  const index = await loadIndex(platform);
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
  cachedPlatformIndexes.clear();
  cachedDays.clear();
  cachedGames.clear();
  cachedTypes.clear();
  cachedPlayerLetters.clear();
  cachedPlayerIndex = null;
  cachedMonthlyLeaderboards.clear();
  cachedAllTimeLeaderboard = null;
  cachedAllTimeLeaderboardPreview = null;
  cachedPlayerHistoryIndex = null;
  cachedPlayerHistoryLetters.clear();
  cachedGamePreviews.clear();
  cachedDayAggregatePreviews.clear();
  cachedDayAggregates.clear();
  cachedMediaKit = null;
  cachedHallOfFame = null;
  cachedClubMembers = null;
  cachedClubMemberStats = null;
  console.log('dY-`?,? Cache cleared');
}
