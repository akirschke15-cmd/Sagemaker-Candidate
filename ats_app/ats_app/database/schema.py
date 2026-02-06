"""
ATS Database Schema Constants
Shared constants, enums, and stage definitions
"""

STAGES = ["Resume Screen", "Phone Screen", "Technical Interview", "Behavioral Interview", "Offer", "Hired", "Rejected"]
STAGE_ORDER = {stage: i for i, stage in enumerate(STAGES)}

# User roles for RBAC
USER_ROLES = ['admin', 'recruiter', 'hiring_manager', 'interviewer']

# Compliance document types
COMPLIANCE_DOC_TYPES = ['W9', 'insurance', 'NDA', 'background_check', 'I9', 'direct_deposit', 'other']

# Contract statuses
CONTRACT_STATUSES = ['active', 'completed', 'terminated', 'extended']
