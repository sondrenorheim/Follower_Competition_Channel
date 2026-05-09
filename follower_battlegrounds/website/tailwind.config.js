/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme backgrounds (layered depth)
        'dark-bg-primary': '#0a0e27',     // Very dark navy - main background
        'dark-bg-secondary': '#13172b',   // Card backgrounds
        'dark-bg-tertiary': '#1a1f3a',    // Nested elements
        'dark-surface': '#232946',        // Hover states

        // Brand colors (optimized for dark theme)
        primary: '#7c80ff',         // Indigo - better contrast
        'primary-bright': '#8b8fff', // Brighter indigo for hover
        secondary: '#a78bfa',       // Purple - better visibility
        'secondary-bright': '#c4b5fd', // Brighter purple
        accent: '#22d3ee',          // Cyan - more vibrant
        'accent-bright': '#67e8f9',  // Brighter cyan
        success: '#34d399',         // Green
        warning: '#fbbf24',         // Amber
        danger: '#fb7185',          // Rose

        // Text colors
        'text-primary': '#e2e8f0',    // High contrast
        'text-secondary': '#cbd5e1',  // Medium contrast
        'text-muted': '#94a3b8',      // Subtle

        // Ranking highlights (Top 3)
        'rank-gold-bg': '#422006',
        'rank-gold-border': '#fbbf24',
        'rank-gold-text': '#fde68a',
        'rank-silver-bg': '#1e293b',
        'rank-silver-border': '#94a3b8',
        'rank-bronze-bg': '#431407',
        'rank-bronze-border': '#fb923c',
        'rank-bronze-text': '#fed7aa',
      },
      boxShadow: {
        'card-dark': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'card-hover-dark': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
        'glow-primary': '0 0 20px rgba(124, 128, 255, 0.3)',
        'glow-accent': '0 0 20px rgba(34, 211, 238, 0.3)',
        'inner-subtle': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
      },
      borderRadius: {
        'card': '1rem',  // 16px - modern card radius
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
        'fade-in': 'fadeIn 0.5s ease-in',
        'slide-up': 'slideUp 0.3s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
      },
    },
  },
  plugins: [],
}
