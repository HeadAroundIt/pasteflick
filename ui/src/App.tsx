import { useEffect, useRef, useState } from 'react'
import {
  type AppState,
  type ExportSettings,
  clearTranscript,
  closeWindow,
  connectWs,
  copyText,
  fetchExportSettings,
  fetchState,
  fetchVersion,
  pasteText,
  saveMarkdown,
  setExportDir,
  setExportFormat,
  setTranscript,
} from './api'

const empty: AppState = {
  title: '',
  markdown: '',
  url: '',
  source: '',
  partial: false,
  turn_count: 0,
  character_count: 0,
  status: 'Connecting…',
  updated_at: 0,
}

function sourceLabel(state: AppState): string {
  if (!state.markdown) return 'Empty'
  if (state.partial) return 'Partial'
  if (state.source === 'selection') return 'Selection'
  if (state.source === 'api') return 'Thread'
  if (state.source === 'dom') return 'Partial'
  if (state.source === 'pasteflick') return 'PasteFlick'
  return state.source || 'Manual'
}

function shortPath(path: string): string {
  const raw = path.replace(/\//g, '\\')
  if (!raw) return 'Documents\\PasteFlick'
  const parts = raw.split('\\').filter(Boolean)
  if (parts.length <= 2) return raw
  return parts.slice(-2).join('\\')
}

export default function App() {
  const [state, setState] = useState<AppState>(empty)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [exportInfo, setExportInfo] = useState<ExportSettings | null>(null)
  const [version, setVersion] = useState('')
  const [settingsNote, setSettingsNote] = useState('')
  const skipBlur = useRef(false)

  useEffect(() => {
    let alive = true
    void fetchState()
      .then((s) => {
        if (!alive) return
        setState(s)
        setDraft(s.markdown)
      })
      .catch(() => {
        if (alive) setState((s) => ({ ...s, status: 'Overlay not reachable' }))
      })
    void fetchVersion().then((v) => {
      if (alive && v) setVersion(v)
    })
    void fetchExportSettings()
      .then((info) => {
        if (alive) setExportInfo(info)
      })
      .catch(() => {
        /* settings load when opened */
      })
    const stop = connectWs((s) => {
      setState(s)
      setDraft(s.markdown)
      setError('')
    })
    return () => {
      alive = false
      stop()
    }
  }, [])

  const run = async (fn: () => Promise<AppState>) => {
    setBusy(true)
    setError('')
    try {
      const next = await fn()
      setState(next)
      setDraft(next.markdown)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const onBlur = () => {
    if (skipBlur.current) {
      skipBlur.current = false
      return
    }
    if (draft === state.markdown) return
    void run(() => setTranscript(draft))
  }

  const openSettings = () => {
    setSettingsNote('')
    setSettingsOpen(true)
    void fetchExportSettings()
      .then(setExportInfo)
      .catch(() => setSettingsNote("Couldn't load save settings."))
  }

  const fmt = exportInfo?.format === 'pdf' ? 'pdf' : 'md'

  return (
    <div className="frame">
      <div
        className={`drag-ledge pywebview-drag-region${settingsOpen ? ' settings' : ''}`}
        aria-hidden
        title="Drag to move"
      />
      <div className="shell">
        {settingsOpen ? (
          <>
            <header className="titlebar">
              <div className="brand-cluster">
                <button
                  type="button"
                  className="ghost"
                  title="Back"
                  aria-label="Back"
                  onClick={() => setSettingsOpen(false)}
                >
                  <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                    <path
                      d="M10.25 3.25 5.5 8l4.75 4.75"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
                <span className="kicker">Settings</span>
              </div>
              <div className="chrome">
                <button type="button" className="ghost close" title="Close" onClick={() => closeWindow()}>
                  ✕
                </button>
              </div>
            </header>
            <p className="lede">Where Save puts the file.</p>
            <div className="page-form">
              <div className="field">
                <span>Format</span>
                <div className="seg" role="radiogroup" aria-label="File format">
                  <button
                    type="button"
                    className={fmt === 'md' ? 'on' : ''}
                    aria-pressed={fmt === 'md'}
                    onClick={() => {
                      void setExportFormat('md').then(setExportInfo)
                    }}
                  >
                    Markdown
                  </button>
                  <button
                    type="button"
                    className={fmt === 'pdf' ? 'on' : ''}
                    aria-pressed={fmt === 'pdf'}
                    onClick={() => {
                      void setExportFormat('pdf').then(setExportInfo)
                    }}
                  >
                    PDF
                  </button>
                </div>
                <p className="field-hint">
                  {fmt === 'pdf' ? 'Save writes a PDF of the transcript.' : 'Save writes a Markdown file.'}
                </p>
              </div>
              <div className="field">
                <div className="field-head">
                  <span>Folder</span>
                  <button
                    type="button"
                    className="text-btn"
                    onClick={() => {
                      setSettingsNote('')
                      void setExportDir()
                        .then((info) => {
                          setExportInfo(info)
                          if (info.picked === false) {
                            setSettingsNote('Choose a folder in the overlay dialog.')
                          }
                        })
                        .catch(() => setSettingsNote("Couldn't change the folder."))
                    }}
                  >
                    Change
                  </button>
                </div>
                <span className="field-hint folder-path" title={exportInfo?.dir || ''}>
                  {shortPath(exportInfo?.dir || '')}
                </span>
              </div>
              <div className="support">
                <p>
                  Help me keep creating useful apps and sharing them freely. A
                  contribution supports new ideas, continued development, and more
                  tools for everyone.
                </p>
                <p>No pressure—just genuine appreciation!</p>
                <a
                  className="kofi"
                  href="https://ko-fi.com/ryandunham"
                  target="_blank"
                  rel="noreferrer"
                  title="Opens Ko-fi"
                >
                  <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden="true">
                    <path
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.55"
                      strokeLinejoin="round"
                      d="M3.4 5.6h7.2v4.3A2.6 2.6 0 0 1 8 12.5H6a2.6 2.6 0 0 1-2.6-2.6V5.6z"
                    />
                    <path
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.55"
                      strokeLinecap="round"
                      d="M10.6 6.4h1.15a1.7 1.7 0 1 1 0 3.4H10.6"
                    />
                  </svg>
                  Leave a tip
                </a>
              </div>
              <p className="version">{version ? `PasteFlick ${version}` : 'PasteFlick'}</p>
              <p className="settings-note">{settingsNote}</p>
            </div>
          </>
        ) : (
          <>
            <header className="titlebar">
              <div className="brand pywebview-drag-region" title="Drag to move">
                <img src="/pasteflick-32.png" alt="" width={28} height={28} />
                <span className="kicker">PasteFlick</span>
              </div>
              <div className="chrome">
                <button type="button" className="ghost" title="Settings" aria-label="Settings" onClick={openSettings}>
                  <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                    <circle cx="12" cy="12" r="3.05" fill="none" stroke="currentColor" strokeWidth="1.85" />
                    <path
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.85"
                      strokeLinecap="round"
                      d="M12 3.7v2.15M12 18.15v2.15M3.7 12h2.15M18.15 12h2.15M6.22 6.22l1.52 1.52M16.26 16.26l1.52 1.52M6.22 17.78l1.52-1.52M16.26 7.74l1.52-1.52"
                    />
                  </svg>
                </button>
                <button type="button" className="ghost close" title="Close" onClick={() => closeWindow()}>
                  ✕
                </button>
              </div>
            </header>

            <div className="meta">
              <div className="meta-title" title={state.title || undefined}>
                {state.title || 'No transcript yet'}
              </div>
              {state.url ? (
                <a className="meta-url" href={state.url} target="_blank" rel="noreferrer">
                  {state.url.replace(/^https?:\/\//, '')}
                </a>
              ) : (
                <div className="meta-url muted">Open a chat.</div>
              )}
            </div>

            <section className="output">
              <div className="transcript-panel">
                <div className="transcript-bar">
                  <span className="transcript-label">Transcript</span>
                  <div className="transcript-bar-actions">
                    <span className={`chip ${state.partial ? 'warn' : ''}`}>{sourceLabel(state)}</span>
                    <span className="chip">
                      {state.turn_count} turn{state.turn_count === 1 ? '' : 's'}
                    </span>
                    <span className="chip">{state.character_count.toLocaleString()} chars</span>
                  </div>
                </div>
                <textarea
                  className="transcript"
                  value={draft}
                  placeholder="Selection appears here…"
                  spellCheck={false}
                  onMouseDown={(e) => e.stopPropagation()}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={onBlur}
                />
              </div>
            </section>

            <div className="paste-section">
              <div className="tools">
                <button
                  type="button"
                  className="btn"
                  disabled={busy || !draft}
                  onMouseDown={() => {
                    skipBlur.current = true
                  }}
                  onClick={() => void run(() => copyText(draft))}
                >
                  Copy
                </button>
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy || !draft}
                  onMouseDown={() => {
                    skipBlur.current = true
                  }}
                  onClick={() => void run(() => pasteText(draft))}
                >
                  Paste
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={busy || !draft}
                  onMouseDown={() => {
                    skipBlur.current = true
                  }}
                  onClick={() => void run(() => saveMarkdown(exportInfo?.format))}
                >
                  Save
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={busy || !draft}
                  onMouseDown={() => {
                    skipBlur.current = true
                  }}
                  onClick={() => void run(() => clearTranscript())}
                >
                  Clear
                </button>
              </div>
            </div>

            <footer className="hint pywebview-drag-region">
              <span>{error || state.status}</span>
              <span>{version ? version : ''}</span>
            </footer>
          </>
        )}
      </div>
    </div>
  )
}
