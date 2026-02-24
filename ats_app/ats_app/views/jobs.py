"""
Jobs view - Job management interface
"""
import streamlit as st
from datetime import datetime
from database import (
    STAGES, get_jobs, create_job, get_job, update_job,
    get_scoring_criteria, set_scoring_criteria,
    get_candidates, get_contractor_roles, get_contractor_role,
    get_job_owners, assign_job_owner, remove_job_owner,
    get_users, USER_ROLES
)
from genai import smart_comparative_resume_analysis
from comparison_view import render_comparison_view
from auth import (
    has_permission, can_access_job, get_visible_job_ids,
    get_current_user, get_role_display_name
)
from views.utils import (
    get_stage_color, safe, section_header, metric_card, status_badge,
    avatar_badge, stage_badge, empty_state, _clean_html
)


def render_jobs():
    """Render jobs management page with RBAC"""
    st.markdown(section_header("Jobs Management", "Create and manage open positions"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.error("Please log in to access this page")
        return

    # Get visible jobs based on user role
    visible_job_ids = get_visible_job_ids()
    all_jobs = get_jobs()

    if visible_job_ids is not None:
        # Hiring manager - filter to their jobs only
        jobs = [j for j in all_jobs if j['id'] in visible_job_ids]
    else:
        # Admin/Recruiter - see all jobs
        jobs = all_jobs

    # Create Job Form
    if has_permission('jobs', 'create'):
        with st.expander("➕ Create New Job", expanded=False):
            with st.form("create_job_form"):
                col1, col2 = st.columns(2)

                with col1:
                    title = st.text_input("Job Title*", placeholder="Senior Python Developer")
                    department = st.text_input("Department", placeholder="Engineering")
                    slots = st.number_input("Number of Slots", min_value=1, value=1)

                with col2:
                    contractor_roles = get_contractor_roles(active_only=True)
                    contractor_role_options = {role['id']: role['name'] for role in contractor_roles}
                    contractor_role_id = st.selectbox(
                        "Contractor Role",
                        options=[None] + list(contractor_role_options.keys()),
                        format_func=lambda x: "Select a role..." if x is None else contractor_role_options[x]
                    )
                    status = st.selectbox("Status", ["Open", "Closed", "On Hold"])

                description = st.text_area("Job Description", height=100)
                requirements = st.text_area("Requirements", height=100)

                submitted = st.form_submit_button("Create Job", type="primary", use_container_width=True)

                if submitted:
                    if not title:
                        st.error("Job title is required")
                    else:
                        job_id = create_job(
                            title=title,
                            description=description,
                            requirements=requirements,
                            department=department,
                            status=status,
                            slots=slots,
                            contractor_role_id=contractor_role_id
                        )
                        st.success(f"Created job: {title}")
                        st.rerun()

    # Job List
    st.subheader("All Jobs")

    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox("Filter by Status", ["All", "Open", "Closed", "On Hold"], key="job_status_filter")
    with col2:
        filter_dept = st.text_input("Filter by Department", key="job_dept_filter")
    with col3:
        sort_by = st.selectbox("Sort by", ["Recent", "Title", "Department"], key="job_sort")

    # Apply filters
    filtered_jobs = jobs
    if filter_status != "All":
        filtered_jobs = [j for j in filtered_jobs if j.get('status') == filter_status]
    if filter_dept:
        filtered_jobs = [j for j in filtered_jobs if filter_dept.lower() in (j.get('department') or '').lower()]

    # Apply sorting
    if sort_by == "Title":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x['title'])
    elif sort_by == "Department":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('department') or '')
    else:  # Recent
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get('created_at', ''), reverse=True)

    if not filtered_jobs:
        st.markdown(empty_state("No jobs found matching the filters", "Try adjusting your filters"), unsafe_allow_html=True)
    else:
        # Display jobs as premium cards
        for job in filtered_jobs:
            status_colors = {"Open": "#2EA043", "Closed": "#C8102E", "On Hold": "#F9B612"}
            status_color = status_colors.get(job['status'], '#6E7681')

            card_html = f"""
            <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                        border: 1px solid rgba(48, 76, 178, 0.2);
                        border-radius: 12px;
                        padding: 24px;
                        margin-bottom: 16px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 8px 0; color: #FFFFFF; font-size: 20px; font-weight: 600;">
                            {safe(job['title'])}
                        </h3>
                        {f'<p style="margin: 0; color: #8B949E; font-size: 14px;">📁 {safe(job.get("department"))}</p>' if job.get('department') else ''}
                    </div>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        {status_badge(job['status'], status_color)}
                    </div>
                </div>
                <div style="display: flex; gap: 24px; margin-top: 16px; flex-wrap: wrap;">
                    <div style="color: #8B949E; font-size: 14px;">
                        <span style="color: #FFFFFF; font-weight: 500;">{job.get('slots', 1)}</span> slots
                    </div>
            """

            if job.get('contractor_role_id'):
                role = get_contractor_role(job['contractor_role_id'])
                if role:
                    card_html += f"""
                    <div style="color: #8B949E; font-size: 14px;">
                        <span style="color: #F9B612; font-weight: 500;">💰</span> {safe(role['name'])}
                        {f' <span style="color: #6E7681;">| ${role["min_hourly_rate"]:.0f}-${role["max_hourly_rate"]:.0f}/hr</span>' if role.get('min_hourly_rate') and role.get('max_hourly_rate') else ''}
                    </div>
                    """

            card_html += """
                </div>
            </div>
            """

            st.markdown(_clean_html(card_html), unsafe_allow_html=True)

            if st.button("View Details", key=f"view_job_{job['id']}", use_container_width=False):
                st.session_state.selected_job = job['id']
                st.rerun()

    # Job Detail View
    if st.session_state.get('selected_job'):
        render_job_detail(st.session_state.selected_job)


