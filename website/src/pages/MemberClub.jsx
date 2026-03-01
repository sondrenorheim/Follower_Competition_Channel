import React, { useEffect, useMemo, useState } from 'react';
import './MemberClub.css';
import { loadClubMemberStats, getDataBasePath } from '../utils/dataLoader';
import { formatPoints, getPlacementSuffix, parseStats, formatDate } from '../utils/formatters';

function resolveAssetUrl(basePath, path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  const trimmed = path.replace(/^\/+/, '');
  return `${basePath}${trimmed}`;
}

function Avatar({ username, avatarUrl }) {
  const [failed, setFailed] = useState(false);
  const initials = useMemo(() => {
    if (!username) return '?';
    const cleaned = username.replace(/[^a-z0-9]/gi, '');
    return cleaned.slice(0, 2).toUpperCase() || username.slice(0, 2).toUpperCase();
  }, [username]);

  if (!avatarUrl || failed) {
    return (
      <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber-200/30 to-amber-500/10 border border-amber-300/40 flex items-center justify-center text-amber-100 font-bold text-xl">
        {initials}
      </div>
    );
  }

  return (
    <img
      src={avatarUrl}
      alt={username}
      className="w-20 h-20 rounded-full object-cover border border-amber-300/40 shadow-lg"
      onError={() => setFailed(true)}
      loading="lazy"
    />
  );
}

function StatLine({ label, value }) {
  return (
    <div className="club-stat rounded-lg px-3 py-2">
      <div className="text-[11px] uppercase tracking-[0.2em] text-amber-100/70">{label}</div>
      <div className="text-lg font-semibold text-amber-50">{value}</div>
    </div>
  );
}

function MemberCard({ member, stats, memberStats }) {
  return (
    <div className="club-card rounded-2xl p-6 md:p-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <Avatar username={member.username} avatarUrl={member.avatarUrl} />
        <div>
          <div className="club-badge px-3 py-1 rounded-full text-xs uppercase tracking-[0.2em] inline-flex items-center gap-2">
            FBG Club Member
          </div>
          <h3 className="mt-3 text-2xl font-semibold text-amber-50">@{member.username}</h3>
          <p className="text-sm text-amber-100/70 mt-1">
            Your support keeps this arena alive. We see you.
          </p>
        </div>
      </div>

      <div>
        <div className="text-sm uppercase tracking-[0.25em] text-amber-200/70 mb-3">All-Time Stats</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatLine label="Total Points" value={formatPoints(stats.totalPoints)} />
          <StatLine label="Games Played" value={stats.gamesPlayed} />
          <StatLine label="Best Result" value={stats.bestPlacement ? getPlacementSuffix(stats.bestPlacement) : '—'} />
          <StatLine label="Avg Placement" value={stats.avgPlacement || '—'} />
          <StatLine label="Wins" value={stats.wins} />
          <StatLine label="Top 3" value={stats.top3Finishes} />
          <StatLine label="Top 10%" value={stats.top10PctFinishes} />
          <StatLine label="Total Kills" value={stats.totalKills} />
        </div>
      </div>

      <div>
        <div className="text-sm uppercase tracking-[0.25em] text-amber-200/70 mb-3">Member-Only Games</div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatLine label="Games" value={memberStats.games} />
          <StatLine label="Points" value={formatPoints(memberStats.points)} />
          <StatLine label="Best Result" value={memberStats.bestPlacement ? getPlacementSuffix(memberStats.bestPlacement) : '—'} />
          <StatLine label="Avg Placement" value={memberStats.avgPlacement || '—'} />
          <StatLine label="Wins" value={memberStats.wins} />
        </div>
        {memberStats.latestGame ? (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-amber-100/70">
            <span className="club-pill px-3 py-1 rounded-full text-xs uppercase tracking-[0.2em]">
              Latest Run
            </span>
            <span>
              Day {memberStats.latestGame.dayNumber} · {formatDate(memberStats.latestGame.timestamp)}
            </span>
            <span>
              {getPlacementSuffix(memberStats.latestGame.placement)} · {formatPoints(memberStats.latestGame.points)} pts
            </span>
          </div>
        ) : (
          <p className="mt-4 text-sm text-amber-100/60">Member-only runs will appear here as soon as they play.</p>
        )}
      </div>
    </div>
  );
}

export default function MemberClub() {
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState([]);

  useEffect(() => {
    let mounted = true;
    async function loadData() {
      setLoading(true);
      try {
        const basePath = getDataBasePath();
        const list = await loadClubMemberStats();
        if (!mounted) return;
        const normalized = Array.isArray(list)
          ? list.map((entry) => ({
              username: entry.username,
              avatarUrl: resolveAssetUrl(basePath, entry.profile_pic_url),
              stats: parseStats(entry.stats || []),
              memberOnly: entry.member_only || {},
            }))
          : [];

        setMembers(normalized);
      } catch (err) {
        console.error('Failed to load club members', err);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="member-club-page">
      <div className="member-club-content max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-12">
        <div className="text-center mb-12">
          <div className="club-heading text-4xl md:text-5xl text-amber-50 mb-4">
            The Follower Battlegrounds Club
          </div>
          <div className="club-subtitle text-lg md:text-xl mb-6">
            Member-only access · Celebrated every day
          </div>
          <div className="club-divider w-2/3 mx-auto"></div>
          <p className="mt-6 text-sm md:text-base text-amber-100/70 max-w-3xl mx-auto">
            This room is reserved for the members who keep the community alive. Every stat here reflects
            your dedication, and every run is a thank you from us.
          </p>
        </div>

        {loading ? (
          <div className="text-center text-amber-100/80">Loading club members...</div>
        ) : (
          <div className="grid grid-cols-1 gap-8">
            {members.map((member) => (
              <MemberCard
                key={member.username}
                member={member}
                stats={member.stats || parseStats([])}
                memberStats={member.memberOnly || { games: 0, points: 0, wins: 0, avgPlacement: '—' }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
