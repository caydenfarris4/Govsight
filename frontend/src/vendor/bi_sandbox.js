// GENERATED copy for the SPA bundle - source of truth is public/assets/.
/*
 * GovSight BI Sandbox - self-service visual analytics builder.
 *
 * A full field-picker analytics surface over every table in the demo
 * dataset: choose a table, drag through dimensions and measures, flip
 * between chart types, group by a second dimension, filter, sort,
 * limit, define custom calculated fields, save charts, and export the
 * aggregated result as CSV. All client-side.
 */
(function () {
  'use strict';

  // Design-system series ramp: cardinal leads, cyan follows, warm neutrals fill
  const PALETTE = ['#d6006c', '#0088b0', '#444141', '#ff90b1', '#62c5ee',
                   '#aa0b56', '#006786', '#9b9797', '#ff458e', '#38a6cf'];
  const CALC_LS = 'gs_bi_calc_fields_v1';
  const SAVED_LS = 'gs_bi_saved_charts_v1';

  const CHART_TYPES = [
    { id: 'bar', label: 'Bar' },
    { id: 'hbar', label: 'Horizontal Bar' },
    { id: 'stacked', label: 'Stacked Bar' },
    { id: 'line', label: 'Line' },
    { id: 'area', label: 'Area' },
    { id: 'pie', label: 'Pie' },
    { id: 'doughnut', label: 'Doughnut' },
    { id: 'scatter', label: 'Scatter' },
    { id: 'radar', label: 'Radar' },
    { id: 'table', label: 'Table' },
    { id: 'kpi', label: 'KPI Card' },
  ];
  const AGGS = ['sum', 'average', 'count', 'min', 'max'];

  let DATA = null;
  let chart = null;
  let state = null;

  // ── table registry ─────────────────────────────────────────────────────
  function buildTables(data) {
    const acctIndex = {};
    data.accounts.forEach(function (a) { acctIndex[a.account_number] = a; });

    const monthly = data.monthly_actuals.map(function (m) {
      const a = acctIndex[m.account_number] || {};
      return {
        period: m.fiscal_year + '-' + String(m.month).padStart(2, '0'),
        fiscal_year: String(m.fiscal_year), month: m.month,
        account_number: m.account_number, account_name: a.account_name || '',
        account_type: a.account_type || '', department: a.department || '',
        fund: a.fund || '', actual: m.actual,
      };
    });
    const transactions = data.transactions.map(function (t) {
      return Object.assign({}, t, { period: t.date.slice(0, 7) });
    });
    const positions = data.positions.map(function (p) {
      return Object.assign({}, p, {
        loaded_cost: Math.round(p.annual_salary * (1 + p.benefits_pct)),
        benefits_pct_display: Math.round(p.benefits_pct * 100),
      });
    });

    return {
      accounts: {
        label: 'GL Accounts (budget vs actual)',
        rows: data.accounts,
        dims: ['account_number', 'account_name', 'account_type', 'department', 'fund'],
        measures: ['budget_amount', 'ytd_actual'],
      },
      monthly_actuals: {
        label: 'Monthly Actuals (3 fiscal years)',
        rows: monthly,
        dims: ['period', 'fiscal_year', 'month', 'account_type', 'department', 'fund', 'account_name'],
        measures: ['actual'],
      },
      transactions: {
        label: 'Transactions (18 months)',
        rows: transactions,
        dims: ['period', 'date', 'vendor', 'department', 'fund', 'account_number', 'account_name'],
        measures: ['amount'],
      },
      balance_sheet: {
        label: 'Balance Sheet',
        rows: data.balance_sheet,
        dims: ['account', 'name', 'fund', 'category'],
        measures: ['amount'],
      },
      positions: {
        label: 'Budgeted Positions',
        rows: positions,
        dims: ['title', 'department', 'status'],
        measures: ['fte', 'annual_salary', 'loaded_cost', 'benefits_pct_display'],
      },
      scenarios: {
        label: 'Planning Scenarios',
        rows: data.scenarios,
        dims: ['name', 'created'],
        measures: ['total_cost', 'tax_revenue', 'grant_funding', 'bonds', 'reallocation'],
      },
    };
  }

  // ── calculated fields ──────────────────────────────────────────────────
  // Expressions over numeric fields with + - * / ( ) and numbers only.
  // Tokenized against a whitelist; unknown identifiers are rejected, so no
  // arbitrary code can run.
  function loadCalcFields() {
    try { return JSON.parse(localStorage.getItem(CALC_LS)) || {}; }
    catch (e) { return {}; }
  }
  function saveCalcFields(cf) { localStorage.setItem(CALC_LS, JSON.stringify(cf)); }

  function compileExpression(expr, allowedFields) {
    const tokens = expr.match(/[A-Za-z_][A-Za-z0-9_]*|[0-9]*\.?[0-9]+|[+\-*/()]|\S/g) || [];
    const compiled = tokens.map(function (t) {
      if (/^[A-Za-z_]/.test(t)) {
        if (allowedFields.indexOf(t) === -1) throw new Error('Unknown field: ' + t);
        return '(Number(r["' + t + '"]) || 0)';
      }
      if (/^[0-9]*\.?[0-9]+$/.test(t) || '+-*/()'.indexOf(t) >= 0) return t;
      throw new Error('Invalid token: ' + t);
    }).join(' ');
    /* eslint-disable no-new-func */
    const fn = new Function('r', 'var v = ' + compiled + '; return isFinite(v) ? v : 0;');
    fn(allowedFields.length ? {} : {});   // smoke-run
    return fn;
  }

  function tableFields(tableId) {
    const t = buildTables(DATA)[tableId];
    const calc = (loadCalcFields()[tableId] || []);
    return {
      dims: t.dims,
      measures: t.measures.concat(calc.map(function (c) { return c.name; })),
      calc: calc,
      rows: t.rows,
      label: t.label,
    };
  }

  function materializeRows(tableId) {
    const t = tableFields(tableId);
    if (!t.calc.length) return t.rows;
    const compiled = [];
    t.calc.forEach(function (c) {
      try {
        compiled.push({ name: c.name, fn: compileExpression(c.expr, baseMeasuresPlusCalc(tableId, c.name)) });
      } catch (e) { /* broken field renders as 0 */ }
    });
    return t.rows.map(function (r) {
      const out = Object.assign({}, r);
      compiled.forEach(function (c) {
        try { out[c.name] = c.fn(out); } catch (e) { out[c.name] = 0; }
      });
      return out;
    });
  }

  function baseMeasuresPlusCalc(tableId, excludeName) {
    const t = buildTables(DATA)[tableId];
    const calc = (loadCalcFields()[tableId] || []).map(function (c) { return c.name; })
      .filter(function (n) { return n !== excludeName; });
    return t.measures.concat(calc);
  }

  // ── aggregation pipeline ───────────────────────────────────────────────
  function aggregate(rows, cfg) {
    let filtered = rows;
    if (cfg.filterField && cfg.filterValues && cfg.filterValues.length) {
      filtered = rows.filter(function (r) {
        return cfg.filterValues.indexOf(String(r[cfg.filterField])) >= 0;
      });
    }
    const aggOne = function (vals) {
      if (!vals.length) return 0;
      if (cfg.agg === 'count') return vals.length;
      if (cfg.agg === 'min') return Math.min.apply(null, vals);
      if (cfg.agg === 'max') return Math.max.apply(null, vals);
      const sum = vals.reduce(function (s, v) { return s + v; }, 0);
      return cfg.agg === 'average' ? sum / vals.length : sum;
    };

    if (cfg.type === 'scatter') {
      return {
        points: filtered.map(function (r) {
          return { x: Number(r[cfg.measure]) || 0, y: Number(r[cfg.measure2]) || 0,
                   label: String(r[cfg.dim] || '') };
        }),
      };
    }

    const groups = {};
    filtered.forEach(function (r) {
      const key = String(r[cfg.dim] != null ? r[cfg.dim] : '(blank)');
      const series = cfg.series ? String(r[cfg.series] != null ? r[cfg.series] : '(blank)') : '_';
      const g = groups[key] = groups[key] || {};
      (g[series] = g[series] || []).push(Number(r[cfg.measure]) || 0);
    });

    let keys = Object.keys(groups);
    const totals = {};
    keys.forEach(function (k) {
      totals[k] = aggOne(Object.values(groups[k]).reduce(function (a, b) { return a.concat(b); }, []));
    });
    if (cfg.sort === 'value_desc') keys.sort(function (a, b) { return totals[b] - totals[a]; });
    else if (cfg.sort === 'value_asc') keys.sort(function (a, b) { return totals[a] - totals[b]; });
    else keys.sort();
    if (cfg.topN && keys.length > cfg.topN) keys = keys.slice(0, cfg.topN);

    const seriesNames = cfg.series
      ? Array.from(new Set(filtered.map(function (r) { return String(r[cfg.series] != null ? r[cfg.series] : '(blank)'); }))).sort()
      : ['_'];
    const datasets = seriesNames.map(function (s) {
      return { name: s, values: keys.map(function (k) { return aggOne((groups[k] || {})[s] || []); }) };
    });
    return { keys: keys, datasets: datasets, totals: totals };
  }

  // ── rendering ──────────────────────────────────────────────────────────
  function fcM(v) {
    return Math.abs(v) >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M'
         : Math.abs(v) >= 1e3 ? '$' + (v / 1e3).toFixed(0) + 'k'
         : String(Math.round(v * 100) / 100);
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function renderChart(host, cfg, result) {
    if (chart) { chart.destroy(); chart = null; }
    if (cfg.type === 'kpi') {
      const all = result.datasets[0] ? result.datasets[0].values : [];
      const grand = Object.values(result.totals || {}).reduce(function (s, v) { return s + v; }, 0);
      host.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%">' +
        '<div style="text-align:center"><div style="font-size:44px;font-weight:800;color:#201e1d">' +
        fcM(cfg.agg === 'average' && all.length ? grand / all.length : grand) + '</div>' +
        '<div style="color:#605d5d;font-size:14px;margin-top:6px">' + esc(cfg.agg) + ' of ' +
        esc(cfg.measure) + (cfg.filterField ? ' (filtered)' : '') + '</div></div></div>';
      return;
    }
    if (cfg.type === 'table') {
      let html = '<div style="overflow:auto;max-height:460px"><table style="width:100%;border-collapse:collapse;font-size:13px">' +
        '<thead><tr><th style="text-align:left;padding:8px;border-bottom:2px solid #d7d3d3;position:sticky;top:0;background: #eae9e9">' + esc(cfg.dim) + '</th>';
      result.datasets.forEach(function (d) {
        html += '<th style="text-align:right;padding:8px;border-bottom:2px solid #d7d3d3;position:sticky;top:0;background: #eae9e9">' +
          esc(d.name === '_' ? cfg.agg + ' of ' + cfg.measure : d.name) + '</th>';
      });
      html += '</tr></thead><tbody>';
      result.keys.forEach(function (k, i) {
        html += '<tr><td style="padding:7px 8px;border-bottom:1px solid #eae7e7">' + esc(k) + '</td>';
        result.datasets.forEach(function (d) {
          html += '<td style="padding:7px 8px;text-align:right;border-bottom:1px solid #eae7e7">' +
            Number(d.values[i]).toLocaleString('en-US', { maximumFractionDigits: 2 }) + '</td>';
        });
        html += '</tr>';
      });
      host.innerHTML = html + '</tbody></table></div>';
      return;
    }
    if (typeof Chart === 'undefined') {
      host.innerHTML = '<div style="padding:30px;color:#605d5d;font-size:13px">Chart library unavailable - ' +
        'use the Table type, or reconnect to the internet for chart rendering.</div>';
      return;
    }
    host.innerHTML = '<canvas id="bi-canvas"></canvas>';
    const ctx = document.getElementById('bi-canvas').getContext('2d');

    if (cfg.type === 'scatter') {
      chart = new Chart(ctx, { type: 'scatter',
        data: { datasets: [{ label: cfg.measure + ' vs ' + cfg.measure2,
          data: result.points, backgroundColor: PALETTE[0] }] },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { tooltip: { callbacks: { label: function (c) {
            return (c.raw.label ? c.raw.label + ': ' : '') + c.parsed.x.toLocaleString() + ', ' + c.parsed.y.toLocaleString();
          } } } },
          scales: { x: { title: { display: true, text: cfg.measure } },
                    y: { title: { display: true, text: cfg.measure2 } } } } });
      return;
    }

    const circular = cfg.type === 'pie' || cfg.type === 'doughnut' || cfg.type === 'radar';
    const chartType = cfg.type === 'hbar' || cfg.type === 'stacked' ? 'bar'
                    : cfg.type === 'area' ? 'line' : cfg.type;
    const datasets = result.datasets.map(function (d, i) {
      return {
        label: d.name === '_' ? cfg.agg + ' of ' + cfg.measure : d.name,
        data: d.values,
        backgroundColor: circular && result.datasets.length === 1
          ? result.keys.map(function (_, j) { return PALETTE[j % PALETTE.length]; })
          : PALETTE[i % PALETTE.length],
        borderColor: PALETTE[i % PALETTE.length],
        fill: cfg.type === 'area',
        tension: 0.25,
      };
    });
    chart = new Chart(ctx, {
      type: chartType,
      data: { labels: result.keys, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        indexAxis: cfg.type === 'hbar' ? 'y' : 'x',
        plugins: { legend: { display: circular || result.datasets.length > 1,
                             position: circular ? 'right' : 'top' } },
        scales: circular ? {} : {
          x: { stacked: cfg.type === 'stacked', ticks: { maxTicksLimit: 20 } },
          y: { stacked: cfg.type === 'stacked',
               ticks: { callback: function (v) { return fcM(v); } } },
        },
      },
    });
  }

  // ── saved charts ───────────────────────────────────────────────────────
  function loadSaved() {
    try { return JSON.parse(localStorage.getItem(SAVED_LS)) || []; }
    catch (e) { return []; }
  }
  function saveSavedList(list) { localStorage.setItem(SAVED_LS, JSON.stringify(list)); }

  // ── UI ─────────────────────────────────────────────────────────────────
  function selectHtml(id, options, selected, allowNone) {
    return '<select id="' + id + '" style="width:100%;padding:6px 8px;border:1px solid #d7d3d3;border-radius:6px;font-size:13px">' +
      (allowNone ? '<option value="">(none)</option>' : '') +
      options.map(function (o) {
        const val = typeof o === 'string' ? o : o.id;
        const label = typeof o === 'string' ? o : o.label;
        return '<option value="' + esc(val) + '"' + (val === selected ? ' selected' : '') + '>' + esc(label) + '</option>';
      }).join('') + '</select>';
  }

  function defaultState() {
    return { table: 'accounts', type: 'bar', dim: 'department', series: '',
             measure: 'budget_amount', measure2: 'ytd_actual', agg: 'sum',
             filterField: '', filterValues: [], sort: 'value_desc', topN: 15 };
  }

  function render(container) {
    if (!state) state = defaultState();
    const t = tableFields(state.table);
    if (t.dims.indexOf(state.dim) === -1) state.dim = t.dims[0];
    if (t.measures.indexOf(state.measure) === -1) state.measure = t.measures[0];
    if (state.measure2 && t.measures.indexOf(state.measure2) === -1) state.measure2 = t.measures[0];
    if (state.series && t.dims.indexOf(state.series) === -1) state.series = '';
    if (state.filterField && t.dims.indexOf(state.filterField) === -1) { state.filterField = ''; state.filterValues = []; }

    const rows = materializeRows(state.table);
    const filterOptions = state.filterField
      ? Array.from(new Set(rows.map(function (r) { return String(r[state.filterField]); }))).sort()
      : [];

    const label = function (text) {
      return '<div style="font-size:11px;color:#605d5d;text-transform:uppercase;letter-spacing:.05em;margin:10px 0 4px">' + text + '</div>';
    };

    container.innerHTML =
      '<div style="display:grid;grid-template-columns:250px 1fr;gap:16px;align-items:start">' +

      // ── left rail: data panel ──
      '<div style="background: #eae9e9;border:1px solid #d7d3d3;border-radius:10px;padding:14px;position:sticky;top:10px">' +
        label('Data table') + selectHtml('bi-table', Object.keys(buildTables(DATA)).map(function (k) {
          return { id: k, label: buildTables(DATA)[k].label };
        }), state.table) +
        label('Category (dimension)') + selectHtml('bi-dim', t.dims, state.dim) +
        label('Group by (series)') + selectHtml('bi-series', t.dims.filter(function (d) { return d !== state.dim; }), state.series, true) +
        label('Measure') + selectHtml('bi-measure', t.measures, state.measure) +
        (state.type === 'scatter' ? label('Second measure (Y axis)') + selectHtml('bi-measure2', t.measures, state.measure2) : '') +
        label('Aggregation') + selectHtml('bi-agg', AGGS, state.agg) +
        label('Filter field') + selectHtml('bi-filter-field', t.dims, state.filterField, true) +
        (state.filterField
          ? label('Filter values (multi-select)') +
            '<select id="bi-filter-values" multiple size="5" style="width:100%;border:1px solid #d7d3d3;border-radius:6px;font-size:12px">' +
            filterOptions.map(function (v) {
              return '<option value="' + esc(v) + '"' + (state.filterValues.indexOf(v) >= 0 ? ' selected' : '') + '>' + esc(v) + '</option>';
            }).join('') + '</select>'
          : '') +
        label('Sort') + selectHtml('bi-sort', [
          { id: 'value_desc', label: 'Value (high to low)' },
          { id: 'value_asc', label: 'Value (low to high)' },
          { id: 'label', label: 'Label (A-Z)' }], state.sort) +
        label('Top N categories') +
        '<input id="bi-topn" type="number" min="0" value="' + state.topN + '" style="width:100%;padding:6px 8px;border:1px solid #d7d3d3;border-radius:6px;font-size:13px">' +
        '<div style="margin-top:14px;border-top:1px solid #eae7e7;padding-top:10px">' +
        label('Calculated fields') +
        (t.calc.map(function (c) {
          return '<div style="font-size:12px;display:flex;justify-content:space-between;margin-bottom:4px">' +
            '<span title="' + esc(c.expr) + '"><strong>' + esc(c.name) + '</strong></span>' +
            '<button data-delcalc="' + esc(c.name) + '" style="border:none;background:none;color:#aa0b56;cursor:pointer;font-weight:700">&times;</button></div>';
        }).join('') || '<div style="font-size:12px;color:#9b9797">none yet</div>') +
        '<button id="bi-addcalc" style="margin-top:6px;width:100%;background: #eae9e9;border:1px dashed #0088b0;color:#0088b0;border-radius:6px;padding:6px;font-size:12px;font-weight:600;cursor:pointer">+ Add calculated field</button>' +
        '</div>' +
      '</div>' +

      // ── main pane ──
      '<div>' +
        '<div style="background: #eae9e9;border:1px solid #d7d3d3;border-radius:10px;padding:10px 14px;margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">' +
        CHART_TYPES.map(function (ct) {
          const active = ct.id === state.type;
          return '<button data-charttype="' + ct.id + '" style="padding:6px 12px;border-radius:99px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid ' +
            (active ? '#201e1d' : '#d7d3d3') + ';background:' + (active ? '#201e1d' : '#fff') + ';color:' + (active ? '#fff' : '#605d5d') + '">' +
            ct.label + '</button>';
        }).join('') +
        '<span style="flex:1"></span>' +
        '<button id="bi-save" style="padding:6px 14px;border-radius:8px;border:none;background:#006786;color:#fff;font-size:12px;font-weight:600;cursor:pointer">Save chart</button>' +
        '<button id="bi-export" style="padding:6px 14px;border-radius:8px;border:1px solid #d7d3d3;background: #eae9e9;color:#201e1d;font-size:12px;font-weight:600;cursor:pointer">Export CSV</button>' +
        '</div>' +
        '<div style="background: #eae9e9;border:1px solid #d7d3d3;border-radius:10px;padding:16px">' +
          '<div id="bi-chart-title" style="font-weight:600;color:#201e1d;margin-bottom:8px"></div>' +
          '<div id="bi-chart-host" style="height:440px"></div>' +
        '</div>' +
        '<div id="bi-saved" style="margin-top:12px"></div>' +
      '</div></div>';

    // title
    document.getElementById('bi-chart-title').textContent =
      state.agg + ' of ' + state.measure + ' by ' + state.dim +
      (state.series ? ', grouped by ' + state.series : '') +
      (state.filterField && state.filterValues.length ? ' (filtered on ' + state.filterField + ')' : '');

    // compute + draw
    const result = aggregate(rows, state);
    renderChart(document.getElementById('bi-chart-host'), state, result);

    // saved gallery
    const saved = loadSaved();
    document.getElementById('bi-saved').innerHTML = saved.length
      ? '<div style="background: #eae9e9;border:1px solid #d7d3d3;border-radius:10px;padding:12px 14px">' +
        '<div style="font-size:11px;color:#605d5d;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Saved charts</div>' +
        saved.map(function (s, i) {
          return '<span style="display:inline-flex;align-items:center;gap:6px;background:#f8f4f4;border-radius:99px;padding:4px 10px;margin:0 6px 6px 0;font-size:12px">' +
            '<a href="#" data-loadsaved="' + i + '" style="color:#201e1d;font-weight:600;text-decoration:none">' + esc(s.name) + '</a>' +
            '<button data-delsaved="' + i + '" style="border:none;background:none;color:#aa0b56;cursor:pointer;font-weight:700">&times;</button></span>';
        }).join('') + '</div>'
      : '';

    // ── events ──
    const bind = function (id, field, isNumber) {
      const elm = document.getElementById(id);
      if (!elm) return;
      elm.addEventListener('change', function () {
        state[field] = isNumber ? (parseInt(elm.value, 10) || 0) : elm.value;
        if (field === 'table') {
          const nt = tableFields(state.table);
          state.dim = nt.dims[0];
          state.series = '';
          state.measure = nt.measures[0];
          state.measure2 = nt.measures[1] || nt.measures[0];
          state.filterField = '';
          state.filterValues = [];
        }
        if (field === 'filterField') state.filterValues = [];
        render(container);
      });
    };
    bind('bi-table', 'table'); bind('bi-dim', 'dim'); bind('bi-series', 'series');
    bind('bi-measure', 'measure'); bind('bi-measure2', 'measure2'); bind('bi-agg', 'agg');
    bind('bi-filter-field', 'filterField'); bind('bi-sort', 'sort'); bind('bi-topn', 'topN', true);

    const fv = document.getElementById('bi-filter-values');
    if (fv) {
      fv.addEventListener('change', function () {
        state.filterValues = Array.from(fv.selectedOptions).map(function (o) { return o.value; });
        render(container);
      });
    }
    container.querySelectorAll('[data-charttype]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.type = btn.getAttribute('data-charttype');
        render(container);
      });
    });
    document.getElementById('bi-addcalc').addEventListener('click', function () {
      const name = prompt('Field name (letters, numbers, underscores):');
      if (!name || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
        if (name !== null) alert('Invalid name.');
        return;
      }
      const expr = prompt('Expression using numeric fields of this table, e.g.\n' +
        'budget_amount - ytd_actual   or   ytd_actual / budget_amount * 100\n\n' +
        'Available fields: ' + baseMeasuresPlusCalc(state.table).join(', '));
      if (!expr) return;
      try {
        compileExpression(expr, baseMeasuresPlusCalc(state.table));
      } catch (e) {
        alert('Expression error: ' + e.message);
        return;
      }
      const cf = loadCalcFields();
      cf[state.table] = (cf[state.table] || []).filter(function (c) { return c.name !== name; });
      cf[state.table].push({ name: name, expr: expr });
      saveCalcFields(cf);
      state.measure = name;
      render(container);
    });
    container.querySelectorAll('[data-delcalc]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const cf = loadCalcFields();
        cf[state.table] = (cf[state.table] || []).filter(function (c) {
          return c.name !== btn.getAttribute('data-delcalc');
        });
        saveCalcFields(cf);
        render(container);
      });
    });
    document.getElementById('bi-save').addEventListener('click', function () {
      const name = prompt('Name this chart:',
        state.agg + ' of ' + state.measure + ' by ' + state.dim);
      if (!name) return;
      const saved2 = loadSaved();
      saved2.push({ name: name, config: JSON.parse(JSON.stringify(state)) });
      saveSavedList(saved2);
      render(container);
    });
    container.querySelectorAll('[data-loadsaved]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        const s = loadSaved()[parseInt(a.getAttribute('data-loadsaved'), 10)];
        if (s) { state = JSON.parse(JSON.stringify(s.config)); render(container); }
      });
    });
    container.querySelectorAll('[data-delsaved]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const saved2 = loadSaved();
        saved2.splice(parseInt(btn.getAttribute('data-delsaved'), 10), 1);
        saveSavedList(saved2);
        render(container);
      });
    });
    document.getElementById('bi-export').addEventListener('click', function () {
      const res = aggregate(rows, state);
      const out = [[state.dim].concat(res.datasets.map(function (d) {
        return d.name === '_' ? state.agg + '_of_' + state.measure : d.name;
      }))];
      res.keys.forEach(function (k, i) {
        out.push(['"' + String(k).replace(/"/g, '""') + '"'].concat(
          res.datasets.map(function (d) { return d.values[i]; })));
      });
      const blob = new Blob([out.map(function (r) { return r.join(','); }).join('\n')],
                            { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'bi_export.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  window.BI_SANDBOX = {
    render: function (container, data) {
      DATA = data;
      state = null;
      render(container);
    },
    _internals: { aggregate: aggregate, compileExpression: compileExpression, buildTables: buildTables },
  };
})();
