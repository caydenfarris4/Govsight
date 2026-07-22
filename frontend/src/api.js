// Unified platform API client. Same-origin, cookie sessions.
export async function api(path, options = {}) {
  const resp = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (resp.status === 401) {
    const err = new Error('Not authenticated');
    err.unauthenticated = true;
    throw err;
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { detail = (await resp.json()).detail || detail; } catch { /* keep */ }
    throw new Error(detail);
  }
  return resp.json();
}

export const login = (username, password) =>
  api('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
export const logout = () => api('/api/auth/logout', { method: 'POST' });
export const me = () => api('/api/auth/me');

let bundlePromise = null;
export function getBundle(force = false) {
  if (!bundlePromise || force) bundlePromise = api('/api/data/bundle');
  return bundlePromise;
}
