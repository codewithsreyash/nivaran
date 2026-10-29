/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#f5f8fc',
          100: '#eaf0f7',
          200: '#d4dfeb',
          300: '#b2c3d6',
          400: '#849bb5',
          500: '#5d7694',
          600: '#405d7c',
          700: '#294663',
          800: '#183450',
          900: '#0d2740',
          950: '#071b30',
        },
        brand: {
          navy: '#0d2740',
          blue: '#1d4ed8',
          'blue-dark': '#1e40af',
        },
        status: {
          success: '#15803d',
          warning: '#b45309',
          danger: '#b42335',
          info: '#1d4ed8',
        },
        slate: {
          925: '#0d1424',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
