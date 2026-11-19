import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { sentryVitePlugin } from '@sentry/vite-plugin'

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }
  const release = env.SENTRY_RELEASE || env.VERCEL_GIT_COMMIT_SHA || env.VITE_SENTRY_RELEASE
  const uploadMaps = Boolean(env.SENTRY_AUTH_TOKEN && env.SENTRY_ORG && env.SENTRY_PROJECT)

  return {
    define: { 'import.meta.env.VITE_SENTRY_RELEASE': JSON.stringify(release) },
    build: { sourcemap: uploadMaps ? 'hidden' : false },
    plugins: [react(), tailwindcss(), ...(uploadMaps ? [sentryVitePlugin({
      authToken: env.SENTRY_AUTH_TOKEN,
      org: env.SENTRY_ORG,
      project: env.SENTRY_PROJECT,
      release: { name: release },
      telemetry: false,
      sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] },
    })] : [])],
    server: {
      host: '0.0.0.0',
      port: 5173,
      hmr: {
        protocol: 'ws',
        host: 'localhost',
        clientPort: 5173,
      },
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 4173,
    },
  }
})
