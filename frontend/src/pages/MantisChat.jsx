import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';

const SUGGESTIONS = [
  'How is the General Fund tracking against budget this year?',
  'Which departments are pacing over budget?',
  'Summarize revenue trends for the last three fiscal years',
  'Are there any unusual transactions this month?',
];

function ResultTable({ data }) {
  if (!data || !data.columns) return null;
  return (
    <div style={{ overflowX: 'auto', marginTop: 10 }}>
      <table className="table" style={{ fontSize: 13 }}>
        <thead>
          <tr>
            {data.columns.map((c) => (
              <th key={c} style={{ whiteSpace: 'nowrap' }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.slice(0, 50).map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} style={{ whiteSpace: 'nowrap' }}>
                  {cell === null || cell === undefined ? '' : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.rows.length > 50 && (
        <div className="chart-note" style={{ padding: '6px 2px' }}>
          Showing first 50 of {data.rows.length} rows
        </div>
      )}
    </div>
  );
}

export default function MantisChat() {
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    api('/api/mantis/status').then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const send = async (text) => {
    const message = (text || input).trim();
    if (!message || busy) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', text: message }]);
    setBusy(true);
    try {
      const resp = await api('/api/mantis/chat', {
        method: 'POST', body: JSON.stringify({ message }),
      });
      setMessages((m) => [...m, { role: 'assistant', result: resp.result,
                                  degraded: resp.degraded }]);
    } catch (err) {
      setMessages((m) => [...m, {
        role: 'assistant',
        result: { type: 'error', title: 'Request failed', message: err.message },
        degraded: true,
      }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{
      maxWidth: 880, margin: '0 auto', width: '100%', padding: '20px 20px 30px',
      display: 'flex', flexDirection: 'column', minHeight: '100%',
    }}>
      {status && !status.ai_available && (
        <div className="msg msg-warn" style={{ marginBottom: 'var(--space-3)' }}>
          {status.degraded_reason}
        </div>
      )}
      <div style={{ flex: 1 }} aria-live="polite">
        {messages.length === 0 && (
          <div style={{ padding: 'var(--space-8) 0', textAlign: 'center' }}>
            <span className="kicker">Mantis</span>
            <h3 style={{ margin: 'var(--space-1) 0 var(--space-1)' }}>
              Ask the ledger a question
            </h3>
            <p className="text-muted" style={{ fontSize: 14, margin: '0 0 var(--space-4)' }}>
              Budgets, revenues, spending patterns, or specific accounts.
            </p>
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)',
              justifyContent: 'center',
            }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}
                        className="btn btn-secondary btn-sm">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => m.role === 'user' ? (
          <div key={i} style={{ display: 'flex', justifyContent: 'flex-end', margin: '10px 0' }}>
            <div className="chat-bubble-user">{m.text}</div>
          </div>
        ) : (
          <div key={i} style={{ display: 'flex', margin: '10px 0' }}>
            <div className="chat-bubble-assistant elev-sm">
              {m.result.title && (
                <div style={{
                  fontFamily: 'var(--font-heading)', fontWeight: 600, marginBottom: 6,
                  color: m.result.type === 'error'
                    ? 'var(--color-cardinal-700)' : 'var(--color-text)',
                }}>{m.result.title}</div>
              )}
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
                {m.result.message}
              </div>
              <ResultTable data={m.result.data} />
              {m.result.tool_used && (
                <div className="chart-note" style={{ marginTop: 8 }}>
                  Source: {m.result.tool_used}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="text-muted" style={{ fontSize: 13, padding: '8px 2px' }}>
            Analyzing…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(); }} style={{
        display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-4)',
        position: 'sticky', bottom: 12, background: 'var(--paper)',
        paddingTop: 'var(--space-1)',
      }}>
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="Ask Mantis a question"
          placeholder="Ask a question about your financial data…"
          style={{ flex: 1 }}
        />
        <button type="submit" className="btn btn-primary"
                disabled={busy || !input.trim()}>
          Send <i className="ph-duotone ph-paper-plane-tilt" aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}
