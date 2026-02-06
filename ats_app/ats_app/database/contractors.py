"""
ATS Contractor Lifecycle Operations
Manages contractor roles, contracts, compliance documents, and rates
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .connection import db_session


# ============ CONTRACTOR ROLE OPERATIONS ============
def create_contractor_role(name: str, description: str = None, min_rate: float = None, max_rate: float = None) -> int:
    """Create a new contractor role with rate range."""
    with db_session() as conn:
        cursor = conn.execute(
            "INSERT INTO contractor_roles (name, description, min_hourly_rate, max_hourly_rate) VALUES (?, ?, ?, ?)",
            (name, description, min_rate, max_rate)
        )
        return cursor.lastrowid


def get_contractor_roles(active_only: bool = True) -> List[Dict]:
    """Get all contractor roles, optionally filtered by active status."""
    with db_session() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM contractor_roles WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contractor_roles ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]


def get_contractor_role(role_id: int) -> Optional[Dict]:
    """Get a contractor role by ID."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM contractor_roles WHERE id = ?", (role_id,)
        ).fetchone()
        return dict(row) if row else None


def update_contractor_role(role_id: int, **kwargs) -> bool:
    """Update a contractor role."""
    ALLOWED_COLUMNS = {'name', 'description', 'min_hourly_rate', 'max_hourly_rate', 'is_active'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE contractor_roles SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), role_id))
        return True


def delete_contractor_role(role_id: int) -> bool:
    """Soft delete a contractor role (set is_active = 0)."""
    with db_session() as conn:
        conn.execute("UPDATE contractor_roles SET is_active = 0 WHERE id = ?", (role_id,))
        return True


def activate_contractor_role(role_id: int) -> bool:
    """Reactivate a contractor role."""
    with db_session() as conn:
        conn.execute("UPDATE contractor_roles SET is_active = 1 WHERE id = ?", (role_id,))
        return True


def check_rate_in_range(expected_rate: float, role_id: int) -> Tuple[bool, float, str]:
    """
    Check if an expected rate falls within a role's rate range.

    Returns:
        (in_range: bool, variance: float, message: str)
        - in_range: True if rate is within the range
        - variance: Percentage variance from nearest boundary (positive = over, negative = under)
        - message: Human-readable status message
    """
    if expected_rate is None or role_id is None:
        return (True, 0.0, "No rate specified")

    role = get_contractor_role(role_id)
    if not role:
        return (True, 0.0, "Role not found")

    min_rate = role.get('min_hourly_rate')
    max_rate = role.get('max_hourly_rate')

    if min_rate is None and max_rate is None:
        return (True, 0.0, "No rate range defined")

    # Calculate variance and status
    if min_rate is not None and expected_rate < min_rate:
        variance = ((expected_rate - min_rate) / min_rate) * 100
        return (False, variance, f"Below minimum (${min_rate:.2f}/hr)")

    if max_rate is not None and expected_rate > max_rate:
        variance = ((expected_rate - max_rate) / max_rate) * 100
        return (False, variance, f"Above maximum (${max_rate:.2f}/hr)")

    return (True, 0.0, "Within range")


