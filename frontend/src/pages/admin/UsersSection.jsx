import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Msg, SectionTitle, btn, card, input } from './shared.jsx';

// Users, roles, and department access for this city.

const ROLES = ['admin', 'editor', 'viewer'];


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
          gap: 4, marginTop: 8, padding: 10, background: 'var(--surface-raised)', borderRadius: 'var(--radius-md)',
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
    <div style={{ borderTop: '1px solid color-mix(in srgb, var(--ink) 8%, transparent)', padding: '10px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{u.username}</span>
          {self && <span style={{ fontSize: 11.5, color: 'var(--text-faint)', marginLeft: 6 }}>(you)</span>}
          {!u.active && (
            <span style={{
              marginLeft: 8, fontSize: 11, fontWeight: 700, color: 'var(--status-err-fg)',
              background: 'var(--status-err-bg)', borderRadius: 'var(--radius-sm)', padding: '2px 8px',
            }}>DEACTIVATED</span>
          )}
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {u.role} - {scope}
            {u.is_platform_admin ? ' - platform admin' : ''}
          </div>
        </div>
        <button style={{ ...btn, background: 'var(--paper)', color: 'var(--color-text)', border: '1px solid var(--color-divider)' }}
                onClick={() => setEditing(!editing)}>{editing ? 'Close' : 'Edit'}</button>
        {!self && (
          <button style={{ ...btn, background: 'var(--paper)', border: '1px solid var(--color-divider)',
                           color: u.active ? 'var(--status-err-fg)' : 'var(--status-ok-fg)' }}
                  disabled={busy} onClick={toggleActive}>
            {u.active ? 'Deactivate' : 'Reactivate'}
          </button>
        )}
      </div>
      {editing && (
        <div style={{ margin: '10px 0 4px', padding: 14, background: 'var(--surface-raised)',
                      border: '1px solid color-mix(in srgb, var(--ink) 8%, transparent)', borderRadius: 'var(--radius-md)' }}>
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
            {error && <span style={{ color: 'var(--status-err-fg)', fontSize: 12.5 }}>{error}</span>}
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
    <div style={{ padding: 14, background: 'var(--surface-raised)', border: '1px solid color-mix(in srgb, var(--ink) 8%, transparent)', borderRadius: 'var(--radius-md)' }}>
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
        <button style={{ ...btn, background: 'var(--paper)', color: 'var(--text-muted)', border: '1px solid var(--color-divider)' }}
                onClick={() => setOpen(false)}>Cancel</button>
        {error && <span style={{ color: 'var(--status-err-fg)', fontSize: 12.5 }}>{error}</span>}
      </div>
    </div>
  );
}


export default function UsersSection({ user }) {
  const [users, setUsers] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [error, setError] = useState('');

  const reload = () => {
    api('/api/admin/users').then((d) => setUsers(d.users)).catch((e) => setError(e.message));
  };
  useEffect(() => {
    reload();
    api('/api/admin/departments').then((d) => setDepartments(d.departments)).catch(() => {});
  }, []);

  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <SectionTitle sub={`Accounts belong to ${user.tenant_name} only. Department
            access controls what each user sees across budgets, transactions,
            insights, and AI analysis.`}>
            Users &amp; Access
          </SectionTitle>
        </div>
        <AddUser departments={departments} onCreated={reload} />
      </div>
      {error && <Msg error={error} />}
      {users === null ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '14px 0' }}>Loading…</div>
      ) : users.map((u) => (
        <UserRow key={u.username} u={u} departments={departments}
                 self={u.username === user.username} onSaved={reload} />
      ))}
    </div>
  );
}
