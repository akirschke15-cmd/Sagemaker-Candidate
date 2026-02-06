"""
ATS Vendor CRUD Operations
Manages staffing agencies and recruiter vendors
"""
from typing import List, Dict, Optional
from .connection import db_session


def create_vendor(name: str, contact_email: str = None, contact_phone: str = None, notes: str = None) -> int:
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO vendors (name, contact_email, contact_phone, notes) VALUES (?, ?, ?, ?)",
            (name, contact_email, contact_phone, notes)
        )
        return cursor.lastrowid


def get_vendors() -> List[Dict]:
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM vendors ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_vendor(vendor_id: int) -> Optional[Dict]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        return dict(row) if row else None
