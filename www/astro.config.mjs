// @ts-check
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://kimimgo.github.io',
  base: '/viznoir',
  integrations: [tailwind()],
});
