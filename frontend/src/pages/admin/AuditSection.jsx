import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Msg, SectionTitle, Table, btnGhost, card, input } from './shared.jsx';

// This city's administrative ledger: sign-ins, permission changes,
// data source activity, policy edits - who, what, when, from where.
export default function AuditSection() {
  const [events, setEvents] = useState([]);
  const [actions, setActions] = useState([]);
  const [action, setAction] = useState('');
  const [error, setError] = useState('');

  const reload = (a = action) => {
    api(`/api/admin/audit?limit=200${a ? `&action=${encodeURIComponent(a)}` : ''}`)
      .then((d) => { setEvents(d.events); setActions(d.actions); })
      .catch((e) => setError(e.message));
  };
  useEffect(() => reload(''), []);

  const fmtDetails = (d) => {
    const entries = Object.entries(d || {});
    if (!entries.length) return '';
    return entries.map(([k, v]) => `${k}: ${
      typeof v === 'object' ? JSON.stringify(v) : v}`).join(', ').slice(0, 140);
  };

  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <SectionTitle sub="Every administrative action in this city - sign-ins,
            permission changes, data syncs, policy edits.">
            Audit Log
          </SectionTitle>
        </div>
        <select style={input} value={action}
                onChange={(e) => { setAction(e.target.value); reload(e.target.value); }}>
          <option value="">All actions</option>
          {actions.map((a) => <option key={a}>{a}</option>)}
        </select>
        <a href="/api/admin/audit/export.csv"
           style={{ ...btnGhost, textDecoration: 'none', display: 'inline-block' }}>
          Export CSV
        </a>
      </div>
      <Table
        headers={['When', 'Who', 'Action', 'Target', 'Details']}
        rows={events.map((e) => [
          new Date(e.ts * 1000).toLocaleString(),
          e.actor, e.action, e.target, fmtDetails(e.details),
        ])}
      />
      <Msg error={error} />
    </div>
  );
}
