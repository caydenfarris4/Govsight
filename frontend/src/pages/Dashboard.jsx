import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MODULES } from '../modules.js';

const MODULE_ICONS = {
  navi: 'ph-duotone ph-compass',
  mantis: 'ph-duotone ph-sparkle',
  vatica: 'ph-duotone ph-chart-bar',
};

export default function Dashboard({ user }) {
  const navigate = useNavigate();
  return (
    <div style={{
      maxWidth: 1080, margin: '0 auto', width: '100%',
      padding: 'var(--space-8) var(--space-4) var(--space-12)',
    }}>
      <span className="kicker">Overview</span>
      <h1 style={{ marginTop: 'var(--space-1)' }}>
        Welcome back{user.username ? `, ${user.username}` : ''}.
      </h1>
      <p className="text-muted" style={{ maxWidth: '52ch', fontSize: 'var(--text-lg)' }}>
        Three modules over your ERP data. Pick where to start.
      </p>

      <div style={{
        display: 'grid', gap: 'var(--space-6)', marginTop: 'var(--space-8)',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
      }}>
        {Object.entries(MODULES).map(([id, m]) => (
          <div key={id} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <i className={MODULE_ICONS[id] || 'ph-duotone ph-squares-four'}
               style={{ fontSize: 30, color: 'var(--color-cardinal)' }} aria-hidden="true" />
            <h3 style={{ margin: 0 }}>{m.name}</h3>
            <p className="text-muted" style={{ margin: 0, fontSize: 14, flex: 1 }}>
              {m.tagline}
            </p>
            <div>
              <Link to={`/${id}/0`} className="btn btn-secondary">
                Enter {m.name} <i className="ph-duotone ph-arrow-right" aria-hidden="true" />
              </Link>
            </div>
          </div>
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
