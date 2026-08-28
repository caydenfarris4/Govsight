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
      <Link to={to} aria-current={active ? 'page' : undefined}
            style={active ? { fontFamily: 'var(--font-heading)', fontWeight: 600 } : undefined}>
        {label}
      </Link>
    );
  };
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="nav">
        <Link to="/" className="nav-brand">
          <strong style={{ fontWeight: 600 }}>Gov</strong>
          <span style={{ fontWeight: 400 }}>Sight</span>
          <span className="kicker" style={{ marginLeft: 10, fontSize: 'var(--text-kicker)' }}>
            Financial Analyzer
          </span>
        </Link>
        {navLink('/navi', 'Navi')}
        {navLink('/mantis', 'Mantis')}
        {navLink('/vatica', 'Vatica')}
        {user.role === 'admin' && navLink('/admin', 'Admin')}
        {user.tenant_name && (
          <span className="tag tag-neutral" style={{ marginLeft: 'var(--space-2)' }}>
            {user.tenant_name}
          </span>
        )}
        <span className="text-muted" style={{ fontSize: 13 }}>
          {user.username} ({user.role})
        </span>
        <button onClick={doLogout} className="btn btn-secondary btn-sm">
          Sign out
        </button>
      </header>
      <main style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {children}
      </main>
    </div>
  );
}
