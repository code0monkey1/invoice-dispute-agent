import { useEffect, useState, useRef } from 'react'
import { Send, CheckCircle2, AlertCircle } from 'lucide-react'
import { api } from '../api'

type Status = 'unknown' | 'disconnected' | 'connected' | 'pending'

export default function TelegramConnect() {
  const [status, setStatus] = useState<Status>('unknown')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pollRef = useRef<number | null>(null)

  const refresh = async () => {
    try {
      const res = await api.telegramStatus()
      setStatus(res.connected ? 'connected' : (status === 'pending' ? 'pending' : 'disconnected'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load Telegram status')
    }
  }

  useEffect(() => {
    refresh()
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const startPolling = () => {
    if (pollRef.current) return
    pollRef.current = window.setInterval(async () => {
      try {
        const res = await api.telegramStatus()
        if (res.connected) {
          setStatus('connected')
          if (pollRef.current) {
            window.clearInterval(pollRef.current)
            pollRef.current = null
          }
        }
      } catch {
        /* ignore polling errors */
      }
    }, 3000)
  }

  const handleConnect = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await api.telegramConnect()
      window.open(res.deep_link, '_blank', 'noopener')
      setStatus('pending')
      startPolling()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start Telegram connection')
    } finally {
      setBusy(false)
    }
  }

  const handleDisconnect = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.telegramDisconnect()
      setStatus('disconnected')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not disconnect Telegram')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-5 flex items-center gap-4">
      <div className="w-11 h-11 rounded-xl bg-sky-100 flex items-center justify-center text-sky-600 shrink-0">
        <Send className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-gray-900">Telegram notifications</h3>
          {status === 'connected' && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3" /> Connected
            </span>
          )}
          {status === 'pending' && (
            <span className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
              Waiting for /start…
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-0.5">
          {status === 'connected'
            ? 'Escalations and client replies are sent to your Telegram chat.'
            : 'Get instant notifications when invoices escalate or clients reply.'}
        </p>
        {error && (
          <p className="text-xs text-red-600 mt-1 inline-flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> {error}
          </p>
        )}
      </div>
      <div className="shrink-0">
        {status === 'connected' ? (
          <button
            onClick={handleDisconnect}
            disabled={busy}
            className="text-sm font-semibold text-gray-600 hover:text-red-600 disabled:opacity-50 px-3 py-2 rounded-lg border border-gray-200 hover:border-red-200 transition"
          >
            Disconnect
          </button>
        ) : (
          <button
            onClick={handleConnect}
            disabled={busy}
            className="text-sm font-bold text-white bg-sky-600 hover:bg-sky-700 disabled:opacity-50 px-4 py-2 rounded-lg transition"
          >
            {status === 'pending' ? 'Reopen link' : 'Connect'}
          </button>
        )}
      </div>
    </div>
  )
}
