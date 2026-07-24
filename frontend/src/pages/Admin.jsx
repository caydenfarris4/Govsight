import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

// City administration: manage this city's users, their roles, and which
// departments each can see. Platform admins additionally create cities.

const ROLES = ['admin', 'editor', 'viewer'];

const card = {
  background: '#fff', border: '1px solid #e3e9ee', borderRadius: 10,
  padding: '18px 20px', marginBottom: 18,
};
const input = {
  padding: '8px 12px', border: '1px solid #cfd8e0', borderRadius: 8,
  fontSize: 13.5, background: '#fff',
};
const btn = {
  background: '#12263a', color: '#fff', border: 'none', borderRadius: 8,
  padding: '8px 18px', fontSize: 13.5, fontWeight: 600, cursor: 'pointer',
};

function DeptPicker({ departments, value, onChange }) {
  const all = value === '*';
  return (
    <div>
      <label style={{ fontSize: 13, display: 'flex', gap: 6, alignItems: 'center', fontWeight: 600 }}>
        <input type="checkbox" checked={all}
               onChange={(e) => onChange(e.target.checked ? '*' : [])} />
        All departments (citywide)
      </label>
      {!all && (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))',
          gap: 4, marginTop: 8, padding: 10, background: '#f4f6f8', borderRadius: 8,
        }}>
          {departments.map((d) => (
            <label key={d} style={{ fontSize: 12.5, display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={value.includes(d)}
                     onChange={(e) => onChange(e.target.checked
                       ? [...value, d] : value.filter((x) => x !== d))} />
              {d}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function UserRow({ u, departments, self, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState(u.role);
  const [deps, setDeps] = useState(u.departments);
  const [newPassword, setNewPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    setBusy(true); setError('');
    try {
      const body = { role, departments: deps };
      if (newPassword) body.password = newPassword;
      await api(`/api/admin/users/${encodeURIComponent(u.username)}`,
                { method: 'PUT', body: JSON.stringify(body) });
      setEditing(false); setNewPassword('');
      onSaved();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const toggleActive = async () => {
    setBusy(true); setError('');
    try {
      await api(`/api/admin/users/${encodeURIComponent(u.username)}`,
                { method: 'PUT', body: JSON.stringify({ active: !u.active }) });
      onSaved();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const scope = u.departments === '*' ? 'All departments'
    : `${u.departments.length} department${u.departments.length !== 1 ? 's' : ''}`;

  return (
    <div style={{ borderTop: '1px solid #eef2f5', padding: '10px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{u.username}</span>
          {self && <span style={{ fontSize: 11.5, color: '#8fa1b0', marginLeft: 6 }}>(you)</span>}
          {!u.active && (
            <span style={{
              marginLeft: 8, fontSize: 11, fontWeight: 700, color: '#a4271c',
              background: '#fdecea', borderRadius: 99, padding: '2px 8px',
            }}>DEACTIVATED</span>
          )}
          <div style={{ fontSize: 12, color: '#5b6b7a', marginTop: 2 }}>
            {u.role} - {scope}
            {u.is_platform_admin ? ' - platform admin' : ''}
          </div>
        </div>
        <button style={{ ...btn, background: '#fff', color: '#12263a', border: '1px solid #cfd8e0' }}
                onClick={() => setEditing(!editing)}>{editing ? 'Close' : 'Edit'}</button>
        {!self && (
          <button style={{ ...btn, background: '#fff', border: '1px solid #cfd8e0',
                           color: u.active ? '#a4271c' : '#1e6b3c' }}
                  disabled={busy} onClick={toggleActive}>
            {u.active ? 'Deactivate' : 'Reactivate'}
          </button>
        )}
      </div>
      {editing && (
        <div style={{ margin: '10px 0 4px', padding: 14, background: '#fafbfc',
                      border: '1px solid #eef2f5', borderRadius: 8 }}>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 12 }}>
            <label style={{ fontSize: 12.5, fontWeight: 600 }}>Role{' '}
              <select value={role} onChange={(e) => setRole(e.target.value)}
                      disabled={self} style={{ ...input, marginLeft: 6 }}>
                {ROLES.map((r) => <option key={r}>{r}</option>)}
              </select>
            </label>
            <input style={{ ...input, flex: 1 }} type="password" value={newPassword}
                   placeholder="New password (leave blank to keep)"
                   onChange={(e) => setNewPassword(e.target.value)} />
          </div>
          <DeptPicker departments={departments} value={deps} onChange={setDeps} />
          <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center' }}>
            <button style={btn} disabled={busy} onClick={save}>Save changes</button>
            {error && <span style={{ color: '#a4271c', fontSize: 12.5 }}>{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function AddUser({ departments, onCreated }) {
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [deps, setDeps] = useState('*');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true); setError('');
    try {
      await api('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify({ username, password, role, departments: deps }),
      });
      setOpen(false); setUsername(''); setPassword(''); setRole('viewer'); setDeps('*');
      onCreated();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  if (!open) {
    return <button style={btn} onClick={() => setOpen(true)}>Add user</button>;
  }
  return (
    <div style={{ padding: 14, background: '#fafbfc', border: '1px solid #eef2f5', borderRadius: 8 }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <input style={input} placeholder="Username" value={username}
               onChange={(e) => setUsername(e.target.value)} />
        <input style={input} type="password" placeholder="Password (min 8 chars)"
               value={password} onChange={(e) => setPassword(e.target.value)} />
        <select value={role} onChange={(e) => setRole(e.target.value)} style={input}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <DeptPicker departments={departments} value={deps} onChange={setDeps} />
      <div style={{ marginTop: 12, display: 'flex', gap: 10, alignItems: 'center' }}>
        <button style={btn} disabled={busy || !username || !password} onClick={create}>
          Create user
        </button>
        <button style={{ ...btn, background: '#fff', color: '#5b6b7a', border: '1px solid #cfd8e0' }}
                onClick={() => setOpen(false)}>Cancel</button>
        {error && <span style={{ color: '#a4271c', fontSize: 12.5 }}>{error}</span>}
      </div>
    </div>
  );
}

function CreateCity({ onCreated }) {
  const [form, setForm] = useState({ tenant_id: '', name: '', state: '',
                                     admin_username: '', admin_password: '' });
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const create = async () => {
    setBusy(true); setError(''); setOk('');
    try {
      await api('/api/admin/tenants', { method: 'POST', body: JSON.stringify(form) });
      setOk(`City "${form.name}" created with admin ${form.admin_username}.`);
      setForm({ tenant_id: '', name: '', state: '', admin_username: '', admin_password: '' });
      onCreated();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: 10, marginBottom: 12 }}>
        <input style={input} placeholder="City id (e.g. provo)" value={form.tenant_id}
               onChange={set('tenant_id')} />
        <input style={input} placeholder="City name" value={form.name} onChange={set('name')} />
        <input style={input} placeholder="State" value={form.state} onChange={set('state')} />
        <input style={input} placeholder="Admin username" value={form.admin_username}
               onChange={set('admin_username')} />
        <input style={input} type="password" placeholder="Admin password"
               value={form.admin_password} onChange={set('admin_password')} />
      </div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <button style={btn} disabled={busy || !form.tenant_id || !form.name ||
                                      !form.admin_username || !form.admin_password}
                onClick={create}>Create city</button>
        {error && <span style={{ color: '#a4271c', fontSize: 12.5 }}>{error}</span>}
        {ok && <span style={{ color: '#1e6b3c', fontSize: 12.5 }}>{ok}</span>}
      </div>
    </div>
  );
}

export default function Admin({ user }) {
  const [users, setUsers] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [error, setError] = useState('');

  const reload = () => {
    api('/api/admin/users').then((d) => setUsers(d.users)).catch((e) => setError(e.message));
    if (user.is_platform_admin) {
      api('/api/admin/tenants').then((d) => setTenants(d.tenants)).catch(() => {});
    }
  };
  useEffect(() => {
    reload();
    api('/api/admin/departments').then((d) => setDepartments(d.departments)).catch(() => {});
  }, []);

  const adminUrl = window.GOVSIGHT_ADMIN_URL ||
    `${window.location.protocol}//${window.location.hostname}:5000`;

  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 24px', width: '100%' }}>
      <h1 style={{ fontSize: 22, color: '#12263a', marginBottom: 4 }}>Administration</h1>
      <p style={{ color: '#5b6b7a', marginBottom: 22, fontSize: 14 }}>
        {user.tenant_name} - users, roles, and department access
      </p>
      {error && (
        <div style={{ background: '#fdecea', color: '#a4271c', borderRadius: 8,
                      padding: '10px 14px', fontSize: 13, marginBottom: 14 }}>{error}</div>
      )}

      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ fontWeight: 700, fontSize: 15.5, color: '#12263a', flex: 1 }}>
            Users
          </div>
          <AddUser departments={departments} onCreated={reload} />
        </div>
        <p style={{ fontSize: 12.5, color: '#5b6b7a', margin: '0 0 8px' }}>
          Accounts belong to {user.tenant_name} only. Department access controls what
          each user sees across budgets, transactions, insights, and AI analysis.
        </p>
        {users === null ? (
          <div style={{ color: '#5b6b7a', fontSize: 13, padding: '14px 0' }}>Loading…</div>
        ) : users.map((u) => (
          <UserRow key={u.username} u={u} departments={departments}
                   self={u.username === user.username} onSaved={reload} />
        ))}
      </div>

      {user.is_platform_admin && (
        <div style={card}>
          <div style={{ fontWeight: 700, fontSize: 15.5, color: '#12263a', marginBottom: 6 }}>
            Platform - Cities
          </div>
          <p style={{ fontSize: 12.5, color: '#5b6b7a', margin: '0 0 10px' }}>
            {tenants.length} cit{tenants.length === 1 ? 'y' : 'ies'} on this deployment:{' '}
            {tenants.map((t) => t.name).join(', ') || '-'}. Each city has its own isolated
            databases; its first admin manages its users.
          </p>
          <CreateCity onCreated={reload} />
        </div>
      )}

      <div style={{ ...card, display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14.5, color: '#12263a' }}>
            Management Console
          </div>
          <div style={{ fontSize: 12.5, color: '#5b6b7a' }}>
            ERP connections, AI data mapping, system settings, and report scheduling
          </div>
        </div>
        <a href={adminUrl} target="_blank" rel="noreferrer" style={{ ...btn, textDecoration: 'none' }}>
          Open Console
        </a>
      </div>
    </div>
  );
}
