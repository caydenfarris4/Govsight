# GovSight Project Cleanup Plan
*Generated: August 20, 2025*

## CRITICAL DEPENDENCIES (MUST KEEP)

### Core Application Files
- `main_app.py` - Primary application entry point
- `replit.md` - Project documentation and user preferences  
- `replit.nix` - Replit environment configuration
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Test configuration

### Essential Root-Level Dependencies (Required by main_app.py)
- `admin_panel.py` - Authentication and user management
- `db_connection.py` - Database connectivity layer
- `accessibility_helper.py` - ADA compliance features
- `google_sheets_config.py` - Google Sheets integration config
- `system_settings.json` - System configuration

### Database Files (Keep Current Data)
- `caselle_gl0_mock.db` - Main GL database
- `govsight_all_in_one_data.db` - Consolidated data
- `mantis_conversations.db` - AI chat history
- `rbac_policies.db` - Role-based access policies
- `security_events.db` - Security audit trail
- `user_sessions.db` - User session management

### Configuration Directory
- `config/` - All configuration JSON files
  - `config/database.json`
  - `config/performance.json` 
  - `config/security.json`
  - `config/ui.json`

### Modules Directory (Complete - Contains All Functionality)
- `modules/` - Entire modular architecture (KEEP ALL)

## FILES TO DELETE (Safe to Remove)

### Legacy Python Files (Replaced by modules)
- `ai_assistant.py` ✓ (moved to modules/mantis/)
- `ai_assistant_clean.py` ✓
- `ai_hub.py` ✓ (moved to modules/mantis/)
- `bi_sandbox.py` ✓ (moved to modules/navi/)
- `scenario_planner.py` ✓ (moved to modules/navi/)
- `scenario_planner.py.bak` ✓
- `scenario_planner_secured_final.py` ✓
- `historical_analysis.py` ✓ (moved to modules/vatica/)
- `department_insights.py` ✓ (moved to modules/vatica/)
- `balance_sheet_position.py` ✓ (moved to modules/vatica/)
- `custom_visualization_builder.py` ✓ (moved to modules/navi/)
- `transaction_analyzer.py` ✓ (moved to modules/vatica/)
- `transaction_analyzer_updated.py` ✓

### Development and Testing Files
- `app.py` ✓ (old entry point)
- `annotations_app.py` ✓ (experimental)
- `test_*.py` ✓ (all root-level test files - tests moved to modules/testing/)
- `fix-*.py` ✓ (temporary fix scripts)
- `temp_*.py` ✓ (temporary files)
- `apply_security_fixes.py` ✓ (one-time script)
- `build_protected.py` ✓ (build script)
- `run_security_audit.py` ✓ (audit script)

### Utility Scripts (One-time use)
- `create_database.py` ✓
- `create_dashboard_db.py` ✓
- `generate_*.py` ✓ (all generation scripts)
- `modify_*.py` ✓ (modification scripts)
- `populate_*.py` ✓ (population scripts)
- `setup_database.sh` ✓
- `db_schema_converter.py` ✓

### Security and Analysis Scripts
- `security_manager.py` ✓ (moved to modules/security/)
- `security_sql_injection_fixes.py` ✓ (one-time fix)
- `performance_optimizer.py` ✓ (moved to modules/core/)
- `anomaly_detection_module.py` ✓ (moved to modules/utils/)

### Utility Modules (Moved to modules)
- `common_utils.py` ✓ (moved to modules/utils/)
- `mask_parser.py` ✓ (moved to modules/utils/)
- `advanced_filters.py` ✓ (moved to modules/advanced_filters/)

### Database Utilities (Replaced)
- `db_utils.py` ✓ (functionality moved to modules/database/)
- `db_utils_extended.py` ✓
- `enhanced_db_utils.py` ✓
- `db_connection_*.py` ✓ (variations)
- `db_archive_utils.py` ✓
- `sql_connection.py` ✓

### Reports and Generators (Moved)
- `summary_report_generator.py` ✓ (moved to modules/reports/)
- `scenario_report_generator_enhanced.py` ✓
- `department_*.py` ✓ (moved to modules/)
- `regulatory_*.py` ✓ (moved to modules/)

### Frontend Files (Legacy)
- `streamlit_*.py` ✓ (old frontend files)
- `city_config_tool.py` ✓

### Archives and Backups
- `attached_assets/` ✓ (backup files and assets)
- `admin_archive/` ✓ (archived admin files)
- `govsight_copy/` ✓ (project backup)
- `govsight_copy.zip` ✓

### Generated Files
- `__pycache__/` ✓ (Python cache)
- `htmlcov/` ✓ (coverage reports)
- `logs/` ✓ (can regenerate)
- `*.log` files ✓ (can regenerate)
- `security_audit_*.json` ✓ (old audit files)

### Documentation (Keep Essential Only)
DELETE:
- `ANTI_SCRAPING_PROTECTION_SUMMARY.md` ✓
- `ARCHITECTURAL_DECISIONS.md` ✓
- `CODE_PROTECTION_SUMMARY.md` ✓
- `REMAINING_SECURITY_ITEMS.md` ✓
- `REORGANIZATION_SUMMARY.md` ✓
- `REQUIREMENTS_SUMMARY.md` ✓
- `SECURITY_*.md` ✓ (multiple security docs)
- `*.pdf` files ✓ (reports and documentation)

KEEP:
- `README.md` ✓ (project overview)
- `replit.md` ✓ (essential project config)

### Test and Development Databases
- `budget.db` ✓ (test database)
- `nonexistent.db` ✓
- `test.db` ✓

### Miscellaneous
- `download_*.html` ✓
- `generated-icon.png` ✓
- `govsight_logo.png` ✓ (if not used)
- `demo_config.json` ✓
- `fund_classifications.json` ✓ (if not used)
- `users_table.csv` ✓
- `uv.lock` ✓

## MIGRATION ACTIONS REQUIRED

### Move Essential Dependencies to Modules
1. Move `admin_panel.py` → `modules/admin_panel/admin_panel.py`
2. Move `db_connection.py` → `modules/database/db_connection.py`  
3. Move `accessibility_helper.py` → `modules/utils/accessibility_helper.py`
4. Move `google_sheets_config.py` → `modules/vatica/google_sheets_config.py`

### Update Import Statements
Update `main_app.py` imports to reflect new module locations:
```python
from modules.admin_panel.admin_panel import login, authorized_tabs, etc.
from modules.database.db_connection import get_org_display_info, etc.
from modules.utils.accessibility_helper import add_accessibility_features, etc.
```

## CLEANUP EXECUTION STEPS

1. **Phase 1**: Move critical dependencies to modules
2. **Phase 2**: Update import statements in main_app.py
3. **Phase 3**: Test application functionality
4. **Phase 4**: Delete safe-to-remove files in batches
5. **Phase 5**: Verify clean deployment

## FINAL STRUCTURE AFTER CLEANUP

```
/
├── main_app.py                 # Entry point
├── replit.md                   # Project docs
├── replit.nix                  # Environment
├── pyproject.toml              # Python config
├── pytest.ini                 # Test config
├── system_settings.json        # System config
├── config/                     # Configuration directory
├── modules/                    # All functionality
├── *.db files                  # Essential databases only
└── README.md                   # Project overview
```

This will result in a clean, modular deployment package with ~90% file reduction.