import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MODULES } from '../modules.js';
import { lastPlace, lastTab } from '../navState.js';

const MODULE_ICONS = {
  navi: 'ph-duotone ph-compass',
  mantis: 'ph-duotone ph-sparkle',
  vatica: 'ph-duotone ph-chart-bar',
};

const TAB_ICONS = {
  'Scenario Planner': 'ph-duotone ph-flow-arrow',
  Budget: 'ph-duotone ph-wallet',
  Personnel: 'ph-duotone ph-users-three',
  Treasury: 'ph-duotone ph-bank',
  'Market Context': 'ph-duotone ph-globe-hemisphere-west',
  'AI Chat': 'ph-duotone ph-chats-circle',
  'Ledger Insights': 'ph-duotone ph-lightbulb',
  'BI Sandbox': 'ph-duotone ph-chart-scatter',
  'Historical Analysis': 'ph-duotone ph-clock-counter-clockwise',
  'Department Insights': 'ph-duotone ph-buildings',
  'Transaction Analyzer': 'ph-duotone ph-magnifying-glass',
  'Balance Sheet': 'ph-duotone ph-scales',
  'Monthly Close': 'ph-duotone ph-calendar-check',
};

export default function Dashboard({ user }) {
  const navigate = useNavigate();
  const resume = lastPlace();

  useEffect(() => { document.title = 'GovSight — Overview'; }, []);

  return (
    <div style={{
      maxWidth: 1080, margin: '0 auto', width: '100%',
      padding: 'var(--space-8) var(--space-4) var(--space-12)',
    }}>
      <span className="kicker">Overview</span>
      <h1 style={{ marginTop: 'var(--space-1)' }}>
        Welcome back{user.username ? `, ${user.username}` : ''}.
      </h1>
      <p className="text-muted" style={{
        maxWidth: '52ch', fontSize: 'var(--text-lg)',
        marginBottom: resume ? 'var(--space-2)' : undefined,
      }}>
        Three modules over your ERP data. Jump straight to a tool, or open a
        module to browse.
      </p>
      {resume && MODULES[resume.moduleId] && (
        <Link className="resume-link" to={`/${resume.moduleId}/${resume.tabIndex}`}>
          <i className="ph-duotone ph-arrow-bend-up-right" aria-hidden="true" />
          Pick up where you left off — {MODULES[resume.moduleId].name}
          {resume.tabName ? ` · ${resume.tabName}` : ''}
        </Link>
      )}

      <div style={{
        display: 'grid', gap: 'var(--space-6)', marginTop: 'var(--space-8)',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
      }}>
        {Object.entries(MODULES).map(([id, m]) => (
          <section key={id} className="dir-col" aria-label={m.name}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              marginBottom: 'var(--space-1)',
            }}>
              <i className={MODULE_ICONS[id] || 'ph-duotone ph-squares-four'}
                 style={{ fontSize: 26, color: 'var(--color-cardinal)' }}
                 aria-hidden="true" />
              <h3 style={{ margin: 0 }}>{m.name}</h3>
            </div>
            <p className="text-muted" style={{ margin: '0 0 var(--space-2)', fontSize: 13 }}>
              {m.tagline}
            </p>
            <ul className="dir-links">
              {m.tabs.map((t, i) => (
                <li key={t.name}>
                  <Link to={`/${id}/${i}`}>
                    <i className={TAB_ICONS[t.name] || 'ph-duotone ph-arrow-right'}
                       aria-hidden="true" />
                    {t.name}
                  </Link>
                </li>
              ))}
            </ul>
            <div style={{ marginTop: 'var(--space-2)' }}>
              <Link to={`/${id}/${lastTab(id)}`} className="btn btn-secondary btn-sm">
                Open {m.name}
              </Link>
            </div>
          </section>
        ))}
      </div>

      {user.role === 'admin' && (
        <div className="panel-ink" style={{
          marginTop: 'var(--space-12)', padding: 'var(--space-6)',
          display: 'flex', alignItems: 'center', gap: 'var(--space-6)', flexWrap: 'wrap',
        }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <span className="kicker">Administration</span>
            <h3 style={{ margin: 'var(--space-1) 0 var(--space-1)' }}>
              Run the platform
            </h3>
            <p style={{ margin: 0, fontSize: 14, opacity: 0.75 }}>
              User management, ERP connections, AI data mapping, and system
              settings.
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/admin')}>
            Open admin settings
          </button>
        </div>
      )}
    </div>
  );
}
