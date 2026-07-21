# GovSight Financial Intelligence Platform

## Overview
The GovSight platform is a municipal financial intelligence system that transforms complex financial data into actionable strategic insights using AI and interactive technologies. It provides tools for financial analysis, scenario planning, and collaborative decision-making, emphasizing accessibility compliance and enterprise-grade organization. The platform aims to revolutionize municipal financial management by offering comprehensive analysis, forecasting, and AI-driven insights to support strategic decisions, ultimately enhancing efficiency and strategic foresight for municipalities.

## User Preferences
- Prefers clean, professional communication without emojis (CRITICAL: Never add emojis back - ABSOLUTE PROHIBITION)
- Specifically requests emoji removal from Google Sheets export functionality and ALL UI elements including login screen and tab navigation
- NO demo credentials or expandable credential sections in login interface
- Keep GovSight logo in login interface for professional branding
- ABSOLUTE PROHIBITION on competitor references (Power BI, Tableau, etc.) in frontend application
- Tab labels must be text-only without any emoji icons for professional appearance
- Values efficient development with multiple simultaneous operations
- Appreciates comprehensive documentation and testing
- Focuses on practical, working solutions
- Wants architectural decisions documented with reasoning ("why I am doing what I am doing")
- Values thorough annotation of code explaining implementation choices

## System Architecture
The system is built on a 3-module architecture (`Navi`, `Mantis`, `Vatica`), accessible via a main application dashboard.

### UI/UX Decisions
-   **Professional Interface**: All emojis are removed from the UI.
-   **Dashboard Design**: Main page features three large icon cards for module selection.
-   **Tabbed Interfaces**: Modules organize functions within tabbed views.
-   **Streamlined Mantis Interface**: Chat experience optimized with history in the sidebar and new conversations starting fresh.
-   **Hybrid Visualization System**: Dual-engine visualization with Apache ECharts for BI dashboards and D3.js for custom municipal visualizations.
-   **Advanced Dashboard Builder**: Features adaptive controls, expandable customization, and professional styling.

