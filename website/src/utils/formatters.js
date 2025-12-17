/**
 * Formatting Utilities
 * Helper functions for displaying data
 */

/**
 * Format a number with commas
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export function formatNumber(num) {
  return num.toLocaleString('en-US');
}

/**
 * Format points with one decimal place
 * @param {number} points - Points value
 * @returns {string} Formatted points
 */
export function formatPoints(points) {
  return points.toFixed(1);
}

/**
 * Format timestamp as relative time (e.g., "2 days ago")
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Relative time string
 */
export function formatRelativeTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffDay > 30) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } else if (diffDay > 0) {
    return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  } else if (diffHour > 0) {
    return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  } else if (diffMin > 0) {
    return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  } else {
    return 'Just now';
  }
}

/**
 * Format timestamp as date string
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted date
 */
export function formatDate(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

/**
 * Format survival time in seconds to minutes:seconds
 * @param {number} seconds - Survival time in seconds
 * @returns {string} Formatted time (e.g., "3:45")
 */
export function formatSurvivalTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Get placement suffix (1st, 2nd, 3rd, 4th, etc.)
 * @param {number} placement - Placement number
 * @returns {string} Placement with suffix
 */
export function getPlacementSuffix(placement) {
  const j = placement % 10;
  const k = placement % 100;

  if (j === 1 && k !== 11) {
    return placement + 'st';
  }
  if (j === 2 && k !== 12) {
    return placement + 'nd';
  }
  if (j === 3 && k !== 13) {
    return placement + 'rd';
  }
  return placement + 'th';
}

/**
 * Get medal emoji for top 3 placements
 * @param {number} placement - Placement number
 * @returns {string} Medal emoji or empty string
 */
export function getMedalEmoji(placement) {
  switch (placement) {
    case 1:
      return '🥇';
    case 2:
      return '🥈';
    case 3:
      return '🥉';
    default:
      return '';
  }
}

/**
 * Get stats array values by index
 * Stats array format:
 * [0] total_points
 * [1] games_played
 * [2] best_placement
 * [3] total_placements
 * [4] wins
 * [5] top_3_finishes
 * [6] top_10_pct_finishes
 * [7] total_survival_time
 * [8] first_eliminations
 * [9] current_hot_streak
 * [10] best_hot_streak
 * [11] total_kills
 * [12] total_damage_dealt
 */
export function parseStats(stats) {
  if (!Array.isArray(stats) || stats.length < 13) {
    return {
      totalPoints: 0,
      gamesPlayed: 0,
      bestPlacement: 0,
      totalPlacements: 0,
      wins: 0,
      top3Finishes: 0,
      top10PctFinishes: 0,
      totalSurvivalTime: 0,
      firstEliminations: 0,
      currentHotStreak: 0,
      bestHotStreak: 0,
      totalKills: 0,
      totalDamage: 0,
      avgPlacement: 0
    };
  }

  return {
    totalPoints: stats[0],
    gamesPlayed: stats[1],
    bestPlacement: stats[2],
    totalPlacements: stats[3],
    wins: stats[4],
    top3Finishes: stats[5],
    top10PctFinishes: stats[6],
    totalSurvivalTime: stats[7],
    firstEliminations: stats[8],
    currentHotStreak: stats[9],
    bestHotStreak: stats[10],
    totalKills: stats[11],
    totalDamage: stats[12],
    avgPlacement: stats[1] > 0 ? (stats[3] / stats[1]).toFixed(1) : 0
  };
}

/**
 * Get game type display info
 * @param {string} gameType - Game type identifier
 * @returns {Object} Display info with name and color
 */
export function getGameTypeInfo(gameType) {
  const gameTypes = {
    battle_royale: {
      name: 'Battle Royale',
      color: 'bg-red-600',
      textColor: 'text-red-600'
    },
    fighter_arena: {
      name: 'Fighter Arena',
      color: 'bg-orange-600',
      textColor: 'text-orange-600'
    },
    obstacle_course: {
      name: 'Obstacle Course',
      color: 'bg-blue-600',
      textColor: 'text-blue-600'
    },
    snake_escape: {
      name: 'Snake Escape',
      color: 'bg-green-600',
      textColor: 'text-green-600'
    },
    team_battle: {
      name: 'Team Battle',
      color: 'bg-purple-600',
      textColor: 'text-purple-600'
    },
    platformer_race: {
      name: 'Platformer Race',
      color: 'bg-yellow-600',
      textColor: 'text-yellow-600'
    },
    gorillas_vs_followers: {
      name: 'Gorillas vs Followers',
      color: 'bg-gray-800',
      textColor: 'text-gray-800'
    }
  };

  return gameTypes[gameType] || {
    name: gameType,
    color: 'bg-gray-600',
    textColor: 'text-gray-600'
  };
}
