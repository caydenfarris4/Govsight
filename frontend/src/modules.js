// Module and tab registry. Mirrors the focused four-tab Navi layout;
// phase-2 entries stay commented out exactly like the platform flag.
export const MODULES = {
  navi: {
    name: 'Navi',
    tagline: 'Navigation & Planning Hub',
    tabs: [
      { name: 'Scenario Planner', component: 'ScenarioPlanner' },
      { name: 'Budget', component: 'BudgetHub' },
      { name: 'Personnel', component: 'Personnel' },
      { name: 'Treasury', component: 'TreasuryHub' },
      { name: 'Market Context', component: 'MarketContext', secondary: true },
      // { name: 'Report Comparison', component: 'ReportComparison' },
      // { name: 'Risk Analysis', component: 'RiskAnalysis' },
      // { name: 'Predictive Analytics', component: 'Predictive' },
    ],
  },
  mantis: {
    name: 'Mantis',
    tagline: 'AI Intelligence Hub',
    tabs: [
      { name: 'AI Chat', component: 'MantisChat' },
      { name: 'Ledger Insights', component: 'LedgerInsights' },
    ],
  },
  vatica: {
    name: 'Vatica',
    tagline: 'Departmental Insights & Reporting',
    tabs: [
      { name: 'BI Sandbox', component: 'BISandbox' },
      { name: 'Historical Analysis', component: 'Historical' },
      { name: 'Department Insights', component: 'DeptInsights' },
      { name: 'Transaction Analyzer', component: 'Transactions' },
      { name: 'Balance Sheet', component: 'BalanceSheet' },
      { name: 'Monthly Close', component: 'MonthlyClose' },
    ],
  },
};
