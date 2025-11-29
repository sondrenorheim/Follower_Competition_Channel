import React from 'react';
import { Link } from 'react-router-dom';
import { formatPoints, getPlacementSuffix, getMedalEmoji } from '../utils/formatters';

/**
 * LeaderboardTable Component
 * Displays a sortable, paginated table of player rankings
 */
export default function LeaderboardTable({
  data,
  columns = ['rank', 'username', 'points'],
  showPagination = true,
  itemsPerPage = 50,
  currentPage = 1,
  onPageChange = () => {}
}) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12 text-text-muted">
        No data available
      </div>
    );
  }

  // Pagination
  const totalPages = Math.ceil(data.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedData = data.slice(startIndex, endIndex);

  return (
    <div className="w-full">
      {/* Table */}
      <div className="overflow-x-auto rounded-card shadow-card-dark border-2 border-slate-700 bg-dark-bg-secondary">
        <table className="min-w-full divide-y-2 divide-slate-700/50">
          <thead className="bg-gradient-to-r from-primary/30 via-secondary/30 to-primary/30 backdrop-blur-sm sticky top-0 border-b-2 border-accent/50">
            <tr>
              {columns.includes('rank') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  🏆 Rank
                </th>
              )}
              {columns.includes('username') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  👤 Player
                </th>
              )}
              {columns.includes('points') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  ⭐ Points
                </th>
              )}
              {columns.includes('games') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  🎮 Games
                </th>
              )}
              {columns.includes('wins') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  🥇 Wins
                </th>
              )}
              {columns.includes('avg') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  📊 Avg Placement
                </th>
              )}
              {columns.includes('kills') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  ⚔️ Kills
                </th>
              )}
              {columns.includes('survivalTime') && (
                <th className="px-6 py-5 text-left text-xs font-black text-text-primary uppercase tracking-wider">
                  ⏱️ Survival Time
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y-2 divide-slate-700/50">
            {paginatedData.map((row, index) => {
              const actualRank = startIndex + index + 1;
              const isTopThree = actualRank <= 3;
              const isFirst = actualRank === 1;
              const isSecond = actualRank === 2;
              const isThird = actualRank === 3;

              return (
                <tr
                  key={row.username || index}
                  className={`group transition-all duration-200 hover:scale-[1.01] hover:shadow-glow-accent hover:z-10 relative ${
                    isFirst
                      ? 'bg-rank-gold-bg border-l-4 border-rank-gold-border'
                      : isSecond
                        ? 'bg-rank-silver-bg border-l-4 border-rank-silver-border'
                        : isThird
                          ? 'bg-rank-bronze-bg border-l-4 border-rank-bronze-border'
                          : index % 2 === 0
                            ? 'bg-dark-bg-tertiary/50 hover:bg-dark-surface hover:border-l-4 hover:border-accent'
                            : 'bg-dark-bg-tertiary/30 hover:bg-dark-surface hover:border-l-4 hover:border-accent'
                  }`}
                >
                  {columns.includes('rank') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm font-bold">
                      <span className="flex items-center gap-2">
                        <span className="text-2xl">{getMedalEmoji(actualRank)}</span>
                        <span className={isFirst ? 'text-rank-gold-text' : isThird ? 'text-rank-bronze-text' : 'text-text-primary'}>
                          {getPlacementSuffix(actualRank)}
                        </span>
                      </span>
                    </td>
                  )}
                  {columns.includes('username') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm">
                      <Link
                        to={`/player/${row.username}`}
                        className="text-accent hover:text-accent-bright font-bold transition-colors duration-200 hover:underline decoration-2 underline-offset-4"
                      >
                        {row.username}
                      </Link>
                    </td>
                  )}
                  {columns.includes('points') && (
                    <td className="px-6 py-5 whitespace-nowrap text-lg font-bold text-success">
                      {formatPoints(row.points || row.totalPoints || 0)}
                    </td>
                  )}
                  {columns.includes('games') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-text-secondary">
                      {row.games || row.gamesPlayed || 0}
                    </td>
                  )}
                  {columns.includes('wins') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm font-bold text-success">
                      {row.wins || 0}
                    </td>
                  )}
                  {columns.includes('avg') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-text-secondary">
                      {row.avgPlacement || 0}
                    </td>
                  )}
                  {columns.includes('kills') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm font-bold text-danger">
                      {row.kills || row.totalKills || 0}
                    </td>
                  )}
                  {columns.includes('survivalTime') && (
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-text-secondary">
                      {row.survivalTime || row.survival_time || 0}s
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {showPagination && totalPages > 1 && (
        <div className="mt-8 flex items-center justify-between bg-dark-bg-secondary border-2 border-slate-700 rounded-card p-6 shadow-card-dark">
          <div className="text-sm font-medium text-text-secondary">
            Showing <span className="text-primary font-bold">{startIndex + 1}</span> to{' '}
            <span className="text-primary font-bold">{Math.min(endIndex, data.length)}</span> of{' '}
            <span className="text-primary font-bold">{data.length}</span> results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-4 py-2 border-2 border-primary rounded-lg text-sm font-bold text-primary bg-dark-surface hover:bg-primary hover:text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-dark-surface disabled:hover:text-primary disabled:border-slate-600 shadow-card-dark hover:shadow-lg"
            >
              ← Previous
            </button>
            <div className="flex items-center gap-1">
              {[...Array(Math.min(totalPages, 5))].map((_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => onPageChange(pageNum)}
                    className={`px-4 py-2 border-2 rounded-lg text-sm font-bold transition-all duration-200 shadow-card-dark hover:shadow-lg ${
                      currentPage === pageNum
                        ? 'bg-gradient-to-r from-primary to-secondary text-white border-accent shadow-glow-primary scale-110'
                        : 'border-slate-600 text-text-secondary bg-dark-surface hover:bg-dark-bg-tertiary hover:border-primary hover:text-text-primary'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-4 py-2 border-2 border-primary rounded-lg text-sm font-bold text-primary bg-dark-surface hover:bg-primary hover:text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-dark-surface disabled:hover:text-primary disabled:border-slate-600 shadow-card-dark hover:shadow-lg"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
