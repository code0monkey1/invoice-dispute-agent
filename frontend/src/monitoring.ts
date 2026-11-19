import * as Sentry from '@sentry/react'

export function safeUrl(value: string): string {
  const [withoutQuery] = value.split(/[?#]/)
  return withoutQuery
    .replace(/^(https?:\/\/)[^/@]+@/, '$1')
    .replace(/(\/invoices?\/)(?!parse(?:\/|$)|upload(?:\/|$)|generated(?:\/|$))[^/]+/g, '$1:id')
}

function cleanText(value: string): string {
  return value
    .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, '[Filtered]')
    .replace(/(bearer\s+|(?:token|secret|password|code|api_key)[=:]\s*)[^\s&,]+/gi, '$1[Filtered]')
}

export function scrubEvent<T extends Sentry.Event>(event: T): T {
  delete event.user
  delete event.extra
  delete event.breadcrumbs
  if (event.transaction) event.transaction = safeUrl(event.transaction)
  if (event.request) {
    event.request = { url: event.request.url ? safeUrl(event.request.url) : undefined, ...(
      event.request.method ? { method: event.request.method } : {}
    ) }
  }
  if (event.message) event.message = cleanText(event.message)
  for (const exception of event.exception?.values ?? []) {
    // Third-party error messages can contain full provider response payloads.
    if (exception.value && !/^(API (network request failed|request failed \(5\d\d\)|response was not valid JSON)|Sentry test error InvoiceChaser (backend|frontend) \d{8})$/.test(exception.value)) {
      exception.value = '[Filtered exception message]'
    }
    for (const frame of exception.stacktrace?.frames ?? []) delete frame.vars
  }
  return event
}

export function initializeMonitoring(options: Pick<Sentry.BrowserOptions, 'dsn' | 'environment' | 'release' | 'transport'> = {}) {
  const dsn = options.dsn ?? import.meta.env.VITE_SENTRY_DSN
  if (!dsn || import.meta.env.MODE === 'test' && !options.dsn) return
  Sentry.init({
    ...options,
    dsn,
    environment: options.environment ?? import.meta.env.VITE_SENTRY_ENVIRONMENT ?? import.meta.env.MODE,
    release: options.release ?? import.meta.env.VITE_SENTRY_RELEASE,
    sampleRate: 1,
    dataCollection: { userInfo: false, httpBodies: [], cookies: false, httpHeaders: false, urlQueryParams: false, genAI: { inputs: false, outputs: false } },
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: (options.environment ?? import.meta.env.VITE_SENTRY_ENVIRONMENT ?? import.meta.env.MODE) === 'production' ? 0.1 : 1,
    tracePropagationTargets: [/^\/api\//],
    beforeSendSpan: (span) => ({
      ...span,
      name: safeUrl(span.name),
      attributes: Object.fromEntries(Object.entries(span.attributes).filter(([key]) => ['sentry.op', 'sentry.origin', 'http.request.method', 'http.response.status_code'].includes(key))),
    }),
    beforeSendLog: (log) => ({ ...log, message: cleanText(String(log.message)), attributes: {} }),
    beforeSend: (event) => {
      const clean = scrubEvent(event)
      if (import.meta.env.MODE !== 'test' && import.meta.env.VITE_SLACK_ERROR_ALERTS === 'true' && clean.event_id) {
        try {
          // This endpoint accepts an ID only. Slack credentials stay server-side.
          void fetch(`${import.meta.env.VITE_API_URL || ''}/api/monitoring/browser-error`, {
            method: 'POST', credentials: 'include', keepalive: true,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_id: clean.event_id }),
          }).catch(() => {})
        } catch { /* Slack reporting cannot suppress the Sentry event. */ }
      }
      return clean
    },
  })
}

function reportApiFailure(message: string, path: string, options?: RequestInit, status?: number) {
  Sentry.logger.error(message)
  Sentry.captureException(new Error(message), {
    tags: { 'api.route': safeUrl(path), 'http.method': options?.method ?? 'GET', 'http.status_code': status },
  })
}

export async function monitoredFetch(url: string, path: string, options: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(url, options)
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError')) {
      reportApiFailure('API network request failed', path, options)
    }
    throw error
  }
  if (response.status >= 500) reportApiFailure(`API request failed (${response.status})`, path, options, response.status)
  return response
}

export async function monitoredJson<T>(response: Response, path: string): Promise<T> {
  try {
    return await response.json()
  } catch (error) {
    reportApiFailure('API response was not valid JSON', path)
    throw error
  }
}
