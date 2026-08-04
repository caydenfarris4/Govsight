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
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 24px', width: '100%' }}>
      <h1 style={{ fontSize: 22, color: '#12263a', marginBottom: 2 }}>Administration</h1>
      <p style={{ color: '#5b6b7a', marginBottom: 18, fontSize: 14 }}>
        {user.tenant_name}
      </p>
      <div style={{ display: 'flex', gap: 22, alignItems: 'flex-start' }}>
        <nav style={{
          flexShrink: 0, width: 190, background: '#fff',
          border: '1px solid #e3e9ee', borderRadius: 10, padding: 8,
          position: 'sticky', top: 16,
        }}>
          {sections.map((s) => {
            const on = s.id === current.id;
            return (
              <button key={s.id} onClick={() => setActive(s.id)} style={{
                display: 'block', width: '100%', textAlign: 'left',
                background: on ? '#eef2f6' : 'none', border: 'none',
                borderLeft: on ? '3px solid #2450b8' : '3px solid transparent',
                borderRadius: 6, padding: '9px 12px', fontSize: 13.5,
                fontWeight: on ? 700 : 500, color: on ? '#12263a' : '#5b6b7a',
                cursor: 'pointer', marginBottom: 2,
              }}>{s.label}</button>
            );
          })}
        </nav>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Body user={user} />
        </div>
      </div>
    </div>
  );
}
