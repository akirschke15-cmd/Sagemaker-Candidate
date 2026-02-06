"""
Views package - exports all render functions for the ATS application
"""

from views.dashboard import render_dashboard
from views.candidates import render_candidates, render_candidate_profile
from views.jobs import render_jobs
from views.contractors import render_contractors
from views.contractor_roles import render_contractor_roles
from views.vendors import render_vendors
from views.scheduling import render_scheduling
from views.analytics import render_analytics
from views.settings import render_settings
from views.bulk_import_view import render_bulk_import

__all__ = [
    'render_dashboard',
    'render_candidates',
    'render_candidate_profile',
    'render_jobs',
    'render_contractors',
    'render_contractor_roles',
    'render_vendors',
    'render_scheduling',
    'render_analytics',
    'render_settings',
    'render_bulk_import',
]
