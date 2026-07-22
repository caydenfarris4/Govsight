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
      <table style={{ borderCollapse: 'collapse', fontSize: 12.5, width: '100%' }}>
        <thead>
          <tr>
            {data.columns.map((c) => (
              <th key={c} style={{
                textAlign: 'left', padding: '6px 10px', background: '#eef2f6',
                borderBottom: '2px solid #d5dee6', color: '#3c4a58',
                whiteSpace: 'nowrap',
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.slice(0, 50).map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} style={{
                  padding: '5px 10px', borderBottom: '1px solid #edf1f5',
                  color: '#22303c', whiteSpace: 'nowrap',
                }}>{cell === null || cell === undefined ? '' : String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.rows.length > 50 && (
        <div style={{ fontSize: 11.5, color: '#8fa1b0', padding: '6px 2px' }}>
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
        <div style={{
          background: '#fdf6e6', border: '1px solid #ecd9a8', borderRadius: 8,
          padding: '10px 14px', fontSize: 13, color: '#7a5d1c', marginBottom: 16,
        }}>
          {status.degraded_reason}
        </div>
      )}
      <div style={{ flex: 1 }}>
        {messages.length === 0 && (
          <div style={{ padding: '30px 0', textAlign: 'center' }}>
            <div style={{ fontSize: 17, fontWeight: 600, color: '#12263a' }}>
              Mantis AI Assistant
            </div>
            <div style={{ fontSize: 13.5, color: '#5b6b7a', margin: '6px 0 20px' }}>
              Ask about budgets, revenues, spending patterns, or specific accounts.
            </div>
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center',
            }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} style={{
                  border: '1px solid #cfd8e0', background: '#fff', color: '#3c4a58',
                  borderRadius: 99, padding: '8px 14px', fontSize: 12.5,
                  cursor: 'pointer',
                }}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => m.role === 'user' ? (
          <div key={i} style={{ display: 'flex', justifyContent: 'flex-end', margin: '10px 0' }}>
            <div style={{
              background: '#2450b8', color: '#fff', borderRadius: '14px 14px 4px 14px',
              padding: '10px 14px', fontSize: 13.5, maxWidth: '78%',
            }}>{m.text}</div>
          </div>
        ) : (
          <div key={i} style={{ display: 'flex', margin: '10px 0' }}>
            <div style={{
              background: '#fff', border: '1px solid #e3e9ee',
              borderRadius: '14px 14px 14px 4px', padding: '12px 16px',
              fontSize: 13.5, maxWidth: '85%', color: '#22303c',
            }}>
              {m.result.title && (
                <div style={{
                  fontWeight: 700, marginBottom: 6,
                  color: m.result.type === 'error' ? '#a4271c' : '#12263a',
                }}>{m.result.title}</div>
              )}
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
                {m.result.message}
              </div>
              <ResultTable data={m.result.data} />
              {m.result.tool_used && (
                <div style={{ fontSize: 11, color: '#8fa1b0', marginTop: 8 }}>
                  Source: {m.result.tool_used}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div style={{ color: '#8fa1b0', fontSize: 13, padding: '8px 2px' }}>
            Analyzing…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(); }} style={{
        display: 'flex', gap: 10, marginTop: 18, position: 'sticky', bottom: 12,
      }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your financial data…"
          style={{
            flex: 1, padding: '11px 16px', borderRadius: 10,
            border: '1px solid #cfd8e0', fontSize: 14, background: '#fff',
          }}
        />
        <button type="submit" disabled={busy || !input.trim()} style={{
          background: '#12263a', color: '#fff', border: 'none', borderRadius: 10,
          padding: '11px 22px', fontSize: 14, fontWeight: 600,
          cursor: busy ? 'default' : 'pointer', opacity: busy || !input.trim() ? 0.6 : 1,
        }}>Send</button>
      </form>
    </div>
  );
}
