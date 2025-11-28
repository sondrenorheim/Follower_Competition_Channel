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
      <div className="text-center py-12 text-gray-500">
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
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-primary text-white">
            <tr>
              {columns.includes('rank') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Rank
                </th>
              )}
              {columns.includes('username') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Username
                </th>
              )}
              {columns.includes('points') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Points
                </th>
              )}
              {columns.includes('games') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Games
                </th>
              )}
              {columns.includes('wins') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Wins
                </th>
              )}
              {columns.includes('avg') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Avg Placement
                </th>
              )}
              {columns.includes('kills') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Kills
                </th>
              )}
              {columns.includes('survivalTime') && (
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">
                  Survival Time
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.map((row, index) => {
              const actualRank = startIndex + index + 1;
              const isTopThree = actualRank <= 3;

              return (
                <tr
                  key={row.username || index}
                  className={`hover:bg-gray-50 ${isTopThree ? 'bg-yellow-50' : ''}`}
                >
                  {columns.includes('rank') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      <span className="flex items-center gap-2">
                        {getMedalEmoji(actualRank)}
                        {getPlacementSuffix(actualRank)}
                      </span>
                    </td>
                  )}
                  {columns.includes('username') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <Link
                        to={`/player/${row.username}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                      >
                        {row.username}
                      </Link>
                    </td>
                  )}
                  {columns.includes('points') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatPoints(row.points || row.totalPoints || 0)}
                    </td>
                  )}
                  {columns.includes('games') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {row.games || row.gamesPlayed || 0}
                    </td>
                  )}
                  {columns.includes('wins') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {row.wins || 0}
                    </td>
                  )}
                  {columns.includes('avg') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {row.avgPlacement || 0}
                    </td>
                  )}
                  {columns.includes('kills') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {row.kills || row.totalKills || 0}
                    </td>
                  )}
                  {columns.includes('survivalTime') && (
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {startIndex + 1} to {Math.min(endIndex, data.length)} of {data.length} results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
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
                    className={`px-3 py-2 border rounded-md text-sm font-medium ${
                      currentPage === pageNum
                        ? 'bg-primary text-white border-primary'
                        : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
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
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
