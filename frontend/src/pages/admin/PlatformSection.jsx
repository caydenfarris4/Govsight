import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Badge, Msg, SectionTitle, btn, btnGhost, card, input } from './shared.jsx';

// Platform administration (GovSight staff): create cities and manage
// the platform-wide AI provider keys. Each city is fully siloed.

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

function AIKeyRow({ provider, label, status, onChanged }) {
  const [key, setKey] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true); setMsg(''); setErr('');
    try {
      await api('/api/admin/ai-keys', {
        method: 'PUT', body: JSON.stringify({ provider, key }),
      });
      setKey(''); setMsg('Key saved (encrypted). Live immediately.');
      onChanged();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };
  const test = async () => {
    setBusy(true); setMsg(''); setErr('');
    try {
      const r = await api('/api/admin/ai-keys/test', {
        method: 'POST', body: JSON.stringify({ provider, key: key || null }),
      });
      (r.valid ? setMsg : setErr)(r.message);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };
  const remove = async () => {
    setBusy(true); setMsg(''); setErr('');
    try {
      await api(`/api/admin/ai-keys/${provider}`, { method: 'DELETE' });
      setMsg('Key removed.');
      onChanged();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ borderTop: '1px solid #eef2f5', padding: '10px 0' }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, fontSize: 14, minWidth: 90 }}>{label}</span>
        {status?.configured
          ? <Badge tone="green">CONFIGURED{status.partial_hash ? ` - ${status.partial_hash}` : ''}</Badge>
          : <Badge tone="amber">NOT CONFIGURED</Badge>}
        <input style={{ ...input, flex: 1, minWidth: 220 }} type="password"
               placeholder={`New ${label} API key`} value={key}
               onChange={(e) => setKey(e.target.value)} />
        <button style={btn} disabled={busy || !key} onClick={save}>Save</button>
        <button style={btnGhost} disabled={busy || (!key && !status?.configured)}
                onClick={test}>Test</button>
        {status?.configured && (
          <button style={{ ...btnGhost, color: '#a4271c' }} disabled={busy}
                  onClick={remove}>Remove</button>
        )}
      </div>
      {(msg || err) && (
        <div style={{ fontSize: 12.5, marginTop: 6,
                      color: err ? '#a4271c' : '#1e6b3c' }}>{err || msg}</div>
      )}
    </div>
  );
}

export default function PlatformSection() {
  const [tenants, setTenants] = useState([]);
  const [keys, setKeys] = useState({});
  const [error, setError] = useState('');

  const reload = () => {
    api('/api/admin/tenants').then((d) => setTenants(d.tenants)).catch((e) => setError(e.message));
    api('/api/admin/ai-keys').then(setKeys).catch(() => {});
  };
  useEffect(reload, []);

  return (
    <div>
      <div style={card}>
        <SectionTitle sub={`${tenants.length} cit${tenants.length === 1 ? 'y' : 'ies'} on this
          deployment. Each city has its own isolated databases, users, permissions, and
          data source - nothing is shared between cities.`}>
          Cities
        </SectionTitle>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {tenants.map((t) => (
            <Badge key={t.id} tone={t.active ? 'blue' : 'gray'}>
              {t.name}{t.state ? `, ${t.state}` : ''}
            </Badge>
          ))}
        </div>
        <CreateCity onCreated={reload} />
        <Msg error={error} />
      </div>
      <div style={card}>
        <SectionTitle sub={`Platform-wide provider keys powering Mantis chat, AI insights,
          field-mapping proposals, and grant intelligence for every city. Stored encrypted
          on the server; never in the browser or the repository.`}>
          AI Provider Keys
        </SectionTitle>
        <AIKeyRow provider="anthropic" label="Anthropic" status={keys.anthropic} onChanged={reload} />
        <AIKeyRow provider="openai" label="OpenAI" status={keys.openai} onChanged={reload} />
      </div>
    </div>
  );
}
