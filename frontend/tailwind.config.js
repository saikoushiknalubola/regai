/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
        display: ['IBM Plex Sans Condensed', 'system-ui', 'sans-serif'],
      },
      colors: {
        ink: {
          50:  '#F2F0ED',
          100: '#E0DDD8',
          200: '#C4C0B8',
          300: '#A09A90',
          400: '#7C7569',
          500: '#5A5349',
          600: '#3E3830',
          700: '#2A2520',
          800: '#1A1714',
          900: '#0D0C0A',
        },
        signal: {
          red:    '#D94F3D',
          amber:  '#D9820D',
          green:  '#2E7D5E',
          blue:   '#1A5FA8',
          indigo: '#3A3FA8',
        },
        surface: {
          base:    '#FAFAF8',
          raised:  '#F4F2EE',
          overlay: '#ECEAE5',
          border:  '#D8D5CF',
        }
      },
      boxShadow: {
        card:   '0 1px 3px 0 rgba(26,23,20,0.08), 0 1px 2px -1px rgba(26,23,20,0.06)',
        panel:  '0 4px 16px 0 rgba(26,23,20,0.10)',
        focus:  '0 0 0 3px rgba(26,95,168,0.25)',
      },
      borderRadius: {
        sm: '3px',
        DEFAULT: '5px',
        md: '7px',
        lg: '11px',
        xl: '15px',
      }
    }
  },
  plugins: []
}
