#!/usr/bin/env python3
"""
One-time script to extract render functions from app.py into separate view modules.
Run this from the ats_app/ directory: python extract_views.py
"""

# Function boundaries (line numbers are 1-indexed)
FUNCTIONS = {
    'dashboard.py': [(352, 516)],  # render_dashboard
    'candidates.py': [(517, 820), (821, 1738)],  # render_candidates + render_candidate_profile
    'jobs.py': [(1739, 1975)],  # render_jobs
    'contractors.py': [(1976, 2347)],  # render_contractors
    'contractor_roles.py': [(2348, 2495)],  # render_contractor_roles
    'vendors.py': [(2496, 2541)],  # render_vendors
    'scheduling.py': [(2542, 2704)],  # render_scheduling
    'analytics.py': [(2705, 3081)],  # render_analytics
    'settings.py': [(3082, 3513)],  # render_settings
    'bulk_import_view.py': [(3514, 3900)],  # render_bulk_import
}

# Imports for each view file (customize as needed)
IMPORTS = {
    'dashboard.py': '''import streamlit as st
import pandas as pd
from database import (
    STAGES, get_jobs, get_pipeline_stats_multirole, get_interviews,
    get_candidates, get_job_stats_multirole, get_compensation_stats_by_job,
    get_contracts_expiring_this_month, get_compliance_alerts
)
''',
    'candidates.py': '''import streamlit as st
from datetime import datetime, timedelta
from database import (
    STAGES, COMPLIANCE_DOC_TYPES,
    get_jobs, get_vendors, get_candidates, get_candidate, create_candidate,
    update_candidate, advance_candidate, reject_candidate,
    get_scoring_criteria, score_candidate, get_candidate_scores, get_stage_total_score,
    add_stage_notes, get_stage_notes, update_note_ai_summary,
    schedule_interview, get_interviews, get_email_templates, log_email,
    get_rate_status, get_contractor_role, get_job,
    get_candidate_jobs, add_candidate_to_job, remove_candidate_from_job,
    advance_candidate_in_role, reject_candidate_in_role,
    update_candidate_role_score, set_primary_job,
    add_stage_notes_for_role, get_stage_notes_with_role, db_session,
    save_interview_question, get_saved_questions, toggle_question_standard, delete_saved_question,
    get_contracts, extend_contract, get_compliance_docs, add_compliance_doc
)
from genai import (
    smart_score_resume, smart_summarize_notes, generate_interview_prep,
    smart_generate_interview_questions
)
from email_utils import render_template, build_email_context, send_email, validate_email
from resume_parser import (
    parse_resume, save_resume_file, get_supported_extensions,
    validate_file_size, get_parse_status
)
from mobile_scorecard import generate_scorecard_token
from comparison_view import render_comparison_view
from calendar_integration import generate_ics_event, generate_ics_filename
from email_automation import trigger_stage_change_email
from auth import get_current_user, get_visible_job_ids
from views.utils import get_stage_color
''',
    'jobs.py': '''import streamlit as st
from database import (
    STAGES, get_jobs, create_job, get_job, update_job,
    get_scoring_criteria, set_scoring_criteria,
    get_candidates, get_contractor_roles, get_contractor_role,
    get_job_owners, assign_job_owner, remove_job_owner,
    get_users, USER_ROLES
)
from auth import (
    has_permission, get_visible_job_ids,
    get_role_display_name
)
''',
    # Add similar imports for other files as needed
}

def extract_views():
    """Extract render functions from app.py into views/ directory"""
    import os

    # Read app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Create views directory if it doesn't exist
    os.makedirs('views', exist_ok=True)

    # Extract each view file
    for filename, function_ranges in FUNCTIONS.items():
        print(f"Creating views/{filename}...")

        with open(f'views/{filename}', 'w', encoding='utf-8') as f:
            # Write docstring
            f.write(f'"""\n{filename.replace(".py", "").replace("_", " ").title()} view\n"""\n')

            # Write imports
            if filename in IMPORTS:
                f.write(IMPORTS[filename])
            f.write('\n\n')

            # Write function(s)
            for start, end in function_ranges:
                # Lines are 1-indexed, so subtract 1
                function_lines = lines[start-1:end]
                f.write(''.join(function_lines))
                f.write('\n')

    print("\nAll view files created!")
    print("\nNext step: Update app.py to import from views/")

if __name__ == '__main__':
    extract_views()
