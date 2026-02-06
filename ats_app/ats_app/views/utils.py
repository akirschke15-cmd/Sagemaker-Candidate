"""
Utility functions for views
"""
from html import escape as html_escape


def safe(value):
    """HTML-escape a value for safe insertion into HTML markup."""
    if value is None:
        return ''
    return html_escape(str(value))


def get_stage_color(stage: str) -> str:
    """Stage colors using Southwest Airlines brand palette"""
    colors = {
        'Resume Screen': '#304CB2',      # Southwest Blue
        'Phone Screen': '#3949AB',       # Blue variant
        'Technical Interview': '#F9B612', # Southwest Yellow
        'Behavioral Interview': '#E65100', # Warm orange
        'Offer': '#C8102E',              # Southwest Red
        'Hired': '#2E7D32',              # Success green
        'Rejected': '#C8102E'            # Southwest Red
    }
    return colors.get(stage, '#304CB2')
