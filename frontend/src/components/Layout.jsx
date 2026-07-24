import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { logout } from '../api.js';

export default function Layout({ user, onLogout, children }) {
  const location = useLocation();
  const doLogout = async () => {
    try { await logout(); } catch { /* session already gone */ }
    onLogout();
  };
  const navLink = (to, label) => {
    const active = location.pathname === to ||
      (to !== '/' && location.pathname.startsWith(to));
    return (
      <Link to={to} style={{
        color: active ? '#fff' : '#b7c6d5', textDecoration: 'none',
        fontSize: 14, fontWeight: active ? 700 : 500, padding: '4px 2px',
        borderBottom: active ? '2px solid #7fb2dd' : '2px solid transparent',
      }}>{label}</Link>
    );
  };
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        background: 'linear-gradient(135deg, #12263a 0%, #1d3a56 100%)',
        color: '#fff', display: 'flex', alignItems: 'center', gap: 18,
        padding: '10px 20px', flexShrink: 0,
      }}>
        <Link to="/" style={{ color: '#fff', textDecoration: 'none' }}>
          <strong style={{ fontSize: 16 }}>GovSight</strong>
          <span style={{ fontSize: 12, color: '#b7c6d5', marginLeft: 8 }}>
            Financial Analyzer
          </span>
        </Link>
        <nav style={{ display: 'flex', gap: 16, marginLeft: 12 }}>
          {navLink('/navi', 'Navi')}
          {navLink('/mantis', 'Mantis')}
          {navLink('/vatica', 'Vatica')}
          {user.role === 'admin' && navLink('/admin', 'Admin')}
        </nav>
        <span style={{ flex: 1 }} />
        {user.tenant_name && (
          <span style={{
            fontSize: 12, color: '#dbe9f5', background: 'rgba(255,255,255,.12)',
            borderRadius: 99, padding: '3px 12px', fontWeight: 600,
          }}>{user.tenant_name}</span>
        )}
        <span style={{ fontSize: 12.5, color: '#b7c6d5' }}>
          {user.username} ({user.role})
        </span>
        <button onClick={doLogout} style={{
          background: 'none', border: '1px solid rgba(255,255,255,.35)',
          color: '#dbe9f5', borderRadius: 6, padding: '5px 14px',
          fontSize: 13, cursor: 'pointer',
        }}>Logout</button>
      </header>
      <main style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>
    </div>
  );
}
