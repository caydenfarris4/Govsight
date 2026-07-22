/*
 * GovSight demo data views.
 *
 * Powers the static app's module tabs with real, interactive views over
 * the bundled demo dataset (demo/demo_data.json): charts, tables,
 * filters, a working Monte Carlo simulator, cash flow projection, and a
 * monthly close review that finds the dataset's planted exceptions.
 *
 * Everything is clearly labeled as demo data. When the full platform
 * backend is deployed, these views are replaced by live equivalents.
 */
(function () {
  'use strict';

  let DATA = null;
  let loadPromise = null;
  const charts = {};

  function loadData() {
    if (!loadPromise) {
      loadPromise = fetch('demo/demo_data.json')
        .then(function (r) { if (!r.ok) throw new Error('demo data ' + r.status); return r.json(); })
        .then(function (d) { DATA = d; return d; });
    }
    return loadPromise;
  }

  // ── helpers ────────────────────────────────────────────────────────────
  const fc = function (v) {
    return '$' + Math.round(v).toLocaleString('en-US');
  };
  const fcM = function (v) {
    return Math.abs(v) >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M'
         : Math.abs(v) >= 1e3 ? '$' + (v / 1e3).toFixed(0) + 'k' : fc(v);
  };
  const esc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };

  function demoBanner() {
    return '<div style="background:#e8eef7;color:#24508f;padding:8px 14px;border-radius:8px;' +
           'font-size:12px;font-weight:600;margin-bottom:14px">DEMO DATA - a complete sample city ' +
           '(3 fiscal years, 3,100+ transactions). Connect your ERP through the platform backend to see live figures.</div>';
  }

  function kpi(label, value, sub) {
    return '<div style="background:#fff;border:1px solid #dde4ea;border-radius:10px;padding:14px 16px;min-width:150px;flex:1">' +
           '<div style="font-size:11px;color:#5b6b7a;text-transform:uppercase;letter-spacing:.05em">' + esc(label) + '</div>' +
           '<div style="font-size:22px;font-weight:700;color:#12263a;margin-top:2px">' + value + '</div>' +
           (sub ? '<div style="font-size:11px;color:#5b6b7a;margin-top:2px">' + sub + '</div>' : '') + '</div>';
  }

  function kpiRow(items) {
    return '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">' + items.join('') + '</div>';
  }

  function card(title, inner, extra) {
    return '<div style="background:#fff;border:1px solid #dde4ea;border-radius:10px;padding:16px;margin-bottom:16px">' +
           '<div style="font-weight:600;color:#12263a;margin-bottom:10px">' + esc(title) +
           (extra ? ' <span style="font-weight:400;font-size:12px;color:#5b6b7a">' + extra + '</span>' : '') +
           '</div>' + inner + '</div>';
  }

  function canvasBox(id, height) {
    return '<div style="height:' + (height || 280) + 'px"><canvas id="' + id + '"></canvas></div>';
  }

  function makeChart(id, config) {
    if (typeof Chart === 'undefined') {
      const el = document.getElementById(id);
      if (el && el.parentElement) {
        el.parentElement.innerHTML = '<div style="color:#5b6b7a;font-size:13px;padding:20px">' +
          'Chart library unavailable (offline) - data table views still work.</div>';
      }
      return;
    }
    const el = document.getElementById(id);
    if (!el) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(el.getContext('2d'), config);
  }

  function table(headers, rows, opts) {
    opts = opts || {};
    let html = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px">';
    html += '<thead><tr>' + headers.map(function (h, i) {
      const align = (opts.rightAlign || []).indexOf(i) >= 0 ? 'right' : 'left';
      return '<th style="text-align:' + align + ';padding:8px 10px;border-bottom:2px solid #dde4ea;color:#5b6b7a;font-size:12px">' + esc(h) + '</th>';
    }).join('') + '</tr></thead><tbody>';
    rows.forEach(function (r) {
      html += '<tr>' + r.map(function (c, i) {
        const align = (opts.rightAlign || []).indexOf(i) >= 0 ? 'right' : 'left';
        return '<td style="text-align:' + align + ';padding:7px 10px;border-bottom:1px solid #eef2f5">' + c + '</td>';
      }).join('') + '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
  }

  // Monthly seasonality shares per account type, from history
  function seasonalShares(accountType) {
    const byYear = {};
    const acctType = {};
    DATA.accounts.forEach(function (a) { acctType[a.account_number] = a.account_type; });
    DATA.monthly_actuals.forEach(function (m) {
      if (acctType[m.account_number] !== accountType) return;
      if (m.fiscal_year >= DATA.meta.current_fiscal_year) return;
      const y = byYear[m.fiscal_year] = byYear[m.fiscal_year] || new Array(12).fill(0);
      y[m.month - 1] += m.actual;
    });
    const years = Object.values(byYear);
    if (!years.length) return null;
    const shares = new Array(12).fill(0);
    years.forEach(function (months) {
      const total = months.reduce(function (s, v) { return s + v; }, 0);
      if (total <= 0) return;
      months.forEach(function (v, i) { shares[i] += (v / total) / years.length; });
    });
    return shares;
  }

  function annualTotals(accountType, fy) {
    const acctType = {};
    DATA.accounts.forEach(function (a) { acctType[a.account_number] = a.account_type; });
    let total = 0;
    DATA.monthly_actuals.forEach(function (m) {
      if (acctType[m.account_number] === accountType && m.fiscal_year === fy) total += m.actual;
    });
    return total;
  }

  // ── views ──────────────────────────────────────────────────────────────
  const views = {};

  function finePrint(text) {
    return '<div style="margin-top:10px;padding-top:8px;border-top:1px solid #eef2f5;' +
           'font-size:10.5px;color:#8a97a3;line-height:1.5">Source: ' + text + '</div>';
  }

  function sourceBadge(live, label) {
    return live
      ? '<span style="background:#e2f2e8;color:#1e6b3c;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">LIVE - ' + label + '</span>'
      : '<span style="background:#fdeeda;color:#8a5a12;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700">ESTIMATED - ' + label + ' unavailable</span>';
  }

  function fetchWithTimeout(url, ms) {
    const ctrl = new AbortController();
    const t = setTimeout(function () { ctrl.abort(); }, ms || 7000);
    return fetch(url, { signal: ctrl.signal }).then(function (r) {
      clearTimeout(t);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  // Live demographics for the city of record from the US Census ACS 5-year
  // API (keyless, CORS-enabled). Falls back to the configured estimates.
  function fetchCensusDemographics(city) {
    const vars = ['B01003_001E', 'B01002_001E', 'B19013_001E', 'B25077_001E',
                  'B03002_001E', 'B03002_003E', 'B03002_004E', 'B03002_006E', 'B03002_012E'];
    const url = 'https://api.census.gov/data/2023/acs/acs5?get=' + vars.join(',') +
                '&for=place:' + city.place_fips + '&in=state:' + city.state_fips;
    return fetchWithTimeout(url).then(function (data) {
      const row = {};
      data[0].forEach(function (h, i) { row[h] = parseFloat(data[1][i]); });
      const total = row.B03002_001E || 1;
      const white = row.B03002_003E / total * 100;
      const black = row.B03002_004E / total * 100;
      const asian = row.B03002_006E / total * 100;
      const hispanic = row.B03002_012E / total * 100;
      return {
        live: true, vintage: '2023 ACS 5-year',
        population: row.B01003_001E,
        median_age: row.B01002_001E,
        median_household_income: row.B19013_001E,
        median_home_value: row.B25077_001E,
        ethnicity: {
          'White': Math.round(white * 10) / 10,
          'Hispanic/Latino': Math.round(hispanic * 10) / 10,
          'Black': Math.round(black * 10) / 10,
          'Asian': Math.round(asian * 10) / 10,
          'Other': Math.round(Math.max(0, 100 - white - hispanic - black - asian) * 10) / 10,
        },
      };
    });
  }

  // Live short-term forecast from the National Weather Service (keyless, CORS)
  function fetchWeather(city) {
    return fetchWithTimeout('https://api.weather.gov/points/' + city.latitude + ',' + city.longitude)
      .then(function (p) { return fetchWithTimeout(p.properties.forecast); })
      .then(function (f) {
        const now = f.properties.periods[0];
        return { live: true, name: now.name, temp: now.temperature + '\u00b0' + now.temperatureUnit,
                 detail: now.shortForecast };
      });
  }

  views.econ = function (el) {
    const city = DATA.city || { name: 'your city', state: '', fallback: {} };
    const fb = city.fallback || {};
    el.innerHTML = demoBanner() +
      '<div style="background:#12263a;color:#fff;padding:10px 16px;border-radius:8px;margin-bottom:14px;font-size:13px">' +
      'Localized to <strong>' + esc(city.name) + ', ' + esc(city.state) + '</strong> (city of record - ' +
      'Census place ' + esc(city.state_fips + city.place_fips || '') + '). Demographics pull live from the US Census; ' +
      'estimates are labeled when a feed is unreachable.</div>' +
      '<div id="demo-demographics">' + card('Demographics', '<div style="color:#5b6b7a;font-size:13px">Loading live Census data\u2026</div>') + '</div>' +
      '<div id="demo-zoning"></div>' +
      '<div id="demo-climate">' + card('Climate and Weather', '<div style="color:#5b6b7a;font-size:13px">Loading forecast\u2026</div>') + '</div>' +
      card('Regional Economic Series',
           canvasBox('ec1') +
           finePrint('Demonstration series for the ' + esc(city.name) + ' area. In production these pull live from ' +
             'Federal Reserve Economic Data (FRED, fred.stlouisfed.org) and the U.S. Bureau of Economic Analysis ' +
             '(BEA, bea.gov) with free API keys configured on the platform backend.'),
           esc(city.name) + ' area') +
      card('Local Building Permits',
           canvasBox('ec3', 220) +
           finePrint('Demonstration series. In production, permit counts pull from the city\u2019s permitting ' +
             'system through the data adapter, or from the U.S. Census Building Permits Survey for the region.'),
           'leading indicator for impact fees and the property tax base');

    const renderDemographics = function (d) {
      const eth = d.ethnicity || {};
      document.getElementById('demo-demographics').innerHTML =
        card('Demographics - ' + esc(city.name),
          kpiRow([
            kpi('Population', (d.population || 0).toLocaleString()),
            kpi('Median age', (d.median_age || 0).toFixed(1)),
            kpi('Median household income', fc(d.median_household_income || 0)),
            kpi('Median home value', fc(d.median_home_value || 0))]) +
          '<div style="display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:center">' +
          '<div style="height:220px"><canvas id="eth-chart"></canvas></div>' +
          table(['Group', 'Share'], Object.entries(eth).map(function (e) {
            return [esc(e[0]), e[1].toFixed(1) + '%'];
          }), { rightAlign: [1] }) + '</div>' +
          finePrint(d.live
            ? 'U.S. Census Bureau, American Community Survey 5-Year Estimates (' + (d.vintage || '2023 ACS') +
              '), retrieved live from api.census.gov for Census place ' + esc(city.state_fips + '-' + city.place_fips) +
              ' (' + esc(city.name) + ', ' + esc(city.state_abbr || city.state) + '). Ethnicity shares computed from table B03002.'
            : 'Cached estimates derived from U.S. Census ACS (2023 vintage) for ' + esc(city.name) +
              '; the live api.census.gov feed was unreachable at render time.'),
          sourceBadge(d.live, 'US Census ' + (d.vintage || '')));
      makeChart('eth-chart', { type: 'doughnut', data: {
        labels: Object.keys(eth),
        datasets: [{ data: Object.values(eth),
          backgroundColor: ['#2e6fa3', '#1c6e64', '#8a5a12', '#4169e1', '#5b6b7a'] }] },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'right' } } } });
    };

    fetchCensusDemographics(city).then(renderDemographics).catch(function () {
      renderDemographics({
        live: false,
        population: fb.population, median_age: fb.median_age,
        median_household_income: fb.median_household_income,
        median_home_value: fb.median_home_value, ethnicity: fb.ethnicity || {},
      });
    });

    // Zoning (planning estimates; live GIS feed is city-configurable)
    const zoning = (fb.zoning || {});
    const zb = zoning.breakdown || {};
    document.getElementById('demo-zoning').innerHTML =
      card('Zoning Mix - ' + esc(city.name),
        '<div style="display:grid;grid-template-columns:280px 1fr;gap:16px;align-items:center">' +
        '<div style="height:220px"><canvas id="zone-chart"></canvas></div>' +
        table(['Zone', 'Share of area'], Object.entries(zb).map(function (e) {
          return [esc(e[0]), e[1].toFixed(1) + '%'];
        }), { rightAlign: [1] }) + '</div>' +
        '<div style="font-size:12px;color:#5b6b7a;margin-top:8px">Total area ~' +
        (zoning.total_area_acres || 0).toLocaleString() + ' acres.</div>' +
        finePrint(esc(zoning.source || 'Municipal planning estimates') +
          ' for ' + esc(city.name) + '. A live parcel-level feed from the city\u2019s GIS server ' +
          '(ArcGIS REST) can be configured per municipality on the platform backend.'));
    makeChart('zone-chart', { type: 'doughnut', data: {
      labels: Object.keys(zb),
      datasets: [{ data: Object.values(zb),
        backgroundColor: ['#2e6fa3', '#4169e1', '#8a5a12', '#5b6b7a', '#1c6e64', '#12263a', '#a4271c'] }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'right' } } } });

    // Climate and live weather
    const renderClimate = function (weather) {
      const cl = fb.climate || {};
      document.getElementById('demo-climate').innerHTML =
        card('Climate and Weather - ' + esc(city.name),
          kpiRow([
            weather ? kpi(weather.name || 'Now', weather.temp, esc(weather.detail || '')) :
                      kpi('Current forecast', 'unavailable'),
            kpi('Avg annual temp', (cl.avg_temp_f || 0) + '\u00b0F'),
            kpi('Annual precipitation', (cl.annual_precipitation_in || 0) + ' in'),
            kpi('Days over 90\u00b0F', cl.heat_days_over_90 || 0)]) +
          finePrint((weather
            ? 'Current forecast retrieved live from the National Weather Service (api.weather.gov) for ' +
              city.latitude + ', ' + city.longitude + ' (' + esc(city.name) + '). '
            : 'The live National Weather Service feed was unreachable at render time. ') +
            'Climate normals (temperature, precipitation, heat days) are NOAA-derived local estimates for ' +
            esc(city.name) + '.'),
          sourceBadge(!!weather, 'National Weather Service'));
    };
    fetchWeather(city).then(renderClimate).catch(function () { renderClimate(null); });

    const e = DATA.economic;
    makeChart('ec1', { type: 'line', data: { labels: e.months, datasets: [
      { label: 'CPI YoY %', data: e.cpi_yoy, borderColor: '#c62828', tension: 0.3 },
      { label: 'Unemployment %', data: e.unemployment, borderColor: '#2e6fa3', tension: 0.3 },
      { label: 'Fed funds %', data: e.fed_funds, borderColor: '#12263a', tension: 0.3 }] },
      options: { responsive: true, maintainAspectRatio: false } });
    makeChart('ec3', { type: 'bar', data: { labels: e.months, datasets: [
      { label: 'Permits', data: e.local_permits, backgroundColor: '#1c6e64' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } });
  };

  views.reportComparison = function (el) {
    const rows = DATA.scenarios.map(function (s) {
      const funding = s.tax_revenue + s.grant_funding + s.bonds + s.reallocation;
      const gap = funding - s.total_cost;
      return [esc(s.name), s.created, fcM(s.total_cost), fcM(funding),
        '<span style="font-weight:700;color:' + (gap >= 0 ? '#1e6b3c' : '#a4271c') + '">' + fcM(gap) + '</span>',
        esc(s.note)];
    });
    el.innerHTML = demoBanner() +
      card('Saved Scenario Comparison',
        table(['Scenario', 'Created', 'Total Cost', 'Total Funding', 'Surplus / (Gap)', 'Notes'], rows,
          { rightAlign: [2, 3, 4] })) +
      card('Funding Mix by Scenario', canvasBox('rc1'));
    makeChart('rc1', { type: 'bar',
      data: { labels: DATA.scenarios.map(function (s) { return s.name; }), datasets: [
        { label: 'Tax revenue', data: DATA.scenarios.map(function (s) { return s.tax_revenue; }), backgroundColor: '#2e6fa3' },
        { label: 'Grants', data: DATA.scenarios.map(function (s) { return s.grant_funding; }), backgroundColor: '#1c6e64' },
        { label: 'Bonds', data: DATA.scenarios.map(function (s) { return s.bonds; }), backgroundColor: '#8a5a12' },
        { label: 'Reallocation', data: DATA.scenarios.map(function (s) { return s.reallocation; }), backgroundColor: '#5b6b7a' }] },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true, ticks: { callback: function (v) { return fcM(v); } } } } } });
  };

  views.risk = function (el) {
    el.innerHTML = demoBanner() +
      card('Monte Carlo Budget Risk Simulation',
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:12px">' +
        ['revMin:Minimum revenue:19000000', 'revLikely:Most likely revenue:20200000', 'revMax:Maximum revenue:21200000',
         'costMin:Minimum cost:33200000', 'costLikely:Most likely cost:34900000', 'costMax:Maximum cost:36800000']
          .map(function (spec) {
            const p = spec.split(':');
            return '<label style="font-size:12px;color:#5b6b7a">' + p[1] +
              '<input id="mc-' + p[0] + '" type="number" value="' + p[2] + '" step="100000" ' +
              'style="width:100%;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>';
          }).join('') +
        '</div><button id="mc-run" style="background:#1d3a56;color:#fff;border:none;border-radius:8px;' +
        'padding:9px 22px;font-weight:600;cursor:pointer">Run 5,000 simulations</button>' +
        '<div id="mc-stats" style="margin-top:14px"></div>', 'other-revenue held at baseline') +
      card('Outcome Distribution (net position incl. other revenue)', canvasBox('mc-chart'));
    document.getElementById('mc-run').addEventListener('click', function () {
      const g = function (id) { return parseFloat(document.getElementById('mc-' + id).value) || 0; };
      const tri = function (lo, mode, hi) {
        const u = Math.random(), c = (mode - lo) / (hi - lo || 1);
        return u < c ? lo + Math.sqrt(u * (hi - lo) * (mode - lo))
                     : hi - Math.sqrt((1 - u) * (hi - lo) * (hi - mode));
      };
      const otherRevenue = 15400000; // non-simulated demo revenue held constant
      const outcomes = [];
      for (let i = 0; i < 5000; i++) {
        outcomes.push(tri(g('revMin'), g('revLikely'), g('revMax')) + otherRevenue -
                      tri(g('costMin'), g('costLikely'), g('costMax')));
      }
      outcomes.sort(function (a, b) { return a - b; });
      const mean = outcomes.reduce(function (s, v) { return s + v; }, 0) / outcomes.length;
      const pct = function (p) { return outcomes[Math.floor(p * outcomes.length)]; };
      const deficitRisk = outcomes.filter(function (v) { return v < 0; }).length / outcomes.length * 100;
      document.getElementById('mc-stats').innerHTML = kpiRow([
        kpi('Mean outcome', fcM(mean)),
        kpi('5th percentile', fcM(pct(0.05))),
        kpi('95th percentile', fcM(pct(0.95))),
        kpi('Deficit risk', deficitRisk.toFixed(1) + '%',
            deficitRisk > 30 ? 'HIGH' : deficitRisk > 15 ? 'ELEVATED' : 'LOW')]);
      const bins = 24, lo = outcomes[0], hi = outcomes[outcomes.length - 1];
      const width = (hi - lo) / bins || 1;
      const freq = new Array(bins).fill(0);
      outcomes.forEach(function (v) { freq[Math.min(bins - 1, Math.floor((v - lo) / width))]++; });
      makeChart('mc-chart', { type: 'bar',
        data: { labels: freq.map(function (_, i) { return fcM(lo + width * (i + 0.5)); }),
          datasets: [{ label: 'Simulations', data: freq,
            backgroundColor: freq.map(function (_, i) { return lo + width * (i + 0.5) < 0 ? '#c62828' : '#2e6fa3'; }) }] },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 9 } } } } });
    });
  };

  views.pbb = function (el) {
    // Excel-style position budgeting workbook: edit cells, test assumptions,
    // compare against the adopted baseline, save the sandbox locally.
    const LS = 'gs_pbb_sandbox_v1';
    const baseline = DATA.positions.map(function (p) {
      return { position_id: p.position_id, title: p.title, department: p.department,
               fte: p.fte, salary: p.annual_salary, benefits: p.benefits_pct * 100,
               status: p.status, start_month: 1 };
    });
    let rows;
    try { rows = JSON.parse(localStorage.getItem(LS)) || null; } catch (e) { rows = null; }
    if (!rows) rows = JSON.parse(JSON.stringify(baseline));
    let assume = { cola: 3.0, benefitsInfl: 0.0, vacancyFactor: 50 };
    try { assume = Object.assign(assume, JSON.parse(localStorage.getItem(LS + '_assume')) || {}); }
    catch (e) { /* defaults */ }

    const loadedCost = function (r, a) {
      const salary = r.salary * (1 + a.cola / 100);
      const benefits = (r.benefits + a.benefitsInfl) / 100;
      let proration = 1.0;
      if (r.status === 'New Hire') proration = (13 - Math.min(12, Math.max(1, r.start_month))) / 12;
      if (r.status === 'Vacant') proration = 1 - a.vacancyFactor / 100;
      return r.fte * salary * (1 + benefits) * proration;
    };
    const baselineTotal = baseline.reduce(function (s, r) {
      return s + loadedCost(r, { cola: 0, benefitsInfl: 0, vacancyFactor: 0 });
    }, 0);

    const baseMap = {};
    baseline.forEach(function (r) { baseMap[r.position_id] = r; });
    const isDirty = function (r) {
      const b = baseMap[r.position_id];
      return !b || b.fte !== r.fte || b.salary !== r.salary ||
             b.benefits !== r.benefits || b.status !== r.status ||
             (r.status === 'New Hire' && r.start_month !== b.start_month);
    };

    const num = function (v, dp) { return Number(v).toLocaleString('en-US', { maximumFractionDigits: dp || 0 }); };
    const cellStyle = 'width:100%;border:1px solid transparent;background:transparent;padding:5px 6px;' +
                      'font-size:13px;text-align:right;border-radius:4px';

    function render() {
      const total = rows.reduce(function (s, r) { return s + loadedCost(r, assume); }, 0);
      const byDept = {};
      rows.forEach(function (r) { byDept[r.department] = (byDept[r.department] || 0) + loadedCost(r, assume); });
      const vacantSavings = rows.filter(function (r) { return r.status === 'Vacant'; })
        .reduce(function (s, r) { return s + loadedCost(r, { cola: assume.cola, benefitsInfl: assume.benefitsInfl, vacancyFactor: 0 }) - loadedCost(r, assume); }, 0);

      let grid = '<div style="overflow-x:auto"><table id="pbb-grid" style="width:100%;border-collapse:collapse;font-size:13px;background:#fff">';
      grid += '<thead><tr>' + ['Position', 'Department', 'FTE', 'Base Salary', 'Benefits %', 'Status', 'Start Mo', 'Loaded Cost', ''].map(function (h, i) {
        return '<th style="text-align:' + (i >= 2 && i <= 7 ? 'right' : 'left') + ';padding:8px;border-bottom:2px solid #dde4ea;color:#5b6b7a;font-size:12px;position:sticky;top:0;background:#fff">' + h + '</th>';
      }).join('') + '</tr></thead><tbody>';
      const depts = Array.from(new Set(rows.map(function (r) { return r.department; })));
      depts.forEach(function (dept) {
        grid += '<tr><td colspan="7" style="background:#eef3f8;padding:6px 8px;font-weight:700;color:#12263a;font-size:12px">' + esc(dept) + '</td>' +
          '<td style="background:#eef3f8;text-align:right;padding:6px 8px;font-weight:700;font-size:12px" class="dept-total" data-dept="' + esc(dept) + '">$' + num(byDept[dept]) + '</td><td style="background:#eef3f8"></td></tr>';
        rows.forEach(function (r, idx) {
          if (r.department !== dept) return;
          const dirty = isDirty(r);
          const bg = dirty ? 'background:#fff8e1;' : '';
          grid += '<tr data-idx="' + idx + '"' + (dirty ? ' class="dirty"' : '') + '>' +
            '<td style="padding:2px 4px;' + bg + '"><input data-f="title" value="' + esc(r.title) + '" style="' + cellStyle + ';text-align:left;font-weight:600"></td>' +
            '<td style="padding:2px 8px;font-size:12px;color:#5b6b7a;' + bg + '">' + esc(r.department) + '</td>' +
            '<td style="padding:2px 4px;' + bg + '"><input data-f="fte" type="number" step="0.25" min="0" value="' + r.fte + '" style="' + cellStyle + '"></td>' +
            '<td style="padding:2px 4px;' + bg + '"><input data-f="salary" type="number" step="1000" min="0" value="' + r.salary + '" style="' + cellStyle + '"></td>' +
            '<td style="padding:2px 4px;' + bg + '"><input data-f="benefits" type="number" step="0.5" min="0" value="' + r.benefits + '" style="' + cellStyle + '"></td>' +
            '<td style="padding:2px 4px;' + bg + '"><select data-f="status" style="' + cellStyle + ';text-align:left">' +
              ['Filled', 'Vacant', 'New Hire'].map(function (s) {
                return '<option' + (r.status === s ? ' selected' : '') + '>' + s + '</option>';
              }).join('') + '</select></td>' +
            '<td style="padding:2px 4px;' + bg + '"><input data-f="start_month" type="number" min="1" max="12" value="' + r.start_month + '" ' +
              (r.status === 'New Hire' ? '' : 'disabled') + ' style="' + cellStyle + '"></td>' +
            '<td class="loaded" style="padding:5px 8px;text-align:right;font-weight:600;' + bg + '">$' + num(loadedCost(r, assume)) + '</td>' +
            '<td style="padding:2px 4px;text-align:center"><button data-remove="' + idx + '" title="Remove position" style="border:none;background:none;color:#a4271c;cursor:pointer;font-weight:700">&times;</button></td></tr>';
        });
      });
      grid += '</tbody></table></div>';

      el.innerHTML = demoBanner() +
        card('Workbook Assumptions',
          '<div style="display:flex;gap:18px;flex-wrap:wrap;align-items:flex-end">' +
          '<label style="font-size:12px;color:#5b6b7a">COLA %<input id="pbb-cola" type="number" step="0.25" value="' + assume.cola + '" style="display:block;width:90px;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>' +
          '<label style="font-size:12px;color:#5b6b7a">Benefits inflation (pp)<input id="pbb-binfl" type="number" step="0.25" value="' + assume.benefitsInfl + '" style="display:block;width:90px;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>' +
          '<label style="font-size:12px;color:#5b6b7a">Vacancy savings %<input id="pbb-vac" type="number" step="5" min="0" max="100" value="' + assume.vacancyFactor + '" style="display:block;width:90px;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>' +
          '<button id="pbb-add" style="background:#1d3a56;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer">Add Position</button>' +
          '<button id="pbb-save" style="background:#1e6b3c;color:#fff;border:none;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer">Save Sandbox</button>' +
          '<button id="pbb-reset" style="background:#fff;color:#a4271c;border:1px solid #a4271c;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer">Reset to Baseline</button>' +
          '<button id="pbb-export" style="background:#fff;color:#12263a;border:1px solid #cfd8e0;border-radius:8px;padding:8px 16px;font-weight:600;cursor:pointer">Export CSV</button>' +
          '<span id="pbb-msg" style="font-size:12px;color:#1e6b3c;font-weight:600"></span></div>',
          'edit any cell - totals and the baseline delta update live; changed cells highlight') +
        '<div id="pbb-kpis">' + kpiRow([
          kpi('Positions', rows.length),
          kpi('Total loaded cost', '<span id="pbb-total">' + fcM(total) + '</span>', 'with assumptions applied'),
          kpi('vs adopted baseline', '<span id="pbb-delta">' + (total >= baselineTotal ? '+' : '') + fcM(total - baselineTotal) + '</span>'),
          kpi('Vacancy savings', '<span id="pbb-vacsave">' + fcM(vacantSavings) + '</span>')]) + '</div>' +
        card('Position Workbook', grid);

      const recalcTotals = function () {
        const total2 = rows.reduce(function (s, r) { return s + loadedCost(r, assume); }, 0);
        const byDept2 = {};
        rows.forEach(function (r) { byDept2[r.department] = (byDept2[r.department] || 0) + loadedCost(r, assume); });
        document.getElementById('pbb-total').textContent = fcM(total2);
        document.getElementById('pbb-delta').textContent = (total2 >= baselineTotal ? '+' : '') + fcM(total2 - baselineTotal);
        const vs = rows.filter(function (r) { return r.status === 'Vacant'; })
          .reduce(function (s, r) { return s + loadedCost(r, { cola: assume.cola, benefitsInfl: assume.benefitsInfl, vacancyFactor: 0 }) - loadedCost(r, assume); }, 0);
        document.getElementById('pbb-vacsave').textContent = fcM(vs);
        el.querySelectorAll('.dept-total').forEach(function (td) {
          td.textContent = '$' + num(byDept2[td.getAttribute('data-dept')] || 0);
        });
        el.querySelectorAll('tr[data-idx]').forEach(function (tr) {
          const r = rows[parseInt(tr.getAttribute('data-idx'), 10)];
          tr.querySelector('.loaded').textContent = '$' + num(loadedCost(r, assume));
        });
      };

      el.querySelectorAll('tr[data-idx] input, tr[data-idx] select').forEach(function (input) {
        input.addEventListener('input', function () {
          const idx = parseInt(input.closest('tr').getAttribute('data-idx'), 10);
          const f = input.getAttribute('data-f');
          rows[idx][f] = (f === 'title' || f === 'status') ? input.value : parseFloat(input.value) || 0;
          if (f === 'status') { render(); return; }   // toggles start-month cell
          recalcTotals();
        });
      });
      el.querySelectorAll('[data-remove]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          rows.splice(parseInt(btn.getAttribute('data-remove'), 10), 1);
          render();
        });
      });
      ['cola:cola', 'binfl:benefitsInfl', 'vac:vacancyFactor'].forEach(function (spec) {
        const parts = spec.split(':');
        document.getElementById('pbb-' + parts[0]).addEventListener('input', function (e) {
          assume[parts[1]] = parseFloat(e.target.value) || 0;
          recalcTotals();
        });
      });
      document.getElementById('pbb-add').addEventListener('click', function () {
        rows.push({ position_id: 'NEW-' + Date.now(), title: 'New Position',
                    department: rows.length ? rows[rows.length - 1].department : 'Administration',
                    fte: 1.0, salary: 60000, benefits: 32, status: 'New Hire', start_month: 7 });
        render();
      });
      document.getElementById('pbb-save').addEventListener('click', function () {
        localStorage.setItem(LS, JSON.stringify(rows));
        localStorage.setItem(LS + '_assume', JSON.stringify(assume));
        document.getElementById('pbb-msg').textContent = 'Sandbox saved.';
        setTimeout(function () {
          const msg = document.getElementById('pbb-msg');
          if (msg) msg.textContent = '';
        }, 2500);
      });
      document.getElementById('pbb-reset').addEventListener('click', function () {
        rows = JSON.parse(JSON.stringify(baseline));
        assume = { cola: 3.0, benefitsInfl: 0.0, vacancyFactor: 50 };
        localStorage.removeItem(LS);
        localStorage.removeItem(LS + '_assume');
        render();
      });
      document.getElementById('pbb-export').addEventListener('click', function () {
        const out = [['position', 'department', 'fte', 'base_salary', 'benefits_pct', 'status', 'start_month', 'loaded_cost']];
        rows.forEach(function (r) {
          out.push(['"' + r.title.replace(/"/g, '""') + '"', r.department, r.fte, r.salary,
                    r.benefits, r.status, r.start_month, Math.round(loadedCost(r, assume))]);
        });
        const blob = new Blob([out.map(function (r) { return r.join(','); }).join('\n')], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'pbb_sandbox.csv';
        a.click();
        URL.revokeObjectURL(a.href);
      });
    }
    render();
  };

  views.predictive = function (el) {
    el.innerHTML = demoBanner() +
      card('Revenue Forecast - next 12 months', canvasBox('pf1', 320),
        'seasonal share method fit on two prior fiscal years; measured on real demo history') +
      '<div id="pf-note"></div>';
    const shares = seasonalShares('Revenue');
    const priorYears = [DATA.meta.current_fiscal_year - 2, DATA.meta.current_fiscal_year - 1];
    const totals = priorYears.map(function (fy) { return annualTotals('Revenue', fy); });
    const growth = totals[0] > 0 ? totals[1] / totals[0] : 1.03;
    const nextTotal = totals[1] * growth;
    const labels = [], history = [], forecast = [];
    const byMonth = {};
    DATA.monthly_actuals.forEach(function (m) {
      const a = DATA.accounts.find(function (x) { return x.account_number === m.account_number; });
      if (!a || a.account_type !== 'Revenue') return;
      const key = m.fiscal_year + '-' + String(m.month).padStart(2, '0');
      byMonth[key] = (byMonth[key] || 0) + m.actual;
    });
    Object.keys(byMonth).sort().forEach(function (k) { labels.push(k); history.push(byMonth[k]); forecast.push(null); });
    let y = DATA.meta.current_fiscal_year, mo = DATA.meta.months_elapsed + 1;
    for (let i = 0; i < 12; i++) {
      labels.push(y + '-' + String(mo).padStart(2, '0'));
      history.push(null);
      forecast.push(nextTotal * shares[mo - 1]);
      mo++; if (mo > 12) { mo = 1; y++; }
    }
    makeChart('pf1', { type: 'line', data: { labels: labels, datasets: [
      { label: 'Actual monthly revenue', data: history, borderColor: '#2e6fa3', tension: 0.25 },
      { label: 'Forecast', data: forecast, borderColor: '#8a5a12', borderDash: [6, 4], tension: 0.25 }] },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { y: { ticks: { callback: function (v) { return fcM(v); } } }, x: { ticks: { maxTicksLimit: 14 } } } } });
    document.getElementById('pf-note').innerHTML =
      kpiRow([kpi('Prior-year revenue', fcM(totals[1])),
              kpi('Observed growth', ((growth - 1) * 100).toFixed(1) + '%'),
              kpi('Next-12-month forecast', fcM(nextTotal), 'seasonal shares applied')]);
  };

  views.cashflow = function (el) {
    el.innerHTML = demoBanner() +
      card('Inputs',
        '<div style="display:flex;gap:14px;flex-wrap:wrap">' +
        '<label style="font-size:12px;color:#5b6b7a">Current cash balance' +
        '<input id="cf-bal" type="number" value="8200000" step="250000" style="display:block;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>' +
        '<label style="font-size:12px;color:#5b6b7a">Operating floor' +
        '<input id="cf-floor" type="number" value="4000000" step="250000" style="display:block;padding:6px 8px;border:1px solid #cfd8e0;border-radius:6px;margin-top:3px"></label>' +
        '<button id="cf-run" style="background:#1d3a56;color:#fff;border:none;border-radius:8px;padding:9px 20px;font-weight:600;cursor:pointer;align-self:flex-end">Project 12 months</button></div>' +
        '<div id="cf-stats" style="margin-top:12px"></div>') +
      card('Projected Cash Balance vs Operating Floor', canvasBox('cf-chart', 320),
        'receipts and disbursements follow each type\'s historical monthly seasonality');
    const run = function () {
      const start = parseFloat(document.getElementById('cf-bal').value) || 0;
      const floor = parseFloat(document.getElementById('cf-floor').value) || 0;
      const revShares = seasonalShares('Revenue'), expShares = seasonalShares('Expense');
      const annualRev = DATA.accounts.filter(function (a) { return a.account_type === 'Revenue'; })
        .reduce(function (s, a) { return s + a.budget_amount; }, 0);
      const annualExp = DATA.accounts.filter(function (a) { return a.account_type === 'Expense'; })
        .reduce(function (s, a) { return s + a.budget_amount; }, 0);
      let bal = start, y = DATA.meta.current_fiscal_year, mo = DATA.meta.months_elapsed + 1;
      const labels = [], balances = [], receipts = [], disb = [];
      for (let i = 0; i < 12; i++) {
        const r = annualRev * revShares[mo - 1], d = annualExp * expShares[mo - 1];
        bal += r - d;
        labels.push(y + '-' + String(mo).padStart(2, '0'));
        balances.push(bal); receipts.push(r); disb.push(-d);
        mo++; if (mo > 12) { mo = 1; y++; }
      }
      const minBal = Math.min.apply(null, balances);
      const minMonth = labels[balances.indexOf(minBal)];
      const investable = function (n) {
        return Math.max(0, Math.min.apply(null, balances.slice(0, n).map(function (b) { return b - floor; })));
      };
      const below = labels.filter(function (_, i) { return balances[i] < floor; });
      document.getElementById('cf-stats').innerHTML =
        kpiRow([kpi('Lowest balance', fcM(minBal), minMonth),
                kpi('Months below floor', below.length, below.slice(0, 3).join(', ')),
                kpi('Investable 90 days', fcM(investable(3))),
                kpi('Investable 12 months', fcM(investable(12)))]);
      makeChart('cf-chart', { type: 'bar', data: { labels: labels, datasets: [
        { type: 'bar', label: 'Receipts', data: receipts, backgroundColor: '#2e7d32' },
        { type: 'bar', label: 'Disbursements', data: disb, backgroundColor: '#c62828' },
        { type: 'line', label: 'Ending balance', data: balances, borderColor: '#12263a', tension: 0.25 },
        { type: 'line', label: 'Operating floor', data: labels.map(function () { return floor; }),
          borderColor: '#8a5a12', borderDash: [6, 4], pointRadius: 0 }] },
        options: { responsive: true, maintainAspectRatio: false,
          scales: { y: { ticks: { callback: function (v) { return fcM(v); } } } } } });
    };
    document.getElementById('cf-run').addEventListener('click', run);
    run();
  };

  views.bi = function (el) {
    el.innerHTML = demoBanner() + '<div id="bi-root"></div>';
    if (window.BI_SANDBOX) {
      window.BI_SANDBOX.render(document.getElementById('bi-root'), DATA);
    } else {
      document.getElementById('bi-root').innerHTML =
        '<div style="padding:30px;color:#a4271c">Analytics builder failed to load.</div>';
    }
  };

  views.historical = function (el) {
    const years = [2024, 2025, 2026];
    const rev = years.map(function (fy) { return annualTotals('Revenue', fy); });
    const exp = years.map(function (fy) { return annualTotals('Expense', fy); });
    el.innerHTML = demoBanner() +
      kpiRow([kpi('FY2025 revenue', fcM(rev[1])), kpi('FY2025 expenditures', fcM(exp[1])),
              kpi('FY2026 YTD revenue', fcM(rev[2]), '6 months'), kpi('FY2026 YTD spend', fcM(exp[2]), '6 months')]) +
      card('Revenue vs Expenditures by Fiscal Year', canvasBox('ha-chart', 300),
        'FY2026 is six months elapsed') +
      '<div id="ha-var"></div>';
    makeChart('ha-chart', { type: 'bar', data: { labels: years.map(String), datasets: [
      { label: 'Revenue', data: rev, backgroundColor: '#2e7d32' },
      { label: 'Expenditures', data: exp, backgroundColor: '#c62828' }] },
      options: { responsive: true, maintainAspectRatio: false,
        scales: { y: { ticks: { callback: function (v) { return fcM(v); } } } } } });
    const deptRows = {};
    DATA.accounts.forEach(function (a) {
      if (a.account_type !== 'Expense') return;
      const d = deptRows[a.department] = deptRows[a.department] || { budget: 0, actual: 0 };
      d.budget += a.budget_amount; d.actual += a.ytd_actual;
    });
    document.getElementById('ha-var').innerHTML = card('FY2026 Department Budget vs YTD Actual',
      table(['Department', 'Annual Budget', 'YTD Actual', '% Used'],
        Object.entries(deptRows).sort(function (a, b) { return b[1].budget - a[1].budget; })
          .map(function (e) {
            const pct = e[1].budget ? e[1].actual / e[1].budget * 100 : 0;
            return [esc(e[0]), fc(e[1].budget), fc(e[1].actual),
              '<span style="font-weight:700;color:' + (pct > 58 ? '#a4271c' : pct < 40 ? '#8a5a12' : '#1e6b3c') + '">' +
              pct.toFixed(1) + '%</span>'];
          }), { rightAlign: [1, 2, 3] }),
      'six months elapsed - roughly 50% is on pace');
  };

  views.deptInsights = function (el) {
    const expShares = seasonalShares('Expense');
    const expectedShare = expShares.slice(0, DATA.meta.months_elapsed)
      .reduce(function (s, v) { return s + v; }, 0);
    const deptAgg = {};
    DATA.accounts.forEach(function (a) {
      if (a.account_type !== 'Expense') return;
      const d = deptAgg[a.department] = deptAgg[a.department] || { budget: 0, actual: 0 };
      d.budget += a.budget_amount; d.actual += a.ytd_actual;
    });
    const rows = Object.entries(deptAgg).map(function (e) {
      const pace = e[1].budget ? e[1].actual / e[1].budget : 0;
      const dev = (pace - expectedShare) * 100;
      return { dept: e[0], budget: e[1].budget, actual: e[1].actual, pace: pace * 100, dev: dev };
    }).sort(function (a, b) { return Math.abs(b.dev) - Math.abs(a.dev); });
    const flagged = rows.filter(function (r) { return Math.abs(r.dev) > 8; });
    el.innerHTML = demoBanner() +
      (flagged.length ? flagged.map(function (r) {
        const over = r.dev > 0;
        return '<div style="background:' + (over ? '#fdecea' : '#fdeeda') + ';color:' + (over ? '#a4271c' : '#8a5a12') +
          ';padding:10px 14px;border-radius:8px;margin-bottom:8px;font-size:13px"><strong>' +
          (over ? 'OVER PACE' : 'UNDER PACE') + ':</strong> ' + esc(r.dept) + ' has spent ' + r.pace.toFixed(1) +
          '% of budget vs a typical ' + (expectedShare * 100).toFixed(1) + '% by this point (' +
          (r.dev > 0 ? '+' : '') + r.dev.toFixed(1) + ' pp). Projected full year: ' +
          fcM(r.actual / Math.max(0.05, expectedShare)) + ' vs budget ' + fcM(r.budget) + '.</div>';
      }).join('') : '<div style="background:#e2f2e8;color:#1e6b3c;padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px">All departments are pacing within 8 points of their historical pattern.</div>') +
      card('Department Pacing vs Historical Pattern',
        table(['Department', 'Annual Budget', 'YTD Actual', '% Spent', 'Typical % by now', 'Deviation'],
          rows.map(function (r) {
            return [esc(r.dept), fc(r.budget), fc(r.actual), r.pace.toFixed(1) + '%',
              (expectedShare * 100).toFixed(1) + '%',
              '<span style="font-weight:700;color:' + (Math.abs(r.dev) > 8 ? '#a4271c' : '#1e6b3c') + '">' +
              (r.dev > 0 ? '+' : '') + r.dev.toFixed(1) + ' pp</span>'];
          }), { rightAlign: [1, 2, 3, 4, 5] }));
  };

  views.transactions = function (el) {
    const depts = ['All'].concat(DATA.departments);
    el.innerHTML = demoBanner() +
      '<div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap">' +
      '<select id="tx-dept" style="padding:7px 10px;border:1px solid #cfd8e0;border-radius:6px">' +
      depts.map(function (d) { return '<option>' + esc(d) + '</option>'; }).join('') + '</select>' +
      '<input id="tx-search" placeholder="Search vendor or description" style="flex:1;min-width:200px;padding:7px 10px;border:1px solid #cfd8e0;border-radius:6px">' +
      '<input id="tx-min" type="number" placeholder="Min $" style="width:110px;padding:7px 10px;border:1px solid #cfd8e0;border-radius:6px"></div>' +
      '<div id="tx-kpis"></div>' + card('Monthly Spend', canvasBox('tx-chart', 220)) +
      '<div id="tx-table"></div><div id="tx-pager" style="text-align:center;margin:10px 0"></div>';
    let pageN = 0;
    const PAGE = 50;
    const render = function () {
      const dept = document.getElementById('tx-dept').value;
      const q = document.getElementById('tx-search').value.toLowerCase();
      const min = parseFloat(document.getElementById('tx-min').value) || 0;
      const rows = DATA.transactions.filter(function (t) {
        return (dept === 'All' || t.department === dept) &&
               t.amount >= min &&
               (!q || (t.vendor + ' ' + t.description).toLowerCase().indexOf(q) >= 0);
      }).sort(function (a, b) { return b.date.localeCompare(a.date); });
      const total = rows.reduce(function (s, t) { return s + t.amount; }, 0);
      document.getElementById('tx-kpis').innerHTML = kpiRow([
        kpi('Transactions', rows.length.toLocaleString()),
        kpi('Total amount', fcM(total)),
        kpi('Distinct vendors', new Set(rows.map(function (t) { return t.vendor; })).size)]);
      const byMonth = {};
      rows.forEach(function (t) { const k = t.date.slice(0, 7); byMonth[k] = (byMonth[k] || 0) + t.amount; });
      const months = Object.keys(byMonth).sort();
      makeChart('tx-chart', { type: 'bar', data: { labels: months,
        datasets: [{ label: 'Spend', data: months.map(function (m) { return byMonth[m]; }), backgroundColor: '#2e6fa3' }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
          scales: { y: { ticks: { callback: function (v) { return fcM(v); } } } } } });
      const pages = Math.max(1, Math.ceil(rows.length / PAGE));
      pageN = Math.min(pageN, pages - 1);
      const slice = rows.slice(pageN * PAGE, (pageN + 1) * PAGE);
      document.getElementById('tx-table').innerHTML = card('Transaction Detail',
        table(['Date', 'Vendor', 'Department', 'Account', 'Description', 'Amount'],
          slice.map(function (t) {
            return [t.date, esc(t.vendor), esc(t.department), t.account_number,
              esc(t.description), fc(t.amount)];
          }), { rightAlign: [5] }));
      document.getElementById('tx-pager').innerHTML =
        '<button id="tx-prev" ' + (pageN === 0 ? 'disabled' : '') + ' style="padding:6px 14px;margin-right:8px">Previous</button>' +
        'Page ' + (pageN + 1) + ' of ' + pages +
        '<button id="tx-next" ' + (pageN >= pages - 1 ? 'disabled' : '') + ' style="padding:6px 14px;margin-left:8px">Next</button>';
      document.getElementById('tx-prev').onclick = function () { pageN--; render(); };
      document.getElementById('tx-next').onclick = function () { pageN++; render(); };
    };
    ['tx-dept', 'tx-search', 'tx-min'].forEach(function (id) {
      document.getElementById(id).addEventListener('input', function () { pageN = 0; render(); });
    });
    render();
  };

  views.balance = function (el) {
    const byCat = {};
    DATA.balance_sheet.forEach(function (b) { byCat[b.category] = (byCat[b.category] || 0) + b.amount; });
    const assets = byCat['Asset'] || 0, liabilities = byCat['Liability'] || 0;
    const fundBal = byCat['Fund Balance'] || 0;
    const gfExp = DATA.accounts.filter(function (a) { return a.account_type === 'Expense' && a.fund === '10'; })
      .reduce(function (s, a) { return s + a.budget_amount; }, 0);
    const unassigned = DATA.balance_sheet.find(function (b) { return b.name.indexOf('Unassigned') >= 0; });
    const months = unassigned ? unassigned.amount / (gfExp / 12) : 0;
    const floor = DATA.reserve_policy_months;
    el.innerHTML = demoBanner() +
      kpiRow([kpi('Total assets', fcM(assets)), kpi('Total liabilities', fcM(liabilities)),
              kpi('Fund balance / net position', fcM(fundBal)),
              kpi('Reserves', months.toFixed(1) + ' months',
                  'GFOA floor: ' + floor.toFixed(1) + ' months of GF spend')]) +
      (months < floor
        ? '<div style="background:#fdecea;color:#a4271c;padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px">Unassigned reserves are below the ' + floor.toFixed(1) + '-month policy floor.</div>'
        : '<div style="background:#e2f2e8;color:#1e6b3c;padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px">Unassigned general fund reserves cover ' + months.toFixed(1) + ' months of spending - above the ' + floor.toFixed(1) + '-month policy floor.</div>') +
      card('Balance Sheet by Fund',
        table(['Account', 'Name', 'Fund', 'Category', 'Amount'],
          DATA.balance_sheet.map(function (b) {
            const fund = DATA.funds.find(function (f) { return f.code === b.fund; });
            return [b.account, esc(b.name), esc(fund ? fund.name : b.fund), b.category, fc(b.amount)];
          }), { rightAlign: [4] }));
  };

  views.close = function (el) {
    el.innerHTML = demoBanner() +
      card('Monthly Close Review - June 2026',
        '<button id="close-run" style="background:#1d3a56;color:#fff;border:none;border-radius:8px;padding:9px 22px;font-weight:600;cursor:pointer">Run close review</button>' +
        '<div id="close-out" style="margin-top:14px"></div>',
        'unusual amounts, duplicates, and split-purchase patterns');
    document.getElementById('close-run').addEventListener('click', function () {
      const month = '2026-06';
      const current = DATA.transactions.filter(function (t) { return t.date.slice(0, 7) === month; });
      const history = DATA.transactions.filter(function (t) { return t.date.slice(0, 7) < month; });
      const findings = [];
      // outliers per account (z-score)
      const hist = {};
      history.forEach(function (t) { (hist[t.account_number] = hist[t.account_number] || []).push(t.amount); });
      current.forEach(function (t) {
        const h = hist[t.account_number] || [];
        if (h.length < 8) return;
        const mean = h.reduce(function (s, v) { return s + v; }, 0) / h.length;
        const sd = Math.sqrt(h.reduce(function (s, v) { return s + (v - mean) * (v - mean); }, 0) / h.length);
        if (sd > 0 && (t.amount - mean) / sd >= 3) {
          findings.push(['high', 'Unusual amount', t.date + ': ' + fc(t.amount) + ' to ' + esc(t.vendor) +
            ' on ' + t.account_number + ' is ' + (((t.amount - mean) / sd)).toFixed(1) +
            ' standard deviations above this account\'s typical transaction (avg ' + fc(mean) + ').']);
        }
      });
      // duplicates: same vendor+amount within 7 days
      const seen = {};
      current.slice().sort(function (a, b) { return a.date.localeCompare(b.date); }).forEach(function (t) {
        const key = t.vendor + '|' + t.amount.toFixed(2);
        if (seen[key]) {
          const gap = (new Date(t.date) - new Date(seen[key].date)) / 86400000;
          if (gap <= 7) {
            findings.push(['high', 'Possible duplicate payment', esc(t.vendor) + ' charged ' + fc(t.amount) +
              ' twice within ' + Math.round(gap) + ' day(s) (' + seen[key].date + ' and ' + t.date + ').']);
          }
        }
        seen[key] = t;
      });
      // threshold hugging
      const nearBy = {};
      current.forEach(function (t) {
        [5000, 10000, 25000, 50000].forEach(function (th) {
          if (t.amount >= th * 0.95 && t.amount < th) (nearBy[t.vendor] = nearBy[t.vendor] || []).push(t);
        });
      });
      Object.entries(nearBy).forEach(function (e) {
        if (e[1].length >= 2) {
          findings.push(['medium', 'Split-purchase pattern', esc(e[0]) + ': ' + e[1].length +
            ' payments each just under an approval threshold this month (total ' +
            fc(e[1].reduce(function (s, t) { return s + t.amount; }, 0)) + ') - review for split purchasing.']);
        }
      });
      const colors = { high: ['#fdecea', '#a4271c'], medium: ['#fdeeda', '#8a5a12'] };
      document.getElementById('close-out').innerHTML =
        kpiRow([kpi('Transactions reviewed', current.length.toLocaleString()),
                kpi('High-priority findings', findings.filter(function (f) { return f[0] === 'high'; }).length),
                kpi('Total findings', findings.length)]) +
        (findings.length ? findings.map(function (f) {
          return '<div style="background:' + colors[f[0]][0] + ';color:' + colors[f[0]][1] +
            ';padding:10px 14px;border-radius:8px;margin-bottom:8px;font-size:13px"><strong>' +
            f[1] + ':</strong> ' + f[2] + '</div>';
        }).join('') : '<div style="background:#e2f2e8;color:#1e6b3c;padding:10px 14px;border-radius:8px;font-size:13px">No exceptions found.</div>');
    });
  };

  views.mantisDemo = function (el) {
    const expShares = seasonalShares('Expense');
    const expected = expShares.slice(0, DATA.meta.months_elapsed).reduce(function (s, v) { return s + v; }, 0);
    const insights = [];
    const deptAgg = {};
    DATA.accounts.forEach(function (a) {
      if (a.account_type !== 'Expense') return;
      const d = deptAgg[a.department] = deptAgg[a.department] || { budget: 0, actual: 0 };
      d.budget += a.budget_amount; d.actual += a.ytd_actual;
    });
    Object.entries(deptAgg).forEach(function (e) {
      const dev = (e[1].actual / e[1].budget - expected) * 100;
      if (dev > 8) insights.push([e[0] + ' is running hot', e[0] + ' has spent ' + (e[1].actual / e[1].budget * 100).toFixed(1) + '% of budget vs a typical ' + (expected * 100).toFixed(1) + '% by July. At this pace it ends the year at ' + fcM(e[1].actual / Math.max(0.05, expected)) + ' against a ' + fcM(e[1].budget) + ' budget.']);
      if (dev < -8) insights.push([e[0] + ' is underspending', e[0] + ' is ' + Math.abs(dev).toFixed(1) + ' points behind its usual pace - potential reallocation capacity if it holds.']);
    });
    insights.push(['November cash lump ahead', 'Property tax collections concentrate in November (about ' + (seasonalShares('Revenue')[10] * 100).toFixed(0) + '% of annual revenue). Plan liquidity through the October trough before locking cash into term investments.']);
    el.innerHTML = demoBanner() +
      '<div style="background:#fdeeda;color:#8a5a12;padding:10px 14px;border-radius:8px;margin-bottom:14px;font-size:13px">The conversational AI assistant requires the platform backend with an AI key. Below are analytical insights computed directly from the demo ledger.</div>' +
      insights.map(function (i) {
        return card(i[0], '<div style="font-size:13.5px;color:#22303c;line-height:1.6">' + i[1] + '</div>');
      }).join('');
  };

  window.DEMO_VIEWS = {
    load: loadData,
    render: function (name, container) {
      const fn = views[name];
      if (!fn) { container.innerHTML = '<div style="padding:30px;color:#5b6b7a">View not found: ' + esc(name) + '</div>'; return; }
      container.innerHTML = '<div style="padding:30px;color:#5b6b7a">Loading demo data…</div>';
      loadData().then(function () { fn(container); })
        .catch(function (err) {
          container.innerHTML = '<div style="padding:30px;color:#a4271c">Could not load demo data: ' + esc(err.message) + '</div>';
        });
    }
  };
})();
