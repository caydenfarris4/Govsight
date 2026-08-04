import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Badge, Msg, SectionTitle, Table, btn, btnGhost, card, input } from './shared.jsx';

// The ERP connection IS the data source: register it once, approve the
// AI-proposed field mapping into the canonical schema, and every sync
// lands in this city's own database - which is exactly what the data
// bundle, every module, and the AI read.

function AddSource({ onDone }) {
  const [mode, setMode] = useState('');
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [recordsKey, setRecordsKey] = useState('');
  const [tokenEnv, setTokenEnv] = useState('');
  const [muni, setMuni] = useState('');
  const [dataset, setDataset] = useState('general_ledger');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true); setError('');
    try {
      if (mode === 'csv') {
        const fd = new FormData();
        fd.append('name', name);
        fd.append('file', file);
        const resp = await fetch('/api/admin/datasource/upload-csv',
                                 { method: 'POST', body: fd, credentials: 'same-origin' });
        if (!resp.ok) throw new Error((await resp.json()).detail || 'Upload failed');
      } else {
        const config = mode === 'rest_api'
          ? { endpoint, records_key: recordsKey || undefined,
              token_env: tokenEnv || undefined }
          : { municipality_id: muni, dataset };
        await api('/api/admin/datasource/sources', {
          method: 'POST',
          body: JSON.stringify({ name, source_type: mode, config }),
        });
      }
      setMode(''); setName(''); setEndpoint(''); setFile(null);
      onDone();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  if (!mode) {
    return (
      <div style={{ display: 'flex', gap: 8 }}>
        <button style={btn} onClick={() => setMode('rest_api')}>Connect ERP API</button>
        <button style={btnGhost} onClick={() => setMode('caselle')}>Connect Caselle</button>
        <button style={btnGhost} onClick={() => setMode('csv')}>Upload CSV</button>
      </div>
    );
  }
  return (
    <div style={{ padding: 14, background: '#fafbfc', border: '1px solid #eef2f5', borderRadius: 8 }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
        <input style={input} placeholder="Source name (e.g. Tyler Munis GL)"
               value={name} onChange={(e) => setName(e.target.value)} />
        {mode === 'rest_api' && (<>
          <input style={{ ...input, minWidth: 280 }} placeholder="API endpoint URL"
                 value={endpoint} onChange={(e) => setEndpoint(e.target.value)} />
          <input style={input} placeholder="Record list key (optional)"
                 value={recordsKey} onChange={(e) => setRecordsKey(e.target.value)} />
          <input style={input} placeholder="Token env var (optional)"
                 value={tokenEnv} onChange={(e) => setTokenEnv(e.target.value)} />
        </>)}
        {mode === 'caselle' && (<>
          <input style={input} placeholder="Municipality id"
                 value={muni} onChange={(e) => setMuni(e.target.value)} />
          <select style={input} value={dataset} onChange={(e) => setDataset(e.target.value)}>
            {['general_ledger', 'budget', 'payroll', 'accounts_payable',
              'vendors', 'departments'].map((d) => <option key={d}>{d}</option>)}
          </select>
        </>)}
        {mode === 'csv' && (
          <input type="file" accept=".csv" style={{ fontSize: 13 }}
                 onChange={(e) => setFile(e.target.files[0])} />
        )}
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button style={btn} disabled={busy || !name || (mode === 'csv' && !file) ||
                                      (mode === 'rest_api' && !endpoint)}
                onClick={submit}>Add source</button>
        <button style={btnGhost} onClick={() => setMode('')}>Cancel</button>
        {error && <span style={{ color: '#a4271c', fontSize: 12.5 }}>{error}</span>}
      </div>
      <div style={{ fontSize: 11.5, color: '#8a97a3', marginTop: 8 }}>
        Credentials are never stored: API sources read their token from a named
        environment variable on the server.
      </div>
    </div>
  );
}

function MappingWorkflow({ source, entities, onDone }) {
  const [entity, setEntity] = useState(entities[0] || '');
  const [proposal, setProposal] = useState(null);
  const [mappingId, setMappingId] = useState(null);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);

  const propose = async () => {
    setBusy(true); setError(''); setOk(''); setProposal(null);
    try {
      const r = await api('/api/admin/datasource/propose', {
        method: 'POST',
        body: JSON.stringify({ source_id: source.id, entity }),
      });
      setProposal(r.proposal);
      setMappingId(r.mapping_id);
      setRows(r.proposal.mappings || []);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const approve = async () => {
    setBusy(true); setError(''); setOk('');
    try {
      await api('/api/admin/datasource/approve', {
        method: 'POST',
        body: JSON.stringify({ mapping_id: mappingId, mappings: rows }),
      });
      setOk('Mapping approved. You can now run a sync.');
      setProposal(null);
      onDone();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const setRow = (i, key, value) => {
    setRows(rows.map((r, j) => (j === i ? { ...r, [key]: value } : r)));
  };

  return (
    <div style={{ marginTop: 10, padding: 12, background: '#fafbfc',
                  border: '1px solid #eef2f5', borderRadius: 8 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: '#5b6b7a' }}>Map into</span>
        <select style={input} value={entity} onChange={(e) => setEntity(e.target.value)}>
          {entities.map((e2) => <option key={e2}>{e2}</option>)}
        </select>
        <button style={btnGhost} disabled={busy} onClick={propose}>
          {busy ? 'Working…' : 'Propose mapping (AI)'}
        </button>
      </div>
      {proposal && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#5b6b7a', marginBottom: 6 }}>
            Review the proposed field mapping - edit source fields or transforms,
            then approve. {proposal.notes ? proposal.notes : ''}
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
              <thead><tr>
                {['Canonical field', 'Source field', 'Transform', 'Confidence'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 8px',
                                       borderBottom: '2px solid #dde4ea',
                                       color: '#5b6b7a', fontSize: 11.5 }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {rows.map((m, i) => (
                  <tr key={i}>
                    <td style={{ padding: '4px 8px', fontWeight: 600 }}>{m.target}</td>
                    <td style={{ padding: '4px 8px' }}>
                      <input style={{ ...input, padding: '5px 8px', fontSize: 12.5 }}
                             value={Array.isArray(m.source)
                               ? m.source.join(', ') : (m.source || '')}
                             onChange={(e) => setRow(i, 'source',
                               Array.isArray(m.source)
                                 ? e.target.value.split(',').map((s) => s.trim())
                                 : e.target.value)} />
                    </td>
                    <td style={{ padding: '4px 8px' }}>{m.transform || 'direct'}</td>
                    <td style={{ padding: '4px 8px' }}>
                      {m.confidence !== undefined ? `${Math.round(m.confidence * 100)}%` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(proposal.unmapped_required || []).length > 0 && (
            <div style={{ fontSize: 12, color: '#8a5a12', marginTop: 6 }}>
              Unmapped required fields: {proposal.unmapped_required.join(', ')}
            </div>
          )}
          <button style={{ ...btn, marginTop: 10 }} disabled={busy} onClick={approve}>
            Approve mapping
          </button>
        </div>
      )}
      <Msg error={error} ok={ok} />
    </div>
  );
}

export default function DataSourceSection() {
  const [data, setData] = useState({ sources: [], entities: [] });
  const [history, setHistory] = useState([]);
  const [openMap, setOpenMap] = useState(null);
  const [error, setError] = useState('');
  const [syncMsg, setSyncMsg] = useState('');

  const reload = () => {
    api('/api/admin/datasource/sources').then(setData).catch((e) => setError(e.message));
    api('/api/admin/datasource/history').then((d) => setHistory(d.runs)).catch(() => {});
  };
  useEffect(reload, []);

  const sync = async (source, entity) => {
    setSyncMsg('');
    try {
      const r = await api('/api/admin/datasource/sync', {
        method: 'POST',
        body: JSON.stringify({ source_name: source.name, entity }),
      });
      const res = r.result;
      setSyncMsg(`Synced ${source.name} -> ${entity}: ${res.succeeded} of ${res.total} rows` +
                 (res.failed ? ` (${res.failed} failed)` : '') +
                 '. The data bundle and all modules now reflect this data.');
      reload();
    } catch (e) { setSyncMsg(`Sync failed: ${e.message}`); }
  };

  return (
    <div style={card}>
      <SectionTitle sub={`Your ERP connection is this city's data source. Register it,
        approve the AI field mapping into GovSight's canonical schema, and each sync
        writes to this city's own database - the same data every module, report, and
        AI feature reads. No separate connection managers.`}>
        Data Source (ERP)
      </SectionTitle>
      <AddSource onDone={reload} />
      {data.sources.map((s) => (
        <div key={s.id} style={{ borderTop: '1px solid #eef2f5', padding: '10px 0', marginTop: 10 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>{s.name}</span>
            <Badge tone="gray">{s.source_type}</Badge>
            {(s.approved_entities || []).map((e) => (
              <Badge key={e} tone="green">mapped: {e}</Badge>
            ))}
            <span style={{ flex: 1 }} />
            {(s.approved_entities || []).map((e) => (
              <button key={e} style={btnGhost} onClick={() => sync(s, e)}>
                Sync {e}
              </button>
            ))}
            <button style={btnGhost}
                    onClick={() => setOpenMap(openMap === s.id ? null : s.id)}>
              {openMap === s.id ? 'Close mapping' : 'Field mapping'}
            </button>
          </div>
          {openMap === s.id && (
            <MappingWorkflow source={s} entities={data.entities} onDone={reload} />
          )}
        </div>
      ))}
      {syncMsg && <Msg ok={!syncMsg.startsWith('Sync failed') ? syncMsg : ''}
                       error={syncMsg.startsWith('Sync failed') ? syncMsg : ''} />}
      <Msg error={error} />
      {history.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <SectionTitle>Sync history</SectionTitle>
          <Table
            headers={['Source', 'Entity', 'Started', 'Rows', 'Failed', 'Status']}
            right={[3, 4]}
            rows={history.map((h) => [
              h.source_name, h.entity,
              (h.started_at || '').replace('T', ' ').slice(0, 19),
              h.succeeded ?? '', h.failed ?? '',
              <Badge key="s" tone={h.status === 'ok' ? 'green' : 'red'}>
                {h.status || '-'}
              </Badge>,
            ])}
          />
        </div>
      )}
    </div>
  );
}
