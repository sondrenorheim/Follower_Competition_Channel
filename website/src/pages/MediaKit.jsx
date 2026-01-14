import { useState, useEffect, useRef } from 'react';
import { loadIndex, loadPlayerIndex } from '../utils/dataLoader';

// Animated counter component
function AnimatedCounter({ end, duration = 2000, suffix = '', prefix = '' }) {
  const [count, setCount] = useState(0);
  const [hasAnimated, setHasAnimated] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          let startTime;
          const animate = (currentTime) => {
            if (!startTime) startTime = currentTime;
            const progress = Math.min((currentTime - startTime) / duration, 1);
            const easeOut = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(easeOut * end));
            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.1 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [end, duration, hasAnimated]);

  return (
    <span ref={ref}>
      {prefix}{count.toLocaleString()}{suffix}
    </span>
  );
}

// Stat card component
function StatCard({ icon, value, label, suffix = '', prefix = '' }) {
  return (
    <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-6 text-center transform hover:scale-105 transition-all duration-300 hover:shadow-[0_0_30px_rgba(124,128,255,0.2)]">
      <div className="text-4xl mb-3">{icon}</div>
      <div className="text-3xl md:text-4xl font-bold text-primary-bright mb-2">
        <AnimatedCounter end={value} suffix={suffix} prefix={prefix} />
      </div>
      <div className="text-text-muted text-sm uppercase tracking-wider">{label}</div>
    </div>
  );
}

// Game card component
function GameCard({ name, description, icon }) {
  return (
    <div className="bg-dark-bg-secondary border border-dark-surface rounded-xl p-5 hover:border-primary/50 transition-all duration-300 hover:shadow-[0_0_20px_rgba(124,128,255,0.15)]">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="text-lg font-semibold text-text-primary mb-2">{name}</h3>
      <p className="text-text-muted text-sm">{description}</p>
    </div>
  );
}

// Partnership card component
function PartnershipCard({ title, description, icon }) {
  return (
    <div className="bg-gradient-to-br from-dark-bg-secondary to-dark-bg-tertiary border border-warning/30 rounded-2xl p-6 hover:border-warning/60 transition-all duration-300 hover:shadow-[0_0_30px_rgba(251,191,36,0.15)]">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-bold text-warning mb-3">{title}</h3>
      <p className="text-text-secondary">{description}</p>
    </div>
  );
}

// Social icons as SVG components
const InstagramIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
  </svg>
);

const TikTokIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

const YouTubeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

const DiscordIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z"/>
  </svg>
);

const GlobeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);

// Social link component
function SocialLink({ platform, handle, url, icon }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-4 bg-dark-bg-secondary border border-dark-surface rounded-xl px-5 py-4 hover:border-primary/50 transition-all duration-300 hover:scale-105"
    >
      <div className="w-8 h-8 text-text-primary">{icon}</div>
      <div className="text-left">
        <div className="text-text-primary font-medium">{platform}</div>
        <div className="text-text-muted text-sm">{handle}</div>
      </div>
    </a>
  );
}

