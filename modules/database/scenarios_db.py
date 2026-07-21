"""
Scenarios Database Management

This module handles database operations for scenario planning data,
providing persistence and integration with admin panel and AI proposal generator.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

# Database path
SCENARIOS_DB_PATH = "databases/core/scenarios.db"

def ensure_db_directory():
    """Ensure the database directory exists"""
    os.makedirs(os.path.dirname(SCENARIOS_DB_PATH), exist_ok=True)

def init_scenarios_database():
    """Initialize the scenarios database with required tables"""
    ensure_db_directory()
    
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    cursor = conn.cursor()
    
    # Create scenarios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            years INTEGER DEFAULT 3,
            costs TEXT, -- JSON array
            funding_sources TEXT, -- JSON array
            departments TEXT, -- JSON array
            assumptions TEXT, -- JSON object
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            created_by TEXT DEFAULT 'user',
            organization TEXT DEFAULT 'cityA',
            status TEXT DEFAULT 'draft',
            metadata TEXT -- JSON object for additional data
        )
    """)
    
    # Create grants table for integration with grant finder
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            agency TEXT,
            amount REAL,
            description TEXT,
            eligibility TEXT,
            deadline TEXT,
            category TEXT,
            created_at TEXT NOT NULL,
            metadata TEXT -- JSON object
        )
    """)
    
    # Create scenario_grants link table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenario_grants (
            scenario_id TEXT,
            grant_id TEXT,
            allocation_amount REAL,
            notes TEXT,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
            FOREIGN KEY (grant_id) REFERENCES grants(id) ON DELETE CASCADE,
            PRIMARY KEY (scenario_id, grant_id)
        )
    """)
    
    # Create AI proposals table for AI proposal generator integration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_proposals (
            id TEXT PRIMARY KEY,
            scenario_id TEXT,
            proposal_type TEXT, -- 'legislative', 'whatif', 'optimization'
            input_params TEXT, -- JSON object
            output_result TEXT, -- JSON object
            confidence_score REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
        )
    """)
    
    # Create index for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_org ON scenarios(organization)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_status ON scenarios(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_created ON scenarios(created_at)")
    
    conn.commit()
    conn.close()
    
    return True

def get_all_scenarios(organization: str = None) -> List[Dict]:
    """Get all scenarios, optionally filtered by organization"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if organization:
        cursor.execute("""
            SELECT * FROM scenarios 
            WHERE organization = ? 
            ORDER BY modified_at DESC
        """, (organization,))
    else:
        cursor.execute("SELECT * FROM scenarios ORDER BY modified_at DESC")
    
    scenarios = []
    for row in cursor.fetchall():
        scenario = dict(row)
        # Parse JSON fields
        scenario['costs'] = json.loads(scenario['costs']) if scenario['costs'] else []
        scenario['funding_sources'] = json.loads(scenario['funding_sources']) if scenario['funding_sources'] else []
        scenario['departments'] = json.loads(scenario['departments']) if scenario['departments'] else []
        scenario['assumptions'] = json.loads(scenario['assumptions']) if scenario['assumptions'] else {}
        scenario['metadata'] = json.loads(scenario['metadata']) if scenario['metadata'] else {}
        scenarios.append(scenario)
    
    conn.close()
    return scenarios

