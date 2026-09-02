// Lightweight navigation memory: where the user last was, per module and
// globally, so entering a module resumes their place. sessionStorage only —
// per-tab convenience, never authoritative state (the URL carries state).
const LAST_TAB_PREFIX = 'gs_last_tab_';
const LAST_PLACE = 'gs_last_place';

export function rememberVisit(moduleId, tabIndex, tabName) {
  try {
    sessionStorage.setItem(LAST_TAB_PREFIX + moduleId, String(tabIndex));
    sessionStorage.setItem(LAST_PLACE,
      JSON.stringify({ moduleId, tabIndex, tabName, at: Date.now() }));
  } catch { /* private mode etc. */ }
}

export function lastTab(moduleId) {
  try {
    const v = parseInt(sessionStorage.getItem(LAST_TAB_PREFIX + moduleId), 10);
    return Number.isFinite(v) ? v : 0;
  } catch { return 0; }
}

export function lastPlace() {
  try { return JSON.parse(sessionStorage.getItem(LAST_PLACE)); }
  catch { return null; }
}
