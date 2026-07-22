import React, { Suspense, lazy, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { MODULES } from '../modules.js';
import VendorView from '../components/VendorView.jsx';
import InvestmentOptimizer from '../components/InvestmentOptimizer.jsx';
import MantisChat from './MantisChat.jsx';

// The two big embedded tools are code-split so the initial bundle stays lean
const ScenarioPlannerApp = lazy(() => import('../tools/ScenarioPlannerApp.jsx'));
const BudgetPlaygroundApp = lazy(() => import('../tools/BudgetPlaygroundApp.jsx'));

function ToolFrame({ children }) {
  return (
    <Suspense fallback={<div style={{ padding: 40, color: '#5b6b7a' }}>Loading tool…</div>}>
      {children}
    </Suspense>
  );
}

// Sub-view toggle for composite tabs (Budget, Treasury) — mirrors the
// static shell's hub pills, but each sub-view is a real component.
function HubToggle({ storageKey, subs }) {
  const [active, setActive] = useState(() => {
    try {
      const saved = sessionStorage.getItem(storageKey);
      if (subs.some((s) => s.id === saved)) return saved;
    } catch { /* ignore */ }
    return subs[0].id;
  });
  const pick = (id) => {
    setActive(id);
    try { sessionStorage.setItem(storageKey, id); } catch { /* ignore */ }
  };
  const current = subs.find((s) => s.id === active) || subs[0];
  return (
    <div style={{ padding: '16px 20px 0', maxWidth: 1240, margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
        {subs.map((s) => {
          const on = s.id === active;
          return (
            <button key={s.id} onClick={() => pick(s.id)} style={{
              padding: '7px 16px', borderRadius: 99, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', border: `1px solid ${on ? '#12263a' : '#cfd8e0'}`,
              background: on ? '#12263a' : '#fff', color: on ? '#fff' : '#5b6b7a',
            }}>{s.label}</button>
          );
        })}
      </div>
      <div key={current.id}>{current.render()}</div>
    </div>
  );
}

const COMPONENTS = {
  ScenarioPlanner: () => (
    <ToolFrame><ScenarioPlannerApp /></ToolFrame>
  ),
  BudgetHub: () => (
    <HubToggle storageKey="gs_hub_budget" subs={[
      { id: 'playground', label: 'Ledger & Scenarios',
        render: () => <ToolFrame><BudgetPlaygroundApp /></ToolFrame> },
      { id: 'forecast', label: 'Revenue Forecast',
        render: () => <VendorView view="predictive" /> },
    ]} />
  ),
  Personnel: () => <VendorView view="pbb" />,
  TreasuryHub: () => (
    <HubToggle storageKey="gs_hub_treasury" subs={[
      { id: 'cashflow', label: 'Cash Flow',
        render: () => <VendorView view="cashflow" /> },
      { id: 'optimizer', label: 'Investment Optimizer',
        render: () => <InvestmentOptimizer /> },
    ]} />
  ),
  MarketContext: () => <VendorView view="econ" />,
  // Phase-2 components, kept registered for when their tabs are re-enabled
  ReportComparison: () => <VendorView view="reportComparison" />,
  RiskAnalysis: () => <VendorView view="risk" />,
  Predictive: () => <VendorView view="predictive" />,

  MantisChat: () => <MantisChat />,
  LedgerInsights: () => <VendorView view="mantisDemo" />,

  BISandbox: () => <VendorView view="bi" />,
  Historical: () => <VendorView view="historical" />,
  DeptInsights: () => <VendorView view="deptInsights" />,
  Transactions: () => <VendorView view="transactions" />,
  BalanceSheet: () => <VendorView view="balance" />,
  MonthlyClose: () => <VendorView view="close" />,
};

export default function ModulePage() {
  const { moduleId, tabIndex } = useParams();
  const mod = MODULES[moduleId];
  if (!mod) return <Navigate to="/" replace />;

  const idx = Math.min(Math.max(parseInt(tabIndex || '0', 10) || 0, 0), mod.tabs.length - 1);
  const tab = mod.tabs[idx];
  const Body = COMPONENTS[tab.component] ||
    (() => <div style={{ padding: 40, color: '#5b6b7a' }}>Coming soon.</div>);

  const primaries = mod.tabs.filter((t) => !t.secondary);
  const secondaries = mod.tabs.filter((t) => t.secondary);
  const tabLink = (t) => {
    const i = mod.tabs.indexOf(t);
    const on = i === idx;
    return (
      <Link key={t.name} to={`/${moduleId}/${i}`} style={{
        padding: '9px 16px', fontSize: 13.5, textDecoration: 'none',
        fontWeight: on ? 700 : (t.secondary ? 500 : 600),
        color: on ? '#12263a' : (t.secondary ? '#8fa1b0' : '#5b6b7a'),
        borderBottom: on ? '3px solid ' + mod.color : '3px solid transparent',
        whiteSpace: 'nowrap',
      }}>{t.name}</Link>
    );
  };

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ background: '#fff', borderBottom: '1px solid #e3e9ee', flexShrink: 0 }}>
        <div style={{
          maxWidth: 1240, margin: '0 auto', padding: '14px 20px 0', width: '100%',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <h1 style={{ fontSize: 19, color: mod.color, margin: 0 }}>
              GovSight {mod.name}
            </h1>
            <span style={{ fontSize: 13, color: '#8fa1b0' }}>{mod.tagline}</span>
          </div>
          <div style={{
            display: 'flex', gap: 4, marginTop: 8, alignItems: 'center',
            overflowX: 'auto',
          }}>
            {primaries.map(tabLink)}
            {secondaries.length > 0 && <span style={{ flex: 1 }} />}
            {secondaries.map(tabLink)}
          </div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: '#f4f6f8' }}>
        <Body />
      </div>
    </div>
  );
}
