const Database = require('better-sqlite3');
const path = require('path');
const { randomUUID } = require('crypto');

const GL_DB_PATH  = path.join(__dirname, '..', 'databases', 'core', 'govsight_all_in_one_data.db');
const PLAY_DB_PATH = path.join(__dirname, '..', 'databases', 'budget_playground.db');

let glDb   = null;
let playDb = null;

function initDatabases() {
    glDb   = new Database(GL_DB_PATH, { readonly: true, fileMustExist: true });
    playDb = new Database(PLAY_DB_PATH);

    playDb.exec(`
        CREATE TABLE IF NOT EXISTS scenarios (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            fiscal_year INTEGER NOT NULL DEFAULT 2025,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            is_locked   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS scenario_lines (
            id              TEXT PRIMARY KEY,
            scenario_id     TEXT NOT NULL,
            account_number  TEXT NOT NULL,
            revised_budget  REAL,
            forecast_yr2    REAL,
            forecast_yr3    REAL,
            note            TEXT DEFAULT '',
            updated_at      TEXT NOT NULL,
            UNIQUE(scenario_id, account_number)
        );

        CREATE TABLE IF NOT EXISTS supplementals (
            id              TEXT PRIMARY KEY,
            scenario_id     TEXT NOT NULL,
            account_number  TEXT,
            department      TEXT,
            category        TEXT NOT NULL DEFAULT 'Supplemental',
            amount          REAL NOT NULL DEFAULT 0,
            justification   TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            submitted_at    TEXT NOT NULL,
            reviewed_at     TEXT
        );
    `);

    seedDefaultScenario();
}

function isPayrollAccount(accountNumber) {
    return /-(5100|5200)$/.test(accountNumber || '');
}

function getNonPayrollAccounts() {
    const rows = glDb.prepare(`
        SELECT account_number, account_name, account_type, department, fund,
               budget_amount, ytd_actual
        FROM gl_accounts
        ORDER BY account_type DESC, department, account_number
    `).all();
    return rows.filter(r => !isPayrollAccount(r.account_number));
}

function seedDefaultScenario() {
    const count = playDb.prepare('SELECT COUNT(*) as n FROM scenarios').get();
    if (count.n > 0) return;

    const id = randomUUID();
    const now = new Date().toISOString();
    playDb.prepare(`
        INSERT INTO scenarios (id, name, description, fiscal_year, created_at, updated_at, is_locked)
        VALUES (?, ?, ?, 2025, ?, ?, 0)
    `).run(id, 'Adopted Budget FY 2025', 'Original adopted budget — do not delete', now, now);

    const accounts = getNonPayrollAccounts();
    const insertLine = playDb.prepare(`
        INSERT INTO scenario_lines (id, scenario_id, account_number, revised_budget, forecast_yr2, forecast_yr3, note, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, '', ?)
    `);
    const insertMany = playDb.transaction((rows) => {
        for (const row of rows) {
            insertLine.run(
                randomUUID(), id, row.account_number,
                row.budget_amount, row.budget_amount, row.budget_amount, now
            );
        }
    });
    insertMany(accounts);
}

function getGlDb()   { return glDb; }
function getPlayDb() { return playDb; }
function uuid()      { return randomUUID(); }

module.exports = { initDatabases, getNonPayrollAccounts, isPayrollAccount, getGlDb, getPlayDb, uuid };