export default function MediaKit() {
  // Dynamic stats from API
  const [stats, setStats] = useState({
    totalGames: 260,
    totalDays: 50,
    totalPlayers: 97000,
    totalFollowers: 90000,
    gameTypes: 10,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        const [index, playerIndex] = await Promise.all([
          loadIndex(),
          loadPlayerIndex()
        ]);

        if (index || playerIndex) {
          setStats(prev => ({
            ...prev,
            totalGames: index?.total_games || prev.totalGames,
            totalDays: index?.total_days || prev.totalDays,
            totalFollowers: index?.total_followers || prev.totalFollowers,
            totalPlayers: playerIndex?.total_players || prev.totalPlayers,
            gameTypes: index?.types_metadata?.length || prev.gameTypes,
          }));
        }
      } catch (err) {
        console.error('Failed to load stats:', err);
      }
    }
    fetchStats();
  }, []);

  const games = [
    { name: 'Battle Royale', description: 'Large-scale elimination supporting 100K+ players', icon: '⚔️' },
    { name: 'Obstacle Course', description: 'Racing through challenging obstacles', icon: '🏃' },
    { name: 'Fighter Arena', description: '1v1 combat tournament brackets', icon: '🥊' },
    { name: 'Snake Escape', description: 'Survive the hunting AI predator', icon: '🐍' },
    { name: 'Platformer Race', description: 'Vertical climbing competition', icon: '🧗' },
    { name: 'Wheel Spinner', description: 'Roulette-style elimination rounds', icon: '🎡' },
    { name: 'Team Battle', description: '4-team tournament format', icon: '👥' },
    { name: 'Meteor Mayhem', description: 'Dodge falling meteors to survive', icon: '☄️' },
    { name: 'Heads or Tails', description: 'Squid Game-style choice elimination', icon: '🪙' },
  ];

  return (
    <div className="min-h-screen bg-dark-bg-primary">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 md:py-32">
        {/* Background effects */}
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent"></div>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary/10 rounded-full blur-[150px] -translate-y-1/2"></div>

        <div className="relative max-w-6xl mx-auto px-6 text-center">
          {/* Logo */}
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-black mb-6 tracking-tight">
            <span className="bg-gradient-to-r from-primary via-accent to-primary-bright bg-clip-text text-transparent">
              FOLLOWER
            </span>
            <br />
            <span className="bg-gradient-to-r from-accent via-primary to-secondary bg-clip-text text-transparent">
              BATTLEGROUNDS
            </span>
          </h1>

          {/* Tagline */}
          <p className="text-xl md:text-2xl text-text-secondary mb-12 max-w-2xl mx-auto">
            Where Social Media Meets Gaming
          </p>

          {/* Key metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            <div className="bg-dark-bg-secondary/80 backdrop-blur border border-primary/30 rounded-2xl p-6 shadow-[0_0_40px_rgba(124,128,255,0.2)]">
              <div className="text-4xl md:text-5xl font-black text-primary-bright">
                <AnimatedCounter end={Math.floor(stats.totalFollowers / 1000)} suffix="K+" />
              </div>
              <div className="text-text-muted mt-2">Followers</div>
            </div>
            <div className="bg-dark-bg-secondary/80 backdrop-blur border border-accent/30 rounded-2xl p-6 shadow-[0_0_40px_rgba(34,211,238,0.2)]">
              <div className="text-4xl md:text-5xl font-black text-accent-bright">
                <AnimatedCounter end={Math.floor(stats.totalPlayers / 1000)} suffix="K+" />
              </div>
              <div className="text-text-muted mt-2">Unique Competitors</div>
            </div>
            <div className="bg-dark-bg-secondary/80 backdrop-blur border border-success/30 rounded-2xl p-6 shadow-[0_0_40px_rgba(52,211,153,0.2)]">
              <div className="text-4xl md:text-5xl font-black text-success">
                <AnimatedCounter end={stats.totalGames} suffix="+" />
              </div>
              <div className="text-text-muted mt-2">Games Produced</div>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="py-16 md:py-24 bg-dark-bg-secondary/30">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-8">
            What is Follower Battlegrounds?
          </h2>
          <p className="text-lg md:text-xl text-text-secondary leading-relaxed mb-6">
            A daily Instagram gaming series where <span className="text-primary-bright font-semibold">followers compete as in-game characters</span>. We create video content featuring our audience in various game modes - from Battle Royales to obstacle courses - building community and driving engagement through competition.
          </p>
          <p className="text-lg text-accent-bright font-medium">
            Every follower is a potential winner.
          </p>
        </div>
      </section>

      {/* Statistics Dashboard */}
      <section className="py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary text-center mb-12">
            By The Numbers
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
            <StatCard icon="👥" value={stats.totalFollowers} suffix="+" label="Total Followers" />
            <StatCard icon="🎮" value={stats.totalPlayers} suffix="+" label="Unique Competitors" />
            <StatCard icon="🎬" value={stats.totalGames} suffix="+" label="Games Produced" />
            <StatCard icon="🕹️" value={stats.gameTypes} suffix="+" label="Game Modes" />
            <StatCard icon="📹" value={6} suffix="-10" label="Daily Videos" />
            <StatCard icon="📅" value={stats.totalDays} label="Days Running" />
          </div>

          {/* Growth indicator */}
          <div className="mt-12 text-center">
            <div className="inline-flex items-center gap-3 bg-success/10 border border-success/30 rounded-full px-6 py-3">
              <span className="text-2xl">📈</span>
              <span className="text-success font-bold text-lg">9,600% Engagement Growth</span>
            </div>
          </div>
        </div>
      </section>

      {/* Engagement & Reach Section */}
      <section className="py-16 md:py-24 bg-dark-bg-secondary/30">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary text-center mb-4">
            Engagement & Reach
          </h2>
          <p className="text-text-muted text-center mb-12 max-w-2xl mx-auto">
            Last 30 days performance metrics from Instagram Insights
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-8">
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-5 text-center">
              <div className="text-3xl md:text-4xl font-bold text-primary-bright mb-1">
                <AnimatedCounter end={4.4} suffix="M" />
              </div>
              <div className="text-text-muted text-sm">Total Views</div>
            </div>
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-5 text-center">
              <div className="text-3xl md:text-4xl font-bold text-accent-bright mb-1">
                <AnimatedCounter end={2} suffix="M+" />
              </div>
              <div className="text-text-muted text-sm">Accounts Reached</div>
            </div>
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-5 text-center">
              <div className="text-3xl md:text-4xl font-bold text-success mb-1">
                <AnimatedCounter end={216} suffix="K" />
              </div>
              <div className="text-text-muted text-sm">Interactions</div>
            </div>
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-5 text-center">
              <div className="text-3xl md:text-4xl font-bold text-warning mb-1">
                <AnimatedCounter end={165} suffix="K" />
              </div>
              <div className="text-text-muted text-sm">Accounts Engaged</div>
            </div>
          </div>

          {/* Key insights */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-dark-bg-tertiary rounded-xl p-5 border border-dark-surface">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">🎯</span>
                <span className="text-text-primary font-semibold">Viral Reach</span>
              </div>
              <p className="text-text-secondary text-sm">
                <span className="text-primary-bright font-bold">79.3%</span> of views come from non-followers, showing strong discovery and viral potential
              </p>
            </div>
            <div className="bg-dark-bg-tertiary rounded-xl p-5 border border-dark-surface">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">👆</span>
                <span className="text-text-primary font-semibold">Profile Activity</span>
              </div>
              <p className="text-text-secondary text-sm">
                <span className="text-accent-bright font-bold">115K</span> profile visits and <span className="text-accent-bright font-bold">10.9K</span> external link taps in 30 days
              </p>
            </div>
            <div className="bg-dark-bg-tertiary rounded-xl p-5 border border-dark-surface">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl">🔥</span>
                <span className="text-text-primary font-semibold">Top Performers</span>
              </div>
              <p className="text-text-secondary text-sm">
                Best reels reach <span className="text-success font-bold">179K</span>, <span className="text-success font-bold">78K</span>, <span className="text-success font-bold">47K</span> views individually
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Audience Demographics Section */}
      <section className="py-16 md:py-24">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary text-center mb-4">
            Audience Demographics
          </h2>
          <p className="text-text-muted text-center mb-12 max-w-2xl mx-auto">
            Who's watching - data from Instagram Insights
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Age Distribution */}
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <span>📊</span> Age Distribution
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-muted">13-17</span>
                    <span className="text-warning font-medium">25.5%</span>
                  </div>
                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                    <div className="h-full bg-warning rounded-full" style={{width: '25.5%'}}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-muted">18-24</span>
                    <span className="text-primary-bright font-medium">34.1%</span>
                  </div>
                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                    <div className="h-full bg-primary-bright rounded-full" style={{width: '34.1%'}}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-muted">25-34</span>
                    <span className="text-primary font-medium">29.7%</span>
                  </div>
                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                    <div className="h-full bg-primary rounded-full" style={{width: '29.7%'}}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-muted">35-44</span>
                    <span className="text-accent font-medium">6.4%</span>
                  </div>
                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                    <div className="h-full bg-accent rounded-full" style={{width: '6.4%'}}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-text-muted">45+</span>
                    <span className="text-text-muted font-medium">4.3%</span>
                  </div>
                  <div className="h-2 bg-dark-surface rounded-full overflow-hidden">
                    <div className="h-full bg-dark-bg-tertiary rounded-full" style={{width: '4.3%'}}></div>
                  </div>
                </div>
              </div>
              <p className="text-accent-bright text-sm mt-4 font-medium">89% under 35 years old</p>
            </div>

            {/* Gender Split */}
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <span>👤</span> Gender Split
              </h3>
              <div className="flex items-center justify-center gap-6 py-4">
                <div className="text-center">
                  <div className="text-4xl font-bold text-primary-bright">81%</div>
                  <div className="text-text-muted text-sm mt-1">Male</div>
                </div>
                <div className="w-px h-16 bg-dark-surface"></div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-accent">19%</div>
                  <div className="text-text-muted text-sm mt-1">Female</div>
                </div>
              </div>
              <p className="text-text-secondary text-sm mt-4 text-center">
                Male-skewed gaming audience
              </p>
            </div>

            {/* Top Countries */}
            <div className="bg-dark-bg-secondary border border-dark-surface rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <span>🌍</span> Top Countries
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">United States</span>
                  <span className="text-primary-bright font-medium">32.5%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">United Kingdom</span>
                  <span className="text-primary font-medium">4.6%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Indonesia</span>
                  <span className="text-accent font-medium">4.2%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">France</span>
                  <span className="text-accent font-medium">3.9%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary">Italy</span>
                  <span className="text-text-muted font-medium">3.7%</span>
                </div>
              </div>
              <p className="text-text-secondary text-sm mt-4">
                Global reach, 50+ countries
              </p>
            </div>
          </div>

          {/* Interests tag */}
          <div className="mt-8 text-center">
            <p className="text-text-muted text-sm mb-3">Audience Interests</p>
            <div className="flex flex-wrap justify-center gap-2">
              {['Gaming', 'Tech', 'Entertainment', 'Memes', 'Esports', 'Social Media'].map((interest, i) => (
                <span key={i} className="bg-dark-bg-secondary border border-dark-surface px-4 py-2 rounded-full text-sm text-text-secondary">
                  {interest}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Games Showcase */}
      <section className="py-16 md:py-24 bg-dark-bg-secondary/30">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary text-center mb-4">
            Our Games
          </h2>
          <p className="text-text-muted text-center mb-12 max-w-2xl mx-auto">
            Diverse game modes keep audiences engaged with fresh content daily
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {games.map((game, index) => (
              <GameCard key={index} {...game} />
            ))}
          </div>

          <p className="text-center text-text-muted mt-8">
            ...and more game modes being added regularly
          </p>
        </div>
      </section>

      {/* Platform Presence */}
      <section className="py-16 md:py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary text-center mb-12">
            Find Us Everywhere
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SocialLink
              platform="Instagram"
              handle="@followerbattlegrounds"
              url="https://instagram.com/followerbattlegrounds"
              icon={<InstagramIcon className="w-full h-full" />}
            />
            <SocialLink
              platform="TikTok"
              handle="@followerbattlegrounds"
              url="https://www.tiktok.com/@followerbattlegro"
              icon={<TikTokIcon className="w-full h-full" />}
            />
            <SocialLink
              platform="YouTube"
              handle="Follower Battlegrounds"
              url="https://youtube.com/@followerbattlegrounds"
              icon={<YouTubeIcon className="w-full h-full" />}
            />
            <SocialLink
              platform="Discord"
              handle="Join our community"
              url="https://discord.gg/followerbattlegrounds"
              icon={<DiscordIcon className="w-full h-full" />}
            />
          </div>

          <div className="mt-8 text-center">
            <a
              href="https://www.followerbattlegrounds.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-primary-bright hover:text-accent transition-colors"
            >
              <GlobeIcon className="w-5 h-5" />
              <span className="font-medium">followerbattlegrounds.com</span>
            </a>
          </div>
        </div>
      </section>

      {/* Partnership Opportunities */}
      <section className="py-16 md:py-24 bg-gradient-to-b from-dark-bg-secondary/30 to-dark-bg-primary">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            <span className="bg-gradient-to-r from-warning to-warning/70 bg-clip-text text-transparent">
              Partner With Us
            </span>
          </h2>
          <p className="text-text-secondary text-center mb-12 max-w-2xl mx-auto">
            Create unique brand experiences that resonate with an engaged gaming community
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <PartnershipCard
              title="Sponsored Games"
              description="Brand-themed tournaments and special events featuring your brand. Create memorable gaming moments your audience will share."
              icon="🏆"
            />
            <PartnershipCard
              title="In-Video Branding"
              description={`Logo placement, shoutouts, and seamless brand integration across our daily content reaching ${Math.floor(stats.totalFollowers / 1000)}K+ engaged followers.`}
              icon="🎯"
            />
            <PartnershipCard
              title="Custom Content"
              description="Exclusive branded game modes and promotional campaigns designed specifically for your brand's goals."
              icon="✨"
            />
          </div>

          {/* Benefits */}
          <div className="bg-dark-bg-tertiary rounded-2xl p-8 border border-dark-surface">
            <h3 className="text-xl font-bold text-text-primary mb-6 text-center">Why Partner With Us?</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <span className="text-success text-xl">✓</span>
                <span className="text-text-secondary">Direct access to {Math.floor(stats.totalFollowers / 1000)}K+ engaged followers</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-success text-xl">✓</span>
                <span className="text-text-secondary">Daily content featuring your brand</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-success text-xl">✓</span>
                <span className="text-text-secondary">Unique, shareable gaming moments</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-success text-xl">✓</span>
                <span className="text-text-secondary">Community engagement and brand awareness</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-16 md:py-24">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-4">
            Let's Create Something Amazing
          </h2>
          <p className="text-text-secondary mb-10">
            Ready to reach a highly engaged gaming audience? Get in touch.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-10">
            <a
              href="mailto:followerbattlegrounds@gmail.com"
              className="inline-flex items-center gap-3 bg-primary hover:bg-primary-bright text-white font-semibold px-8 py-4 rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-[0_0_30px_rgba(124,128,255,0.4)]"
            >
              <span className="text-xl">📧</span>
              <span>followerbattlegrounds@gmail.com</span>
            </a>
          </div>

          <p className="text-text-muted mb-6">Or reach out via social media</p>

          <div className="flex justify-center gap-4">
            <a
              href="https://instagram.com/followerbattlegrounds"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-dark-bg-secondary hover:bg-dark-surface border border-dark-surface hover:border-primary/50 rounded-full p-4 transition-all duration-300 hover:scale-110"
            >
              <InstagramIcon className="w-6 h-6 text-text-primary" />
            </a>
            <a
              href="https://www.tiktok.com/@followerbattlegro"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-dark-bg-secondary hover:bg-dark-surface border border-dark-surface hover:border-primary/50 rounded-full p-4 transition-all duration-300 hover:scale-110"
            >
              <TikTokIcon className="w-6 h-6 text-text-primary" />
            </a>
            <a
              href="https://youtube.com/@followerbattlegrounds"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-dark-bg-secondary hover:bg-dark-surface border border-dark-surface hover:border-primary/50 rounded-full p-4 transition-all duration-300 hover:scale-110"
            >
              <YouTubeIcon className="w-6 h-6 text-text-primary" />
            </a>
            <a
              href="https://discord.gg/followerbattlegrounds"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-dark-bg-secondary hover:bg-dark-surface border border-dark-surface hover:border-primary/50 rounded-full p-4 transition-all duration-300 hover:scale-110"
            >
              <DiscordIcon className="w-6 h-6 text-text-primary" />
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-dark-surface">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-text-muted text-sm">
            © 2025-2026 Follower Battlegrounds. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
