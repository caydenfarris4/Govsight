import React, { useEffect, useState } from 'react';
import { login } from '../api.js';

/* Sign-in: ink panel with the type wordmark, form on paper. */
export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const result = await login(username.trim(), password);
      onLogin(result);
    } catch (err) {
      setError(err.message || 'Sign in failed');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { document.title = 'GovSight — Sign in'; }, []);

  return (
    <div className="login-split">
      <div className="panel-ink" style={{
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        padding: 'var(--space-12) var(--space-8)', borderRadius: 0,
      }}>
        <span className="kicker">GovSight</span>
        <div>
          <div style={{
            fontFamily: 'var(--font-heading)', fontSize: 'var(--text-display)',
            lineHeight: 1.05, letterSpacing: '-0.02em',
          }}>
            <strong style={{ fontWeight: 600 }}>Gov</strong>
            <span style={{ fontWeight: 400 }}>Sight</span>
          </div>
          <p style={{
            fontSize: 'var(--text-lg)', opacity: 0.8, maxWidth: '36ch',
            marginTop: 'var(--space-3)',
          }}>
            Your financial communication tool. Analytics over the ERP you
            already run.
          </p>
        </div>
        <span style={{ fontSize: 12, opacity: 0.5 }}>
          Municipal Financial Intelligence Platform
        </span>
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 'var(--space-8)',
      }}>
        <form onSubmit={submit} style={{
          width: '100%', maxWidth: 340, display: 'flex', flexDirection: 'column',
          gap: 'var(--space-4)',
        }}>
          <h2 style={{ margin: 0 }}>Sign in</h2>
          <div className="field">
            <label htmlFor="login-username">Username</label>
            <input id="login-username" className="input" value={username}
                   autoFocus type="text" name="username" autoComplete="username"
                   onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="login-password">Password</label>
            <input id="login-password" className="input" type="password"
                   value={password} name="password"
                   autoComplete="current-password"
                   onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          {error && <div className="msg msg-err">{error}</div>}
          <p className="text-muted" style={{ fontSize: 12, margin: 0 }}>
            Sign in with the account your administrator provisioned.
          </p>
        </form>
      </div>
    </div>
  );
}
