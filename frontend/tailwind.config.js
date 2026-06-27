/** @type {import('tailwindcss').Config} */
import typography from '@tailwindcss/typography'

export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fdf2ff',
          100: '#fae8ff',
          200: '#f5d0fe',
          300: '#f0abfc',
          400: '#e879f9',
          500: '#d946ef',
          600: '#c026d3',
          700: '#a21caf',
          800: '#86198f',
          900: '#701a75',
        },
        accent: {
          cyan: '#22d3ee',
          violet: '#a78bfa',
          pink: '#f472b6',
          orange: '#fb923c',
          emerald: '#34d399',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '4xl': '2rem',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        glow: '0 0 40px rgba(217, 70, 239, 0.3)',
        'glow-cyan': '0 0 30px rgba(34, 211, 238, 0.25)',
      },
      animation: {
        'gradient-shift': 'gradient-shift 12s ease infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
    },
  },
  plugins: [typography],
}
