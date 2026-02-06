"""
Contractors view - Contract lifecycle tracking
"""
import streamlit as st
from datetime import datetime, timedelta
from database import (
    get_contracts, create_contract, get_contract, update_contract,
    get_expiring_contracts, extend_contract, complete_contract, terminate_contract,
    add_compliance_doc, get_compliance_docs, get_compliance_doc, update_compliance_doc,
    delete_compliance_doc, get_compliance_alerts, get_compliance_matrix,
    mark_as_past_contractor, get_past_contractors, update_rehire_status,
    get_contract_history, get_active_contractors_count, get_contracts_expiring_this_month,
    COMPLIANCE_DOC_TYPES, CONTRACT_STATUSES,
    get_candidate, get_candidates, get_jobs, get_contractor_roles
)
from auth import has_permission, get_current_user
from views.utils import safe, section_header, kpi_row, metric_card, status_badge, avatar_badge, empty_state


def render_contractors():
    """Render contractor lifecycle tracking page"""
    st.markdown(section_header("Contractor Management", "Contract lifecycle tracking"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.error("Please log in to access this page")
        return

    # Summary metrics - Premium KPI Row
    active_count = get_active_contractors_count()
    expiring_count = get_contracts_expiring_this_month()
    all_contracts = get_contracts()
    completed = len([c for c in all_contracts if c.get('status') == 'completed'])
    past_contractors = get_past_contractors()

    kpi_items = [
        {"label": "Active Contractors", "value": active_count, "icon": "&#128188;", "color": "#2EA043"},
        {"label": "Expiring This Month", "value": len(expiring_count), "icon": "&#9888;", "color": "#F9B612"},
        {"label": "Completed Contracts", "value": completed, "icon": "&#10003;", "color": "#304CB2"},
        {"label": "Past Contractors", "value": len(past_contractors), "icon": "&#128101;", "color": "#6E7681"}
    ]

    st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Active Contractors",
        "⚠️ Expiring Contracts",
        "📄 Compliance",
        "👥 Past Contractors",
        "💰 Rate Analysis"
    ])

    with tab1:
        render_active_contractors()

    with tab2:
        render_expiring_contracts()

    with tab3:
        render_compliance_tracking()

    with tab4:
        render_past_contractors()

    with tab5:
        render_rate_analysis()


