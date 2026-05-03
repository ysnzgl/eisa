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
          950: '#060E1F',
          900: '#0B1D3A',
          800: '#122B56',
          700: '#1A3C78',
          600: '#1E4E9F',
          500: '#2563EB',
          400: '#3B82F6',
          300: '#7DD3FC',
          200: '#BAE6FD',
          100: '#E0F2FE',
          50:  '#F0F9FF',
        },
        accent: {
          DEFAULT: '#06B6D4',
          dark:    '#0891B2',
          light:   '#67E8F9',
        },
        surface: {
          DEFAULT: '#F8FAFC',
          card:    '#FFFFFF',
          muted:   '#F1F5F9',
        },
      },
      borderRadius: {
        brand: '14px',
        card:  '20px',
        input: '12px',
      },
      boxShadow: {
        card:    '0 4px 24px -2px rgba(11,29,58,0.10), 0 1px 4px rgba(11,29,58,0.06)',
        'card-lg':'0 12px 48px -6px rgba(11,29,58,0.18), 0 2px 8px rgba(11,29,58,0.08)',
        input:   '0 0 0 3px rgba(37,99,235,0.12)',
        btn:     '0 4px 14px rgba(37,99,235,0.35)',
        'btn-hover': '0 6px 20px rgba(37,99,235,0.45)',
      },
    },
  },
  plugins: [],
};
