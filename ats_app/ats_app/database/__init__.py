"""
ATS Database Package
Organized database operations for the Applicant Tracking System

This package re-exports all database functions to maintain backward compatibility
with the original database.py module structure.
"""

# Connection and schema
from .connection import (
    DB_PATH,
    get_connection,
    db_session,
    init_db,
    migrate_db,
    get_db_type,
    adapt_query,
    explain_query
)

from .schema import (
    STAGES,
    STAGE_ORDER,
    USER_ROLES,
    COMPLIANCE_DOC_TYPES,
    CONTRACT_STATUSES
)

# Vendor operations
from .vendors import (
    create_vendor,
    get_vendors,
    get_vendor
)

# Job operations
from .jobs import (
    create_job,
    get_jobs,
    get_job,
    update_job,
    get_jobs_by_contractor_role,
    set_scoring_criteria,
    get_scoring_criteria
)

# Candidate operations
from .candidates import (
    create_candidate,
    get_candidates,
    get_candidate,
    update_candidate,
    advance_candidate,
    reject_candidate,
    add_candidate_to_job,
    remove_candidate_from_job,
    get_candidate_jobs,
    get_candidate_role_status,
    advance_candidate_in_role,
    reject_candidate_in_role,
    update_candidate_role_score,
    set_primary_job,
    get_candidates_for_job_multirole,
    get_candidates_for_comparison,
    export_candidates_data,
    batch_update_candidates
)

# Scoring operations
from .scoring import (
    score_candidate,
    get_candidate_scores,
    get_stage_total_score,
    add_stage_notes,
    get_stage_notes,
    update_note_ai_summary,
    add_stage_notes_for_role,
    get_stage_notes_with_role,
    save_interview_question,
    get_saved_questions,
    get_saved_question,
    update_saved_question,
    delete_saved_question,
    toggle_question_standard,
    get_question_bank_stats
)

# Interview operations
from .interviews import (
    schedule_interview,
    get_interviews,
    schedule_interview_for_role,
    get_interviews_with_role
)

# Contractor operations
from .contractors import (
    create_contractor_role,
    get_contractor_roles,
    get_contractor_role,
    update_contractor_role,
    delete_contractor_role,
    activate_contractor_role,
    check_rate_in_range,
    get_rate_status,
    get_compensation_stats_by_job,
    create_contract,
    get_contracts,
    get_contract,
    update_contract,
    get_expiring_contracts,
    extend_contract,
    complete_contract,
    terminate_contract,
    get_contract_history,
    get_active_contractors_count,
    get_contracts_expiring_this_month,
    add_compliance_doc,
    get_compliance_docs,
    get_compliance_doc,
    update_compliance_doc,
    delete_compliance_doc,
    get_compliance_alerts,
    get_compliance_matrix,
    mark_as_past_contractor,
    get_past_contractors,
    update_rehire_status
)

# User and RBAC operations
from .users import (
    create_user,
    get_users,
    get_user,
    get_user_by_email,
    update_user,
    deactivate_user,
    activate_user,
    assign_job_owner,
    remove_job_owner,
    get_job_owners,
    get_user_jobs,
    get_user_job_ids,
    is_job_owner,
    get_candidates_for_user_jobs,
    seed_admin_user
)

# Notification operations
from .notifications_db import (
    create_webhook,
    get_webhooks,
    get_webhook,
    update_webhook,
    delete_webhook,
    get_notification_settings,
    update_notification_setting,
    get_webhooks_for_job,
    log_notification_event,
    update_webhook_status,
    get_notification_log
)

# Email operations
from .email_db import (
    get_email_templates,
    get_email_template,
    log_email,
    create_automation_rule,
    get_automation_rules,
    get_automation_rule,
    update_automation_rule,
    delete_automation_rule,
    get_matching_automation_rules,
    queue_email,
    get_pending_emails,
    mark_email_sent,
    mark_email_failed,
    reset_failed_email,
    get_email_queue,
    get_email_automation_stats,
    cancel_pending_email
)

# Analytics operations
from .analytics import (
    get_pipeline_stats,
    get_pipeline_stats_multirole,
    get_vendor_stats,
    get_job_stats,
    get_job_stats_multirole,
    get_pipeline_velocity,
    get_time_to_hire_stats,
    get_stage_conversion_rates,
    get_vendor_performance,
    get_hiring_trends,
    get_rejection_reasons,
    get_ai_score_accuracy,
    get_source_effectiveness
)