def render_job_detail(job_id: int):
    """Render detailed job view with scoring criteria and job owners"""
    current_user = get_current_user()

    # Check access
    if not can_access_job(job_id):
        st.error("You don't have permission to access this job")
        if st.button("← Back to Jobs"):
            st.session_state.selected_job = None
            st.rerun()
        return

    job = get_job(job_id)
    if not job:
        st.error("Job not found")
        if st.button("← Back to Jobs"):
            st.session_state.selected_job = None
            st.rerun()
        return

    # Header with back button
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(section_header(job['title'], job.get('department', '')), unsafe_allow_html=True)
    with col2:
        if st.button("← Back", use_container_width=True):
            st.session_state.selected_job = None
            st.rerun()

    # Job Info - Premium metrics
    candidates = get_candidates(job_id=job_id)
    active_candidates = len([c for c in candidates if c.get('status') == 'Active'])

    status_colors = {"Open": "#2EA043", "Closed": "#C8102E", "On Hold": "#F9B612"}
    status_color = status_colors.get(job['status'], '#6E7681')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Status", job['status'], icon="🔵", color=status_color), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Available Slots", job.get('slots', 1), icon="💼", color="#304CB2"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Active Candidates", active_candidates, icon="👥", color="#304CB2"), unsafe_allow_html=True)

    if job.get('department'):
        st.markdown(f"**Department:** {job['department']}", unsafe_allow_html=True)

    if job.get('contractor_role_id'):
        role = get_contractor_role(job['contractor_role_id'])
        if role:
            st.markdown(f"**Contractor Role:** {role['name']}", unsafe_allow_html=True)
            if role.get('min_hourly_rate') and role.get('max_hourly_rate'):
                st.markdown(f"**Rate Range:** ${role['min_hourly_rate']:.0f} - ${role['max_hourly_rate']:.0f}/hr", unsafe_allow_html=True)

    if job.get('description'):
        st.markdown("**Description:**", unsafe_allow_html=True)
        st.markdown(job['description'], unsafe_allow_html=True)

    if job.get('requirements'):
        st.markdown("**Requirements:**", unsafe_allow_html=True)
        st.markdown(job['requirements'], unsafe_allow_html=True)

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Scoring Criteria", "👥 Job Owners", "⚙️ Settings", "📋 Candidate Overview & Analysis"])

    with tab1:
        render_scoring_criteria(job_id)

    with tab2:
        render_job_owners_section(job_id)

    with tab3:
        render_job_settings(job_id)

    with tab4:
        render_candidate_analysis(job_id, job, candidates)


