"""
Bulk Import Module - CSV/Excel Resume/Candidate Import
Handles parsing, validation, duplicate detection, and bulk creation
"""
import pandas as pd
import io
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from database import (
    db_session, get_candidates, create_candidate, update_candidate,
    get_job, get_vendor
)


# System fields that can be mapped from CSV columns
SYSTEM_FIELDS = {
    'name': {'required': True, 'label': 'Full Name'},
    'email': {'required': False, 'label': 'Email Address'},
    'phone': {'required': False, 'label': 'Phone Number'},
    'resume_text': {'required': False, 'label': 'Resume Text'},
    'notes': {'required': False, 'label': 'Notes'},
}

# Common column name variations for auto-detection
COLUMN_MAPPINGS = {
    'name': ['name', 'full_name', 'fullname', 'candidate_name', 'candidate name',
             'applicant_name', 'applicant name', 'first_last', 'full name'],
    'email': ['email', 'email_address', 'email address', 'e-mail', 'e_mail',
              'candidate_email', 'candidate email', 'applicant_email', 'mail'],
    'phone': ['phone', 'phone_number', 'phone number', 'telephone', 'tel',
              'mobile', 'cell', 'contact_number', 'contact number', 'cell_phone'],
    'resume_text': ['resume', 'resume_text', 'resume text', 'cv', 'cv_text',
                    'resume_content', 'resume content', 'experience', 'summary'],
    'notes': ['notes', 'note', 'comments', 'comment', 'remarks', 'additional_info',
              'additional info', 'info'],
}