def get_scenario(scenario_id: str) -> Optional[Dict]:
    """Get a specific scenario by ID"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
    row = cursor.fetchone()
    
    if row:
        scenario = dict(row)
        # Parse JSON fields
        scenario['costs'] = json.loads(scenario['costs']) if scenario['costs'] else []
        scenario['funding_sources'] = json.loads(scenario['funding_sources']) if scenario['funding_sources'] else []
        scenario['departments'] = json.loads(scenario['departments']) if scenario['departments'] else []
        scenario['assumptions'] = json.loads(scenario['assumptions']) if scenario['assumptions'] else {}
        scenario['metadata'] = json.loads(scenario['metadata']) if scenario['metadata'] else {}
        conn.close()
        return scenario
    
    conn.close()
    return None

def create_scenario(scenario_data: Dict) -> str:
    """Create a new scenario"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    cursor = conn.cursor()
    
    # Generate ID if not provided
    scenario_id = scenario_data.get('id') or str(uuid.uuid4())
    
    # Prepare data
    now = datetime.now().isoformat()
    costs = json.dumps(scenario_data.get('costs', []))
    funding_sources = json.dumps(scenario_data.get('fundingSources', []))
    departments = json.dumps(scenario_data.get('departments', []))
    assumptions = json.dumps(scenario_data.get('assumptions', {}))
    metadata = json.dumps(scenario_data.get('metadata', {}))
    
    cursor.execute("""
        INSERT INTO scenarios (
            id, name, description, years, costs, funding_sources, 
            departments, assumptions, created_at, modified_at,
            created_by, organization, status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scenario_id,
        scenario_data.get('name', 'Untitled Scenario'),
        scenario_data.get('description', ''),
        scenario_data.get('years', 3),
        costs,
        funding_sources,
        departments,
        assumptions,
        scenario_data.get('createdAt', now),
        scenario_data.get('modifiedAt', now),
        scenario_data.get('created_by', 'user'),
        scenario_data.get('organization', 'cityA'),
        scenario_data.get('status', 'draft'),
        metadata
    ))
    
    conn.commit()
    conn.close()
    
    return scenario_id

def update_scenario(scenario_id: str, scenario_data: Dict) -> bool:
    """Update an existing scenario"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    cursor = conn.cursor()
    
    # Check if scenario exists
    cursor.execute("SELECT id FROM scenarios WHERE id = ?", (scenario_id,))
    if not cursor.fetchone():
        conn.close()
        return False
    
    # Prepare data
    costs = json.dumps(scenario_data.get('costs', []))
    funding_sources = json.dumps(scenario_data.get('fundingSources', []))
    departments = json.dumps(scenario_data.get('departments', []))
    assumptions = json.dumps(scenario_data.get('assumptions', {}))
    metadata = json.dumps(scenario_data.get('metadata', {}))
    
    cursor.execute("""
        UPDATE scenarios SET 
            name = ?, description = ?, years = ?, costs = ?, 
            funding_sources = ?, departments = ?, assumptions = ?,
            modified_at = ?, status = ?, metadata = ?
        WHERE id = ?
    """, (
        scenario_data.get('name', 'Untitled Scenario'),
        scenario_data.get('description', ''),
        scenario_data.get('years', 3),
        costs,
        funding_sources,
        departments,
        assumptions,
        datetime.now().isoformat(),
        scenario_data.get('status', 'draft'),
        metadata,
        scenario_id
    ))
    
    conn.commit()
    conn.close()
    
    return True

def delete_scenario(scenario_id: str) -> bool:
    """Delete a scenario"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted

def save_ai_proposal(scenario_id: str, proposal_type: str, 
                    input_params: Dict, output_result: Dict, 
                    confidence_score: float = 0.0) -> str:
    """Save an AI-generated proposal linked to a scenario"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    cursor = conn.cursor()
    
    proposal_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO ai_proposals (
            id, scenario_id, proposal_type, input_params, 
            output_result, confidence_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        proposal_id,
        scenario_id,
        proposal_type,
        json.dumps(input_params),
        json.dumps(output_result),
        confidence_score,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return proposal_id

def get_scenario_proposals(scenario_id: str) -> List[Dict]:
    """Get all AI proposals for a scenario"""
    conn = sqlite3.connect(SCENARIOS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM ai_proposals 
        WHERE scenario_id = ? 
        ORDER BY created_at DESC
    """, (scenario_id,))
    
    proposals = []
    for row in cursor.fetchall():
        proposal = dict(row)
        proposal['input_params'] = json.loads(proposal['input_params']) if proposal['input_params'] else {}
        proposal['output_result'] = json.loads(proposal['output_result']) if proposal['output_result'] else {}
        proposals.append(proposal)
    
    conn.close()
    return proposals

# Initialize database on module import
if not os.path.exists(SCENARIOS_DB_PATH):
    init_scenarios_database()