def render_candidate_analysis(job_id: int, job: dict, candidates: list):
    """Render candidate overview table and AI comparative analysis"""

    # Initialize session state for head-to-head selection
    h2h_key = f'h2h_candidates_{job_id}'
    if h2h_key not in st.session_state:
        st.session_state[h2h_key] = []

    # If showing head-to-head comparison view, render it and return
    if st.session_state.get(f'show_h2h_{job_id}', False) and len(st.session_state[h2h_key]) >= 2:
        if st.button("← Back to Candidate Overview", key=f"back_h2h_{job_id}"):
            st.session_state[f'show_h2h_{job_id}'] = False
            st.rerun()
        render_comparison_view(st.session_state[h2h_key])
        return

    active_candidates = [c for c in candidates if c.get('status') == 'Active']

    # ============ CANDIDATE SUMMARY TABLE WITH CHECKBOXES ============
    st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Candidates for this Role</div>", unsafe_allow_html=True)

    if not active_candidates:
        st.markdown(empty_state("No candidates assigned", "Add candidates to this job to enable comparative analysis", icon="&#128100;"), unsafe_allow_html=True)
        return

    # Head-to-head selection bar
    selected_ids = st.session_state[h2h_key]
    selected_names = [c.get('name', '?') for c in active_candidates if c.get('id') in selected_ids]

    h2h_bar_cols = st.columns([3, 1, 1])
    with h2h_bar_cols[0]:
        if selected_names:
            st.info(f"Selected for head-to-head: **{', '.join(selected_names)}** ({len(selected_names)}/3)")
        else:
            st.caption("Select 2-3 candidates below for head-to-head comparison")
    with h2h_bar_cols[1]:
        if len(selected_ids) >= 2:
            if st.button("Head-to-Head Compare", type="primary", use_container_width=True, key=f"h2h_btn_{job_id}"):
                st.session_state[f'show_h2h_{job_id}'] = True
                st.rerun()
    with h2h_bar_cols[2]:
        if selected_ids:
            if st.button("Clear Selection", use_container_width=True, key=f"h2h_clear_{job_id}"):
                st.session_state[h2h_key] = []
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Candidate cards with checkboxes
    for c in active_candidates:
        candidate_id = c.get('id')
        score = c.get('ai_resume_score', 0) or 0
        has_resume = bool(c.get('resume_text'))
        score_display = f"{score:.0f}%" if score > 0 else "Not scored"
        resume_display = "On file" if has_resume else "Missing"
        resume_color = "#2EA043" if has_resume else "#C8102E"

        row_cols = st.columns([0.5, 11.5])

        with row_cols[0]:
            is_selected = candidate_id in selected_ids
            checked = st.checkbox("", value=is_selected, key=f"h2h_check_{job_id}_{candidate_id}", label_visibility="collapsed")
            if checked and candidate_id not in st.session_state[h2h_key]:
                if len(st.session_state[h2h_key]) < 3:
                    st.session_state[h2h_key].append(candidate_id)
                    st.rerun()
                else:
                    st.toast("Maximum 3 candidates for head-to-head comparison")
            elif not checked and candidate_id in st.session_state[h2h_key]:
                st.session_state[h2h_key].remove(candidate_id)
                st.rerun()

        with row_cols[1]:
            st.markdown(_clean_html(f"""
            <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid {"#304CB2" if is_selected else "rgba(255,255,255,0.06)"};
            border-radius: 10px; padding: 16px; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between;'>
                <div style='display: flex; align-items: center; gap: 16px;'>
                    {avatar_badge(c.get('name', 'Unknown'), subtitle=c.get('email', ''))}
                </div>
                <div style='display: flex; align-items: center; gap: 24px;'>
                    <div style='text-align: center;'>
                        <div style='color: rgba(255,255,255,0.5); font-size: 11px; text-transform: uppercase;'>Stage</div>
                        <div>{stage_badge(c.get('current_stage', 'Unknown'))}</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: rgba(255,255,255,0.5); font-size: 11px; text-transform: uppercase;'>AI Score</div>
                        <div style='color: rgba(255,255,255,0.9); font-size: 15px; font-weight: 600;'>{score_display}</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: rgba(255,255,255,0.5); font-size: 11px; text-transform: uppercase;'>Resume</div>
                        <div style='color: {resume_color}; font-size: 13px; font-weight: 600;'>{resume_display}</div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============ COMPARATIVE ANALYSIS (ALL CANDIDATES) ============
    st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 16px;'>AI Comparative Analysis — All Candidates</div>", unsafe_allow_html=True)

    # Disclaimer
    st.markdown(_clean_html("""
    <div style='background: rgba(249,182,18,0.08); border: 1px solid rgba(249,182,18,0.3);
    border-radius: 10px; padding: 16px; margin-bottom: 20px;'>
        <div style='color: #F9B612; font-weight: 700; font-size: 13px; margin-bottom: 8px;'>&#9888; IMPORTANT DISCLAIMER</div>
        <div style='color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.6;'>
            This comparative analysis is based <b>solely on resume merit</b> relative to the job description.
            It does <b>not</b> include interview performance, scoring criteria results, or interviewer feedback.
            It is intended only as a side-by-side comparison to assist in initial evaluation.
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Check eligibility
    candidates_with_resumes = [c for c in active_candidates if c.get('resume_text')]

    if len(candidates_with_resumes) < 2:
        st.warning(f"At least 2 candidates with resumes are needed for comparative analysis. Currently {len(candidates_with_resumes)} candidate(s) have resumes.")
    else:
        if st.button("🤖 Generate Comparative Analysis", type="primary", use_container_width=True, key=f"comp_analysis_{job_id}"):
            with st.spinner("Generating comparative resume analysis... This may take a moment."):
                report = smart_comparative_resume_analysis(candidates_with_resumes, job)
                st.session_state[f'comp_analysis_result_{job_id}'] = report

    # Display stored results
    stored_report = st.session_state.get(f'comp_analysis_result_{job_id}')
    if stored_report:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(stored_report)


def render_scoring_criteria(job_id: int):
    """Render and manage scoring criteria for a job"""
    st.subheader("Scoring Criteria by Stage")

    if not has_permission('jobs', 'edit'):
        st.info("You don't have permission to edit scoring criteria")

    # Show criteria for each stage
    for stage in STAGES:
        if stage == "Rejected":
            continue  # Skip rejected stage

        with st.expander(f"{stage}", expanded=stage == "Resume Screen"):
            criteria = get_scoring_criteria(job_id, stage)

            if criteria:
                # Display existing criteria
                for crit in criteria:
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(f"**{crit['criteria_name']}**")
                        if crit.get('description'):
                            st.caption(crit['description'])
                    with col2:
                        st.caption(f"Max: {crit['max_score']}")
                    with col3:
                        st.caption(f"Weight: {crit['weight']}")
                    with col4:
                        if has_permission('jobs', 'edit'):
                            # Note: Delete would require a new database function
                            pass
            else:
                st.info("No scoring criteria defined for this stage")

            # Add new criteria form
            if has_permission('jobs', 'edit'):
                with st.form(f"add_criteria_{stage}"):
                    st.markdown("**Add New Criterion**")
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        crit_name = st.text_input("Criterion Name", key=f"name_{stage}")
                        crit_desc = st.text_input("Description (optional)", key=f"desc_{stage}")
                    with col2:
                        max_score = st.number_input("Max Score", min_value=1, max_value=10, value=5, key=f"max_{stage}")
                    with col3:
                        weight = st.number_input("Weight", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key=f"weight_{stage}")

                    if st.form_submit_button("Add Criterion"):
                        if not crit_name:
                            st.error("Criterion name is required")
                        else:
                            # Get existing criteria and add new one
                            existing = criteria or []
                            new_criteria = existing + [{
                                'criteria_name': crit_name,
                                'max_score': max_score,
                                'weight': weight,
                                'description': crit_desc
                            }]
                            set_scoring_criteria(job_id, stage, new_criteria)
                            st.success(f"Added criterion: {crit_name}")
                            st.rerun()


def render_job_owners_section(job_id: int):
    """Render and manage job owners"""
    st.subheader("Job Owners")

    owners = get_job_owners(job_id)

    if owners:
        st.markdown("**Current Owners:**")
        for owner in owners:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                subtitle = f"{get_role_display_name(owner['user_role'])} • {owner.get('owner_role', 'hiring_manager')}"
                st.markdown(avatar_badge(owner['user_name'], subtitle), unsafe_allow_html=True)
            with col2:
                pass  # Empty for spacing
            with col3:
                if has_permission('jobs', 'edit'):
                    if st.button("Remove", key=f"remove_owner_{owner['user_id']}"):
                        remove_job_owner(job_id, owner['user_id'])
                        st.success(f"Removed {owner['user_name']} from job")
                        st.rerun()
    else:
        st.markdown(empty_state("No owners assigned to this job", "Add an owner below"), unsafe_allow_html=True)

    # Add owner form
    if has_permission('jobs', 'edit'):
        st.divider()
        with st.form("add_job_owner"):
            st.markdown("**Assign New Owner**")

            users = get_users()
            # Filter out users already assigned
            owner_ids = {o['user_id'] for o in owners}
            available_users = [u for u in users if u['id'] not in owner_ids and u.get('is_active', 1)]

            if not available_users:
                st.info("All users are already assigned to this job")
            else:
                user_options = {u['id']: f"{u['name']} ({get_role_display_name(u['role'])})" for u in available_users}

                col1, col2 = st.columns(2)
                with col1:
                    user_id = st.selectbox("User", options=list(user_options.keys()), format_func=lambda x: user_options[x])
                with col2:
                    owner_role = st.selectbox("Owner Role", ["hiring_manager", "recruiter", "contributor"])

                if st.form_submit_button("Assign Owner", type="primary"):
                    assign_job_owner(job_id, user_id, owner_role)
                    st.success(f"Assigned {user_options[user_id]} to job")
                    st.rerun()


def render_job_settings(job_id: int):
    """Render job settings and edit form"""
    st.subheader("Job Settings")

    if not has_permission('jobs', 'edit'):
        st.info("You don't have permission to edit job settings")
        return

    job = get_job(job_id)

    with st.form("edit_job"):
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Job Title", value=job['title'])
            department = st.text_input("Department", value=job.get('department') or '')
            slots = st.number_input("Number of Slots", min_value=1, value=job.get('slots', 1))

        with col2:
            contractor_roles = get_contractor_roles(active_only=True)
            contractor_role_options = {role['id']: role['name'] for role in contractor_roles}
            current_role_id = job.get('contractor_role_id')

            contractor_role_id = st.selectbox(
                "Contractor Role",
                options=[None] + list(contractor_role_options.keys()),
                index=0 if current_role_id is None else (list(contractor_role_options.keys()).index(current_role_id) + 1 if current_role_id in contractor_role_options else 0),
                format_func=lambda x: "No role assigned" if x is None else contractor_role_options.get(x, "Unknown")
            )
            status = st.selectbox("Status", ["Open", "Closed", "On Hold"], index=["Open", "Closed", "On Hold"].index(job['status']))

        description = st.text_area("Job Description", value=job.get('description') or '', height=100)
        requirements = st.text_area("Requirements", value=job.get('requirements') or '', height=100)

        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("Update Job", type="primary", use_container_width=True)

        if submitted:
            if not title:
                st.error("Job title is required")
            else:
                update_job(
                    job_id,
                    title=title,
                    description=description,
                    requirements=requirements,
                    department=department,
                    status=status,
                    slots=slots,
                    contractor_role_id=contractor_role_id
                )
                st.success("Job updated successfully")
                st.rerun()
