/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#08090d",
        foreground: "#f0f2f5",
        primary: "#00e5ff",
        accent: "#7c3aed",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Syne', 'sans-serif'],
      },
      keyframes: {
        'think-dot': {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '40%': { transform: 'translateY(-10px)', opacity: '1' },
        },
        'eq-bar': {
          '0%, 100%': { transform: 'scaleY(0.3)' },
          '50%': { transform: 'scaleY(1)' },
        },
      },
      animation: {
        'think-dot': 'think-dot 1.2s ease-in-out infinite',
        'eq-bar': 'eq-bar 0.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
