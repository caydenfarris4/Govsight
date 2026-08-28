import React from 'react';

// Shared admin primitives, expressed in the design system's tokens. The
// sections spread these style objects; the values resolve to theme.css vars.
export const card = {
  background: 'var(--surface-card)', borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)', marginBottom: 'var(--space-4)',
};
export const input = {
  padding: '7px 10px', border: '1px solid var(--color-divider)',
  borderRadius: 'var(--radius-md)', fontSize: 14, font: 'inherit',
  background: 'var(--paper)', color: 'var(--color-text)',
  caretColor: 'var(--color-accent)',
};
export const btn = {
  background: 'var(--color-accent)', color: 'var(--text-on-accent)',
  border: '1px solid transparent', borderRadius: 'var(--radius-md)',
  padding: '8px 16px', fontSize: 14, fontFamily: 'var(--font-heading)',
  fontWeight: 600, cursor: 'pointer',
};
export const btnGhost = {
  ...btn, background: 'transparent', color: 'var(--color-text)',
  border: '1px solid var(--color-divider)',
};

export function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 'var(--space-3)' }}>
      <div style={{
        fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: 17,
      }}>{children}</div>
      {sub && (
        <div className="text-muted" style={{ fontSize: 13, marginTop: 2 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export function Msg({ error, ok }) {
  if (!error && !ok) return null;
  return (
    <div className={`msg ${error ? 'msg-err' : 'msg-ok'}`}
         style={{ marginTop: 'var(--space-2)' }}>
      {error || ok}
    </div>
  );
}

export function Badge({ tone = 'blue', children }) {
  const tones = {
    green: 'tag-accent', amber: 'tag-warn', red: 'tag-cardinal',
    blue: 'tag-accent', gray: 'tag-neutral',
  };
  return (
    <span className={`tag ${tones[tone] || 'tag-neutral'}`}
          style={{ whiteSpace: 'nowrap' }}>
      {children}
    </span>
  );
}

export function Table({ headers, rows, right = [] }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="table" style={{ fontSize: 13 }}>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={h} className={right.includes(i) ? 'num-col' : undefined}
                  style={{ whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j} className={right.includes(j) ? 'num-col' : undefined}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <div className="text-muted" style={{ fontSize: 13, padding: '14px 4px' }}>
          Nothing here yet.
        </div>
      )}
    </div>
  );
}