### Technical Implementations
-   **Enterprise Service Layer**: Major backend architecture upgrade utilizing database-backed enterprise services (`ConfigService`, `DatabaseService`, `MigrationService`, `Bootstrap`) for configuration, database connection management, and schema migrations. Secrets are strictly managed via environment variables.
-   **API-First Data Architecture**: Unified data adapter (`modules/data_adapter/`) for integrating Caselle ERP API and file import systems (CSV, PDF), supported by a `Report Archive Database`.
-   **Multi-Database Architecture**: Integrates with five distinct databases: GL Primary (SQLite), Utility Management (PostgreSQL), Asset Management (MySQL), Permits & Licensing (SQL Server), and Payroll (PostgreSQL).
-   **Modular Structure**: Python files are organized into functional modules (`navi/`, `mantis/`, `vatica/`, `core/`).
-   **Enterprise File Organization**: Dedicated directories for `documentation/`, `configs/`, `databases/`, `logos/`, and `attached_assets/`.
-   **Accessibility Module**: WCAG 2.1 compliant helper module for charts, CSS, and screen reader support.
-   **Authorization System**: Role-based access managed via `admin_panel.py` and Google Sheets.
-   **Graph Stability Enhancement**: Implemented unique key parameters for all `st.plotly_chart()` calls to prevent collapse during Streamlit reruns.
-   **Comprehensive HTML Scenario Planner** (February 2026): Fully rebuilt at `modules/scenario_planner_html/scenario_planner.html` (1,383 lines, React via CDN). Consolidated into a **3-section + 4-independent architecture** with a **floating collaboration sidebar** accessible from all tabs. Tab structure: (1) **Scenario** — project setup, funding sources, funding mix pie chart, grant search, save; (2) **Revenue** — two sub-sections: (a) Grant Pipeline (8 federal grant templates auto-matched to detected funding gaps, 4-stage tracker Researching/Applied/Awarded/Denied, 30-day deadline alerts, awarded grant-to-expense mapping), (b) Department Reallocation (budget vs. actuals scanner for sample/real departments, configurable safety floor slider 70–100%, computes headroom above floor per department, ranked recommendations list, total reallocation potential stat); (3) **Expenses & Analytics** — two sub-sections: (a) Expense Planner (multi-year timeline, per-category inflation, contingency buffer 0–30%, year-by-year gap table with red/green rows, inline expense row annotations), (b) Analytics (Chart.js stacked bar + cumulative funding line chart, funding diversity score 0–100 with warnings, ROI/cost-benefit calculator with NPV/BCR/payback/IRR); (4) **Scenario Comparison** — three editable panels (Optimistic/Baseline/Worst Case) with live what-if sliders ±50%, summary comparison table, PDF export via `window.print()`; (5) **What-If Simulator** — independent natural language analysis; (6) **Legislative Impact** — independent federal/state bill lookup; (7) **Monte Carlo** — independent risk simulation. Collaboration sidebar floats fixed on the right edge of every tab, shows threaded notes tagged by section, persisted in localStorage. Shareable read-only links via base64 URL hash (`#share=<encoded>`). No emojis anywhere.
-   **Budget Playground** (March 2026): Dynamic re-forecasting and scenario modeling tool embedded as a new Navi tab (tab 7, "Budget Playground"). Covers all 60 non-payroll GL accounts (10 Revenue, 50 Expense — payroll accounts 5100/5200 live in PBB). 5-tab React HTML frontend (`modules/navi/budget_playground.html`) rendered via Streamlit iframe: (1) **Budget Ledger** — spreadsheet with editable Revised Forecast/Yr+1/Yr+2/Note per account, department-collapsible rows, live footer totals (Revenue/Expense/Net Surplus), dirty-cell highlighting, Save/Reset/Export CSV; (2) **Scenarios** — card grid CRUD (create, duplicate, rename, lock, delete), copy-from seed; (3) **Supplementals** — mid-year amendment tracker with Pending/Approved/Denied workflow and Apply to Ledger action; (4) **Reforecast** — YTD extrapolation engine (months-elapsed slider, auto-extrapolation, accept checkboxes, custom override, push to ledger); (5) **Summary** — KPI strip, grouped-bar chart (dept Adopted vs Revised), 3-year trajectory line chart, sortable dept breakdown table, top-5 favorable/unfavorable variances. Backend: Node.js Express API at `budget_playground_api/server.js` on port 5002 (workflow: "Budget Playground API"); reads GL accounts from `databases/core/govsight_all_in_one_data.db` (read-only) and reads/writes scenarios + supplementals to `databases/budget_playground.db` (tables: scenarios, scenario_lines, supplementals); default "Adopted Budget FY 2025" scenario seeded on first run. Python server: `modules/navi/budget_playground_server.py` injects `window.BUDGET_PLAYGROUND_API_URL = "/bp-api"` (relative path). **Replit networking**: Only port 5000 is browser-accessible in Replit. The `modules/navi/bp_proxy.py` Tornado reverse proxy is installed at app startup (`main_app.py`) using Python's `gc` module to locate Streamlit's running `tornado.web.Application` in memory and call `add_handlers()` to register `/bp-api/(.*)` routes that forward server-side to `localhost:5002/*`. The HTML uses relative paths so the browser hits port 5000 (same origin), which the proxy forwards internally.
-   **Enhanced Position-Based Budgeting (PBB)**: Comprehensive Excel-style multi-sheet workbook system in the `Navi` module with SQLite persistence, including split cost center allocations, multi-year budgeting, vacancy management, dynamic employee filtering, Prior Year Actuals Import, audit trails, advanced filtering, AI Budget Assistant integration, PDF export, union contract compliance, and department comparison.
-   **Municipal Investment Optimizer (HTML/TypeScript)**: Modern React-based investment dashboard in `Navi` module with interactive tabs, Chart.js visualizations, and real-time calculators.
-   **Mantis Module (AI Intelligence Hub)**: Unifies AI capabilities including grant discovery, anomaly detection, natural language queries, multi-database analysis, secure file processing, data quality assessment, economic scenario analysis, economic intelligence, and **GASB compliance checking**. **Dual AI Routing (February 2026)**: Intelligent prompt classifier in `modules/mantis/dual_ai_router.py` routes between two AI engines using keyword scoring — Claude 3.5 Sonnet (Anthropic) handles technical/coding/debugging questions; GPT-4o (OpenAI) handles financial analysis, data queries, grants, and GASB compliance (keeping the full function-calling tool pipeline on GPT). Cross-check mode triggered by words like "verify", "confirm", or "second opinion" — both models answer and peer-review each other's response. Model badge displayed under each assistant message. Sidebar shows live connection status of both engines. Both models gracefully fall back to the other if one is unavailable. Uses OpenAI GPT-4o with function calling tools for data routing. Includes a comprehensive support training system.
-   **BI Sandbox Enhancement**: Rebuilt with AI-powered natural language analytics, an easy chart builder, and real-time data integration.
-   **Security**: Enterprise-grade security features including memory-only processing for sensitive uploads, 5-layer source code protection, HTML/XML scraping protection, and unified secret management.
-   **Unified Secret Management**: Integrates Replit Secrets and Google Cloud Secret Manager.
-   **AI/ML Features**: Utilizes RAG architecture with TF-IDF, secure SQL generation, IsolationForest for anomaly detection, TF-IDF for grant matching, and LinearRegression for forecasting.
-   **Audit Logging System**: SQLite-based system for tracking authentication, data access, admin operations, and security events.
-   **Automated Backup System**: Enterprise-grade backup manager with full/incremental backups, gzip compression, and SHA-256 integrity verification.
-   **Google Cloud Platform Integration**: Comprehensive cloud architecture for document archiving, data analytics, and AI model deployment (GCS, BigQuery, Vertex AI).
-   **Google Cloud Production Deployment**: Deployment infrastructure for Cloud Run with multi-tenant subdomain architecture, Docker, CI/CD via Cloud Build, and Cloud SQL PostgreSQL.
-   **Enterprise SSO Authentication**: Production-ready Single Sign-On supporting OAuth 2.0/OIDC (Google Workspace, Microsoft Azure AD) with PKCE, Just-in-Time provisioning, secure password generation, automatic `sso_required` flag enforcement, and SOC-2 compliance.
-   **Claude Code Background Agent**: Agentic automation layer wrapping the Claude Code CLI for autonomous background task execution via a FastAPI service (`agent/agent_service.py`), with predefined tasks in `agent/tasks.py`, SQLite persistence in `agent/agent_db.py`, and a Streamlit dashboard in `modules/agent/agent_dashboard.py`.