# Helper functions
from .helpers import (
    get_jobs_dict,
    get_contractor_roles_dict
)

__all__ = [
    # Connection and schema
    'DB_PATH',
    'get_connection',
    'db_session',
    'init_db',
    'migrate_db',
    'get_db_type',
    'adapt_query',
    'explain_query',
    'STAGES',
    'STAGE_ORDER',
    'USER_ROLES',
    'COMPLIANCE_DOC_TYPES',
    'CONTRACT_STATUSES',

    # Vendors
    'create_vendor',
    'get_vendors',
    'get_vendor',

    # Jobs
    'create_job',
    'get_jobs',
    'get_job',
    'update_job',
    'get_jobs_by_contractor_role',
    'set_scoring_criteria',
    'get_scoring_criteria',

    # Candidates
    'create_candidate',
    'get_candidates',
    'get_candidate',
    'update_candidate',
    'advance_candidate',
    'reject_candidate',
    'add_candidate_to_job',
    'remove_candidate_from_job',
    'get_candidate_jobs',
    'get_candidate_role_status',
    'advance_candidate_in_role',
    'reject_candidate_in_role',
    'update_candidate_role_score',
    'set_primary_job',
    'get_candidates_for_job_multirole',
    'get_candidates_for_comparison',
    'export_candidates_data',
    'batch_update_candidates',

    # Scoring
    'score_candidate',
    'get_candidate_scores',
    'get_stage_total_score',
    'add_stage_notes',
    'get_stage_notes',
    'update_note_ai_summary',
    'add_stage_notes_for_role',
    'get_stage_notes_with_role',
    'save_interview_question',
    'get_saved_questions',
    'get_saved_question',
    'update_saved_question',
    'delete_saved_question',
    'toggle_question_standard',
    'get_question_bank_stats',

    # Interviews
    'schedule_interview',
    'get_interviews',
    'schedule_interview_for_role',
    'get_interviews_with_role',

    # Contractors
    'create_contractor_role',
    'get_contractor_roles',
    'get_contractor_role',
    'update_contractor_role',
    'delete_contractor_role',
    'activate_contractor_role',
    'check_rate_in_range',
    'get_rate_status',
    'get_compensation_stats_by_job',
    'create_contract',
    'get_contracts',
    'get_contract',
    'update_contract',
    'get_expiring_contracts',
    'extend_contract',
    'complete_contract',
    'terminate_contract',
    'get_contract_history',
    'get_active_contractors_count',
    'get_contracts_expiring_this_month',
    'add_compliance_doc',
    'get_compliance_docs',
    'get_compliance_doc',
    'update_compliance_doc',
    'delete_compliance_doc',
    'get_compliance_alerts',
    'get_compliance_matrix',
    'mark_as_past_contractor',
    'get_past_contractors',
    'update_rehire_status',

    # Users and RBAC
    'create_user',
    'get_users',
    'get_user',
    'get_user_by_email',
    'update_user',
    'deactivate_user',
    'activate_user',
    'assign_job_owner',
    'remove_job_owner',
    'get_job_owners',
    'get_user_jobs',
    'get_user_job_ids',
    'is_job_owner',
    'get_candidates_for_user_jobs',
    'seed_admin_user',

    # Notifications
    'create_webhook',
    'get_webhooks',
    'get_webhook',
    'update_webhook',
    'delete_webhook',
    'get_notification_settings',
    'update_notification_setting',
    'get_webhooks_for_job',
    'log_notification_event',
    'update_webhook_status',
    'get_notification_log',

    # Email
    'get_email_templates',
    'get_email_template',
    'log_email',
    'create_automation_rule',
    'get_automation_rules',
    'get_automation_rule',
    'update_automation_rule',
    'delete_automation_rule',
    'get_matching_automation_rules',
    'queue_email',
    'get_pending_emails',
    'mark_email_sent',
    'mark_email_failed',
    'reset_failed_email',
    'get_email_queue',
    'get_email_automation_stats',
    'cancel_pending_email',

    # Analytics
    'get_pipeline_stats',
    'get_pipeline_stats_multirole',
    'get_vendor_stats',
    'get_job_stats',
    'get_job_stats_multirole',
    'get_pipeline_velocity',
    'get_time_to_hire_stats',
    'get_stage_conversion_rates',
    'get_vendor_performance',
    'get_hiring_trends',
    'get_rejection_reasons',
    'get_ai_score_accuracy',
    'get_source_effectiveness',

    # Helpers
    'get_jobs_dict',
    'get_contractor_roles_dict',
]
