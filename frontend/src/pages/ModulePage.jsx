import React, { Suspense, lazy, useEffect } from 'react';
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom';
import { MODULES } from '../modules.js';
import { rememberVisit } from '../navState.js';
import VendorView from '../components/VendorView.jsx';
import InvestmentOptimizer from '../components/InvestmentOptimizer.jsx';
import MantisChat from './MantisChat.jsx';

// The two big embedded tools are code-split so the initial bundle stays lean
const ScenarioPlannerApp = lazy(() => import('../tools/ScenarioPlannerApp.jsx'));
const BudgetPlaygroundApp = lazy(() => import('../tools/BudgetPlaygroundApp.jsx'));

function ToolSkeleton() {
  return (
    <div style={{ padding: 'var(--space-6) var(--space-4)', maxWidth: 1240, margin: '0 auto' }}
         aria-hidden="true">
      <div className="skeleton" style={{ height: 52, marginBottom: 'var(--space-3)' }} />
      <div className="skeleton" style={{ height: 34, width: '55%', marginBottom: 'var(--space-4)' }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        <div className="skeleton" style={{ height: 280 }} />
        <div className="skeleton" style={{ height: 280 }} />
      </div>
    </div>
  );
}

function ToolFrame({ children }) {
  return <Suspense fallback={<ToolSkeleton />}>{children}</Suspense>;
}

// Sub-view toggle for composite tabs (Budget, Treasury). The active
// sub-view lives in the URL (?sub=) so views are linkable and survive
// reload; sessionStorage only remembers the choice across navigations.
function HubToggle({ storageKey, subs }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const fromUrl = searchParams.get('sub');
  let active = subs.some((s) => s.id === fromUrl) ? fromUrl : null;
  if (!active) {
    try {
      const saved = sessionStorage.getItem(storageKey);
      if (subs.some((s) => s.id === saved)) active = saved;
    } catch { /* ignore */ }
  }
  if (!active) active = subs[0].id;

  const pick = (id) => {
    setSearchParams({ sub: id }, { replace: true });
    try { sessionStorage.setItem(storageKey, id); } catch { /* ignore */ }
  };
  const current = subs.find((s) => s.id === active) || subs[0];
  return (
    <div style={{ padding: '16px 20px 0', maxWidth: 1240, margin: '0 auto', width: '100%' }}>
      <div className="seg" role="group" aria-label="Sub-views"
           style={{ marginBottom: 'var(--space-1)' }}>
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

  const idx = mod
    ? Math.min(Math.max(parseInt(tabIndex || '0', 10) || 0, 0), mod.tabs.length - 1)
    : 0;
  const tab = mod ? mod.tabs[idx] : null;

  useEffect(() => {
    if (!mod || !tab) return;
    document.title = `GovSight — ${mod.name} · ${tab.name}`;
    rememberVisit(moduleId, idx, tab.name);
  }, [moduleId, idx, mod, tab]);

  if (!mod) return <Navigate to="/" replace />;

  const Body = COMPONENTS[tab.component] ||
    (() => <div className="text-muted" style={{ padding: 40 }}>Coming soon.</div>);

  const primaries = mod.tabs.filter((t) => !t.secondary);
  const secondaries = mod.tabs.filter((t) => t.secondary);
  const tabLink = (t) => {
    const i = mod.tabs.indexOf(t);
    const on = i === idx;
    return (
      <Link key={t.name} className="tab" aria-current={on ? 'page' : undefined}
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
          <nav className="tabs" aria-label={`${mod.name} sections`} style={{
            marginTop: 'var(--space-2)', overflowX: 'auto', alignItems: 'center',
          }}>
            {primaries.map(tabLink)}
            {secondaries.length > 0 && <span style={{ flex: 1 }} />}
            {secondaries.map(tabLink)}
          </nav>
        </div>
      </div>
      {/* key resets scroll position when switching tabs */}
      <div key={`${moduleId}/${idx}`} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <Body />
      </div>
    </div>
  );
}
