/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        primary: '#0a0a0a',
        secondary: '#111111',
        tertiary: '#1a1a1a',
        accent: '#00d4ff',
        'accent-hover': '#33ddff',
        'text-primary': '#f5f5f5',
        'text-secondary': '#a0a0a0',
        border: '#2a2a2a',
      },
      fontFamily: {
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
