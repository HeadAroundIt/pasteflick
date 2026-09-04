export type AppState = {
  title: string
  markdown: string
  url: string
  source: string
  partial: boolean
  turn_count: number
  character_count: number
  status: string
  updated_at: number
}

export type ExportSettings = {
  dir: string
  exists: boolean
  default: string
  format: string
  picked?: boolean
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return res.json() as Promise<T>
}

export async function fetchState(): Promise<AppState> {
  return json(await fetch('/api/state'))
}

export async function setTranscript(markdown: string): Promise<AppState> {
  return json(
    await fetch('/api/transcript', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown }),
    }),
  )
}

export async function copyText(text?: string): Promise<AppState> {
  return json(
    await fetch('/api/copy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(text === undefined ? {} : { text }),
    }),
  )
}

export async function pasteText(text?: string): Promise<AppState> {
  return json(
    await fetch('/api/paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(text === undefined ? {} : { text }),
    }),
  )
}

export async function clearTranscript(): Promise<AppState> {
  return json(await fetch('/api/clear', { method: 'POST' }))
}

export async function saveMarkdown(format?: string): Promise<AppState> {
  return json(
    await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(format ? { format } : {}),
    }),
  )
}

export async function fetchExportSettings(): Promise<ExportSettings> {
  return json(await fetch('/api/export-settings'))
}

export async function setExportDir(): Promise<ExportSettings> {
  return json(
    await fetch('/api/export-dir', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }),
  )
}

export async function setExportFormat(format: string): Promise<ExportSettings> {
  return json(
    await fetch('/api/export-format', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format }),
    }),
  )
}

export async function fetchVersion(): Promise<string> {
  try {
    const data = await json<{ version?: string }>(await fetch('/api/health'))
    return data.version || ''
  } catch {
    return ''
  }
}

export function connectWs(onState: (s: AppState) => void): () => void {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onmessage = (ev) => {
    try {
      onState(JSON.parse(String(ev.data)) as AppState)
    } catch {
      /* ignore */
    }
  }
  return () => ws.close()
}

declare global {
  interface Window {
    pywebview?: {
      api?: {
        close_window?: () => void
      }
    }
  }
}

export function closeWindow() {
  window.pywebview?.api?.close_window?.()
}
