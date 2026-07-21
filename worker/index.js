/**
 * GovSight edge worker: authentication gate for the static application.
 *
 * All requests pass through this worker before any asset is served
 * (run_worker_first in wrangler.toml). Requests without a valid session
 * cookie are redirected to the login page; /api/login issues the cookie.
 *
 * Credentials and the cookie-signing secret come from Worker
 * variables/secrets, with development defaults matching the platform's
 * default admin account. Override in production:
 *   npx wrangler secret put GOVSIGHT_PASSWORD
 *   npx wrangler secret put SESSION_SECRET
 */

const COOKIE_NAME = 'gs_session';
const SESSION_HOURS = 8;

// Paths reachable without a session
const PUBLIC_PATHS = new Set(['/login', '/login.html', '/api/login']);
const PUBLIC_PREFIXES = ['/assets/'];

const encoder = new TextEncoder();

async function sign(secret, data) {
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(data));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function getConfig(env) {
  return {
    username: env.GOVSIGHT_USER || 'admin_user',
    password: env.GOVSIGHT_PASSWORD || 'govsight123',
    secret: env.SESSION_SECRET || 'govsight-dev-session-secret-change-me',
  };
}

function parseCookies(request) {
  const out = {};
  const header = request.headers.get('Cookie') || '';
  for (const part of header.split(';')) {
    const idx = part.indexOf('=');
    if (idx > 0) out[part.slice(0, idx).trim()] = part.slice(idx + 1).trim();
  }
  return out;
}

async function hasValidSession(request, config) {
  const raw = parseCookies(request)[COOKIE_NAME];
  if (!raw) return false;
  const dot = raw.indexOf('.');
  if (dot < 0) return false;
  const exp = raw.slice(0, dot);
  const sig = raw.slice(dot + 1);
  if (!/^\d+$/.test(exp) || Number(exp) < Date.now()) return false;
  return (await sign(config.secret, exp)) === sig;
}

async function handleLogin(request, config) {
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ ok: false, error: 'Invalid request' }, { status: 400 });
  }
  if (body.username !== config.username || body.password !== config.password) {
    return Response.json({ ok: false, error: 'Invalid username or password' }, { status: 401 });
  }
  const exp = String(Date.now() + SESSION_HOURS * 3600 * 1000);
  const cookie = `${exp}.${await sign(config.secret, exp)}`;
  return new Response(JSON.stringify({ ok: true }), {
    headers: {
      'Content-Type': 'application/json',
      'Set-Cookie': `${COOKIE_NAME}=${cookie}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${SESSION_HOURS * 3600}`,
    },
  });
}

function handleLogout() {
  return new Response(null, {
    status: 302,
    headers: {
      Location: '/login',
      'Set-Cookie': `${COOKIE_NAME}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`,
    },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const config = getConfig(env);

    if (path === '/api/login' && request.method === 'POST') {
      return handleLogin(request, config);
    }
    if (path === '/api/logout') {
      return handleLogout();
    }

    const isPublic = PUBLIC_PATHS.has(path) || PUBLIC_PREFIXES.some(p => path.startsWith(p));
    if (!isPublic && !(await hasValidSession(request, config))) {
      const wantsHtml = (request.headers.get('Accept') || '').includes('text/html');
      if (wantsHtml) return Response.redirect(`${url.origin}/login`, 302);
      return Response.json({ ok: false, error: 'Not authenticated' }, { status: 401 });
    }

    // Already signed in: keep the login page out of the way
    if ((path === '/login' || path === '/login.html') && (await hasValidSession(request, config))) {
      return Response.redirect(`${url.origin}/`, 302);
    }

    return env.ASSETS.fetch(request);
  },
};
