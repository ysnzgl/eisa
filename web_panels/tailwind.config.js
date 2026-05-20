/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Lexend Deca', 'sans-serif'],
        body: ['Figtree', 'sans-serif'],
      },
      colors: {
        eisa: {
          950: '#440000',
          900: '#5F1417',
          800: '#7F1D1D',
          700: '#9D1E1E',
          600: '#B1121B',
          500: '#B1121B',
          400: '#D72638',
          300: '#F59CA3',
          200: '#FECACA',
          100: '#FEF2F2',
          50:  '#FFF5F5',
        },
        accent: {
          DEFAULT: '#B1121B',
          dark:    '#7F1D1D',
          light:   '#F59CA3',
        },
        surface: {
          DEFAULT: '#F7F9FC',
          card:    '#FFFFFF',
          muted:   '#F7F9FC',
        },
      },
      borderRadius: {
        brand: '14px',
        card:  '20px',
        input: '12px',
      },
      boxShadow: {
        card:    '0 4px 24px -2px rgba(177,18,27,0.10), 0 1px 4px rgba(177,18,27,0.06)',
        'card-lg':'0 12px 48px -6px rgba(177,18,27,0.18), 0 2px 8px rgba(177,18,27,0.08)',
        input:   '0 0 0 3px rgba(177,18,27,0.12)',
        btn:     '0 4px 14px rgba(177,18,27,0.35)',
        'btn-hover': '0 6px 20px rgba(177,18,27,0.45)',
      },
    },
  },
  plugins: [],
};