def get_rate_status(expected_rate: float, role_id: int) -> Dict:
    """
    Get detailed rate status for display purposes.

    Returns dict with:
        - status: 'in_range', 'warning' (within 10%), or 'out_of_range'
        - color: Southwest-themed color for display
        - variance: percentage variance from nearest boundary
        - message: human-readable status
        - min_rate, max_rate: role's rate range
    """
    if expected_rate is None or role_id is None:
        return {
            'status': 'no_data',
            'color': '#6c757d',  # gray
            'variance': 0,
            'message': 'No rate data',
            'min_rate': None,
            'max_rate': None
        }

    role = get_contractor_role(role_id)
    if not role:
        return {
            'status': 'no_data',
            'color': '#6c757d',
            'variance': 0,
            'message': 'Role not found',
            'min_rate': None,
            'max_rate': None
        }

    min_rate = role.get('min_hourly_rate')
    max_rate = role.get('max_hourly_rate')

    if min_rate is None and max_rate is None:
        return {
            'status': 'no_data',
            'color': '#6c757d',
            'variance': 0,
            'message': 'No range defined',
            'min_rate': None,
            'max_rate': None
        }

    # Southwest Airlines colors
    COLOR_IN_RANGE = '#304CB2'   # Southwest Blue - in range
    COLOR_WARNING = '#F9B612'    # Southwest Yellow - within 10%
    COLOR_OUT_OF_RANGE = '#C8102E'  # Southwest Red - out of range

    # Check if within 10% of boundaries (warning zone)
    warning_threshold = 0.10

    if min_rate is not None and expected_rate < min_rate:
        variance = ((expected_rate - min_rate) / min_rate) * 100
        return {
            'status': 'out_of_range',
            'color': COLOR_OUT_OF_RANGE,
            'variance': variance,
            'message': f'${variance:.1f}% below minimum',
            'min_rate': min_rate,
            'max_rate': max_rate
        }

    if max_rate is not None and expected_rate > max_rate:
        variance = ((expected_rate - max_rate) / max_rate) * 100
        return {
            'status': 'out_of_range',
            'color': COLOR_OUT_OF_RANGE,
            'variance': variance,
            'message': f'+{variance:.1f}% above maximum',
            'min_rate': min_rate,
            'max_rate': max_rate
        }

    # Check warning zones (within 10% of min or max)
    if min_rate is not None:
        warning_min = min_rate * (1 + warning_threshold)
        if expected_rate < warning_min:
            variance = ((expected_rate - min_rate) / min_rate) * 100
            return {
                'status': 'warning',
                'color': COLOR_WARNING,
                'variance': variance,
                'message': f'Near minimum (+{variance:.1f}%)',
                'min_rate': min_rate,
                'max_rate': max_rate
            }

    if max_rate is not None:
        warning_max = max_rate * (1 - warning_threshold)
        if expected_rate > warning_max:
            variance = ((expected_rate - max_rate) / max_rate) * 100
            return {
                'status': 'warning',
                'color': COLOR_WARNING,
                'variance': variance,
                'message': f'Near maximum ({variance:.1f}%)',
                'min_rate': min_rate,
                'max_rate': max_rate
            }

    # In range
    return {
        'status': 'in_range',
        'color': COLOR_IN_RANGE,
        'variance': 0,
        'message': 'Within range',
        'min_rate': min_rate,
        'max_rate': max_rate
    }


def get_compensation_stats_by_job() -> List[Dict]:
    """Get compensation analysis stats per job for dashboard."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT
                j.id as job_id,
                j.title as job_title,
                cr.name as role_name,
                cr.min_hourly_rate,
                cr.max_hourly_rate,
                COUNT(DISTINCT cj.candidate_id) as total_candidates,
                SUM(CASE
                    WHEN cj.expected_hourly_rate IS NOT NULL
                         AND cr.min_hourly_rate IS NOT NULL
                         AND cr.max_hourly_rate IS NOT NULL
                         AND cj.expected_hourly_rate >= cr.min_hourly_rate
                         AND cj.expected_hourly_rate <= cr.max_hourly_rate
                    THEN 1 ELSE 0 END) as in_range_count,
                SUM(CASE
                    WHEN cj.expected_hourly_rate IS NOT NULL
                         AND ((cr.min_hourly_rate IS NOT NULL AND cj.expected_hourly_rate < cr.min_hourly_rate)
                              OR (cr.max_hourly_rate IS NOT NULL AND cj.expected_hourly_rate > cr.max_hourly_rate))
                    THEN 1 ELSE 0 END) as out_of_range_count,
                SUM(CASE WHEN cj.expected_hourly_rate IS NULL THEN 1 ELSE 0 END) as no_rate_count
            FROM jobs j
            LEFT JOIN contractor_roles cr ON j.contractor_role_id = cr.id
            LEFT JOIN candidate_jobs cj ON j.id = cj.job_id AND cj.status = 'Active'
            WHERE j.status = 'Open'
            GROUP BY j.id, j.title, cr.name, cr.min_hourly_rate, cr.max_hourly_rate
            ORDER BY j.title
        """).fetchall()
        return [dict(r) for r in rows]


