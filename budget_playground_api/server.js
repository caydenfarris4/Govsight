const express = require('express');
const cors    = require('cors');
const { initDatabases, getNonPayrollAccounts, getGlDb, getPlayDb, uuid } = require('./db');

const PORT = 5002;
const app  = express();

app.use(cors());
app.use(express.json());

// ── Health ────────────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => res.json({ status: 'ok', port: PORT }));

// ── Accounts ──────────────────────────────────────────────────────────────────
app.get('/api/accounts', (_req, res) => {
    try {
        res.json(getNonPayrollAccounts());
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// ── Scenarios ─────────────────────────────────────────────────────────────────
app.get('/api/scenarios', (_req, res) => {
    try {
        const db = getPlayDb();
        const rows = db.prepare('SELECT * FROM scenarios ORDER BY created_at ASC').all();
        res.json(rows);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/api/scenarios', (req, res) => {
    try {
        const db = getPlayDb();
        const { name, description = '', fiscal_year = 2025, copy_from_id } = req.body;
        if (!name) return res.status(400).json({ error: 'name is required' });

        const id  = uuid();
        const now = new Date().toISOString();
        db.prepare(`
            INSERT INTO scenarios (id, name, description, fiscal_year, created_at, updated_at, is_locked)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        `).run(id, name, description, fiscal_year, now, now);

        if (copy_from_id) {
            const sourceLines = db.prepare(
                'SELECT * FROM scenario_lines WHERE scenario_id = ?'
            ).all(copy_from_id);
            const ins = db.prepare(`
                INSERT INTO scenario_lines (id, scenario_id, account_number, revised_budget, forecast_yr2, forecast_yr3, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            `);
            const copyAll = db.transaction((rows) => {
                for (const r of rows) ins.run(uuid(), id, r.account_number, r.revised_budget, r.forecast_yr2, r.forecast_yr3, r.note, now);
            });
            copyAll(sourceLines);
        } else {
            // Seed from GL adopted budgets
            const accounts = getNonPayrollAccounts();
            const ins = db.prepare(`
                INSERT INTO scenario_lines (id, scenario_id, account_number, revised_budget, forecast_yr2, forecast_yr3, note, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, '', ?)
            `);
            const seedAll = db.transaction((rows) => {
                for (const r of rows) ins.run(uuid(), id, r.account_number, r.budget_amount, r.budget_amount, r.budget_amount, now);
            });
            seedAll(accounts);
        }

        const created = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(id);
        res.status(201).json(created);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Return scenario metadata + merged lines (base from gl_accounts, overridden by scenario_lines)
app.get('/api/scenarios/:id', (req, res) => {
    try {
        const db       = getPlayDb();
        const scenario = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!scenario) return res.status(404).json({ error: 'Scenario not found' });

        const accounts = getNonPayrollAccounts();
        const lines    = db.prepare('SELECT * FROM scenario_lines WHERE scenario_id = ?').all(req.params.id);
        const lineMap  = {};
        for (const l of lines) lineMap[l.account_number] = l;

        const merged = accounts.map(a => {
            const line = lineMap[a.account_number];
            return {
                ...a,
                revised_budget: line?.revised_budget ?? a.budget_amount,
                forecast_yr2:   line?.forecast_yr2   ?? a.budget_amount,
                forecast_yr3:   line?.forecast_yr3   ?? a.budget_amount,
                note:           line?.note            ?? '',
                has_override:   !!line,
            };
        });

        res.json({ ...scenario, lines: merged });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.put('/api/scenarios/:id', (req, res) => {
    try {
        const db = getPlayDb();
        const s  = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!s) return res.status(404).json({ error: 'Not found' });

        const { name, description, is_locked } = req.body;
        const now = new Date().toISOString();
        db.prepare(`
            UPDATE scenarios SET
                name        = COALESCE(?, name),
                description = COALESCE(?, description),
                is_locked   = COALESCE(?, is_locked),
                updated_at  = ?
            WHERE id = ?
        `).run(name ?? null, description ?? null, is_locked ?? null, now, req.params.id);

        res.json(db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id));
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.delete('/api/scenarios/:id', (req, res) => {
    try {
        const db = getPlayDb();
        const s  = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!s) return res.status(404).json({ error: 'Not found' });
        if (s.is_locked) return res.status(403).json({ error: 'Scenario is locked and cannot be deleted' });

        db.prepare('DELETE FROM scenario_lines WHERE scenario_id = ?').run(req.params.id);
        db.prepare('DELETE FROM scenarios WHERE id = ?').run(req.params.id);
        res.json({ deleted: req.params.id });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Bulk upsert scenario lines
app.put('/api/scenarios/:id/lines', (req, res) => {
    try {
        const db = getPlayDb();
        const s  = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!s) return res.status(404).json({ error: 'Scenario not found' });
        if (s.is_locked) return res.status(403).json({ error: 'Scenario is locked' });

        const now   = new Date().toISOString();
        const lines = Array.isArray(req.body) ? req.body : [];
        const upsert = db.prepare(`
            INSERT INTO scenario_lines (id, scenario_id, account_number, revised_budget, forecast_yr2, forecast_yr3, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_id, account_number) DO UPDATE SET
                revised_budget = excluded.revised_budget,
                forecast_yr2   = excluded.forecast_yr2,
                forecast_yr3   = excluded.forecast_yr3,
                note           = excluded.note,
                updated_at     = excluded.updated_at
        `);
        const upsertAll = db.transaction((rows) => {
            for (const r of rows) {
                upsert.run(
                    uuid(), req.params.id, r.account_number,
                    r.revised_budget, r.forecast_yr2, r.forecast_yr3,
                    r.note ?? '', now
                );
            }
        });
        upsertAll(lines);
        res.json({ saved: lines.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// CSV export

// Seasonality curves for reforecasting. Computes each account's historical
// cumulative-share-of-year curve from monthly_actuals (when present), plus a
// per-account-type average curve as fallback. Straight-line is the final
// fallback and the response says which accounts have real curves.
app.get('/api/seasonality', (req, res) => {
    const fyStartMonth = (req.query.fyStart === 'January') ? 1 : 7; // calendar month of fiscal month 1
    const glDb = getGlDb();
    const hasTable = glDb.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_actuals'").get();
    if (!hasTable) {
        return res.json({ available: false, byAccount: {}, byType: {}, reason: 'no monthly history' });
    }
    const rows = glDb.prepare(
        'SELECT account_number, fiscal_year, month, actual FROM monthly_actuals').all();
    if (!rows.length) {
        return res.json({ available: false, byAccount: {}, byType: {}, reason: 'no monthly history' });
    }

    const toFiscalIdx = (calMonth) => ((calMonth - fyStartMonth + 12) % 12); // 0-based fiscal month
    // account -> year -> [12 months of actuals in fiscal order]
    const perAcctYear = {};
    for (const r of rows) {
        const key = r.account_number;
        perAcctYear[key] = perAcctYear[key] || {};
        const yr = perAcctYear[key][r.fiscal_year] = perAcctYear[key][r.fiscal_year] || new Array(12).fill(0);
        yr[toFiscalIdx(r.month)] += r.actual;
    }

    const types = {};
    for (const a of getNonPayrollAccounts()) types[a.account_number] = a.account_type;

    const byAccount = {};
    const typeAccum = {};
    for (const [acct, years] of Object.entries(perAcctYear)) {
        const shares = new Array(12).fill(0);
        let usableYears = 0;
        for (const months of Object.values(years)) {
            const total = months.reduce((s, v) => s + Math.abs(v), 0);
            if (total <= 0) continue;
            usableYears++;
            let cum = 0;
            for (let i = 0; i < 12; i++) {
                cum += Math.abs(months[i]);
                shares[i] += cum / total;
            }
        }
        if (!usableYears) continue;
        const curve = shares.map(s => s / usableYears);
        byAccount[acct] = curve;
        const t = types[acct] || 'Expense';
        typeAccum[t] = typeAccum[t] || { sum: new Array(12).fill(0), n: 0 };
        for (let i = 0; i < 12; i++) typeAccum[t].sum[i] += curve[i];
        typeAccum[t].n++;
    }
    const byType = {};
    for (const [t, acc] of Object.entries(typeAccum)) {
        byType[t] = acc.sum.map(v => v / acc.n);
    }
    res.json({ available: Object.keys(byAccount).length > 0, byAccount, byType });
});

app.get('/api/scenarios/:id/export.csv', (req, res) => {
    try {
        const db       = getPlayDb();
        const scenario = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!scenario) return res.status(404).json({ error: 'Not found' });

        const accounts = getNonPayrollAccounts();
        const lines    = db.prepare('SELECT * FROM scenario_lines WHERE scenario_id = ?').all(req.params.id);
        const lineMap  = {};
        for (const l of lines) lineMap[l.account_number] = l;

        const rows = accounts.map(a => {
            const line    = lineMap[a.account_number];
            const revised = line?.revised_budget ?? a.budget_amount;
            const variance = revised - a.budget_amount;
            return [
                a.account_number, `"${a.account_name}"`, a.department,
                a.account_type, a.budget_amount.toFixed(2),
                revised.toFixed(2), variance.toFixed(2),
                a.budget_amount ? ((variance / a.budget_amount) * 100).toFixed(1) + '%' : '0%',
                (line?.forecast_yr2 ?? a.budget_amount).toFixed(2),
                (line?.forecast_yr3 ?? a.budget_amount).toFixed(2),
                `"${line?.note ?? ''}"`,
            ].join(',');
        });

        const header = 'Account #,Account Name,Department,Type,Adopted Budget,Revised Budget,Variance,% Variance,Yr+1 Forecast,Yr+2 Forecast,Note';
        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', `attachment; filename="budget_playground_${scenario.fiscal_year}_${scenario.name.replace(/\s+/g,'_')}.csv"`);
        res.send([header, ...rows].join('\n'));
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// ── Supplementals ─────────────────────────────────────────────────────────────
app.get('/api/supplementals', (req, res) => {
    try {
        const db  = getPlayDb();
        const sql = req.query.scenario_id
            ? db.prepare('SELECT * FROM supplementals WHERE scenario_id = ? ORDER BY submitted_at DESC')
            : db.prepare('SELECT * FROM supplementals ORDER BY submitted_at DESC');
        res.json(req.query.scenario_id ? sql.all(req.query.scenario_id) : sql.all());
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/api/supplementals', (req, res) => {
    try {
        const db = getPlayDb();
        const { scenario_id, account_number, department, category = 'Supplemental', amount, justification = '' } = req.body;
        if (!scenario_id || amount === undefined) return res.status(400).json({ error: 'scenario_id and amount are required' });

        const id  = uuid();
        const now = new Date().toISOString();
        db.prepare(`
            INSERT INTO supplementals (id, scenario_id, account_number, department, category, amount, justification, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        `).run(id, scenario_id, account_number, department, category, amount, justification, now);

        res.status(201).json(db.prepare('SELECT * FROM supplementals WHERE id = ?').get(id));
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.put('/api/supplementals/:id', (req, res) => {
    try {
        const db = getPlayDb();
        const { status, amount, justification } = req.body;
        const now = new Date().toISOString();
        db.prepare(`
            UPDATE supplementals SET
                status        = COALESCE(?, status),
                amount        = COALESCE(?, amount),
                justification = COALESCE(?, justification),
                reviewed_at   = CASE WHEN ? IN ('approved','denied') THEN ? ELSE reviewed_at END
            WHERE id = ?
        `).run(status ?? null, amount ?? null, justification ?? null, status, now, req.params.id);

        const updated = db.prepare('SELECT * FROM supplementals WHERE id = ?').get(req.params.id);
        if (!updated) return res.status(404).json({ error: 'Not found' });
        res.json(updated);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.delete('/api/supplementals/:id', (req, res) => {
    try {
        const db = getPlayDb();
        db.prepare('DELETE FROM supplementals WHERE id = ?').run(req.params.id);
        res.json({ deleted: req.params.id });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Apply approved supplementals to scenario lines
app.post('/api/scenarios/:id/apply-supplementals', (req, res) => {
    try {
        const db       = getPlayDb();
        const scenario = db.prepare('SELECT * FROM scenarios WHERE id = ?').get(req.params.id);
        if (!scenario) return res.status(404).json({ error: 'Not found' });
        if (scenario.is_locked) return res.status(403).json({ error: 'Scenario is locked' });

        const approved = db.prepare(
            "SELECT * FROM supplementals WHERE scenario_id = ? AND status = 'approved'"
        ).all(req.params.id);

        const now = new Date().toISOString();
        const upsert = db.prepare(`
            INSERT INTO scenario_lines (id, scenario_id, account_number, revised_budget, forecast_yr2, forecast_yr3, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_id, account_number) DO UPDATE SET
                revised_budget = revised_budget + excluded.revised_budget,
                note           = note || ' [Supplemental applied]',
                updated_at     = excluded.updated_at
        `);
        const applyAll = db.transaction((rows) => {
            for (const s of rows) {
                upsert.run(uuid(), req.params.id, s.account_number, s.amount, 0, 0, '', now);
            }
        });
        applyAll(approved);
        res.json({ applied: approved.length });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// ── Start ─────────────────────────────────────────────────────────────────────
try {
    initDatabases();
    console.log('Databases initialized successfully');
} catch (e) {
    console.error('Database initialization failed:', e.message);
    process.exit(1);
}

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Budget Playground API running on http://0.0.0.0:${PORT}`);
});
