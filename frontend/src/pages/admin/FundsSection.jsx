import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Badge, Msg, SectionTitle, btn, card, input } from './shared.jsx';

// GASB 54 fund classifications: the reallocation policy the scenario
// planner, Mantis, and the monthly close assistant all enforce.
export default function FundsSection() {
  const [data, setData] = useState(null);
  const [cls, setCls] = useState({});
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/api/admin/funds').then((d) => {
      setData(d);
      setCls(d.classifications || {});
    }).catch((e) => setError(e.message));
  }, []);

  const save = async () => {
    setBusy(true); setError(''); setOk('');
    try {
      await api('/api/admin/funds', { method: 'PUT', body: JSON.stringify(cls) });
      setOk('Saved. Reallocation eligibility is enforced platform-wide immediately.');
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  if (!data) return <div style={card}>Loading…</div>;
  const catNames = Object.keys(data.categories);

  const badgeFor = (fund) => {
    const cat = data.categories[cls[fund]];
    if (!cat) return <Badge tone="gray">Unclassified</Badge>;
    if (cat.eligible) return <Badge tone="green">Eligible for reallocation</Badge>;
    if (cat.requires_approval) return <Badge tone="amber">Requires approval</Badge>;
    return <Badge tone="red">Blocked from reallocation</Badge>;
  };

  return (
    <div style={card}>
      <SectionTitle sub={`Classify each fund under GASB Statement No. 54. This is
        live policy: the Scenario Planner blocks reallocations from restricted
        funds, the AI assistant respects it, and the monthly close review flags
        restricted-fund activity against it.`}>
        Fund Classifications (GASB 54)
      </SectionTitle>
      {data.funds.length === 0 && (
        <div style={{ fontSize: 13, color: '#8fa1b0' }}>
          No funds found yet - funds appear here once your data source has synced
          general ledger data.
        </div>
      )}
      {data.funds.map((f) => (
        <div key={f} style={{
          display: 'flex', gap: 12, alignItems: 'center',
          borderTop: '1px solid #eef2f5', padding: '9px 0',
        }}>
          <div style={{ minWidth: 160 }}>
            <span style={{ fontWeight: 700, fontSize: 13.5 }}>Fund {f}</span>
            {data.fund_names[f] && (
              <div style={{ fontSize: 12, color: '#5b6b7a' }}>{data.fund_names[f]}</div>
            )}
          </div>
          <select style={input} value={cls[f] || ''}
                  onChange={(e) => setCls({ ...cls, [f]: e.target.value })}>
            <option value="" disabled>Choose classification…</option>
            {catNames.map((c) => <option key={c}>{c}</option>)}
          </select>
          {badgeFor(f)}
          {cls[f] && data.categories[cls[f]] && (
            <span style={{ fontSize: 11.5, color: '#8a97a3' }}>
              {data.categories[cls[f]].reference}
            </span>
          )}
        </div>
      ))}
      {data.funds.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <button style={btn} disabled={busy} onClick={save}>Save classifications</button>
        </div>
      )}
      <Msg error={error} ok={ok} />
    </div>
  );
}