### Reporting System
-   **Core Reporting Engine**: Centralized report generation supporting PDF, CSV, XLSX, JSON, and HTML formats with Jinja2 templating.
-   **Data Access Layer**: Secure parameterized queries, role-based filtering, and performance caching.
-   **Chart Generation Service**: Plotly-based visualization engine supporting multiple chart types.
-   **Audit Logger**: Complete audit trail for report generation, access, and performance metrics.
-   **Google Sheets Handler**: Graceful degradation for Google Sheets export.
-   **BI Dashboard Export**: Enhanced Data Export tab for data, dashboard, and report generation.

## External Dependencies
-   **Frontend Framework**: Streamlit
-   **AI Integration**: OpenAI GPT-4o
-   **Data Visualization**: Plotly, Apache ECharts, D3.js, Chart.js
-   **Databases**: PostgreSQL, SQLite, MySQL, SQL Server
-   **Numerical Operations**: NumPy, scikit-learn
-   **Google Integration**: Google Sheets API, Google Cloud Secret Manager, Google Cloud Storage, BigQuery, Vertex AI
-   **External Data Connectors**: Federal Reserve Economic Data (FRED), Bureau of Economic Analysis (BEA), US Treasury Fiscal Data API, OFR Money Market Fund Monitor API
-   **Investment Data Sources**: US Treasury, Office of Financial Research (OFR), CDARS/ICS network, State LGIPs
-   **Backup & Recovery**: SQLite backup API, gzip
-   **Cloud Authentication**: Application Default Credentials