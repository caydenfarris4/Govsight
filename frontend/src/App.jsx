import React, { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { me, getBundle } from './api.js';
import Login from './pages/Login.jsx';
import Layout from './components/Layout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import ModulePage from './pages/ModulePage.jsx';
import Admin from './pages/Admin.jsx';

export default function App() {
  const [user, setUser] = useState(undefined); // undefined = checking

  useEffect(() => {
    me().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (!user) return;
    // Environment the embedded tools expect (formerly server-injected)
    window.GOVSIGHT_API_URL = window.location.origin;
    window.GOVSIGHT_USER = { username: user.username, role: user.role,
                             tenant: user.tenant_id, tenant_name: user.tenant_name };
    getBundle().then((bundle) => {
      const accounts = bundle.accounts || [];
      const shape = (type) => accounts
        .filter((a) => a.account_type === type)
        .map((a) => ({ name: a.account_name, department: a.department,
                       amount: a.budget_amount, number: a.account_number }));
      window.GOVSIGHT_GL_ACCOUNTS = {
        revenue: shape('Revenue'), expense: shape('Expense'), asset: [],
      };
      if (window.DEMO_VIEWS && window.DEMO_VIEWS.setData) {
        window.DEMO_VIEWS.setData(bundle);
      }
      if (window.GOVSIGHT_BUNDLE_READY) window.GOVSIGHT_BUNDLE_READY(bundle);
      window.GOVSIGHT_BUNDLE = bundle;
    }).catch(() => { /* views fall back to their own loading */ });
  }, [user]);

  if (user === undefined) {
    return (
      <div style={{ padding: 'var(--space-8)' }} aria-label="Loading…" role="status">
        <div className="skeleton" style={{ height: 40, width: 300, marginBottom: 'var(--space-4)' }} />
        <div className="skeleton" style={{ height: 18, width: 420, marginBottom: 'var(--space-8)' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-6)', maxWidth: 1000 }}>
          <div className="skeleton" style={{ height: 180 }} />
          <div className="skeleton" style={{ height: 180 }} />
          <div className="skeleton" style={{ height: 180 }} />
        </div>
      </div>
    );
  }
  if (!user) {
    return <Login onLogin={setUser} />;
  }
  return (
    <Layout user={user} onLogout={() => setUser(null)}>
      <Routes>
        <Route path="/" element={<Dashboard user={user} />} />
        <Route path="/admin" element={<Admin user={user} />} />
        <Route path="/:moduleId/:tabIndex?" element={<ModulePage user={user} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