def render_active_contractors():
    """Display and manage active contractor contracts"""
    st.subheader("Active Contractors")

    # Create new contract
    if has_permission('candidates', 'edit'):
        with st.expander("➕ Create New Contract", expanded=False):
            with st.form("create_contract"):
                col1, col2 = st.columns(2)

                with col1:
                    # Get hired candidates to create contracts for
                    all_candidates = get_candidates()
                    hired_candidates = [c for c in all_candidates if c.get('current_stage') == 'Hired']

                    if not hired_candidates:
                        st.info("No hired candidates available. Candidates must be in 'Hired' stage to create contracts.")
                        candidate_id = None
                    else:
                        candidate_options = {c['id']: f"{c['name']} - {c.get('email', 'No email')}" for c in hired_candidates}
                        candidate_id = st.selectbox("Candidate*", options=list(candidate_options.keys()), format_func=lambda x: candidate_options[x])

                    start_date = st.date_input("Start Date*", value=datetime.now().date())

                with col2:
                    jobs = get_jobs()
                    job_options = {j['id']: j['title'] for j in jobs}
                    job_id = st.selectbox(
                        "Job",
                        options=[None] + list(job_options.keys()),
                        format_func=lambda x: "Select a job..." if x is None else job_options[x]
                    )

                    end_date = st.date_input("End Date*", value=(datetime.now() + timedelta(days=90)).date())

                hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.0, step=5.0)
                notes = st.text_area("Notes", height=80)

                if st.form_submit_button("Create Contract", type="primary", disabled=not hired_candidates):
                    if candidate_id and start_date and end_date:
                        contract_id = create_contract(
                            candidate_id=candidate_id,
                            job_id=job_id,
                            start_date=start_date.isoformat(),
                            end_date=end_date.isoformat(),
                            hourly_rate=hourly_rate,
                            notes=notes
                        )
                        st.success(f"Contract created successfully (ID: {contract_id})")
                        st.rerun()
                    else:
                        st.error("Candidate, start date, and end date are required")

    # Display active contracts
    active_contracts = get_contracts(status='active')

    if not active_contracts:
        st.markdown(empty_state("No active contracts", "Create your first contract above"), unsafe_allow_html=True)
    else:
        # OPTIMIZATION: Batch-fetch all candidates and jobs to avoid N+1 queries
        candidate_ids = {c['candidate_id'] for c in active_contracts}
        all_candidates_list = get_candidates()  # Get all candidates once
        candidates_map = {c['id']: c for c in all_candidates_list if c['id'] in candidate_ids}

        job_ids = {c['job_id'] for c in active_contracts if c.get('job_id')}
        all_jobs_list = get_jobs()  # Get all jobs once
        jobs_map = {j['id']: j for j in all_jobs_list if j['id'] in job_ids}

        for contract in active_contracts:
            candidate = candidates_map.get(contract['candidate_id'])
            if not candidate:
                continue

            # Calculate days remaining
            days_remaining = 0
            if contract.get('end_date'):
                end_date = datetime.fromisoformat(contract['end_date'])
                days_remaining = (end_date - datetime.now()).days

            # Get job info from map
            job_title = ""
            if contract.get('job_id'):
                job = jobs_map.get(contract['job_id'])
                if job:
                    job_title = job['title']

            # Premium contract card
            card_html = f"""
            <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                        border: 1px solid rgba(48, 76, 178, 0.2);
                        border-radius: 12px;
                        padding: 24px;
                        margin-bottom: 16px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                    <div>
                        {avatar_badge(safe(candidate['name']), safe(job_title) if job_title else "No job assigned")}
                    </div>
                    <div style="text-align: right;">
                        {metric_card("Rate", f"${contract.get('hourly_rate', 0):.2f}/hr", icon="&#128176;", color="#2EA043") if contract.get('hourly_rate') else ''}
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; font-size: 14px;">
                    <div>
                        <div style="color: #8B949E; margin-bottom: 4px;">Start Date</div>
                        <div style="color: #FFFFFF;">{contract['start_date']}</div>
                    </div>
                    <div>
                        <div style="color: #8B949E; margin-bottom: 4px;">End Date</div>
                        <div style="color: #FFFFFF;">{contract['end_date']}</div>
                    </div>
                    <div>
                        <div style="color: #8B949E; margin-bottom: 4px;">Days Remaining</div>
                        <div style="color: {'#C8102E' if days_remaining < 30 else '#2EA043'}; font-weight: 500;">
                            {days_remaining} days {'⚠' if days_remaining < 30 else ''}
                        </div>
                    </div>
                </div>
            </div>
            """

            st.markdown(card_html, unsafe_allow_html=True)

            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                with col1:
                    pass  # Spacer

                with col2:
                    pass  # Spacer

                with col3:
                    pass  # Spacer

                with col4:
                    # Contract actions
                    if has_permission('candidates', 'edit'):
                        if st.button("Extend", key=f"extend_{contract['id']}", use_container_width=True):
                            st.session_state[f'extend_contract_{contract["id"]}'] = True

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("Complete", key=f"complete_{contract['id']}", use_container_width=True):
                                complete_contract(contract['id'])
                                st.success("Contract marked as completed")
                                st.rerun()
                        with col_b:
                            if st.button("Terminate", key=f"terminate_{contract['id']}", use_container_width=True):
                                st.session_state[f'terminate_contract_{contract["id"]}'] = True

                # Extension dialog
                if st.session_state.get(f'extend_contract_{contract["id"]}'):
                    with st.form(f"extend_form_{contract['id']}"):
                        new_end_date = st.date_input("New End Date", value=(datetime.now() + timedelta(days=90)).date())
                        extension_notes = st.text_area("Extension Notes")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Confirm Extension", type="primary"):
                                new_contract_id = extend_contract(contract['id'], new_end_date.isoformat(), extension_notes)
                                st.success(f"Contract extended (New ID: {new_contract_id})")
                                del st.session_state[f'extend_contract_{contract["id"]}']
                                st.rerun()
                        with col2:
                            if st.form_submit_button("Cancel"):
                                del st.session_state[f'extend_contract_{contract["id"]}']
                                st.rerun()

                # Termination dialog
                if st.session_state.get(f'terminate_contract_{contract["id"]}'):
                    with st.form(f"terminate_form_{contract['id']}"):
                        termination_notes = st.text_area("Termination Reason*")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Confirm Termination", type="primary"):
                                if termination_notes:
                                    terminate_contract(contract['id'], termination_notes)
                                    st.success("Contract terminated")
                                    del st.session_state[f'terminate_contract_{contract["id"]}']
                                    st.rerun()
                                else:
                                    st.error("Termination reason is required")
                        with col2:
                            if st.form_submit_button("Cancel"):
                                del st.session_state[f'terminate_contract_{contract["id"]}']
                                st.rerun()

                st.divider()


