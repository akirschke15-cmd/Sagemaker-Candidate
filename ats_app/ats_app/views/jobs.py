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
from auth import (
    has_permission, can_access_job, get_visible_job_ids,
    get_current_user, get_role_display_name
)
from views.utils import get_stage_color, safe


def render_jobs():
    """Render jobs management page with RBAC"""
    st.title("💼 Jobs Management")

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
        st.info("No jobs found matching the filters")
    else:
        # Display jobs as cards
        for job in filtered_jobs:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"### {job['title']}")
                    if job.get('department'):
                        st.caption(f"📁 {job['department']}")

                with col2:
                    status_color = {"Open": "🟢", "Closed": "🔴", "On Hold": "🟡"}
                    st.markdown(f"{status_color.get(job['status'], '⚪')} {job['status']}")
                    st.caption(f"Slots: {job.get('slots', 1)}")

                with col3:
                    if job.get('contractor_role_id'):
                        role = get_contractor_role(job['contractor_role_id'])
                        if role:
                            st.markdown(f"💰 {role['name']}")
                            if role.get('min_hourly_rate') and role.get('max_hourly_rate'):
                                st.caption(f"${role['min_hourly_rate']:.0f}-${role['max_hourly_rate']:.0f}/hr")

                with col4:
                    if st.button("View", key=f"view_job_{job['id']}", use_container_width=True):
                        st.session_state.selected_job = job['id']
                        st.rerun()

                st.divider()

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
        st.title(f"💼 {job['title']}")
    with col2:
        if st.button("← Back", use_container_width=True):
            st.session_state.selected_job = None
            st.rerun()

    # Job Info
    st.subheader("Job Information")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", job['status'])
    with col2:
        st.metric("Slots", job.get('slots', 1))
    with col3:
        candidates = get_candidates(job_id=job_id)
        st.metric("Candidates", len([c for c in candidates if c.get('status') == 'Active']))

    if job.get('department'):
        st.markdown(f"**Department:** {job['department']}")

    if job.get('contractor_role_id'):
        role = get_contractor_role(job['contractor_role_id'])
        if role:
            st.markdown(f"**Contractor Role:** {role['name']}")
            if role.get('min_hourly_rate') and role.get('max_hourly_rate'):
                st.markdown(f"**Rate Range:** ${role['min_hourly_rate']:.0f} - ${role['max_hourly_rate']:.0f}/hr")

    if job.get('description'):
        st.markdown("**Description:**")
        st.markdown(job['description'])

    if job.get('requirements'):
        st.markdown("**Requirements:**")
        st.markdown(job['requirements'])

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 Scoring Criteria", "👥 Job Owners", "⚙️ Settings"])

    with tab1:
        render_scoring_criteria(job_id)

    with tab2:
        render_job_owners_section(job_id)

    with tab3:
        render_job_settings(job_id)


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
                st.markdown(f"👤 {owner['user_name']}")
            with col2:
                st.caption(f"{get_role_display_name(owner['user_role'])} ({owner.get('owner_role', 'hiring_manager')})")
            with col3:
                if has_permission('jobs', 'edit'):
                    if st.button("Remove", key=f"remove_owner_{owner['user_id']}"):
                        remove_job_owner(job_id, owner['user_id'])
                        st.success(f"Removed {owner['user_name']} from job")
                        st.rerun()
    else:
        st.info("No owners assigned to this job")

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
