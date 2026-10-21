import { useEffect, useRef, useState } from 'react'
import { api, authHeaders, getToken, setToken } from './api'

function Auth({ onSignedIn }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')

  async function submit(e) {
    e.preventDefault()
    setErr('')
    try {
      const out = await api(mode === 'login' ? '/auth/login' : '/auth/register', {
        method: 'POST',
        body: { email, password },
      })
      setToken(out.token)
      onSignedIn()
    } catch (ex) {
      setErr(ex.message)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1 className="brand">wren</h1>
        <p className="tagline">your personal AI agent</p>
        <form onSubmit={submit}>
          <input type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input
            type="password"
            placeholder="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          <button className="primary" type="submit">
            {mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
          {err && <p className="error">{err}</p>}
        </form>
        <button className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'No account yet? Create one' : 'Already have an account? Sign in'}
        </button>
      </div>
    </div>
  )
}

function Chat({ onSignedOut }) {
  const [threads, setThreads] = useState([])
  const [active, setActive] = useState(null)
  const [items, setItems] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef(null)

  useEffect(() => {
    api('/threads').then(setThreads).catch(() => {})
  }, [])

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [items])

  async function openThread(id) {
    setActive(id)
    setItems(await api(`/threads/${id}/messages`))
  }

  async function newThread() {
    const t = await api('/threads', { method: 'POST', body: {} })
    setThreads((prev) => [t, ...prev])
    setActive(t.id)
    setItems([])
  }

  function upsertAssistant(text) {
    setItems((prev) => {
      const last = prev[prev.length - 1]
      if (last && last.role === 'assistant' && last.streaming) {
        const copy = prev.slice()
        copy[copy.length - 1] = { role: 'assistant', content: text, streaming: true }
        return copy
      }
      return [...prev, { role: 'assistant', content: text, streaming: true }]
    })
  }

  function finalize(text) {
    setItems((prev) => {
      const last = prev[prev.length - 1]
      const copy = prev.slice()
      if (last && last.role === 'assistant' && last.streaming) copy[copy.length - 1] = { role: 'assistant', content: text }
      else copy.push({ role: 'assistant', content: text })
      return copy
    })
  }

  async function send(e) {
    e.preventDefault()
    const message = input.trim()
    if (!message || busy) return
    let threadId = active
    if (!threadId) {
      const t = await api('/threads', { method: 'POST', body: {} })
      setThreads((prev) => [t, ...prev])
      setActive(t.id)
      threadId = t.id
    }
    setInput('')
    setItems((prev) => [...prev, { role: 'user', content: message }])
    setBusy(true)
    try {
      const res = await fetch(`/api/threads/${threadId}/stream`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ message }),
      })
      if (!res.ok || !res.body) throw new Error(`stream failed (${res.status})`)
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop()
        for (const part of parts) {
          const line = part.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue
          const ev = JSON.parse(line.slice(6))
          if (ev.type === 'assistant') upsertAssistant(ev.content)
          else if (ev.type === 'tool_call') setItems((p) => [...p, { role: 'tool_call', name: ev.name, args: ev.arguments }])
          else if (ev.type === 'tool_result') setItems((p) => [...p, { role: 'tool_result', name: ev.name, text: ev.content }])
          else if (ev.type === 'done') finalize(ev.content)
          else if (ev.type === 'error') setItems((p) => [...p, { role: 'error', text: ev.message }])
        }
      }
    } catch (ex) {
      setItems((p) => [...p, { role: 'error', text: ex.message }])
    } finally {
      setBusy(false)
    }
  }

  async function signOut() {
    setToken(null)
    onSignedOut()
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-row">
          <span className="brand small">wren</span>
          <button className="link" onClick={signOut}>
            sign out
          </button>
        </div>
        <button className="primary wide" onClick={newThread}>
          New chat
        </button>
        <div className="thread-list">
          {threads.map((t) => (
            <button key={t.id} className={`thread ${t.id === active ? 'active' : ''}`} onClick={() => openThread(t.id)}>
              {t.title}
            </button>
          ))}
        </div>
      </aside>
      <main className="chat">
        <div className="messages" ref={listRef}>
          {items.map((m, i) => {
            if (m.role === 'user') return <div key={i} className="bubble user">{m.content}</div>
            if (m.role === 'assistant') return <div key={i} className="bubble assistant">{m.content}</div>
            if (m.role === 'tool_call')
              return (
                <div key={i} className="chip">
                  tool · {m.name}
                </div>
              )
            if (m.role === 'tool_result')
              return (
                <div key={i} className="chip result">
                  {m.name} → {m.text}
                </div>
              )
            return (
              <div key={i} className="bubble error">
                {m.text}
              </div>
            )
          })}
          {busy && <div className="chip">thinking…</div>}
        </div>
        <form className="composer" onSubmit={send}>
          <input
            placeholder={busy ? 'Wren is working…' : 'Ask Wren anything'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <button className="primary" disabled={busy || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  )
}

export default function App() {
  const [signedIn, setSignedIn] = useState(!!getToken())
  return signedIn ? <Chat onSignedOut={() => setSignedIn(false)} /> : <Auth onSignedIn={() => setSignedIn(true)} />
}
