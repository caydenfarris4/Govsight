import React from 'react';

export const card = {
  background: '#fff', border: '1px solid #e3e9ee', borderRadius: 10,
  padding: '18px 20px', marginBottom: 18,
};
export const input = {
  padding: '8px 12px', border: '1px solid #cfd8e0', borderRadius: 8,
  fontSize: 13.5, background: '#fff',
};
export const btn = {
  background: '#12263a', color: '#fff', border: 'none', borderRadius: 8,
  padding: '8px 18px', fontSize: 13.5, fontWeight: 600, cursor: 'pointer',
};
export const btnGhost = {
  ...btn, background: '#fff', color: '#12263a', border: '1px solid #cfd8e0',
};

export function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 700, fontSize: 15.5, color: '#12263a' }}>{children}</div>
      {sub && <div style={{ fontSize: 12.5, color: '#5b6b7a', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export function Msg({ error, ok }) {
  if (!error && !ok) return null;
  return (
    <div style={{
      background: error ? '#fdecea' : '#e2f2e8', color: error ? '#a4271c' : '#1e6b3c',
      borderRadius: 8, padding: '9px 13px', fontSize: 13, marginTop: 10,
    }}>{error || ok}</div>
  );
}

export function Badge({ tone = 'blue', children }) {
  const tones = {
    green: ['#e2f2e8', '#1e6b3c'], amber: ['#fdeeda', '#8a5a12'],
    red: ['#fdecea', '#a4271c'], blue: ['#e8eef7', '#24508f'],
    gray: ['#eef2f6', '#5b6b7a'],
  };
  const [bg, fg] = tones[tone] || tones.blue;
  return (
    <span style={{
      background: bg, color: fg, padding: '2px 10px', borderRadius: 99,
      fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
    }}>{children}</span>
  );
}

export function Table({ headers, rows, right = [] }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={h} style={{
                textAlign: right.includes(i) ? 'right' : 'left', padding: '7px 10px',
                borderBottom: '2px solid #dde4ea', color: '#5b6b7a', fontSize: 12,
                whiteSpace: 'nowrap',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j} style={{
                  textAlign: right.includes(j) ? 'right' : 'left',
                  padding: '6px 10px', borderBottom: '1px solid #eef2f5',
                }}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <div style={{ color: '#8fa1b0', fontSize: 13, padding: '14px 4px' }}>Nothing here yet.</div>
      )}
    </div>
  );
}