def render_expiring_contracts():
    """Display contracts expiring soon"""
    st.subheader("Expiring Contracts (Next 60 Days)")

    expiring = get_expiring_contracts(days=60)

    if not expiring:
        st.success("No contracts expiring in the next 60 days")
    else:
        # OPTIMIZATION: Batch-fetch all candidates to avoid N+1 queries
        candidate_ids = {c['candidate_id'] for c in expiring}
        all_candidates_list = get_candidates()
        candidates_map = {c['id']: c for c in all_candidates_list if c['id'] in candidate_ids}

        for contract in expiring:
            candidate = candidates_map.get(contract['candidate_id'])
            if not candidate:
                continue

            end_date = datetime.fromisoformat(contract['end_date'])
            days_remaining = (end_date - datetime.now()).days

            alert_level = "🔴" if days_remaining < 15 else "🟡" if days_remaining < 30 else "🟢"

            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"{alert_level} **{safe(candidate['name'])}**")
            with col2:
                st.caption(f"End Date: {contract['end_date']}")
            with col3:
                st.caption(f"{days_remaining} days remaining")
            with col4:
                if has_permission('candidates', 'edit'):
                    if st.button("Extend", key=f"extend_exp_{contract['id']}"):
                        st.session_state[f'extend_contract_{contract["id"]}'] = True
                        st.rerun()


def render_compliance_tracking():
    """Display compliance document tracking"""
    st.subheader("Compliance Document Tracking")

    # Get all active contractors
    active_contracts = get_contracts(status='active')
    active_candidate_ids = {c['candidate_id'] for c in active_contracts}

    # Compliance alerts
    alerts = get_compliance_alerts(days=30)
    if alerts:
        st.warning(f"⚠️ {len(alerts)} compliance documents expiring in the next 30 days")

        # OPTIMIZATION: Batch-fetch all candidates to avoid N+1 queries
        alert_candidate_ids = {a['candidate_id'] for a in alerts}
        all_candidates_list = get_candidates()
        alert_candidates_map = {c['id']: c for c in all_candidates_list if c['id'] in alert_candidate_ids}

        for alert in alerts:
            candidate = alert_candidates_map.get(alert['candidate_id'])
            if candidate:
                st.markdown(f"- **{safe(candidate['name'])}**: {safe(alert['doc_type'])} expires {alert['expiry_date']}")

    st.divider()

    # Add compliance document
    if has_permission('candidates', 'edit') and active_candidate_ids:
        with st.expander("➕ Add Compliance Document", expanded=False):
            with st.form("add_compliance_doc"):
                col1, col2 = st.columns(2)

                with col1:
                    # OPTIMIZATION: Get candidates from active contracts using batch fetch
                    all_candidates_list = get_candidates()
                    candidates_with_contracts = [c for c in all_candidates_list if c['id'] in active_candidate_ids]

                    candidate_options = {c['id']: c['name'] for c in candidates_with_contracts}
                    candidate_id = st.selectbox("Contractor*", options=list(candidate_options.keys()), format_func=lambda x: candidate_options[x])

                    doc_type = st.selectbox("Document Type*", options=COMPLIANCE_DOC_TYPES)

                with col2:
                    status = st.selectbox("Status*", options=['pending', 'received', 'verified', 'expired'])
                    received_date = st.date_input("Received Date", value=None)

                expiry_date = st.date_input("Expiry Date (if applicable)", value=None)
                notes = st.text_area("Notes", height=60)

                if st.form_submit_button("Add Document", type="primary"):
                    add_compliance_doc(
                        candidate_id=candidate_id,
                        doc_type=doc_type,
                        status=status,
                        received_date=received_date.isoformat() if received_date else None,
                        expiry_date=expiry_date.isoformat() if expiry_date else None,
                        notes=notes
                    )
                    st.success(f"Added {doc_type} document")
                    st.rerun()

    # Compliance matrix
    st.markdown("### Compliance Matrix")
    matrix = get_compliance_matrix()

    if matrix:
        # OPTIMIZATION: Batch-fetch all candidates to avoid N+1 queries
        matrix_candidate_ids = set(matrix.keys())
        all_candidates_list = get_candidates()
        matrix_candidates_map = {c['id']: c for c in all_candidates_list if c['id'] in matrix_candidate_ids}

        for candidate_id, docs in matrix.items():
            candidate = matrix_candidates_map.get(candidate_id)
            if not candidate:
                continue

            with st.expander(f"👤 {safe(candidate['name'])}", expanded=False):
                for doc in docs:
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        status_icon = {
                            'pending': '⏳',
                            'received': '📄',
                            'verified': '✅',
                            'expired': '❌'
                        }
                        st.markdown(f"{status_icon.get(doc['status'], '⚪')} **{safe(doc['doc_type'])}**")
                    with col2:
                        if doc.get('expiry_date'):
                            expiry = datetime.fromisoformat(doc['expiry_date'])
                            if expiry < datetime.now():
                                st.error(f"Expired: {doc['expiry_date']}")
                            else:
                                st.caption(f"Expires: {doc['expiry_date']}")
                        else:
                            st.caption("No expiry")
                    with col3:
                        st.caption(doc['status'])


