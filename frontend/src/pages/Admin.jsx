import React, { useState } from 'react';
import UsersSection from './admin/UsersSection.jsx';
import CityProfileSection from './admin/CityProfileSection.jsx';
import DataSourceSection from './admin/DataSourceSection.jsx';
import FundsSection from './admin/FundsSection.jsx';
import ReportsSection from './admin/ReportsSection.jsx';
import AuditSection from './admin/AuditSection.jsx';
import PlatformSection from './admin/PlatformSection.jsx';

// The unified admin: one owner per concern, grouped by what it drives.
//   Users & Access  -> who can sign in, what departments they see
//   City Profile    -> the city block (Economic Indicators, branding, AI)
//   Data Source     -> the ERP connection feeding this city's database
//   Fund Policy     -> GASB 54 reallocation policy, enforced platform-wide
//   Reports         -> schedules, history, and the file archive
//   Audit Log       -> this city's administrative ledger
//   Platform        -> cities and AI keys (platform admins only)

const SECTIONS = [
  { id: 'users', label: 'Users & Access', component: UsersSection },
  { id: 'city', label: 'City Profile', component: CityProfileSection },
  { id: 'datasource', label: 'Data Source (ERP)', component: DataSourceSection },
  { id: 'funds', label: 'Fund Policy', component: FundsSection },
  { id: 'reports', label: 'Reports & Archive', component: ReportsSection },
  { id: 'audit', label: 'Audit Log', component: AuditSection },
  { id: 'platform', label: 'Platform', component: PlatformSection, platformOnly: true },
];

export default function Admin({ user }) {
  const sections = SECTIONS.filter((s) => !s.platformOnly || user.is_platform_admin);
  const [active, setActive] = useState('users');
  const current = sections.find((s) => s.id === active) || sections[0];
  const Body = current.component;

  return (
    <div style={{
      maxWidth: 1100, margin: '0 auto', width: '100%',
      padding: 'var(--space-6) var(--space-4) var(--space-12)',
    }}>
      <span className="kicker">Administration</span>
      <h2 style={{ margin: 'var(--space-1) 0 0' }}>{user.tenant_name}</h2>
      <div style={{
        display: 'flex', gap: 'var(--space-6)', alignItems: 'flex-start',
        marginTop: 'var(--space-6)',
      }}>
        <nav className="adminnav" style={{ flexShrink: 0, width: 190 }}>
          {sections.map((s) => (
            <button key={s.id} onClick={() => setActive(s.id)}
                    aria-current={s.id === current.id ? 'true' : undefined}>
              {s.label}
            </button>
          ))}
        </nav>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Body user={user} />
        </div>
      </div>
    </div>
  );
}