# ============ CONTRACT LIFECYCLE TRACKING OPERATIONS ============
def create_contract(candidate_id: int, job_id: int = None, start_date: str = None,
                   end_date: str = None, hourly_rate: float = None, notes: str = None,
                   extension_of: int = None) -> int:
    """
    Create a new contract for a candidate.

    Args:
        candidate_id: Candidate ID
        job_id: Optional job ID
        start_date: Contract start date (YYYY-MM-DD)
        end_date: Contract end date (YYYY-MM-DD)
        hourly_rate: Hourly rate for the contract
        notes: Additional notes
        extension_of: ID of previous contract if this is an extension

    Returns:
        New contract ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO contracts (candidate_id, job_id, start_date, end_date, hourly_rate, notes, extension_of)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, job_id, start_date, end_date, hourly_rate, notes, extension_of))
        return cursor.lastrowid


def get_contracts(candidate_id: int = None, status: str = None, job_id: int = None) -> List[Dict]:
    """
    Get contracts with optional filtering.

    Args:
        candidate_id: Filter by candidate ID
        status: Filter by status (active, completed, terminated, extended)
        job_id: Filter by job ID

    Returns:
        List of contract dictionaries
    """
    with db_session() as conn:
        query = """
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE 1=1
        """
        params = []

        if candidate_id:
            query += " AND c.candidate_id = ?"
            params.append(candidate_id)
        if status:
            query += " AND c.status = ?"
            params.append(status)
        if job_id:
            query += " AND c.job_id = ?"
            params.append(job_id)

        query += " ORDER BY c.end_date ASC, c.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_contract(contract_id: int) -> Optional[Dict]:
    """Get a single contract by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.id = ?
        """, (contract_id,)).fetchone()
        return dict(row) if row else None


def update_contract(contract_id: int, **kwargs) -> bool:
    """Update contract fields."""
    ALLOWED_COLUMNS = {'candidate_id', 'job_id', 'start_date', 'end_date', 'hourly_rate', 'status', 'extension_of', 'notes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE contracts SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), contract_id))
        return True


def get_expiring_contracts(days: int = 30) -> List[Dict]:
    """
    Get contracts ending within N days.

    Args:
        days: Number of days to look ahead

    Returns:
        List of contracts ending soon, sorted by end date
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title,
                   julianday(c.end_date) - julianday('now') as days_remaining
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.status = 'active'
            AND c.end_date IS NOT NULL
            AND date(c.end_date) <= date('now', '+' || ? || ' days')
            AND date(c.end_date) >= date('now')
            ORDER BY c.end_date ASC
        """, (days,)).fetchall()
        return [dict(r) for r in rows]


def extend_contract(contract_id: int, new_end_date: str, new_rate: float = None,
                   notes: str = None) -> int:
    """
    Extend a contract by creating a new contract linked to the original.

    Args:
        contract_id: Original contract ID
        new_end_date: New end date for the extension
        new_rate: New hourly rate (optional, uses original if not provided)
        notes: Notes for the extension

    Returns:
        New contract ID
    """
    original = get_contract(contract_id)
    if not original:
        raise ValueError(f"Contract {contract_id} not found")

    # Mark original as extended
    update_contract(contract_id, status='extended')

    # Create extension contract
    return create_contract(
        candidate_id=original['candidate_id'],
        job_id=original['job_id'],
        start_date=original['end_date'],  # Extension starts when original ends
        end_date=new_end_date,
        hourly_rate=new_rate if new_rate else original['hourly_rate'],
        notes=notes,
        extension_of=contract_id
    )


def complete_contract(contract_id: int, notes: str = None) -> bool:
    """
    Mark a contract as completed and update candidate as past contractor.

    Args:
        contract_id: Contract ID
        notes: Optional completion notes

    Returns:
        True if successful
    """
    contract = get_contract(contract_id)
    if not contract:
        return False

    with db_session() as conn:
        # Update contract status
        conn.execute("""
            UPDATE contracts SET status = 'completed', notes = COALESCE(?, notes)
            WHERE id = ?
        """, (notes, contract_id))

        # Mark candidate as past contractor
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                last_contract_end = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contract['end_date'], contract['candidate_id']))

        return True


def terminate_contract(contract_id: int, notes: str = None) -> bool:
    """
    Terminate a contract early.

    Args:
        contract_id: Contract ID
        notes: Termination notes

    Returns:
        True if successful
    """
    contract = get_contract(contract_id)
    if not contract:
        return False

    with db_session() as conn:
        # Update contract status
        conn.execute("""
            UPDATE contracts SET status = 'terminated', notes = COALESCE(?, notes)
            WHERE id = ?
        """, (notes, contract_id))

        # Mark candidate as past contractor with today's date
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                last_contract_end = date('now'),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (contract['candidate_id'],))

        return True


def get_contract_history(candidate_id: int) -> List[Dict]:
    """
    Get full contract history for a candidate including extensions.

    Args:
        candidate_id: Candidate ID

    Returns:
        List of contracts ordered by date
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, j.title as job_title,
                   ec.id as extended_to_id
            FROM contracts c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN contracts ec ON ec.extension_of = c.id
            WHERE c.candidate_id = ?
            ORDER BY c.start_date DESC
        """, (candidate_id,)).fetchall()
        return [dict(r) for r in rows]


def get_active_contractors_count() -> int:
    """Get count of candidates with active contracts."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT COUNT(DISTINCT candidate_id) as count
            FROM contracts
            WHERE status = 'active'
        """).fetchone()
        return row['count'] if row else 0


def get_contracts_expiring_this_month() -> List[Dict]:
    """Get contracts expiring within the current month."""
    with db_session() as conn:
        rows = conn.execute("""
            SELECT c.*, cand.name as candidate_name, cand.email as candidate_email,
                   j.title as job_title,
                   julianday(c.end_date) - julianday('now') as days_remaining
            FROM contracts c
            JOIN candidates cand ON c.candidate_id = cand.id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.status = 'active'
            AND c.end_date IS NOT NULL
            AND strftime('%Y-%m', c.end_date) = strftime('%Y-%m', 'now')
            ORDER BY c.end_date ASC
        """).fetchall()
        return [dict(r) for r in rows]


# ============ COMPLIANCE DOCUMENT OPERATIONS ============
def add_compliance_doc(candidate_id: int, doc_type: str, status: str = 'pending',
                       received_date: str = None, expiry_date: str = None,
                       file_path: str = None, notes: str = None) -> int:
    """
    Add a compliance document record for a candidate.

    Args:
        candidate_id: Candidate ID
        doc_type: Document type (W9, insurance, NDA, etc.)
        status: Document status (pending, received, verified, expired)
        received_date: Date document was received
        expiry_date: Document expiration date
        file_path: Path to uploaded document
        notes: Additional notes

    Returns:
        New document ID
    """
    with db_session() as conn:
        cursor = conn.execute("""
            INSERT INTO compliance_documents
            (candidate_id, doc_type, status, received_date, expiry_date, file_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (candidate_id, doc_type, status, received_date, expiry_date, file_path, notes))
        return cursor.lastrowid


