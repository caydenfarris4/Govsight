import React, { useState } from 'react';
import { login } from '../api.js';

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
      onLogin({ username: result.username, role: result.role });
    } catch (err) {
      setError(err.message || 'Sign in failed');
    } finally {
      setBusy(false);
    }
  };

  const input = {
    width: '100%', padding: '10px 12px', border: '1px solid #cfd8e0',
    borderRadius: 8, fontSize: 15, marginTop: 4,
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #12263a 0%, #1d3a56 100%)',
    }}>
      <form onSubmit={submit} style={{
        background: '#fff', borderRadius: 12, padding: '40px 36px',
        width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,.35)',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 26 }}>
          <img src="/assets/govsight_logo.png" alt="GovSight" style={{ height: 48 }}
               onError={(e) => { e.target.style.display = 'none'; }} />
          <h1 style={{ fontSize: 19, color: '#12263a', marginTop: 12 }}>
            GovSight Financial Analyzer
          </h1>
          <p style={{ fontSize: 13, color: '#5b6b7a', marginTop: 4 }}>
            Municipal Financial Intelligence Platform
          </p>
        </div>
        <label style={{ fontSize: 13, fontWeight: 600 }}>Username
          <input style={input} value={username} autoFocus
                 type="text" name="username" autoComplete="username"
                 onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginTop: 14 }}>
          Password
          <input style={input} type="password" value={password}
                 name="password" autoComplete="current-password"
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button type="submit" disabled={busy} style={{
          width: '100%', marginTop: 22, padding: 11, background: '#1d3a56',
          color: '#fff', border: 'none', borderRadius: 8, fontSize: 15,
          fontWeight: 600, cursor: 'pointer', opacity: busy ? 0.7 : 1,
        }}>
          {busy ? 'Signing in…' : 'Sign In'}
        </button>
        {error && (
          <div style={{
            marginTop: 14, padding: '9px 12px', background: '#fdecea',
            color: '#a4271c', borderRadius: 8, fontSize: 13,
          }}>{error}</div>
        )}
      </form>
    </div>
  );
}
