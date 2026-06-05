/** @type {import('tailwindcss').Config} */
const withAlpha = (cssVariable) => `rgb(var(${cssVariable}) / <alpha-value>)`;

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme backgrounds
        'dark-darkest': withAlpha('--color-dark-darkest'),
        'dark-medium': withAlpha('--color-dark-medium'),
        'dark-light': withAlpha('--color-dark-light'),
        'dark-border': withAlpha('--color-dark-border'),

        // Text colors
        'text-primary': withAlpha('--color-text-primary'),
        'text-secondary': withAlpha('--color-text-secondary'),
        'text-muted': withAlpha('--color-text-muted'),

        // Accent colors - Column types
        'accent-textual': withAlpha('--color-accent-textual'),
        'accent-numerical': withAlpha('--color-accent-numerical'),
        'accent-categorical': withAlpha('--color-accent-categorical'),

        // Other accents
        'accent-blue': withAlpha('--color-accent-blue'),
        'accent-blue-light': withAlpha('--color-accent-blue-light'),
        'accent-blue-dark': withAlpha('--color-accent-blue-dark'),
        'accent-orange': withAlpha('--color-accent-orange'),
        'accent-green': withAlpha('--color-accent-green'),
        'accent-purple': withAlpha('--color-accent-purple'),

        // Syntax highlighting (VS Code dark theme)
        'syntax-keyword': withAlpha('--color-syntax-keyword'),
        'syntax-string': withAlpha('--color-syntax-string'),
        'syntax-comment': withAlpha('--color-syntax-comment'),
        'syntax-function': withAlpha('--color-syntax-function'),
        'syntax-variable': withAlpha('--color-syntax-variable'),
        'syntax-number': withAlpha('--color-syntax-number'),
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Fira Code', 'Monaco', 'Consolas', 'monospace'],
      },
      keyframes: {
        sparkle: {
          '0%, 100%': { transform: 'scale(1) rotate(0deg)', opacity: '0.75' },
          '30%':       { transform: 'scale(1.2) rotate(12deg)', opacity: '1' },
          '60%':       { transform: 'scale(0.9) rotate(-8deg)', opacity: '0.85' },
        },
      },
      animation: {
        sparkle: 'sparkle 1.8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
