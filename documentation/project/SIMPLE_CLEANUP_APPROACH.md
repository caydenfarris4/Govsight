# Simplified Cleanup Approach

Based on analysis, here's a safer approach to clean up the project:

## PHASE 1: IDENTIFY SAFE-TO-DELETE FILES (Current Assessment)

### ✅ CONFIRMED SAFE TO DELETE (Legacy/Duplicate Files)

**Legacy Python Files (Functionality moved to modules/):**
- ai_assistant.py, ai_assistant_clean.py (→ modules/mantis/)
- ai_hub.py (→ modules/mantis/) 
- bi_sandbox.py (→ modules/navi/)
- scenario_planner.py, scenario_planner.py.bak (→ modules/navi/)
- historical_analysis.py (→ modules/vatica/)
- department_insights.py (→ modules/vatica/)
- balance_sheet_position.py (→ modules/vatica/)
- custom_visualization_builder.py (→ modules/navi/)
- transaction_analyzer.py, transaction_analyzer_updated.py (→ modules/vatica/)

**Development/Testing Scripts:**
- app.py (old entry point)
- fix-*.py (temporary fix scripts)
- temp_*.py (temporary files)
- test_*.py (root level tests - moved to modules/testing/)
- create_*.py (database setup scripts)
- generate_*.py (data generation scripts)
- modify_*.py, populate_*.py (one-time scripts)

**Archive/Backup Directories:**
- attached_assets/ (backup files)
- admin_archive/ (archived admin files)
- govsight_copy/ (project backup)
- govsight_copy.zip

**Generated/Cache Directories:**
- __pycache__/ (Python cache)
- htmlcov/ (coverage reports)
- logs/ (regeneratable)

**Documentation (Keep minimal):**
- Keep: README.md, replit.md
- Delete: All other .md files (security docs, architectural docs, etc.)

### ❗ KEEP (Essential for current functionality)

**Core Application:**
- main_app.py (entry point)
- admin_panel.py (required import)
- db_connection.py (required import)
- accessibility_helper.py (required import)
- google_sheets_config.py (required import)

**Configuration:**
- config/ directory
- system_settings.json
- replit.nix, pyproject.toml, pytest.ini

**Databases (with data):**
- caselle_gl0_mock.db
- govsight_all_in_one_data.db
- mantis_conversations.db
- rbac_policies.db
- security_events.db
- user_sessions.db

**Complete Modules Directory:**
- modules/ (entire directory - contains all functionality)

## EXECUTION PLAN

**Step 1: Delete Safe Files in Batches**
1. Delete legacy Python files
2. Delete development scripts
3. Delete archive directories
4. Delete generated files

**Step 2: Test After Each Batch**
- Ensure application still works
- Check all three modules (Navi, Mantis, Vatica)

**Step 3: Final Structure**
```
/
├── main_app.py
├── admin_panel.py  
├── db_connection.py
├── accessibility_helper.py
├── google_sheets_config.py
├── system_settings.json
├── config/
├── modules/
├── *.db (essential databases)
├── README.md
├── replit.md
├── replit.nix
├── pyproject.toml
└── pytest.ini
```

This approach keeps the current working imports while dramatically reducing file count.