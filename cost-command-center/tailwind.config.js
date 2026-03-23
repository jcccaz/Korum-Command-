/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'korum-charcoal': '#0D0D0D',
        'korum-green': '#00FF41',
        'korum-amber': '#FFBF00',
        'korum-red': '#FF3131',
        'korum-border': '#2A2A2A',
        'korum-panel': '#151515',
        'korum-text': '#E0E0E0',
        'korum-muted': '#7A7A72'
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}
