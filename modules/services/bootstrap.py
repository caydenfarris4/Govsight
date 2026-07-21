"""
Application Bootstrap - Initializes all enterprise services on startup

Called once during application startup to ensure:
1. Database schema is current (migrations applied)
2. JSON configs are migrated to database on first run
3. All services are initialized and healthy

ARCHITECTURAL DECISIONS:
1. Single bootstrap entry point
   WHY: Guarantees initialization order; services depend on each other
2. Migration runs before service initialization
   WHY: ConfigService needs its tables to exist before it can read/write
3. Idempotent - safe to call multiple times
   WHY: Streamlit reruns the script on every interaction
"""

import logging
import os

logger = logging.getLogger("govsight.services.bootstrap")

_bootstrapped = False


def bootstrap_services():
    global _bootstrapped
    if _bootstrapped:
        return

    logger.info("Bootstrapping enterprise services...")

    try:
        from modules.services.migration_service import get_migration_service
        migration_svc = get_migration_service()
        applied = migration_svc.apply_all()
        if applied:
            logger.info(f"Applied {len(applied)} migrations: {applied}")
        else:
            logger.info("All migrations up to date")
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    try:
        from modules.services.config_service import get_config_service
        config_svc = get_config_service()

        _ensure_secrets_in_env(config_svc)

        namespaces = config_svc.list_namespaces()
        logger.info(f"ConfigService ready with {len(namespaces)} namespaces: {namespaces}")
    except Exception as e:
        logger.error(f"ConfigService initialization failed: {e}")

    try:
        from modules.services.database_service import get_database_service
        db_svc = get_database_service()
        result = db_svc.test_connection()
        logger.info(f"DatabaseService ready - connection test: {result['status']}")
    except Exception as e:
        logger.error(f"DatabaseService initialization failed: {e}")

    _bootstrapped = True
    logger.info("Enterprise services bootstrap complete")


def _ensure_secrets_in_env(config_svc):
    secret_keys = ["OpenAI_Key", "DefaultPassword", "GoogleSheets_Credentials"]
    env_mapping = {
        "OpenAI_Key": "OPENAI_API_KEY",
        "DefaultPassword": "ADMIN_PASSWORD",
        "GoogleSheets_Credentials": "GOOGLE_SHEETS_CREDENTIALS",
    }

    for config_key in secret_keys:
        env_key = env_mapping.get(config_key, config_key)
        if os.environ.get(env_key):
            config_svc.delete("system_settings", config_key, deleted_by="bootstrap_security")
            logger.info(f"Removed secret '{config_key}' from config database (using env var '{env_key}' instead)")
