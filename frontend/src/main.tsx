import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Analytics } from '@vercel/analytics/react'
import { AuthProvider } from './contexts/AuthContext'
import App from './App'
import { CACHE_MAX_AGE, cacheBuster, persister, queryClient } from './queryClient'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Restores the cache saved on this device before any query runs, then
        refreshes stale entries in the background. */}
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{ persister, maxAge: CACHE_MAX_AGE, buster: cacheBuster() }}
    >
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Analytics />
        </AuthProvider>
      </BrowserRouter>
      {import.meta.env.DEV && <ReactQueryDevtools buttonPosition="bottom-left" />}
    </PersistQueryClientProvider>
  </StrictMode>,
)