def render_past_contractors():
    """Display past contractors with rehire status"""
    st.subheader("Past Contractors")

    past = get_past_contractors()

    if not past:
        st.info("No past contractors")
    else:
        for contractor in past:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"### {safe(contractor['name'])}")
                if contractor.get('email'):
                    st.caption(contractor['email'])

            with col2:
                if contractor.get('last_contract_end'):
                    st.caption(f"Last contract ended: {contractor['last_contract_end']}")

            with col3:
                rehire_status = "✅ Eligible" if contractor.get('rehire_eligible', 1) else "❌ Not Eligible"
                st.markdown(f"**Rehire Status:** {rehire_status}")

            with col4:
                if has_permission('candidates', 'edit'):
                    if st.button("Toggle", key=f"toggle_rehire_{contractor['id']}"):
                        new_status = 0 if contractor.get('rehire_eligible', 1) else 1
                        update_rehire_status(contractor['id'], new_status)
                        st.rerun()

            if contractor.get('rehire_notes'):
                st.caption(f"📝 {contractor['rehire_notes']}")

            # Show contract history
            history = get_contract_history(contractor['id'])
            if history:
                with st.expander(f"Contract History ({len(history)})"):
                    for h in history:
                        st.markdown(f"- **{h['status']}**: {h['start_date']} → {h['end_date']} ({h.get('hourly_rate', 'N/A')}$/hr)")

            st.divider()


def render_rate_analysis():
    """Display rate analysis by contractor role"""
    st.subheader("Rate Analysis by Contractor Role")

    roles = get_contractor_roles(active_only=False)
    contracts = get_contracts()

    # OPTIMIZATION: Get all jobs once and build a map
    all_jobs = get_jobs()
    jobs_map = {j['id']: j for j in all_jobs}

    for role in roles:
        # Find contracts for this role via jobs
        role_contracts = []
        for contract in contracts:
            if contract.get('job_id'):
                job = jobs_map.get(contract['job_id'])
                if job and job.get('contractor_role_id') == role['id']:
                    role_contracts.append(contract)

        if not role_contracts:
            continue

        with st.expander(f"💰 {safe(role['name'])}", expanded=False):
            rates = [c['hourly_rate'] for c in role_contracts if c.get('hourly_rate')]

            if rates:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Active Contracts", len(role_contracts))
                with col2:
                    st.metric("Avg Rate", f"${sum(rates)/len(rates):.2f}/hr")
                with col3:
                    st.metric("Min Rate", f"${min(rates):.2f}/hr")
                with col4:
                    st.metric("Max Rate", f"${max(rates):.2f}/hr")

                # Rate range comparison
                if role.get('min_hourly_rate') and role.get('max_hourly_rate'):
                    st.caption(f"Expected range: ${role['min_hourly_rate']:.2f} - ${role['max_hourly_rate']:.2f}/hr")

                    # Check for out-of-range rates
                    out_of_range = [r for r in rates if r < role['min_hourly_rate'] or r > role['max_hourly_rate']]
                    if out_of_range:
                        st.warning(f"⚠️ {len(out_of_range)} contracts outside expected range")
