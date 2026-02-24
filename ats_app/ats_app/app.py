"""
Agentic Program ATS - Applicant Tracking System
Streamlit application for managing contractor hiring pipeline
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import logging
from logging_config import setup_logging

# Configure logging once at module load
setup_logging()
logger = logging.getLogger(__name__)

# Local imports
from database import (
    STAGES, get_vendors, create_vendor, get_vendor,
    get_jobs, create_job, get_job, update_job,
    get_scoring_criteria, set_scoring_criteria,
    get_candidates, create_candidate, get_candidate, update_candidate,
    advance_candidate, reject_candidate,
    score_candidate, get_candidate_scores, get_stage_total_score,
    add_stage_notes, get_stage_notes, update_note_ai_summary,
    schedule_interview, get_interviews,
    get_email_templates, log_email,
    get_pipeline_stats, get_vendor_stats, get_job_stats, export_candidates_data,
    # Notification webhook functions (Feature 3)
    create_webhook, get_webhooks, get_webhook, update_webhook, delete_webhook,
    get_notification_settings, update_notification_setting, get_notification_log,
    init_db, migrate_db
)
import database as db_module  # For notification service initialization

# Ensure schema and migrations are current on every startup
init_db()
migrate_db()
from genai import smart_score_resume, smart_summarize_notes, smart_generate_interview_prep, get_ai_backend_status, compare_candidates, smart_generate_interview_questions
from email_utils import render_template, build_email_context, send_email, validate_email
from resume_parser import (
    parse_resume, save_resume_file, get_supported_extensions,
    validate_file_size, get_parse_status
)
from mobile_scorecard import (
    generate_scorecard_token, validate_scorecard_token, submit_mobile_scorecard,
    get_recommendation_options, get_scorecard_tokens_for_interview
)
from mobile_scorecard_ui import render_mobile_scorecard
from comparison_view import render_comparison_view
from bulk_import import (
    parse_import_file, auto_detect_columns, validate_import_row,
    check_duplicate, bulk_create_candidates, generate_error_report,
    get_import_preview, validate_all_rows, SYSTEM_FIELDS
)
from calendar_integration import (
    generate_ics_event, generate_ics_filename, format_event_description,
    save_calendar_event, get_calendar_event
)
from notifications import (
    init_notification_service, get_notification_service,
    send_slack_notification, send_teams_notification,
    format_test_notification
)
from config import settings
# Feature 7: Authentication and RBAC
from auth import (
    init_auth_session, get_current_user, set_current_user, logout_user,
    is_logged_in, has_permission, check_permission, get_user_role,
    is_admin, is_recruiter, is_hiring_manager, is_interviewer,
    can_view_all_jobs, can_view_all_candidates, get_visible_job_ids,
    can_access_job, can_access_candidate, get_allowed_nav_items,
    render_user_selector, get_role_display_name, get_role_badge_color
)
from database import (
    get_users, create_user, get_user, update_user, deactivate_user, activate_user,
    get_job_owners, assign_job_owner, remove_job_owner, get_user_jobs,
    get_candidates_for_user_jobs, USER_ROLES,
    # Multi-role matching functions (Feature 6)
    add_candidate_to_job, remove_candidate_from_job, get_candidate_jobs,
    get_candidate_role_status, advance_candidate_in_role, reject_candidate_in_role,
    update_candidate_role_score, set_primary_job, get_candidates_for_job_multirole,
    get_pipeline_stats_multirole, get_job_stats_multirole,
    add_stage_notes_for_role, get_stage_notes_with_role,
    schedule_interview_for_role, get_interviews_with_role,
    # Contractor Roles functions
    create_contractor_role, get_contractor_roles, get_contractor_role,
    update_contractor_role, delete_contractor_role, activate_contractor_role,
    check_rate_in_range, get_rate_status, get_jobs_by_contractor_role,
    get_compensation_stats_by_job,
    # Candidate Comparison
    get_candidates_for_comparison,
    # Saved Interview Questions functions
    save_interview_question, get_saved_questions, get_saved_question,
    update_saved_question, delete_saved_question, toggle_question_standard,
    get_question_bank_stats,
    # Email Automation functions
    create_automation_rule, get_automation_rules, get_automation_rule,
    update_automation_rule, delete_automation_rule, get_email_queue,
    get_email_automation_stats, cancel_pending_email, reset_failed_email,
    # Contract Lifecycle Tracking functions
    create_contract, get_contracts, get_contract, update_contract,
    get_expiring_contracts, extend_contract, complete_contract, terminate_contract,
    add_compliance_doc, get_compliance_docs, get_compliance_doc, update_compliance_doc,
    delete_compliance_doc, get_compliance_alerts, get_compliance_matrix,
    mark_as_past_contractor, get_past_contractors, update_rehire_status,
    get_contract_history, get_active_contractors_count, get_contracts_expiring_this_month,
    COMPLIANCE_DOC_TYPES, CONTRACT_STATUSES,
    # Analytics Dashboard functions
    get_pipeline_velocity, get_time_to_hire_stats, get_stage_conversion_rates,
    get_vendor_performance, get_hiring_trends, get_rejection_reasons,
    get_ai_score_accuracy, get_source_effectiveness
)
# Email Automation module
from email_automation import (
    trigger_stage_change_email, process_email_queue, get_automation_summary,
    validate_automation_rule, get_stage_transitions
)

# Import view rendering functions
from views import (
    render_dashboard, render_candidates, render_bulk_import,
    render_jobs, render_contractors, render_contractor_roles,
    render_vendors, render_scheduling, render_analytics, render_settings
)

# Initialize notification service
notification_service = init_notification_service(db_module)

# Helper function to trigger notifications
def trigger_notification_for_event(event_type: str, candidate: dict, job_id: int = None, interview: dict = None):
    """
    Trigger notifications for a specific event.

    Args:
        event_type: 'new_candidate', 'stage_change', or 'interview_scheduled'
        candidate: Candidate data dict
        job_id: Job ID (optional, will use candidate's job_id if not provided)
        interview: Interview data dict (for interview_scheduled events)
    """
    if job_id is None:
        job_id = candidate.get('job_id')

    if not job_id:
        return  # No job assigned, no notifications to send

    job = get_job(job_id)
    job_title = job.get('title', 'Unknown') if job else 'Unknown'

    payload = {
        'job_id': job_id,
        'job_title': job_title,
        'candidate': candidate,
    }

    if interview:
        payload['interview'] = interview

    # Get the notification service and trigger
    ns = get_notification_service()
    if ns:
        try:
            ns.trigger_notification(event_type, payload)
        except (ValueError, TypeError, ConnectionError) as e:
            # Log but don't fail the main operation
            logger.warning(f"Notification error: {e}")

# Page config
st.set_page_config(
    page_title="Agentic Program ATS",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check for mobile scorecard token in URL parameters
query_params = st.query_params
scorecard_token = query_params.get("token", None)

# Apply premium dark SaaS CSS theme
from views.utils import premium_css
st.markdown(premium_css(), unsafe_allow_html=True)

# Session state init — restore from URL query params on refresh
if 'current_view' not in st.session_state:
    st.session_state.current_view = query_params.get('view', 'dashboard')
if 'selected_candidate' not in st.session_state:
    _cand_param = query_params.get('candidate', None)
    st.session_state.selected_candidate = int(_cand_param) if _cand_param else None
if 'selected_job' not in st.session_state:
    st.session_state.selected_job = None
# Candidate comparison state
if 'comparison_candidates' not in st.session_state:
    st.session_state.comparison_candidates = []
if 'show_comparison_view' not in st.session_state:
    st.session_state.show_comparison_view = False

# Initialize auth session state
init_auth_session()

# DEV_MODE: Auto-login as admin if no user is logged in (skip manual login on every refresh)
if settings.DEV_MODE and not get_current_user():
    set_current_user(1)  # Auto-login as first user (admin)

# ============ SIDEBAR ============
with st.sidebar:
    st.title("✈️ Agentic ATS")

    # User login/selector at the top
    render_user_selector()

    st.divider()

    # Only show navigation if logged in
    current_user = get_current_user()
    if current_user:
        # Role-based navigation - define all possible nav items with required permissions
        all_nav_options = {
            'dashboard': {'label': '📊 Dashboard', 'resource': 'dashboard', 'action': 'view'},
            'candidates': {'label': '👥 Candidates', 'resource': 'candidates', 'action': 'view'},
            'bulk_import': {'label': '📤 Bulk Import', 'resource': 'candidates', 'action': 'create'},
            'jobs': {'label': '💼 Jobs', 'resource': 'jobs', 'action': 'view'},
            'contractors': {'label': '📋 Contractors', 'resource': 'candidates', 'action': 'view'},
            'contractor_roles': {'label': '💰 Contractor Roles', 'resource': 'jobs', 'action': 'view'},
            'vendors': {'label': '🏢 Vendors', 'resource': 'vendors', 'action': 'view'},
            'scheduling': {'label': '📅 Scheduling', 'resource': 'scheduling', 'action': 'view'},
            'analytics': {'label': '📈 Analytics', 'resource': 'analytics', 'action': 'view'},
            'settings': {'label': '⚙️ Settings', 'resource': 'settings', 'action': 'view'}
        }

        # Filter navigation based on user permissions
        for key, config in all_nav_options.items():
            if has_permission(config['resource'], config['action']):
                if st.button(config['label'], key=f"nav_{key}", use_container_width=True):
                    st.session_state.current_view = key
                    st.session_state.selected_candidate = None
                    # Sync navigation state to URL query params
                    st.query_params['view'] = key
                    if 'candidate' in st.query_params:
                        del st.query_params['candidate']
                    if "token" in st.query_params:
                        del st.query_params["token"]
                    st.rerun()

        st.divider()

        # Quick stats - filtered for hiring managers
        if can_view_all_candidates():
            stats = get_pipeline_stats()
        else:
            # For hiring managers, count only their candidates
            user_candidates = get_candidates_for_user_jobs(current_user['id'])
            stats = {}
            for c in user_candidates:
                stage = c['current_stage']
                stats[stage] = stats.get(stage, 0) + 1

        total_active = sum(stats.values())
        st.metric("Active Candidates", total_active)

        if can_view_all_jobs():
            jobs = get_jobs(status='Open')
            st.metric("Open Roles", len(jobs))
        else:
            user_jobs = get_user_jobs(current_user['id'])
            st.metric("My Jobs", len(user_jobs))
    else:
        st.info("Please log in to access the ATS")

    # Show interview count and AI status only when logged in
    if current_user:
        interviews = get_interviews(upcoming_only=True)
        st.metric("Upcoming Interviews", len(interviews))

        st.divider()

        # AI Backend Status
        ai_status = get_ai_backend_status()
        if "Claude API" in ai_status:
            st.success(f"🤖 {ai_status}")
        elif "Bedrock" in ai_status:
            st.info(f"☁️ {ai_status}")
        else:
            st.warning(f"⚠️ {ai_status}")

# ============ MAIN ROUTER ============
# All render functions have been moved to views/ directory
# Check for mobile scorecard token first (Feature 5)
if scorecard_token:
    render_mobile_scorecard(scorecard_token)
else:
    view = st.session_state.current_view

    if view == 'dashboard':
        render_dashboard()
    elif view == 'candidates':
        render_candidates()
    elif view == 'bulk_import':
        render_bulk_import()
    elif view == 'jobs':
        render_jobs()
    elif view == 'contractors':
        render_contractors()
    elif view == 'contractor_roles':
        render_contractor_roles()
    elif view == 'vendors':
        render_vendors()
    elif view == 'scheduling':
        render_scheduling()
    elif view == 'analytics':
        render_analytics()
    elif view == 'settings':
        render_settings()
