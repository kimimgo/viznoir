// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://kimimgo.github.io',
  base: '/viznoir',
  vite: {
    plugins: [tailwindcss()],
  },
});