def get_compliance_docs(candidate_id: int = None, doc_type: str = None,
                       status: str = None) -> List[Dict]:
    """
    Get compliance documents with optional filtering.

    Args:
        candidate_id: Filter by candidate ID
        doc_type: Filter by document type
        status: Filter by status

    Returns:
        List of compliance document dictionaries
    """
    with db_session() as conn:
        query = """
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            WHERE 1=1
        """
        params = []

        if candidate_id:
            query += " AND cd.candidate_id = ?"
            params.append(candidate_id)
        if doc_type:
            query += " AND cd.doc_type = ?"
            params.append(doc_type)
        if status:
            query += " AND cd.status = ?"
            params.append(status)

        query += " ORDER BY cd.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_compliance_doc(doc_id: int) -> Optional[Dict]:
    """Get a single compliance document by ID."""
    with db_session() as conn:
        row = conn.execute("""
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            WHERE cd.id = ?
        """, (doc_id,)).fetchone()
        return dict(row) if row else None


def update_compliance_doc(doc_id: int, **kwargs) -> bool:
    """Update compliance document fields."""
    ALLOWED_COLUMNS = {'candidate_id', 'doc_type', 'status', 'received_date', 'expiry_date', 'file_path', 'notes'}
    invalid_cols = set(kwargs.keys()) - ALLOWED_COLUMNS
    if invalid_cols:
        raise ValueError(f"Invalid column names: {invalid_cols}")
    with db_session() as conn:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        conn.execute(f"UPDATE compliance_documents SET {set_clause} WHERE id = ?",
                    (*kwargs.values(), doc_id))
        return True


def delete_compliance_doc(doc_id: int) -> bool:
    """Delete a compliance document."""
    with db_session() as conn:
        conn.execute("DELETE FROM compliance_documents WHERE id = ?", (doc_id,))
        return True


