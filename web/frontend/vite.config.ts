import { defineConfig } from 'vite';

// Relative asset URLs plus <base href> in index.html let one build run from "/" (FastAPI) or from a sub-path
// (GitHub Pages; tools/web_export.py rewrites the base).
export default defineConfig({
  base: './',
  publicDir: 'public',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    target: 'es2020',
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 700,
    rollupOptions: { output: { manualChunks: { three: ['three'], gsap: ['gsap'] } } },
  },
  server: { proxy: { '/data': 'http://localhost:8000' } },
});
