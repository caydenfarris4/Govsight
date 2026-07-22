import React from 'react';
import { Link } from 'react-router-dom';
import { MODULES } from '../modules.js';

export default function Dashboard({ user }) {
  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '40px 24px', width: '100%' }}>
      <h1 style={{ fontSize: 24, color: '#12263a', marginBottom: 6 }}>
        Welcome to GovSight Financial Analyzer
      </h1>
      <p style={{ color: '#5b6b7a', marginBottom: 28 }}>
        Select a module below to access different analytical tools.
      </p>
      <div style={{
        display: 'grid', gap: 20,
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
      }}>
        {Object.entries(MODULES).map(([id, m]) => (
          <Link key={id} to={`/${id}/0`} style={{
            background: m.color, borderRadius: 12, padding: '34px 24px',
            color: '#fff', textAlign: 'center', textDecoration: 'none',
            boxShadow: '0 8px 24px rgba(18,38,58,.18)',
          }}>
            <div style={{ fontSize: 12, letterSpacing: '.12em', opacity: 0.85 }}>
              GOVSIGHT {m.name.toUpperCase()}
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, margin: '8px 0 6px' }}>
              {m.name}
            </div>
            <div style={{ fontSize: 14, opacity: 0.95 }}>{m.tagline}</div>
            <div style={{
              display: 'inline-block', marginTop: 18, padding: '8px 22px',
              border: '1px solid rgba(255,255,255,.45)', borderRadius: 999,
              background: 'rgba(255,255,255,.16)', fontSize: 14, fontWeight: 600,
            }}>Enter {m.name}</div>
          </Link>
        ))}
      </div>
      {user.role === 'admin' && (
        <div style={{
          marginTop: 28, background: '#1d3a56', borderRadius: 12,
          padding: '22px 24px', color: '#fff', textAlign: 'center',
        }}>
          <div style={{ fontSize: 17, fontWeight: 600 }}>Administration</div>
          <div style={{ fontSize: 13, opacity: 0.85, margin: '6px 0 14px' }}>
            User management, ERP connections, AI data mapping, and system settings
          </div>
          <Link to="/admin" style={{
            color: '#fff', border: '1px solid rgba(255,255,255,.45)',
            borderRadius: 999, padding: '8px 22px', textDecoration: 'none',
            fontSize: 14, fontWeight: 600, background: 'rgba(255,255,255,.12)',
          }}>Open Admin Settings</Link>
        </div>
      )}
    </div>
  );
}
