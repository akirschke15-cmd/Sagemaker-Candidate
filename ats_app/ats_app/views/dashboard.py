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
from views.utils import (
    safe, get_stage_color, get_stage_icon, metric_card, status_badge,
    stage_badge, section_header, pipeline_tracker, empty_state,
    avatar_badge, kpi_row, progress_bar_html
)
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
    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view the dashboard")
        return

    # ============ HERO KPI ROW ============
    st.markdown(section_header("Dashboard", "Real-time overview of your hiring pipeline"), unsafe_allow_html=True)

    pipeline_stats = get_pipeline_stats_multirole()
    upcoming_interviews = get_interviews(upcoming_only=True)
    jobs = get_jobs(status='Open')
    expiring_contracts = get_contracts_expiring_this_month()

    total_active = sum(pipeline_stats.values())

    kpi_items = [
        {
            'label': 'Total Active Candidates',
            'value': total_active,
            'icon': '&#128101;',
            'color': '#304CB2'
        },
        {
            'label': 'Upcoming Interviews',
            'value': len(upcoming_interviews),
            'icon': '&#128197;',
            'color': '#F9B612'
        },
        {
            'label': 'Open Jobs',
            'value': len(jobs),
            'icon': '&#128188;',
            'color': '#2EA043'
        },
        {
            'label': 'Expiring Contracts',
            'value': len(expiring_contracts),
            'icon': '&#9200;',
            'color': '#C8102E' if len(expiring_contracts) > 0 else '#2EA043'
        }
    ]

    st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

    # ============ PIPELINE FUNNEL ============
    st.markdown(section_header("Pipeline Funnel", "Candidates across all stages"), unsafe_allow_html=True)

    st.markdown(pipeline_tracker(STAGES, None, show_icons=True), unsafe_allow_html=True)

    # ============ STAGE COUNTS GRID ============
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    stage_cols = st.columns(len(STAGES))
    for i, stage in enumerate(STAGES):
        count = pipeline_stats.get(stage, 0)
        color = get_stage_color(stage)
        icon = get_stage_icon(stage)

        with stage_cols[i]:
            st.markdown(
                metric_card(stage, count, icon=icon, color=color),
                unsafe_allow_html=True
            )

    # ============ TWO COLUMN LAYOUT ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)

    left_col, right_col = st.columns(2)

    with left_col:
        # ============ UPCOMING INTERVIEWS ============
        st.markdown(section_header("Upcoming Interviews", f"{len(upcoming_interviews)} scheduled"), unsafe_allow_html=True)

        if upcoming_interviews:
            # OPTIMIZATION: Combine HTML generation to reduce st.markdown() calls
            interviews_html_parts = ["""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """]

            # Build expander content separately since expanders need to be interactive
            for interview in upcoming_interviews[:5]:
                scheduled_time = interview.get('scheduled_time', '')
                try:
                    dt = datetime.fromisoformat(scheduled_time)
                    time_str = dt.strftime("%b %d, %I:%M %p")
                except:
                    time_str = scheduled_time

                candidate_name = interview.get('candidate_name', 'Unknown')
                stage = interview.get('stage', 'Unknown')
                job_title = interview.get('job_title', 'N/A')
                interviewer_name = interview.get('interviewer_name', 'N/A')
                interviewer_email = interview.get('interviewer_email', 'N/A')
                location = interview.get('location', '')
                meeting_link = interview.get('meeting_link', '')

                stage_color = get_stage_color(stage)

                # Build expander content
                location_html = f"**Location:** {safe(location)}<br>" if location else ""
                meeting_link_html = f"**Meeting Link:** [{safe(meeting_link)}]({meeting_link})<br>" if meeting_link else ""

                with st.expander(f"**{safe(candidate_name)}** - {time_str}", expanded=False):
                    # OPTIMIZATION: Combine multiple markdown calls into one
                    combined_html = f"""
                    {avatar_badge(candidate_name, f"{safe(job_title)} • {safe(stage)}")}
                    <div style='margin-top:12px;'></div>
                    **Interviewer:** {safe(interviewer_name)}<br>
                    **Email:** {safe(interviewer_email)}<br>
                    {location_html}
                    {meeting_link_html}
                    """
                    st.markdown(combined_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No upcoming interviews", "Schedule interviews to see them here", "&#128197;"),
                unsafe_allow_html=True
            )

        # ============ RECENT CANDIDATES ============
        st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
        st.markdown(section_header("Recent Candidates", "Latest active candidates"), unsafe_allow_html=True)

        recent_candidates = get_candidates(status='Active')[:10]

        if recent_candidates:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

            for candidate in recent_candidates:
                stage = candidate.get('current_stage', 'Unknown')
                job_title = candidate.get('job_title', 'No job')
                candidate_name = candidate.get('name', 'Unknown')

                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    if st.button(candidate_name, key=f"dash_cand_{candidate['id']}", use_container_width=True):
                        st.session_state.current_view = 'candidates'
                        st.session_state.selected_candidate = candidate['id']
                        st.rerun()
                with col2:
                    st.markdown(f"<small style='color:#94a3b8;'>{safe(job_title)}</small>", unsafe_allow_html=True)
                with col3:
                    st.markdown(stage_badge(stage), unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No active candidates", "Add candidates to see them here", "&#128101;"),
                unsafe_allow_html=True
            )

    with right_col:
        # ============ JOB SLOTS OVERVIEW ============
        st.markdown(section_header("Job Slots Overview", "Hiring progress by role"), unsafe_allow_html=True)

        job_stats = get_job_stats_multirole()

        if job_stats:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

            for job_stat in job_stats[:5]:
                job_title = job_stat.get('title', 'Unknown')
                filled = job_stat.get('filled', 0)
                slots = job_stat.get('slots', 1)
                remaining = job_stat.get('remaining_slots', slots)
                total_candidates = job_stat.get('total_candidates', 0)
                active = job_stat.get('active', 0)

                with st.expander(f"**{safe(job_title)}** - {filled}/{slots} filled", expanded=False):
                    st.markdown(progress_bar_html(filled, slots, color='#2EA043'), unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                    st.markdown(f"**Total Candidates:** {total_candidates}")
                    st.markdown(f"**Active:** {active}")
                    st.markdown(f"**Filled:** {filled}")
                    st.markdown(f"**Remaining Slots:** {remaining}")

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No open jobs", "Create jobs to track hiring progress", "&#128188;"),
                unsafe_allow_html=True
            )

        # ============ COMPENSATION OVERVIEW ============
        st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
        st.markdown(section_header("Compensation Overview", "Rate ranges and compliance"), unsafe_allow_html=True)

        comp_stats = get_compensation_stats_by_job()

        if comp_stats:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

            for stat in comp_stats[:5]:
                job_title = stat.get('job_title', 'Unknown')
                role_name = stat.get('contractor_role_name', 'N/A')
                min_rate = stat.get('min_hourly_rate')
                max_rate = stat.get('max_hourly_rate')
                in_range = stat.get('in_range_count', 0)
                out_range = stat.get('out_of_range_count', 0)
                no_rate = stat.get('no_rate_count', 0)

                with st.expander(f"**{safe(job_title)}** - {safe(role_name)}", expanded=False):
                    if min_rate and max_rate:
                        st.markdown(f"**Rate Range:** ${min_rate:.2f} - ${max_rate:.2f}/hr")
                    st.markdown(f"<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

                    # In range
                    st.markdown(f"{status_badge('✓ In Range', '#2EA043')} {in_range} candidates", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

                    # Out of range
                    if out_range > 0:
                        st.markdown(f"{status_badge('⚠ Out of Range', '#F9B612')} {out_range} candidates", unsafe_allow_html=True)
                        st.markdown(f"<div style='margin-top:4px;'></div>", unsafe_allow_html=True)

                    # No rate
                    if no_rate > 0:
                        st.markdown(f"{status_badge('? No Rate', '#64748b')} {no_rate} candidates", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No compensation data", "Add compensation info to candidates", "&#128176;"),
                unsafe_allow_html=True
            )

    # ============ ALERTS SECTION ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Alerts & Actions", "Items requiring attention"), unsafe_allow_html=True)

    alert_cols = st.columns(2)

    with alert_cols[0]:
        # Expiring contracts
        st.markdown("""
        <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                    border-left: 4px solid #C8102E; padding:20px;'>
            <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                &#9200; Expiring Contracts
            </h4>
        """, unsafe_allow_html=True)

        if expiring_contracts:
            for contract in expiring_contracts[:5]:
                candidate_name = contract.get('candidate_name', 'Unknown')
                end_date = contract.get('end_date', 'N/A')
                job_title = contract.get('job_title', 'N/A')

                st.markdown(f"""
                <div style='background: rgba(200,16,46,0.1); border: 1px solid rgba(200,16,46,0.3);
                            border-radius:8px; padding:12px; margin-bottom:8px;'>
                    <div style='color:#ffffff; font-weight:600; margin-bottom:4px;'>
                        {safe(candidate_name)}
                    </div>
                    <div style='color:#94a3b8; font-size:13px;'>
                        {safe(job_title)} • Ends: {safe(end_date)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: rgba(46,160,67,0.1); border: 1px solid rgba(46,160,67,0.3);
                        border-radius:8px; padding:12px; text-align:center; color:#2EA043;'>
                ✓ No contracts expiring this month
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with alert_cols[1]:
        # Compliance alerts
        st.markdown("""
        <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                    border-left: 4px solid #F9B612; padding:20px;'>
            <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                &#9888; Compliance Alerts
            </h4>
        """, unsafe_allow_html=True)

        compliance_alerts = get_compliance_alerts()

        if compliance_alerts:
            for alert in compliance_alerts[:5]:
                candidate_name = alert.get('candidate_name', 'Unknown')
                doc_type = alert.get('doc_type', 'Unknown')
                status = alert.get('status', 'Unknown')
                expiry_date = alert.get('expiry_date', '')

                if status == 'expired':
                    alert_color = '#C8102E'
                    alert_text = f"{safe(doc_type)} EXPIRED"
                elif status == 'expiring_soon':
                    alert_color = '#F9B612'
                    alert_text = f"{safe(doc_type)} expires {safe(expiry_date)}"
                else:
                    alert_color = '#64748b'
                    alert_text = f"{safe(doc_type)} {safe(status)}"

                st.markdown(f"""
                <div style='background: rgba({int(alert_color[1:3], 16)},{int(alert_color[3:5], 16)},{int(alert_color[5:7], 16)},0.1);
                            border: 1px solid rgba({int(alert_color[1:3], 16)},{int(alert_color[3:5], 16)},{int(alert_color[5:7], 16)},0.3);
                            border-radius:8px; padding:12px; margin-bottom:8px;'>
                    <div style='color:#ffffff; font-weight:600; margin-bottom:4px;'>
                        {safe(candidate_name)}
                    </div>
                    <div style='color:#94a3b8; font-size:13px;'>
                        {alert_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background: rgba(46,160,67,0.1); border: 1px solid rgba(46,160,67,0.3);
                        border-radius:8px; padding:12px; text-align:center; color:#2EA043;'>
                ✓ All compliance documents up to date
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
