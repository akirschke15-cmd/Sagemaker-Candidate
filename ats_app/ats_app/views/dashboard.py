"""
Dashboard view - Main overview of pipeline metrics and key stats
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    STAGES, get_jobs, get_pipeline_stats_multirole, get_interviews,
    get_candidates, get_job_stats_multirole, get_compensation_stats_by_job,
    get_contracts_expiring_this_month, get_compliance_alerts
)
from views.utils import get_stage_color, safe
from auth import get_current_user, can_view_all_jobs, can_view_all_candidates


def render_dashboard():
    """
    Render the main dashboard showing:
    - Pipeline funnel metrics (candidates per stage)
    - Upcoming interviews
    - Recent candidates
    - Job slots overview
    - Compensation stats
    - Expiring contracts
    - Compliance alerts
    """
    st.title("📊 Dashboard")

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view the dashboard")
        return

    # ============ PIPELINE FUNNEL METRICS ============
    st.subheader("Pipeline Overview")

    # Get pipeline stats
    pipeline_stats = get_pipeline_stats_multirole()

    # Display metrics in columns
    cols = st.columns(len(STAGES))
    for i, stage in enumerate(STAGES):
        count = pipeline_stats.get(stage, 0)
        color = get_stage_color(stage)
        with cols[i]:
            st.markdown(
                f"<div style='background-color:{color}20; padding:16px; border-radius:8px; "
                f"border-left:4px solid {color}; text-align:center;'>"
                f"<div style='font-size:12px; color:{color}; font-weight:600;'>{safe(stage)}</div>"
                f"<div style='font-size:32px; font-weight:700; margin-top:8px;'>{count}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ============ KEY METRICS ROW ============
    metric_cols = st.columns(4)

    with metric_cols[0]:
        total_active = sum(pipeline_stats.values())
        st.metric("Total Active Candidates", total_active)

    with metric_cols[1]:
        upcoming_interviews = get_interviews(upcoming_only=True)
        st.metric("Upcoming Interviews", len(upcoming_interviews))

    with metric_cols[2]:
        jobs = get_jobs(status='Open')
        st.metric("Open Jobs", len(jobs))

    with metric_cols[3]:
        expiring_contracts = get_contracts_expiring_this_month()
        st.metric("Contracts Expiring This Month", len(expiring_contracts))

    st.divider()

    # ============ TWO COLUMN LAYOUT ============
    left_col, right_col = st.columns(2)

    with left_col:
        # ============ UPCOMING INTERVIEWS ============
        st.subheader("📅 Upcoming Interviews")

        if upcoming_interviews:
            for interview in upcoming_interviews[:5]:  # Show top 5
                scheduled_time = interview.get('scheduled_time', '')
                try:
                    dt = datetime.fromisoformat(scheduled_time)
                    time_str = dt.strftime("%b %d, %I:%M %p")
                except:
                    time_str = scheduled_time

                with st.expander(f"**{safe(interview.get('candidate_name'))}** - {safe(interview.get('stage'))} - {time_str}"):
                    st.markdown(f"**Job:** {interview.get('job_title', 'N/A')}")
                    st.markdown(f"**Interviewer:** {interview.get('interviewer_name', 'N/A')}")
                    st.markdown(f"**Email:** {interview.get('interviewer_email', 'N/A')}")
                    if interview.get('location'):
                        st.markdown(f"**Location:** {interview.get('location')}")
                    if interview.get('meeting_link'):
                        st.markdown(f"**Meeting Link:** [{interview.get('meeting_link')}]({interview.get('meeting_link')})")
        else:
            st.info("No upcoming interviews scheduled")

        st.divider()

        # ============ RECENT CANDIDATES ============
        st.subheader("👥 Recent Candidates")

        recent_candidates = get_candidates(status='Active')[:10]  # Top 10 most recent

        if recent_candidates:
            for candidate in recent_candidates:
                stage = candidate.get('current_stage', 'Unknown')
                color = get_stage_color(stage)

                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    if st.button(candidate.get('name', 'Unknown'), key=f"dash_cand_{candidate['id']}", use_container_width=True):
                        st.session_state.current_view = 'candidates'
                        st.session_state.selected_candidate = candidate['id']
                        st.rerun()
                with col2:
                    st.markdown(f"<small>{safe(candidate.get('job_title', 'No job'))}</small>", unsafe_allow_html=True)
                with col3:
                    st.markdown(
                        f"<span style='background-color:{color}; color:white; padding:4px 8px; "
                        f"border-radius:12px; font-size:11px; font-weight:600;'>{safe(stage)}</span>",
                        unsafe_allow_html=True
                    )
        else:
            st.info("No active candidates")

    with right_col:
        # ============ JOB SLOTS OVERVIEW ============
        st.subheader("💼 Job Slots Overview")

        job_stats = get_job_stats_multirole()

        if job_stats:
            for job_stat in job_stats[:5]:  # Top 5 jobs
                job_title = job_stat.get('title', 'Unknown')
                filled = job_stat.get('filled', 0)
                slots = job_stat.get('slots', 1)
                remaining = job_stat.get('remaining_slots', slots)

                with st.expander(f"**{safe(job_title)}** - {filled}/{slots} filled"):
                    st.progress(filled / slots if slots > 0 else 0)
                    st.markdown(f"**Total Candidates:** {job_stat.get('total_candidates', 0)}")
                    st.markdown(f"**Active:** {job_stat.get('active', 0)}")
                    st.markdown(f"**Filled:** {filled}")
                    st.markdown(f"**Remaining Slots:** {remaining}")
        else:
            st.info("No open jobs")

        st.divider()

        # ============ COMPENSATION STATS ============
        st.subheader("💰 Compensation Overview")

        comp_stats = get_compensation_stats_by_job()

        if comp_stats:
            for stat in comp_stats[:5]:  # Top 5 jobs
                job_title = stat.get('job_title', 'Unknown')
                role_name = stat.get('contractor_role_name', 'N/A')
                min_rate = stat.get('min_hourly_rate')
                max_rate = stat.get('max_hourly_rate')
                in_range = stat.get('in_range_count', 0)
                out_range = stat.get('out_of_range_count', 0)
                no_rate = stat.get('no_rate_count', 0)

                with st.expander(f"**{safe(job_title)}** - {safe(role_name)}"):
                    if min_rate and max_rate:
                        st.markdown(f"**Rate Range:** ${min_rate:.2f} - ${max_rate:.2f}/hr")
                    st.markdown(f"✅ In Range: {in_range}")
                    if out_range > 0:
                        st.markdown(f"⚠️ Out of Range: {out_range}")
                    if no_rate > 0:
                        st.markdown(f"❓ No Rate Specified: {no_rate}")
        else:
            st.info("No compensation data available")

    st.divider()

    # ============ ALERTS SECTION ============
    st.subheader("🚨 Alerts & Actions")

    alert_cols = st.columns(2)

    with alert_cols[0]:
        # Expiring contracts
        st.markdown("**📋 Expiring Contracts**")
        if expiring_contracts:
            for contract in expiring_contracts[:5]:
                candidate_name = contract.get('candidate_name', 'Unknown')
                end_date = contract.get('end_date', 'N/A')
                job_title = contract.get('job_title', 'N/A')

                st.warning(f"**{safe(candidate_name)}** - {safe(job_title)}\nEnds: {end_date}")
        else:
            st.success("No contracts expiring this month")

    with alert_cols[1]:
        # Compliance alerts
        st.markdown("**⚠️ Compliance Alerts**")
        compliance_alerts = get_compliance_alerts()

        if compliance_alerts:
            for alert in compliance_alerts[:5]:
                candidate_name = alert.get('candidate_name', 'Unknown')
                doc_type = alert.get('doc_type', 'Unknown')
                status = alert.get('status', 'Unknown')
                expiry_date = alert.get('expiry_date', '')

                if status == 'expired':
                    st.error(f"**{safe(candidate_name)}** - {safe(doc_type)} EXPIRED")
                elif status == 'expiring_soon':
                    st.warning(f"**{safe(candidate_name)}** - {safe(doc_type)} expires {expiry_date}")
                else:
                    st.info(f"**{safe(candidate_name)}** - {safe(doc_type)} {status}")
        else:
            st.success("All compliance documents up to date")
