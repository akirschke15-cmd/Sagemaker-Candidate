"""
Contractor Roles view - Manage contractor roles and rate ranges
"""
import streamlit as st
from database import (
    create_contractor_role, get_contractor_roles, get_contractor_role,
    update_contractor_role, delete_contractor_role, activate_contractor_role,
    get_jobs_by_contractor_role, get_compensation_stats_by_job,
    get_contracts
)
from auth import has_permission, get_current_user
from views.utils import safe, section_header, kpi_row, metric_card, status_badge, progress_bar_html, empty_state


def render_contractor_roles():
    """Render contractor roles management page"""
    st.markdown(section_header("Contractor Roles", "Manage roles and rate ranges"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.error("Please log in to access this page")
        return

    # Summary metrics - Premium KPI Row
    all_roles = get_contractor_roles(active_only=False)
    active_roles = [r for r in all_roles if r.get('is_active', 1)]
    jobs_with_roles = sum(1 for role in active_roles if get_jobs_by_contractor_role(role['id']))

    kpi_items = [
        {"label": "Total Roles", "value": len(all_roles), "icon": "&#128188;", "color": "#304CB2"},
        {"label": "Active Roles", "value": len(active_roles), "icon": "&#9989;", "color": "#2EA043"},
        {"label": "Roles in Use", "value": jobs_with_roles, "icon": "&#128188;", "color": "#F9B612"}
    ]

    st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

    st.divider()

    # Create new role
    if has_permission('jobs', 'create'):
        with st.expander("➕ Create New Contractor Role", expanded=False):
            with st.form("create_contractor_role"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input("Role Name*", placeholder="Senior Python Developer")
                    min_rate = st.number_input("Minimum Hourly Rate ($)*", min_value=0.0, step=5.0, value=50.0)

                with col2:
                    description = st.text_area("Description", height=100, placeholder="Role responsibilities and requirements...")
                    max_rate = st.number_input("Maximum Hourly Rate ($)*", min_value=0.0, step=5.0, value=150.0)

                submitted = st.form_submit_button("Create Role", type="primary", use_container_width=True)

                if submitted:
                    if not name:
                        st.error("Role name is required")
                    elif min_rate <= 0 or max_rate <= 0:
                        st.error("Rates must be greater than 0")
                    elif min_rate >= max_rate:
                        st.error("Minimum rate must be less than maximum rate")
                    else:
                        role_id = create_contractor_role(
                            name=name,
                            description=description,
                            min_rate=min_rate,
                            max_rate=max_rate
                        )
                        st.success(f"Created contractor role: {name}")
                        st.rerun()

    # Filter controls
    col1, col2 = st.columns([3, 1])
    with col1:
        show_inactive = st.checkbox("Show Inactive Roles", value=False)
    with col2:
        sort_by = st.selectbox("Sort by", ["Name", "Min Rate", "Max Rate"], key="role_sort")

    # Display roles
    st.subheader("All Contractor Roles")

    roles_to_display = all_roles if show_inactive else active_roles

    # Apply sorting
    if sort_by == "Name":
        roles_to_display = sorted(roles_to_display, key=lambda x: x['name'])
    elif sort_by == "Min Rate":
        roles_to_display = sorted(roles_to_display, key=lambda x: x.get('min_hourly_rate', 0), reverse=True)
    elif sort_by == "Max Rate":
        roles_to_display = sorted(roles_to_display, key=lambda x: x.get('max_hourly_rate', 0), reverse=True)

    if not roles_to_display:
        st.markdown(empty_state("No contractor roles found", "Create your first role above"), unsafe_allow_html=True)
    else:
        for role in roles_to_display:
            render_contractor_role_card(role)


def render_contractor_role_card(role: dict):
    """Render a single contractor role card with details and actions"""
    is_active = role.get('is_active', 1)

    # Get jobs using this role
    jobs = get_jobs_by_contractor_role(role['id'])

    # Show active contracts for this role
    all_contracts = get_contracts(status='active')
    role_contracts = []
    for contract in all_contracts:
        if contract.get('job_id'):
            job = next((j for j in jobs if j['id'] == contract['job_id']), None)
            if job:
                role_contracts.append(contract)

    status_color = "#2EA043" if is_active else "#6E7681"
    status_text = "Active" if is_active else "Inactive"

    # Premium role card
    card_html = f"""
    <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                border: 1px solid rgba(48, 76, 178, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 16px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
            <div style="flex: 1;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #FFFFFF; font-size: 20px; font-weight: 600;">
                        {safe(role['name'])}
                    </h3>
                    {status_badge(status_text, status_color)}
                </div>
                {f'<p style="margin: 0; color: #8B949E; font-size: 14px;">{safe(role.get("description"))}</p>' if role.get('description') else ''}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
            <div>
                <div style="color: #8B949E; font-size: 12px; margin-bottom: 4px;">RATE RANGE</div>
                <div style="color: #2EA043; font-size: 18px; font-weight: 600;">
                    {f'${role["min_hourly_rate"]:.0f} - ${role["max_hourly_rate"]:.0f}/hr' if role.get('min_hourly_rate') and role.get('max_hourly_rate') else 'Not set'}
                </div>
            </div>
            <div>
                <div style="color: #8B949E; font-size: 12px; margin-bottom: 4px;">JOBS USING ROLE</div>
                <div style="color: #FFFFFF; font-size: 18px; font-weight: 600;">{len(jobs)}</div>
            </div>
            <div>
                <div style="color: #8B949E; font-size: 12px; margin-bottom: 4px;">ACTIVE CONTRACTS</div>
                <div style="color: #FFFFFF; font-size: 18px; font-weight: 600;">{len(role_contracts)}</div>
            </div>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col4:
            if has_permission('jobs', 'edit'):
                if st.button("Edit", key=f"edit_role_{role['id']}", use_container_width=True):
                    st.session_state[f'edit_role_{role["id"]}'] = True
                    st.rerun()

                if is_active:
                    if st.button("Deactivate", key=f"deactivate_role_{role['id']}", use_container_width=True):
                        activate_contractor_role(role['id'], is_active=False)
                        st.success(f"Deactivated role: {role['name']}")
                        st.rerun()
                else:
                    if st.button("Activate", key=f"activate_role_{role['id']}", use_container_width=True):
                        activate_contractor_role(role['id'], is_active=True)
                        st.success(f"Activated role: {role['name']}")
                        st.rerun()

        # Edit form
        if st.session_state.get(f'edit_role_{role["id"]}'):
            with st.form(f"edit_role_form_{role['id']}"):
                st.markdown("**Edit Contractor Role**")

                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Role Name*", value=role['name'])
                    min_rate = st.number_input("Minimum Hourly Rate ($)*", min_value=0.0, step=5.0, value=float(role.get('min_hourly_rate', 0)))

                with col2:
                    description = st.text_area("Description", value=role.get('description') or '', height=100)
                    max_rate = st.number_input("Maximum Hourly Rate ($)*", min_value=0.0, step=5.0, value=float(role.get('max_hourly_rate', 0)))

                col1, col2, col3 = st.columns([2, 1, 1])
                with col2:
                    if st.form_submit_button("Save Changes", type="primary"):
                        if not name:
                            st.error("Role name is required")
                        elif min_rate <= 0 or max_rate <= 0:
                            st.error("Rates must be greater than 0")
                        elif min_rate >= max_rate:
                            st.error("Minimum rate must be less than maximum rate")
                        else:
                            update_contractor_role(
                                role['id'],
                                name=name,
                                description=description,
                                min_rate=min_rate,
                                max_rate=max_rate
                            )
                            st.success("Role updated successfully")
                            del st.session_state[f'edit_role_{role["id"]}']
                            st.rerun()
                with col3:
                    if st.form_submit_button("Cancel"):
                        del st.session_state[f'edit_role_{role["id"]}']
                        st.rerun()

        # Show linked jobs
        jobs = get_jobs_by_contractor_role(role['id'])
        if jobs:
            with st.expander(f"📋 Jobs Using This Role ({len(jobs)})", expanded=False):
                for job in jobs:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.markdown(f"**{safe(job['title'])}**")
                    with col2:
                        st.caption(f"Status: {job['status']}")
                    with col3:
                        st.caption(f"{job.get('slots', 1)} slots")

        # Show rate compliance overview
        if jobs and role.get('min_hourly_rate') and role.get('max_hourly_rate'):
            with st.expander(f"💵 Rate Compliance Overview", expanded=False):
                render_rate_compliance_for_role(role, jobs)

        st.divider()


def render_rate_compliance_for_role(role: dict, jobs: list):
    """Display rate compliance analysis for a contractor role"""
    # Get all contracts for jobs using this role
    all_contracts = get_contracts()
    role_contracts = []

    for contract in all_contracts:
        if contract.get('job_id'):
            job = next((j for j in jobs if j['id'] == contract['job_id']), None)
            if job:
                role_contracts.append(contract)

    if not role_contracts:
        st.info("No contracts found for this role")
        return

    # Calculate rate statistics
    rates = [c['hourly_rate'] for c in role_contracts if c.get('hourly_rate')]

    if not rates:
        st.info("No rate data available")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Contracts", len(role_contracts))
    with col2:
        avg_rate = sum(rates) / len(rates)
        st.metric("Average Rate", f"${avg_rate:.2f}/hr")
    with col3:
        st.metric("Lowest Rate", f"${min(rates):.2f}/hr")
    with col4:
        st.metric("Highest Rate", f"${max(rates):.2f}/hr")

    st.markdown("**Expected Range**")
    st.markdown(f"${role['min_hourly_rate']:.0f} - ${role['max_hourly_rate']:.0f}/hr")

    # Check for out-of-range rates
    below_min = [r for r in rates if r < role['min_hourly_rate']]
    above_max = [r for r in rates if r > role['max_hourly_rate']]
    in_range = [r for r in rates if role['min_hourly_rate'] <= r <= role['max_hourly_rate']]

    # Compliance visualization
    total_rates = len(rates)
    compliance_percent = (len(in_range) / total_rates * 100) if total_rates > 0 else 0

    st.markdown(progress_bar_html(compliance_percent, 100, "#2EA043", "8px", True), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        badge_color = "#C8102E" if below_min else "#2EA043"
        badge_text = f"{len(below_min)} below minimum" if below_min else "None below minimum"
        st.markdown(status_badge(badge_text, badge_color), unsafe_allow_html=True)
    with col2:
        st.markdown(status_badge(f"{len(in_range)} in range", "#2EA043"), unsafe_allow_html=True)
    with col3:
        badge_color = "#C8102E" if above_max else "#2EA043"
        badge_text = f"{len(above_max)} above maximum" if above_max else "None above maximum"
        st.markdown(status_badge(badge_text, badge_color), unsafe_allow_html=True)

    # Show out-of-range contracts
    if below_min or above_max:
        st.markdown("**Out-of-Range Contracts:**")
        from database import get_candidate

        for contract in role_contracts:
            rate = contract.get('hourly_rate', 0)
            if rate < role['min_hourly_rate'] or rate > role['max_hourly_rate']:
                candidate = get_candidate(contract['candidate_id'])
                if candidate:
                    variance = rate - role['min_hourly_rate'] if rate < role['min_hourly_rate'] else rate - role['max_hourly_rate']
                    st.markdown(f"- **{safe(candidate['name'])}**: ${rate:.2f}/hr (${variance:+.2f} from range)")
