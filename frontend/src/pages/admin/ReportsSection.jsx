import React, { useEffect, useState } from 'react';
import { api } from '../../api.js';
import { Badge, Msg, SectionTitle, Table, btn, btnGhost, card, input } from './shared.jsx';

const REPORTS = {
  Vatica: ['Historical Analysis', 'Department Insights', 'Transaction Analyzer', 'Balance Sheet'],
  Navi: ['Scenario Planner', 'Economic Intelligence', 'Position-Based Budget'],
  Mantis: ['AI Insights', 'Anomaly Detection', 'Grant Discovery'],
};

function AddSchedule({ onDone }) {
  const [open, setOpen] = useState(false);
  const [module, setModule] = useState('Vatica');
  const [report, setReport] = useState(REPORTS.Vatica[0]);
  const [frequency, setFrequency] = useState('monthly');
  const [time, setTime] = useState('06:00');
  const [error, setError] = useState('');

  const create = async () => {
    setError('');
    try {
      await api('/api/admin/reports/schedules', {
        method: 'POST',
        body: JSON.stringify({ module, report_name: report,
                               frequency, schedule_time: time }),
      });
      setOpen(false);
      onDone();
    } catch (e) { setError(e.message); }
  };

  if (!open) return <button style={btn} onClick={() => setOpen(true)}>Add schedule</button>;
  return (
    <div style={{ padding: 12, background: '#fafbfc', border: '1px solid #eef2f5', borderRadius: 8 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <select style={input} value={module}
                onChange={(e) => { setModule(e.target.value); setReport(REPORTS[e.target.value][0]); }}>
          {Object.keys(REPORTS).map((m) => <option key={m}>{m}</option>)}
        </select>
        <select style={input} value={report} onChange={(e) => setReport(e.target.value)}>
          {REPORTS[module].map((r) => <option key={r}>{r}</option>)}
        </select>
        <select style={input} value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          {['daily', 'weekly', 'monthly', 'quarterly'].map((f) => <option key={f}>{f}</option>)}
        </select>
        <input style={input} type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        <button style={btn} onClick={create}>Create</button>
        <button style={btnGhost} onClick={() => setOpen(false)}>Cancel</button>
      </div>
      {error && <div style={{ color: '#a4271c', fontSize: 12.5, marginTop: 6 }}>{error}</div>}
    </div>
  );
}

export default function ReportsSection() {
  const [schedules, setSchedules] = useState([]);
  const [history, setHistory] = useState([]);
  const [archive, setArchive] = useState([]);
  const [error, setError] = useState('');

  const reload = () => {
    api('/api/admin/reports/schedules').then((d) => setSchedules(d.schedules)).catch((e) => setError(e.message));
    api('/api/admin/reports/history').then((d) => setHistory(d.history)).catch(() => {});
    api('/api/admin/archive').then((d) => setArchive(d.files)).catch(() => {});
  };
  useEffect(reload, []);

  const toggle = (s) => api(`/api/admin/reports/schedules/${s.id}`, {
    method: 'PUT', body: JSON.stringify({ enabled: !s.enabled }),
  }).then(reload).catch((e) => setError(e.message));
  const remove = (s) => api(`/api/admin/reports/schedules/${s.id}`, { method: 'DELETE' })
    .then(reload).catch((e) => setError(e.message));

  const fmtSize = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB`
    : b > 1024 ? `${(b / 1024).toFixed(0)} KB` : `${b} B`);

  return (
    <div style={card}>
      <SectionTitle sub="Recurring report generation and the archive of produced files.">
        Reports &amp; Archive
      </SectionTitle>
      <AddSchedule onDone={reload} />
      <div style={{ marginTop: 12 }}>
        <Table
          headers={['Module', 'Report', 'Frequency', 'Time', 'Status', '', '']}
          rows={schedules.map((s) => [
            s.module, s.report_name, s.frequency, s.schedule_time,
            <Badge key="b" tone={s.enabled ? 'green' : 'gray'}>
              {s.enabled ? 'ENABLED' : 'PAUSED'}
            </Badge>,
            <button key="t" style={{ ...btnGhost, padding: '4px 12px', fontSize: 12 }}
                    onClick={() => toggle(s)}>{s.enabled ? 'Pause' : 'Resume'}</button>,
            <button key="d" style={{ ...btnGhost, padding: '4px 12px', fontSize: 12, color: '#a4271c' }}
                    onClick={() => remove(s)}>Delete</button>,
          ])}
        />
      </div>
      {history.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <SectionTitle>Execution history</SectionTitle>
          <Table
            headers={['Report', 'Executed', 'Status', 'File / error']}
            rows={history.map((h) => [
              `${h.module || ''} ${h.report_name || ''}`,
              (h.execution_time || '').replace('T', ' ').slice(0, 19),
              <Badge key="s" tone={h.status === 'success' ? 'green' : 'red'}>{h.status}</Badge>,
              h.file_path || h.error_message || '',
            ])}
          />
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <SectionTitle sub="Files produced by report runs and scenario exports.">
          Archive
        </SectionTitle>
        <Table
          headers={['File', 'Size', 'Modified', '']}
          right={[1]}
          rows={archive.map((f) => [
            f.name, fmtSize(f.size),
            new Date(f.modified * 1000).toLocaleString(),
            <a key="dl" href={`/api/admin/archive/download?name=${encodeURIComponent(f.name)}`}
               style={{ fontSize: 12.5, fontWeight: 600 }}>Download</a>,
          ])}
        />
      </div>
      <Msg error={error} />
    </div>
  );
}