def get_compliance_alerts() -> List[Dict]:
    """
    Get compliance documents that need attention (expired or expiring soon).

    Returns:
        List of documents with issues, sorted by urgency
    """
    with db_session() as conn:
        rows = conn.execute("""
            SELECT cd.*, c.name as candidate_name, c.email as candidate_email,
                   CASE
                       WHEN cd.status = 'expired' THEN 'expired'
                       WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) < date('now') THEN 'expired'
                       WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days') THEN 'expiring_soon'
                       WHEN cd.status = 'pending' THEN 'pending'
                       ELSE 'ok'
                   END as alert_type,
                   julianday(cd.expiry_date) - julianday('now') as days_until_expiry
            FROM compliance_documents cd
            JOIN candidates c ON cd.candidate_id = c.id
            JOIN contracts con ON cd.candidate_id = con.candidate_id AND con.status = 'active'
            WHERE cd.status IN ('pending', 'expired')
               OR (cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days'))
            ORDER BY
                CASE
                    WHEN cd.status = 'expired' OR (cd.expiry_date IS NOT NULL AND date(cd.expiry_date) < date('now')) THEN 1
                    WHEN cd.expiry_date IS NOT NULL AND date(cd.expiry_date) <= date('now', '+30 days') THEN 2
                    WHEN cd.status = 'pending' THEN 3
                    ELSE 4
                END,
                cd.expiry_date ASC
        """).fetchall()
        return [dict(r) for r in rows]


def get_compliance_matrix() -> List[Dict]:
    """
    Get compliance status matrix for all active contractors.

    Returns:
        List of candidates with their compliance document statuses
    """
    from .schema import COMPLIANCE_DOC_TYPES

    with db_session() as conn:
        # Get all candidates with active contracts
        candidates = conn.execute("""
            SELECT DISTINCT c.id, c.name, c.email
            FROM candidates c
            JOIN contracts con ON c.id = con.candidate_id
            WHERE con.status = 'active'
            ORDER BY c.name
        """).fetchall()

        result = []
        for cand in candidates:
            cand_dict = dict(cand)
            # Get all compliance docs for this candidate
            docs = conn.execute("""
                SELECT doc_type, status, expiry_date
                FROM compliance_documents
                WHERE candidate_id = ?
            """, (cand['id'],)).fetchall()

            doc_status = {}
            for doc_type in COMPLIANCE_DOC_TYPES:
                doc_status[doc_type] = 'missing'

            for doc in docs:
                doc_type = doc['doc_type']
                status = doc['status']
                expiry = doc['expiry_date']

                # Check if expired
                if expiry and status == 'verified':
                    try:
                        exp_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                        if exp_date < datetime.now().date():
                            status = 'expired'
                    except ValueError:
                        pass

                doc_status[doc_type] = status

            cand_dict['documents'] = doc_status
            result.append(cand_dict)

        return result


# ============ PAST CONTRACTOR / REHIRE OPERATIONS ============
def mark_as_past_contractor(candidate_id: int, rehire_eligible: bool = True,
                           notes: str = None) -> bool:
    """
    Mark a candidate as a past contractor.

    Args:
        candidate_id: Candidate ID
        rehire_eligible: Whether the candidate is eligible for rehire
        notes: Rehire notes/reasons

    Returns:
        True if successful
    """
    with db_session() as conn:
        conn.execute("""
            UPDATE candidates
            SET is_past_contractor = 1,
                rehire_eligible = ?,
                rehire_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if rehire_eligible else 0, notes, candidate_id))
        return True


def get_past_contractors(rehire_eligible: bool = None) -> List[Dict]:
    """
    Get all past contractors with optional rehire eligibility filter.

    Args:
        rehire_eligible: Filter by rehire eligibility (None for all)

    Returns:
        List of past contractor candidates
    """
    with db_session() as conn:
        query = """
            SELECT c.*, j.title as job_title, v.name as vendor_name,
                   (SELECT MAX(end_date) FROM contracts WHERE candidate_id = c.id) as last_contract_end_date,
                   (SELECT COUNT(*) FROM contracts WHERE candidate_id = c.id) as total_contracts
            FROM candidates c
            LEFT JOIN jobs j ON c.job_id = j.id
            LEFT JOIN vendors v ON c.vendor_id = v.id
            WHERE c.is_past_contractor = 1
        """
        params = []

        if rehire_eligible is not None:
            query += " AND c.rehire_eligible = ?"
            params.append(1 if rehire_eligible else 0)

        query += " ORDER BY c.last_contract_end DESC, c.name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_rehire_status(candidate_id: int, rehire_eligible: bool, notes: str = None) -> bool:
    """Update a candidate's rehire eligibility status."""
    with db_session() as conn:
        conn.execute("""
            UPDATE candidates
            SET rehire_eligible = ?,
                rehire_notes = COALESCE(?, rehire_notes),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (1 if rehire_eligible else 0, notes, candidate_id))
        return True
