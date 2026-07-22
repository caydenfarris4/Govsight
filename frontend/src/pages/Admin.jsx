import React from 'react';

// Administration stays in the Streamlit console (user management, ERP
// connections, AI data mapping, system settings). This page is the SPA's
// gateway to it.
const AREAS = [
  ['User Management', 'Accounts, roles, and access control'],
  ['ERP Integration Hub', 'Connections, sync schedules, and the AI data mapping review queue'],
  ['System Settings', 'API keys, municipal profile, reserve policy, and payroll rates'],
  ['Report Scheduler', 'Recurring report delivery and history'],
];

export default function Admin() {
  const adminUrl = window.GOVSIGHT_ADMIN_URL ||
    `${window.location.protocol}//${window.location.hostname}:5000`;
  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '40px 24px', width: '100%' }}>
      <h1 style={{ fontSize: 22, color: '#12263a', marginBottom: 6 }}>Administration</h1>
      <p style={{ color: '#5b6b7a', marginBottom: 24, fontSize: 14 }}>
        Platform administration runs in the GovSight management console.
      </p>
      <div style={{
        display: 'grid', gap: 14,
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        marginBottom: 26,
      }}>
        {AREAS.map(([title, desc]) => (
          <div key={title} style={{
            background: '#fff', border: '1px solid #e3e9ee', borderRadius: 10,
            padding: '16px 18px',
          }}>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: '#12263a' }}>{title}</div>
            <div style={{ fontSize: 13, color: '#5b6b7a', marginTop: 4 }}>{desc}</div>
          </div>
        ))}
      </div>
      <a href={adminUrl} target="_blank" rel="noreferrer" style={{
        display: 'inline-block', background: '#12263a', color: '#fff',
        borderRadius: 8, padding: '11px 26px', textDecoration: 'none',
        fontSize: 14, fontWeight: 600,
      }}>Open Management Console</a>
      <div style={{ fontSize: 12, color: '#8fa1b0', marginTop: 10 }}>
        Sign in with the same platform credentials.
      </div>
    </div>
  );
}
