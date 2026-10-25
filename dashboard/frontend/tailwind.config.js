/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        industrial: {
          950: '#090d16',
          900: '#0f172a',
          850: '#141e33',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          400: '#94a3b8',
          accent: '#0284c7',
          highlight: '#38bdf8',
        },
        sorter: {
          red: '#ef4444',
          redGlow: '#f87171',
          green: '#10b981',
          greenGlow: '#34d399',
          blue: '#3b82f6',
          blueGlow: '#60a5fa',
        }
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      boxShadow: {
        'neon-blue': '0 0 15px rgba(56, 189, 248, 0.25)',
        'neon-green': '0 0 15px rgba(16, 185, 129, 0.25)',
        'neon-red': '0 0 15px rgba(239, 68, 68, 0.25)',
      }
    },
  },
  plugins: [],
}
