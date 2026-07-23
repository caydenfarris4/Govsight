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

// Sliding-window rate limiting, per worker isolate. Cloudflare may run
// several isolates so the effective global limit is a small multiple of
// these numbers - still a hard ceiling on brute force and AI spend.
const RATE_BUCKETS = new Map();
function rateAllow(key, limit, windowMs) {
  const now = Date.now();
  if (RATE_BUCKETS.size > 10000) RATE_BUCKETS.clear(); // memory bound
  let hits = RATE_BUCKETS.get(key);
  if (!hits) { hits = []; RATE_BUCKETS.set(key, hits); }
  while (hits.length && hits[0] <= now - windowMs) hits.shift();
  if (hits.length >= limit) return false;
  hits.push(now);
  return true;
}
function clientIp(request) {
  return request.headers.get('CF-Connecting-IP') ||
         request.headers.get('X-Forwarded-For') || 'unknown';
}
function rateLimited(message, retryS) {
  return Response.json(
    { ok: false, error: 'rate_limited', message },
    { status: 429, headers: { 'Retry-After': String(retryS) } });
}

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

/**
 * AI chat proxy. The static app cannot hold an API key (anything shipped
 * to the browser is public), so the worker calls Anthropic server-side
 * with a key stored as a Cloudflare secret:
 *   npx wrangler secret put ANTHROPIC_API_KEY
 * The client sends a compact digest of the demo financials as context;
 * the model is instructed to answer only from that data.
 */
const CHAT_MODEL = 'claude-sonnet-5';
const OPENAI_CHAT_MODEL = 'gpt-4o';
const MAX_MESSAGE_CHARS = 4000;
const MAX_CONTEXT_CHARS = 12000;
const MAX_HISTORY_TURNS = 10;

// Accept common alternate spellings admins use in the dashboard
function anthropicKey(env) {
  return env.ANTHROPIC_API_KEY || env.ANTHROPIC_KEY || env.Anthropic_API_Key || null;
}
function openaiKey(env) {
  return env.OPENAI_API_KEY || env.OPEN_AI_KEY || env.OPEN_AI_Key || env.OpenAI_Key || null;
}

