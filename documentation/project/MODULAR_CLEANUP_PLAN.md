# Modular Cleanup Plan - Maintain 200-Line File Structure

## Objective
Move essential root dependencies into modules/ while keeping focused, ~200-line files organized by specific functionality.

## Essential Files to Modularize

### 1. admin_panel.py (1,200+ lines) → Break into focused modules
- `modules/admin/authentication.py` (~200 lines) - login, user auth
- `modules/admin/user_management.py` (~200 lines) - user CRUD operations  
- `modules/admin/role_management.py` (~200 lines) - roles, permissions
- `modules/admin/system_settings.py` (~200 lines) - system configuration
- `modules/admin/google_sheets_config.py` (~200 lines) - GS credential management
- `modules/admin/archive_management.py` (~200 lines) - data archiving

### 2. db_connection.py (800+ lines) → Break into focused modules
- `modules/database/connection_manager.py` (~200 lines) - connection handling
- `modules/database/query_executor.py` (~200 lines) - safe SQL execution
- `modules/database/org_management.py` (~200 lines) - organization data
- `modules/database/security_validation.py` (~200 lines) - SQL injection protection

### 3. accessibility_helper.py (400+ lines) → Keep as focused module
- `modules/utils/accessibility_helper.py` (~400 lines) - ADA compliance features

### 4. google_sheets_config.py (200+ lines) → Move to admin
- Already fits size requirement, move to `modules/admin/google_sheets_config.py`

## Migration Strategy

### Phase 1: Create Module Structure
1. Create focused files in modules/admin/, modules/database/
2. Extract specific functionality maintaining ~200 line limit
3. Update internal imports to reference modules/

### Phase 2: Update main_app.py Imports
```python
# Before
from admin_panel import login, authorized_tabs, etc.
from db_connection import get_org_display_info, etc.

# After  
from modules.admin.authentication import login, authorized_tabs
from modules.database.org_management import get_org_display_info
```

### Phase 3: Test and Clean
1. Verify all functionality works
2. Delete original root files
3. Clean up any remaining legacy files

## File Organization Benefits
- Each file has single responsibility (~200 lines)
- Clear naming conventions indicate purpose
- Easy to maintain and debug
- No massive 1000+ line files
- All dependencies contained in modules/

This maintains your preferred focused file structure while achieving full modularization.