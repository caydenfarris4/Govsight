import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Msg, SectionTitle, btn, card, input } from './shared.jsx';

// City Profile: the single source of "which city is this". Feeds the
// data bundle's city block - Economic Indicators (Census FIPS, weather
// coordinates), branding, and AI context.
export default function CityProfileSection({ user }) {
  const [fields, setFields] = useState([]);
  const [form, setForm] = useState({});
  const [effective, setEffective] = useState({});
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/api/admin/city-profile').then((d) => {
      setFields(d.fields);
      setForm(d.profile || {});
      setEffective(d.effective || {});
    }).catch((e) => setError(e.message));
  }, []);

  const save = async () => {
    setBusy(true); setError(''); setOk('');
    try {
      const r = await api('/api/admin/city-profile',
                          { method: 'PUT', body: JSON.stringify(form) });
      setForm(r.profile);
      setOk('Saved. Economic Indicators, branding, and AI context now use this profile.');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div style={card}>
      <SectionTitle sub={`Everything city-specific reads from here: the Economic
        Indicators page localizes to the Census place (state + place FIPS) and
        weather coordinates below, reports carry the city name, and the AI
        assistant answers for this city.`}>
        City Profile - {user.tenant_name}
      </SectionTitle>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: 12,
      }}>
        {fields.map((f) => (
          <label key={f.key} style={{ fontSize: 12, fontWeight: 600, color: '#5b6b7a' }}>
            {f.label}
            <input
              style={{ ...input, display: 'block', width: '100%', marginTop: 4 }}
              type={f.kind === 'number' ? 'number' : 'text'}
              value={form[f.key] ?? ''}
              placeholder={effective[f.key] !== undefined ? String(effective[f.key]) : ''}
              onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
            />
          </label>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: '#8a97a3', marginTop: 10 }}>
        FIPS codes come from the US Census (census.gov geography reference); they are
        what make demographics, income, and housing data resolve to this exact city.
        Placeholder values show what is currently in effect.
      </div>
      <div style={{ marginTop: 12 }}>
        <button style={btn} disabled={busy} onClick={save}>Save profile</button>
      </div>
      <Msg error={error} ok={ok} />
    </div>
  );
}