async function callAnthropic(key, system, history, message) {
  const resp = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: CHAT_MODEL,
      max_tokens: 1000,
      system,
      messages: [...history, { role: 'user', content: message }],
    }),
  });
  if (!resp.ok) throw new Error(`Anthropic ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
  const data = await resp.json();
  const reply = (data.content || []).filter(b => b.type === 'text').map(b => b.text).join('');
  return { reply, model: data.model || CHAT_MODEL };
}

async function callOpenAI(key, system, history, message) {
  const resp = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`,
    },
    body: JSON.stringify({
      model: OPENAI_CHAT_MODEL,
      max_tokens: 1000,
      messages: [{ role: 'system', content: system }, ...history,
                 { role: 'user', content: message }],
    }),
  });
  if (!resp.ok) throw new Error(`OpenAI ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
  const data = await resp.json();
  return { reply: data.choices?.[0]?.message?.content || '',
           model: data.model || OPENAI_CHAT_MODEL };
}

async function handleChat(request, env) {
  const aKey = anthropicKey(env);
  const oKey = openaiKey(env);
  if (!aKey && !oKey) {
    return Response.json({
      ok: false, error: 'not_configured',
      message: 'AI chat is not configured for this deployment. An administrator ' +
               'can enable it by adding the ANTHROPIC_API_KEY secret to the ' +
               'Cloudflare Worker (Settings > Variables, or ' +
               '"npx wrangler secret put ANTHROPIC_API_KEY").',
    }, { status: 503 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ ok: false, error: 'bad_request' }, { status: 400 });
  }
  const message = String(body.message || '').slice(0, MAX_MESSAGE_CHARS).trim();
  if (!message) {
    return Response.json({ ok: false, error: 'empty_message' }, { status: 400 });
  }

  const context = JSON.stringify(body.context || {}).slice(0, MAX_CONTEXT_CHARS);
  const history = Array.isArray(body.history)
    ? body.history.slice(-MAX_HISTORY_TURNS)
        .filter(t => (t.role === 'user' || t.role === 'assistant') && typeof t.text === 'string')
        .map(t => ({ role: t.role, content: t.text.slice(0, MAX_MESSAGE_CHARS) }))
    : [];

  const system =
    'You are Mantis, the AI financial analyst inside GovSight, a municipal ' +
    'finance platform. You are answering for the demo city whose financial ' +
    'digest is provided below as JSON (budgets, actuals by department, top ' +
    'vendors, fund balances). Answer as a concise municipal finance analyst: ' +
    'cite the actual numbers from the digest, name departments and vendors, ' +
    'and suggest concrete next steps a finance director could take. If a ' +
    'question needs data that is not in the digest, say what is missing ' +
    'instead of guessing. Keep answers under 250 words. Plain text only, no ' +
    'markdown headers.\n\nFINANCIAL DIGEST:\n' + context;

  // Claude is primary; OpenAI is the fallback provider (or primary when
  // it is the only key configured)
  const attempts = [];
  if (aKey) attempts.push(() => callAnthropic(aKey, system, history, message));
  if (oKey) attempts.push(() => callOpenAI(oKey, system, history, message));

  const failures = [];
  for (const attempt of attempts) {
    try {
      const { reply, model } = await attempt();
      if (reply) return Response.json({ ok: true, reply, model });
      failures.push(`${attempts.length > 1 ? 'provider' : 'model'} returned empty reply`);
    } catch (err) {
      failures.push(String(err && err.message || err).slice(0, 200));
    }
  }
  return Response.json({
    ok: false, error: 'upstream',
    message: `AI request failed. ${failures.join(' | ')}`,
  }, { status: 502 });
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
      // Brute-force ceiling per source IP
      if (!rateAllow(`login:${clientIp(request)}`, 10, 60_000)) {
        return rateLimited('Too many sign-in attempts. Wait a minute and try again.', 60);
      }
      return handleLogin(request, config);
    }
    if (path === '/api/logout') {
      return handleLogout();
    }
    if (path === '/api/chat' && request.method === 'POST') {
      if (!(await hasValidSession(request, config))) {
        return Response.json({ ok: false, error: 'Not authenticated' }, { status: 401 });
      }
      // AI spend ceiling per session (and per IP as a backstop)
      const session = parseCookies(request)[COOKIE_NAME] || clientIp(request);
      if (!rateAllow(`chat-m:${session}`, 8, 60_000)) {
        return rateLimited('Chat rate limit reached (8 per minute). Give it a moment.', 60);
      }
      if (!rateAllow(`chat-h:${session}`, 60, 3_600_000)) {
        return rateLimited('Hourly chat limit reached (60 per hour). Try again later.', 900);
      }
      return handleChat(request, env);
    }
    // Diagnostic: confirms whether the AI secret is visible to this
    // deployment (value never returned)
    if (path === '/api/ai-status') {
      if (!(await hasValidSession(request, config))) {
        return Response.json({ ok: false, error: 'Not authenticated' }, { status: 401 });
      }
      const providers = {
        anthropic: Boolean(anthropicKey(env)),
        openai: Boolean(openaiKey(env)),
      };
      const configured = providers.anthropic || providers.openai;
      return Response.json({
        ai_configured: configured,
        providers,
        hint: configured
          ? 'AI chat is enabled' +
            (providers.anthropic && providers.openai ? ' (Claude primary, OpenAI fallback).'
              : providers.anthropic ? ' (Claude).' : ' (OpenAI).')
          : 'Add ANTHROPIC_API_KEY as a SECRET on this Worker (Settings > ' +
            'Variables and Secrets > Add > Type: Secret), then click Deploy.',
      });
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