def parse_import_file(file_bytes: bytes, filename: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Parse CSV or Excel file into a DataFrame.

    Args:
        file_bytes: Raw file bytes
        filename: Original filename (used to detect format)

    Returns:
        Tuple of (DataFrame or None, error message or None)
    """
    try:
        filename_lower = filename.lower()

        if filename_lower.endswith('.csv'):
            # Try different encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return None, "Could not decode CSV file. Please ensure it's UTF-8 encoded."

        elif filename_lower.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
            except ImportError:
                return None, "Excel support requires openpyxl. Please install with: pip install openpyxl"
            except (ValueError, KeyError) as e:
                return None, f"Failed to parse Excel file: {str(e)}"
        else:
            return None, f"Unsupported file format. Please upload CSV or Excel (.xlsx) files."

        if df.empty:
            return None, "File is empty or contains no data."

        if len(df.columns) == 0:
            return None, "No columns detected in file."

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]

        # Remove completely empty rows
        df = df.dropna(how='all')

        if df.empty:
            return None, "File contains only empty rows."

        return df, None

    except (ValueError, KeyError, pd.errors.ParserError) as e:
        logger.error(f"Failed to parse file {filename}: {e}")
        return None, f"Failed to parse file: {str(e)}"


def auto_detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Auto-detect which CSV columns map to system fields.

    Args:
        df: DataFrame to analyze

    Returns:
        Dict mapping system field names to detected CSV column names (or None if not detected)
    """
    detected = {field: None for field in SYSTEM_FIELDS.keys()}
    csv_columns = [col.lower().strip() for col in df.columns]
    original_columns = list(df.columns)

    for system_field, variations in COLUMN_MAPPINGS.items():
        for variation in variations:
            variation_lower = variation.lower()
            for i, csv_col in enumerate(csv_columns):
                if csv_col == variation_lower or variation_lower in csv_col:
                    detected[system_field] = original_columns[i]
                    break
            if detected[system_field]:
                break

    return detected


def validate_email_format(email: str) -> bool:
    """Validate email format using regex."""
    if not email or pd.isna(email):
        return True  # Empty email is valid (not required)
    email = str(email).strip()
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone_format(phone: str) -> bool:
    """Basic phone validation - allows various formats."""
    if not phone or pd.isna(phone):
        return True  # Empty phone is valid (not required)
    phone = str(phone).strip()
    if not phone:
        return True
    # Remove common formatting characters and check if mostly digits
    cleaned = re.sub(r'[\s\-\.\(\)\+]', '', phone)
    return len(cleaned) >= 7 and cleaned.replace('+', '').isdigit()


def validate_import_row(row: pd.Series, mapping: Dict[str, Optional[str]], row_index: int) -> Tuple[bool, List[str]]:
    """
    Validate a single row from the import file.

    Args:
        row: DataFrame row
        mapping: Dict mapping system fields to CSV columns
        row_index: Row number for error messages

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check required fields
    for field, config in SYSTEM_FIELDS.items():
        if config['required']:
            csv_col = mapping.get(field)
            if not csv_col:
                errors.append(f"Row {row_index}: Required field '{config['label']}' is not mapped")
            elif csv_col not in row.index:
                errors.append(f"Row {row_index}: Mapped column '{csv_col}' not found")
            else:
                value = row.get(csv_col)
                if pd.isna(value) or str(value).strip() == '':
                    errors.append(f"Row {row_index}: Required field '{config['label']}' is empty")

    # Validate email format if mapped and present
    email_col = mapping.get('email')
    if email_col and email_col in row.index:
        email_value = row.get(email_col)
        if not validate_email_format(email_value):
            errors.append(f"Row {row_index}: Invalid email format '{email_value}'")

    # Validate phone format if mapped and present
    phone_col = mapping.get('phone')
    if phone_col and phone_col in row.index:
        phone_value = row.get(phone_col)
        if not validate_phone_format(phone_value):
            errors.append(f"Row {row_index}: Invalid phone format '{phone_value}'")

    return len(errors) == 0, errors


def check_duplicate(email: str) -> Optional[Dict]:
    """
    Check if a candidate with the given email already exists.

    Args:
        email: Email to check

    Returns:
        Existing candidate dict or None
    """
    if not email or pd.isna(email):
        return None

    email = str(email).strip().lower()
    if not email:
        return None

    # Get all candidates and check email (case-insensitive)
    candidates = get_candidates(status=None)  # Get all including rejected
    for candidate in candidates:
        existing_email = candidate.get('email', '')
        if existing_email and existing_email.lower() == email:
            return candidate

    return None


def extract_row_data(row: pd.Series, mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """
    Extract mapped data from a row.

    Args:
        row: DataFrame row
        mapping: Dict mapping system fields to CSV columns

    Returns:
        Dict with extracted values
    """
    data = {}
    for field, csv_col in mapping.items():
        if csv_col and csv_col in row.index:
            value = row.get(csv_col)
            if pd.notna(value):
                data[field] = str(value).strip()
            else:
                data[field] = None
        else:
            data[field] = None
    return data


def bulk_create_candidates(
    df: pd.DataFrame,
    mapping: Dict[str, Optional[str]],
    job_id: Optional[int],
    vendor_id: Optional[int],
    on_duplicate: str = 'skip',  # 'skip', 'update', 'create'
    progress_callback=None
) -> Dict[str, Any]:
    """
    Bulk create candidates from DataFrame.

    Args:
        df: DataFrame with candidate data
        mapping: Dict mapping system fields to CSV columns
        job_id: Optional job ID to assign all candidates
        vendor_id: Optional vendor ID to assign all candidates
        on_duplicate: How to handle duplicates - 'skip', 'update', or 'create'
        progress_callback: Optional callback function(current, total) for progress

    Returns:
        Dict with 'created', 'updated', 'skipped', 'failed' counts and 'failed_rows' list
    """
    results = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0,
        'failed_rows': [],  # List of (row_index, row_data, errors)
        'processed_candidates': []  # List of candidate IDs that were created/updated
    }

    total_rows = len(df)

    for idx, row in df.iterrows():
        row_index = idx + 2  # Excel/CSV row numbers (1-indexed, plus header)

        if progress_callback:
            progress_callback(idx + 1, total_rows)

        # Validate row
        is_valid, errors = validate_import_row(row, mapping, row_index)
        if not is_valid:
            results['failed'] += 1
            row_data = extract_row_data(row, mapping)
            results['failed_rows'].append((row_index, row_data, errors))
            continue

        # Extract data
        row_data = extract_row_data(row, mapping)

        # Check for duplicate by email
        email = row_data.get('email')
        existing = check_duplicate(email) if email else None

        if existing:
            if on_duplicate == 'skip':
                results['skipped'] += 1
                continue
            elif on_duplicate == 'update':
                # Update existing candidate
                try:
                    update_fields = {}
                    for field in ['name', 'phone', 'resume_text', 'notes']:
                        if row_data.get(field):
                            update_fields[field] = row_data[field]
                    if job_id:
                        update_fields['job_id'] = job_id
                    if vendor_id:
                        update_fields['vendor_id'] = vendor_id

                    if update_fields:
                        update_candidate(existing['id'], **update_fields)

                    results['updated'] += 1
                    results['processed_candidates'].append(existing['id'])
                except (KeyError, ValueError) as e:
                    logger.error(f"Invalid data when updating candidate {existing['id']} at row {row_index}: {e}")
                    results['failed'] += 1
                    results['failed_rows'].append((row_index, row_data, [f"Update failed: {str(e)}"]))
                except Exception as e:
                    logger.exception(f"Unexpected error updating candidate {existing['id']} at row {row_index}")
                    results['failed'] += 1
                    results['failed_rows'].append((row_index, row_data, [f"Update failed: {str(e)}"]))
                continue
            # on_duplicate == 'create' falls through to create new

        # Create new candidate
        try:
            candidate_id = create_candidate(
                name=row_data.get('name', 'Unknown'),
                email=row_data.get('email'),
                phone=row_data.get('phone'),
                job_id=job_id,
                vendor_id=vendor_id,
                resume_text=row_data.get('resume_text')
            )

            # Add notes if present
            if row_data.get('notes'):
                update_candidate(candidate_id, notes=row_data['notes'])

            results['created'] += 1
            results['processed_candidates'].append(candidate_id)

        except (KeyError, ValueError) as e:
            logger.error(f"Invalid data when creating candidate at row {row_index}: {e}")
            results['failed'] += 1
            results['failed_rows'].append((row_index, row_data, [f"Creation failed: {str(e)}"]))
        except Exception as e:
            logger.exception(f"Unexpected error creating candidate at row {row_index}")
            results['failed'] += 1
            results['failed_rows'].append((row_index, row_data, [f"Creation failed: {str(e)}"]))

    return results


def generate_error_report(failed_rows: List[Tuple[int, Dict, List[str]]]) -> bytes:
    """
    Generate a CSV error report for failed rows.

    Args:
        failed_rows: List of (row_index, row_data, errors) tuples

    Returns:
        CSV file as bytes
    """
    if not failed_rows:
        return b"No errors to report"

    report_data = []
    for row_index, row_data, errors in failed_rows:
        report_data.append({
            'Original Row': row_index,
            'Name': row_data.get('name', ''),
            'Email': row_data.get('email', ''),
            'Phone': row_data.get('phone', ''),
            'Errors': '; '.join(errors)
        })

    df = pd.DataFrame(report_data)

    # Convert to CSV bytes
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    return output.getvalue()


def get_import_preview(df: pd.DataFrame, mapping: Dict[str, Optional[str]], max_rows: int = 10) -> pd.DataFrame:
    """
    Generate a preview DataFrame showing mapped data.

    Args:
        df: Original DataFrame
        mapping: Current column mapping
        max_rows: Maximum rows to include in preview

    Returns:
        Preview DataFrame with mapped columns
    """
    preview_data = []

    for idx, row in df.head(max_rows).iterrows():
        row_data = {
            'Row #': idx + 2  # Excel row number
        }

        for field, config in SYSTEM_FIELDS.items():
            csv_col = mapping.get(field)
            if csv_col and csv_col in row.index:
                value = row.get(csv_col)
                row_data[config['label']] = value if pd.notna(value) else ''
            else:
                row_data[config['label']] = ''

        preview_data.append(row_data)

    return pd.DataFrame(preview_data)


def validate_all_rows(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """
    Validate all rows and return summary.

    Args:
        df: DataFrame to validate
        mapping: Column mapping

    Returns:
        Dict with validation results
    """
    results = {
        'total_rows': len(df),
        'valid_rows': 0,
        'invalid_rows': 0,
        'duplicate_emails': 0,
        'errors': [],  # List of (row_index, errors)
        'duplicates': []  # List of (row_index, email, existing_candidate_name)
    }

    seen_emails = {}  # Track emails within this import for internal duplicates

    for idx, row in df.iterrows():
        row_index = idx + 2

        # Validate row
        is_valid, errors = validate_import_row(row, mapping, row_index)
        if not is_valid:
            results['invalid_rows'] += 1
            results['errors'].append((row_index, errors))
        else:
            results['valid_rows'] += 1

        # Check for duplicates
        email_col = mapping.get('email')
        if email_col and email_col in row.index:
            email = row.get(email_col)
            if email and pd.notna(email):
                email = str(email).strip().lower()

                # Check internal duplicate (within this import file)
                if email in seen_emails:
                    results['duplicate_emails'] += 1
                    results['duplicates'].append((
                        row_index,
                        email,
                        f"Duplicate of row {seen_emails[email]}"
                    ))
                else:
                    seen_emails[email] = row_index

                    # Check database duplicate
                    existing = check_duplicate(email)
                    if existing:
                        results['duplicate_emails'] += 1
                        results['duplicates'].append((
                            row_index,
                            email,
                            f"Existing candidate: {existing.get('name', 'Unknown')}"
                        ))

    return results
