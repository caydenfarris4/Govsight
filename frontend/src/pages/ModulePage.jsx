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
    <Suspense fallback={
      <div className="text-muted" style={{ padding: 40 }}>Loading tool…</div>
    }>
      {children}
    </Suspense>
  );
}

// Sub-view toggle for composite tabs (Budget, Treasury) — the design
// system's segmented control; each sub-view is a real component.
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
      <div className="seg" style={{ marginBottom: 'var(--space-1)' }}>
        {subs.map((s) => (
          <label key={s.id} className="seg-opt">
            <input type="radio" name={storageKey} checked={s.id === active}
                   onChange={() => pick(s.id)} />
            {s.label}
          </label>
        ))}
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
    (() => <div className="text-muted" style={{ padding: 40 }}>Coming soon.</div>);

  const primaries = mod.tabs.filter((t) => !t.secondary);
  const secondaries = mod.tabs.filter((t) => t.secondary);
  const tabLink = (t) => {
    const i = mod.tabs.indexOf(t);
    const on = i === idx;
    return (
      <Link key={t.name} className="tab" aria-selected={on ? 'true' : 'false'}
            to={`/${moduleId}/${i}`}
            style={{ whiteSpace: 'nowrap', textDecoration: 'none' }}>
        {t.name}
      </Link>
    );
  };

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div className="module-head">
        <div className="module-head-inner">
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
            <h2 style={{ margin: 0, fontSize: 'var(--text-h3)' }}>{mod.name}</h2>
            <span className="kicker">{mod.tagline}</span>
          </div>
          <div className="tabs" style={{
            marginTop: 'var(--space-2)', overflowX: 'auto', alignItems: 'center',
          }}>
            {primaries.map(tabLink)}
            {secondaries.length > 0 && <span style={{ flex: 1 }} />}
            {secondaries.map(tabLink)}
          </div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <Body />
      </div>
    </div>
  );
}
