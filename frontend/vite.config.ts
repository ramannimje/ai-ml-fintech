import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const configDir = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = path.resolve(configDir, '..');

export default defineConfig(({ mode }) => {
  const frontendEnv = loadEnv(mode, configDir, '');
  const rootEnv = loadEnv(mode, repoRoot, '');
  const env = { ...rootEnv, ...frontendEnv };

  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000';
  const auth0Domain = env.VITE_AUTH0_DOMAIN || env.AUTH0_DOMAIN || '';
  const auth0ClientId = env.VITE_AUTH0_CLIENT_ID || env.AUTH0_CLIENT_ID || '';
  const auth0Audience = env.VITE_AUTH0_AUDIENCE || env.AUTH0_AUDIENCE || '';

  return {
    plugins: [react()],
    define: {
      __AUTH0_DOMAIN__: JSON.stringify(auth0Domain),
      __AUTH0_CLIENT_ID__: JSON.stringify(auth0ClientId),
      __AUTH0_AUDIENCE__: JSON.stringify(auth0Audience),
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: { environment: 'jsdom', setupFiles: './src/vitest.setup.ts', globals: true },
  };
});
