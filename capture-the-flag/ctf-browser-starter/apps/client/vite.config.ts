import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    base: env.VITE_BASE_PATH || '/',
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/game': {
          target: env.GAME_PROXY_TARGET || 'http://127.0.0.1:2567',
          ws: true,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/game/, ''),
        },
      },
    },
    build: {
      rollupOptions: { output: { manualChunks: { phaser: ['phaser'] } } },
      chunkSizeWarningLimit: 1600,
    },
  };
});
