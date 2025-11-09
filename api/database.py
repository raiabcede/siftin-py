"""
Database module for storing capture runs and leads
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json


# Database file path
DB_PATH = Path(__file__).parent / "capture_runs.db"


def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def init_database():
    """Initialize the database by creating tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_label TEXT NOT NULL,
            linkedin_url TEXT NOT NULL,
            ai_criteria TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_leads INTEGER DEFAULT 0,
            selected_leads INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success',
            error_message TEXT
        )
    """)
    
    # Add status and error_message columns if they don't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE runs ADD COLUMN status TEXT DEFAULT 'success'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE runs ADD COLUMN error_message TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create run_leads table to store all leads for each run
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            lead_id TEXT NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            company TEXT,
            location TEXT,
            match_score INTEGER DEFAULT 0,
            description TEXT,
            linkedin_url TEXT NOT NULL,
            email TEXT,
            profile_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_selected INTEGER DEFAULT 0,
            FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
            UNIQUE(run_id, lead_id)
        )
    """)
    
    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_run_leads_run_id ON run_leads(run_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_run_leads_lead_id ON run_leads(lead_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)
    """)
    
    conn.commit()
    conn.close()
    print(f"[Database] Database initialized at {DB_PATH}")


def create_run(
    run_label: str,
    linkedin_url: str,
    ai_criteria: str,
    leads: List[Dict],
    selected_lead_ids: List[str],
    status: str = 'success',
    error_message: Optional[str] = None
) -> int:
    """
    Create a new run and save all leads
    
    Args:
        run_label: Label for the run
        linkedin_url: LinkedIn search URL
        ai_criteria: AI criteria used
        leads: List of all lead dictionaries
        selected_lead_ids: List of selected lead IDs
        status: Status of the run ('success', 'failed', 'partial')
        error_message: Error message if run failed
    
    Returns:
        The ID of the created run
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert run
        cursor.execute("""
            INSERT INTO runs (run_label, linkedin_url, ai_criteria, total_leads, selected_leads, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_label, linkedin_url, ai_criteria, len(leads), len(selected_lead_ids), status, error_message))
        
        run_id = cursor.lastrowid
        
        # Insert all leads (only if there are leads)
        if leads:
            for lead in leads:
                is_selected = 1 if lead.get('id') in selected_lead_ids else 0
                
                cursor.execute("""
                    INSERT INTO run_leads (
                        run_id, lead_id, name, title, company, location,
                        match_score, description, linkedin_url, email,
                        profile_image, is_selected
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    lead.get('id', ''),
                    lead.get('name', ''),
                    lead.get('title', ''),
                    lead.get('company', ''),
                    lead.get('location', ''),
                    lead.get('match_score', 0),
                    lead.get('description', ''),
                    lead.get('linkedin_url', ''),
                    lead.get('email'),
                    lead.get('profile_image'),
                    is_selected
                ))
        
        conn.commit()
        print(f"[Database] Created run {run_id} with status '{status}' - {len(leads)} leads ({len(selected_lead_ids)} selected)")
        return run_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_failed_run(
    run_label: str,
    linkedin_url: str,
    ai_criteria: str,
    error_message: str
) -> int:
    """
    Create a failed run record (no leads)
    
    Args:
        run_label: Label for the run
        linkedin_url: LinkedIn search URL
        ai_criteria: AI criteria used
        error_message: Error message describing the failure
    
    Returns:
        The ID of the created run
    """
    return create_run(
        run_label=run_label,
        linkedin_url=linkedin_url,
        ai_criteria=ai_criteria,
        leads=[],
        selected_lead_ids=[],
        status='failed',
        error_message=error_message
    )


def get_run(run_id: int) -> Optional[Dict]:
    """Get a run by ID with all its leads"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get run info
    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    run_row = cursor.fetchone()
    
    if not run_row:
        conn.close()
        return None
    
    run = dict(run_row)
    
    # Get all leads for this run
    cursor.execute("""
        SELECT * FROM run_leads 
        WHERE run_id = ? 
        ORDER BY created_at
    """, (run_id,))
    
    leads = [dict(row) for row in cursor.fetchall()]
    run['leads'] = leads
    
    conn.close()
    return run


def get_all_runs(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Get all runs with summary information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            r.*,
            COUNT(rl.id) as total_leads_count,
            SUM(CASE WHEN rl.is_selected = 1 THEN 1 ELSE 0 END) as selected_leads_count
        FROM runs r
        LEFT JOIN run_leads rl ON r.id = rl.run_id
        GROUP BY r.id
        ORDER BY r.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return runs


def get_run_leads(run_id: int, selected_only: bool = False) -> List[Dict]:
    """Get leads for a specific run"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if selected_only:
        cursor.execute("""
            SELECT * FROM run_leads 
            WHERE run_id = ? AND is_selected = 1
            ORDER BY created_at
        """, (run_id,))
    else:
        cursor.execute("""
            SELECT * FROM run_leads 
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,))
    
    leads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return leads


def update_run_selections(run_id: int, selected_lead_ids: List[str]) -> bool:
    """Update the selected leads for a run"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, unselect all leads for this run
        cursor.execute("""
            UPDATE run_leads 
            SET is_selected = 0 
            WHERE run_id = ?
        """, (run_id,))
        
        # Then, mark the selected leads
        if selected_lead_ids:
            placeholders = ','.join(['?'] * len(selected_lead_ids))
            cursor.execute(f"""
                UPDATE run_leads 
                SET is_selected = 1 
                WHERE run_id = ? AND lead_id IN ({placeholders})
            """, (run_id, *selected_lead_ids))
        
        # Update the selected_leads count in the runs table
        cursor.execute("""
            UPDATE runs 
            SET selected_leads = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (len(selected_lead_ids), run_id))
        
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        
        if updated:
            print(f"[Database] Updated run {run_id} with {len(selected_lead_ids)} selected leads")
        
        return updated
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


def delete_run(run_id: int) -> bool:
    """Delete a run and all its leads"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e


# Initialize database on import
init_database()

