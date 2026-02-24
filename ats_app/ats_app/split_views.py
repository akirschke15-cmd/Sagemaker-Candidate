"""
Script to split app.py into separate view modules
"""
import re

# Read the original app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find render function boundaries
render_functions = [
    ('render_dashboard', 352, 516),
    ('render_candidates', 517, 820),  # List view only
    ('render_candidate_profile', 821, 1738),
    ('render_jobs', 1739, 1975),
    ('render_contractors', 1976, 2347),
    ('render_contractor_roles', 2348, 2495),
    ('render_vendors', 2496, 2541),
    ('render_scheduling', 2542, 2704),
    ('render_analytics', 2705, 3081),
    ('render_settings', 3082, 3513),
    ('render_bulk_import', 3514, 3900),
]

# Extract imports needed for each view
common_imports = '''import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
'''

# Extract render_candidates and render_candidate_profile together
candidates_content = common_imports + '''
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
    smart_score_resume, smart_summarize_notes, smart_generate_interview_prep,
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


'''

# Extract render_candidates + render_candidate_profile (lines 517-1738)
candidates_functions = '\n'.join(lines[516:1738])  # -1 because line numbers are 1-indexed

with open('views/candidates.py', 'w', encoding='utf-8') as f:
    f.write('"""\nCandidates view - list and profile views\n"""\n')
    f.write(candidates_content)
    f.write(candidates_functions)

print("Created views/candidates.py")

# Now extract each other view file
# ... (continue for other views)
