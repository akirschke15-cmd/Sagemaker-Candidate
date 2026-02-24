"""
Candidates view - List and detail views for candidate management
"""
import json
import streamlit as st
from datetime import datetime, timedelta
from database import (
    STAGES, COMPLIANCE_DOC_TYPES,
    get_jobs, get_vendors, get_candidates, get_candidate, create_candidate,
    update_candidate, advance_candidate, reject_candidate,
    get_scoring_criteria, score_candidate, get_candidate_scores, get_stage_total_score,
    add_stage_notes, get_stage_notes, update_note_ai_summary,
    schedule_interview, get_interviews, get_email_templates, log_email,
    get_rate_status, get_contractor_role, get_job,
    get_candidate_jobs, add_candidate_to_job, remove_candidate_from_job,
    advance_candidate_in_role, reject_candidate_in_role,
    update_candidate_role_score, set_primary_job,
    add_stage_notes_for_role, get_stage_notes_with_role, db_session,
    save_interview_question, get_saved_questions, toggle_question_standard, delete_saved_question,
    get_contracts, extend_contract, get_compliance_docs, add_compliance_doc
)
from genai import (
    smart_score_resume, smart_summarize_notes, smart_generate_interview_prep,
    smart_generate_interview_questions, smart_extract_candidate_info
)
from email_utils import render_template, build_email_context, send_email, validate_email
from resume_parser import (
    parse_resume, save_resume_file, get_supported_extensions,
    validate_file_size, get_parse_status
)
from mobile_scorecard import generate_scorecard_token
from comparison_view import render_comparison_view
from calendar_integration import generate_ics_event, generate_ics_filename
from email_automation import trigger_stage_change_email
from auth import get_current_user, get_visible_job_ids, can_view_all_candidates
from views.utils import (
    get_stage_color, safe, get_stage_icon,
    metric_card, status_badge, stage_badge, section_header,
    avatar_badge, progress_bar_html, pipeline_tracker, empty_state, _clean_html
)


def glass_card(content: str, padding='20px') -> str:
    """Wrap content in glass-morphism card"""
    return f"""
    <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: {padding}; margin-bottom: 16px;'>
        {content}
    </div>
    """


def render_candidates():
    """
    Render the candidates list view with filters and comparison functionality.
    Shows candidate list with checkboxes for comparison, filters by job/stage/vendor,
    and provides access to the candidate profile detail view.
    """
    # Check if showing comparison view
    if st.session_state.get('show_comparison_view', False) and st.session_state.get('comparison_candidates'):
        render_comparison_view(st.session_state.comparison_candidates)
        return

    # Check if viewing a specific candidate profile
    if st.session_state.get('selected_candidate'):
        render_candidate_profile(st.session_state.selected_candidate)
        return

    # Main candidates list view
    st.markdown(section_header("Candidates", subtitle="Manage your hiring pipeline"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view candidates")
        return

    # ============ FILTERS ============
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    filter_cols = st.columns([2, 2, 2, 1])

    # Get available jobs (filtered by permissions)
    if can_view_all_candidates():
        all_jobs = get_jobs()
    else:
        visible_job_ids = get_visible_job_ids(current_user['id'])
        all_jobs = [j for j in get_jobs() if j['id'] in visible_job_ids]

    jobs_dict = {j['id']: j for j in all_jobs}
    job_options = ['All Jobs'] + [f"{j['title']} (ID: {j['id']})" for j in all_jobs]

    with filter_cols[0]:
        selected_job_filter = st.selectbox("Job", job_options, key="job_filter")

    with filter_cols[1]:
        stage_options = ['All Stages'] + STAGES
        selected_stage = st.selectbox("Stage", stage_options, key="stage_filter")

    with filter_cols[2]:
        vendors = get_vendors()
        vendor_options = ['All Vendors'] + [v['name'] for v in vendors]
        selected_vendor = st.selectbox("Vendor", vendor_options, key="vendor_filter")

    with filter_cols[3]:
        status_options = ['Active', 'Rejected', 'All']
        selected_status = st.selectbox("Status", status_options, key="status_filter")

    # Parse filters
    filter_job_id = None
    if selected_job_filter != 'All Jobs':
        # Extract ID from "Title (ID: X)" format
        try:
            filter_job_id = int(selected_job_filter.split('ID: ')[1].rstrip(')'))
        except:
            pass

    filter_stage = None if selected_stage == 'All Stages' else selected_stage

    filter_vendor_id = None
    if selected_vendor != 'All Vendors':
        selected_vendor_obj = next((v for v in vendors if v['name'] == selected_vendor), None)
        if selected_vendor_obj:
            filter_vendor_id = selected_vendor_obj['id']

    filter_status = None if selected_status == 'All' else selected_status

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============ COMPARISON CONTROLS ============
    comparison_col1, comparison_col2 = st.columns([3, 1])

    with comparison_col1:
        if len(st.session_state.get('comparison_candidates', [])) > 0:
            st.info(f"Selected {len(st.session_state.comparison_candidates)} candidates for comparison")

    with comparison_col2:
        if len(st.session_state.get('comparison_candidates', [])) >= 2:
            if st.button("Compare Selected", type="primary", use_container_width=True):
                st.session_state.show_comparison_view = True
                st.rerun()
        if len(st.session_state.get('comparison_candidates', [])) > 0:
            if st.button("Clear Selection", use_container_width=True):
                st.session_state.comparison_candidates = []
                st.rerun()

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============ CANDIDATE LIST ============

    # Fetch candidates
    candidates = get_candidates(
        job_id=filter_job_id,
        vendor_id=filter_vendor_id,
        stage=filter_stage,
        status=filter_status
    )

    if not candidates:
        st.markdown(empty_state("No candidates found", "Try adjusting your filters", icon='&#128269;'), unsafe_allow_html=True)
    else:
        # Table headers - aligned with new row layout
        st.markdown("""
        <div style='background: rgba(26,35,50,0.4); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;'>
            <div style='display: grid; grid-template-columns: 50px 11.5fr; gap: 12px;'>
                <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase;'>Select</div>
                <div style='display: grid; grid-template-columns: 2.5fr 2.5fr 2fr 2fr 1.5fr; gap: 12px;'>
                    <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase;'>Name</div>
                    <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase;'>Job</div>
                    <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase;'>Stage</div>
                    <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase;'>AI Score</div>
                    <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; text-align: center;'>Rate</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Candidate rows
        for candidate in candidates:
            candidate_id = candidate['id']
            candidate_name = candidate.get('name', 'Unknown')
            job_title = candidate.get('job_title', 'No job assigned')
            stage = candidate.get('current_stage', 'Unknown')
            ai_score = candidate.get('ai_resume_score', 0) or 0
            expected_rate = candidate.get('expected_hourly_rate')

            # Rate status calculation
            rate_badge_html = ""
            if expected_rate and candidate.get('job_id'):
                job = jobs_dict.get(candidate['job_id'])
                if job and job.get('contractor_role_id'):
                    rate_status = get_rate_status(candidate['job_id'], expected_rate)
                    if rate_status == 'in_range':
                        rate_badge_html = status_badge('In Range', '#2EA043')
                    elif rate_status == 'below_range':
                        rate_badge_html = status_badge('Below', '#304CB2')
                    elif rate_status == 'above_range':
                        rate_badge_html = status_badge('Above', '#F9B612')
                    else:
                        rate_badge_html = "<span style='color: rgba(255,255,255,0.3);'>-</span>"
                else:
                    rate_badge_html = "<span style='color: rgba(255,255,255,0.3);'>-</span>"
            else:
                rate_badge_html = "<span style='color: rgba(255,255,255,0.3);'>-</span>"

            # Create container for the row with proper layout
            with st.container():
                # Top row: Checkbox + Info Card
                top_cols = st.columns([0.5, 11.5])

                with top_cols[0]:
                    is_selected = candidate_id in st.session_state.get('comparison_candidates', [])
                    if st.checkbox("", value=is_selected, key=f"select_{candidate_id}", label_visibility="collapsed"):
                        if candidate_id not in st.session_state.comparison_candidates:
                            if len(st.session_state.comparison_candidates) < 3:
                                st.session_state.comparison_candidates.append(candidate_id)
                            else:
                                st.warning("Maximum 3 candidates can be compared")
                                st.rerun()
                    else:
                        if candidate_id in st.session_state.comparison_candidates:
                            st.session_state.comparison_candidates.remove(candidate_id)

                with top_cols[1]:
                    # Render candidate info card
                    st.markdown(_clean_html(f"""
                    <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 10px; padding: 16px; transition: all 0.2s ease;'
                    onmouseover="this.style.borderColor='rgba(48,76,178,0.5)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.06)'">
                        <div style='display: grid; grid-template-columns: 2.5fr 2.5fr 2fr 2fr 1.5fr; gap: 12px; align-items: center;'>
                            <div>{avatar_badge(candidate_name, size='sm')}</div>
                            <div style='color: rgba(255,255,255,0.8); font-size: 14px;'>{safe(job_title)}</div>
                            <div>{stage_badge(stage)}</div>
                            <div>{progress_bar_html(ai_score, 100, show_label=True) if ai_score > 0 else "<span style='color: rgba(255,255,255,0.4); font-size: 13px;'>Not scored</span>"}</div>
                            <div style='text-align: center;'>{rate_badge_html}</div>
                        </div>
                    </div>
                    """), unsafe_allow_html=True)

                # Bottom row: View button
                bottom_cols = st.columns([10.5, 1.5])
                with bottom_cols[1]:
                    if st.button("View Profile", key=f"view_{candidate_id}", use_container_width=True):
                        st.session_state.selected_candidate = candidate_id
                        st.query_params['candidate'] = str(candidate_id)
                        st.rerun()

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: rgba(255,255,255,0.5); font-size: 13px; text-align: right;'>Total: {len(candidates)} candidates</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============ ADD CANDIDATE FORM ============
    with st.expander("➕ Add New Candidate", expanded=False):
        st.markdown("<div style='color: white; font-size: 18px; font-weight: 600; margin-bottom: 16px;'>Create Candidate</div>", unsafe_allow_html=True)

        # Resume upload (outside form so it can trigger extraction immediately)
        resume_file = st.file_uploader(
            "Upload Resume to Auto-Fill",
            type=get_supported_extensions(),
            key="new_cand_resume_upload"
        )

        if resume_file:
            # Only process if we haven't already processed this file
            file_key = f"{resume_file.name}_{resume_file.size}"
            if st.session_state.get('_parsed_resume_key') != file_key:
                with st.spinner("Extracting info from resume..."):
                    file_bytes = resume_file.getvalue()
                    resume_text, warnings = parse_resume(file_bytes, resume_file.name)

                    if resume_text:
                        extracted = smart_extract_candidate_info(resume_text)
                        st.session_state['_parsed_resume_text'] = resume_text
                        st.session_state['_parsed_resume_filename'] = resume_file.name
                        st.session_state['_parsed_resume_key'] = file_key
                        # Write directly to widget keys so form fields update
                        st.session_state['new_cand_name'] = extracted.get('name', '')
                        st.session_state['new_cand_email'] = extracted.get('email', '')
                        st.session_state['new_cand_phone'] = extracted.get('phone', '')
                        if warnings:
                            for w in warnings:
                                st.warning(w)
                        st.success(f"Resume parsed — fields auto-filled below")
                        st.rerun()
                    else:
                        for w in warnings:
                            st.error(w)

        with st.form("add_candidate_form"):
            new_name = st.text_input("Name*", key="new_cand_name")
            new_email = st.text_input("Email", key="new_cand_email")
            new_phone = st.text_input("Phone", key="new_cand_phone")

            job_options_form = ['No job'] + [f"{j['title']} (ID: {j['id']})" for j in all_jobs]
            new_job = st.selectbox("Job", job_options_form, key="new_cand_job")

            vendor_options_form = ['No vendor'] + [v['name'] for v in vendors]
            new_vendor = st.selectbox("Vendor", vendor_options_form, key="new_cand_vendor")

            new_rate = st.number_input("Expected Hourly Rate ($)", min_value=0.0, step=1.0, key="new_cand_rate")

            submitted = st.form_submit_button("Create Candidate", type="primary")

            if submitted:
                if not new_name:
                    st.error("Name is required")
                else:
                    # Parse job and vendor
                    job_id = None
                    if new_job != 'No job':
                        try:
                            job_id = int(new_job.split('ID: ')[1].rstrip(')'))
                        except:
                            pass

                    vendor_id = None
                    if new_vendor != 'No vendor':
                        vendor_obj = next((v for v in vendors if v['name'] == new_vendor), None)
                        if vendor_obj:
                            vendor_id = vendor_obj['id']

                    # Get resume data from session state if uploaded
                    resume_text = st.session_state.get('_parsed_resume_text')
                    resume_filename = st.session_state.get('_parsed_resume_filename')

                    # Create candidate
                    candidate_id = create_candidate(
                        name=new_name,
                        email=new_email if new_email else None,
                        phone=new_phone if new_phone else None,
                        vendor_id=vendor_id,
                        job_id=job_id,
                        resume_text=resume_text,
                        resume_original_filename=resume_filename
                    )

                    # Update rate if provided
                    if new_rate > 0:
                        update_candidate(candidate_id, expected_hourly_rate=new_rate)

                    # Add to candidate_jobs if job assigned
                    if job_id:
                        add_candidate_to_job(candidate_id, job_id, is_primary=1)

                    # Clear parsed resume session state
                    for key in ['_parsed_resume_text', '_parsed_resume_filename', '_parsed_resume_name',
                                '_parsed_resume_email', '_parsed_resume_phone', '_parsed_resume_key']:
                        st.session_state.pop(key, None)

                    st.success(f"Candidate '{new_name}' created successfully!")
                    st.session_state.selected_candidate = candidate_id
                    st.query_params['candidate'] = str(candidate_id)
                    st.rerun()


def render_candidate_profile(candidate_id: int):
    """
    Render detailed candidate profile view with all information:
    - Basic info
    - Resume upload and AI scoring
    - Stage progression controls
    - Scoring criteria
    - Interview notes
    - Stage history
    - Multi-role matching
    - Contract info
    """
    # Get candidate data
    candidate = get_candidate(candidate_id)

    if not candidate:
        st.error("Candidate not found")
        if st.button("Back to Candidates"):
            st.session_state.selected_candidate = None
            if 'candidate' in st.query_params:
                del st.query_params['candidate']
            st.rerun()
        return

    # Resolve job_id: fall back to primary job from candidate_jobs if not set
    if not candidate.get('job_id'):
        candidate_jobs = get_candidate_jobs(candidate_id)
        primary_jobs = [cj for cj in candidate_jobs if cj.get('is_primary')]
        if primary_jobs:
            candidate['job_id'] = primary_jobs[0]['job_id']
        elif candidate_jobs:
            candidate['job_id'] = candidate_jobs[0]['job_id']

    # ============ HEADER WITH BACK BUTTON ============
    if st.button("← Back to List", key="back_btn"):
        st.session_state.selected_candidate = None
        if 'candidate' in st.query_params:
            del st.query_params['candidate']
        st.rerun()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ============ PROFILE HEADER ============
    candidate_name = candidate.get('name', 'Unknown')
    candidate_email = candidate.get('email', 'N/A')
    stage = candidate.get('current_stage', 'Unknown')
    ai_score = candidate.get('ai_resume_score', 0) or 0

    # Profile header card
    st.markdown(_clean_html(f"""
    <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px; padding: 32px; margin-bottom: 24px;'>
        <div style='display: flex; align-items: center; gap: 24px;'>
            {avatar_badge(candidate_name, subtitle=candidate_email, size='lg')}
            <div style='flex: 1;'></div>
            <div>{stage_badge(stage)}</div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ============ QUICK METRICS ROW ============
    metric_cols = st.columns(4)

    with metric_cols[0]:
        st.markdown(metric_card("AI Score", f"{ai_score:.0f}%" if ai_score > 0 else "Not scored", icon="&#129302;", color="#304CB2"), unsafe_allow_html=True)

    with metric_cols[1]:
        expected_rate = candidate.get('expected_hourly_rate')
        rate_display = f"${expected_rate:.2f}/hr" if expected_rate else "Not set"
        st.markdown(metric_card("Expected Rate", rate_display, icon="&#128176;", color="#F9B612"), unsafe_allow_html=True)

    with metric_cols[2]:
        vendor_name = candidate.get('vendor_name', 'Direct')
        st.markdown(metric_card("Vendor", vendor_name, icon="&#127970;", color="#304CB2"), unsafe_allow_html=True)

    with metric_cols[3]:
        status = candidate.get('status', 'Unknown')
        status_color = "#2EA043" if status == "Active" else "#C8102E"
        st.markdown(metric_card("Status", status, icon="&#9989;", color=status_color), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ============ INFO SECTION ============
    info_cols = st.columns(3)

    with info_cols[0]:
        contact_html = f"""
        <div style='color: rgba(255,255,255,0.9); font-size: 14px;'>
            <div style='margin-bottom: 12px;'><span style='opacity: 0.6;'>&#128231;</span> {safe(candidate.get('email', 'N/A'))}</div>
            <div><span style='opacity: 0.6;'>&#128241;</span> {safe(candidate.get('phone', 'N/A'))}</div>
        </div>
        """
        st.markdown(glass_card(f"<div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Contact Information</div>{contact_html}", padding='20px'), unsafe_allow_html=True)

    with info_cols[1]:
        stage_color = get_stage_color(stage)
        status_html = f"""
        <div style='text-align: center;'>
            <div style='margin-bottom: 16px;'>{stage_badge(stage)}</div>
            <div style='color: rgba(255,255,255,0.7); font-size: 14px;'>Current Stage</div>
        </div>
        """
        st.markdown(glass_card(f"<div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Current Status</div>{status_html}", padding='20px'), unsafe_allow_html=True)

    with info_cols[2]:
        current_job_id = candidate.get('job_id')
        job_title = candidate.get('job_title', '')
        changing_job = st.session_state.get(f'changing_job_{candidate_id}', False)

        if current_job_id and not changing_job:
            # Locked state — show assigned job with a change button
            job_html = f"""
            <div style='color: rgba(255,255,255,0.9); font-size: 14px;'>
                <div style='margin-bottom: 8px;'><span style='opacity: 0.6;'>&#128188;</span> {safe(job_title or 'Assigned')}</div>
            </div>
            """
            st.markdown(glass_card(f"<div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Job Assignment</div>{job_html}", padding='20px'), unsafe_allow_html=True)
            if st.button("Change Job", key=f"change_job_btn_{candidate_id}", type="secondary"):
                st.session_state[f'changing_job_{candidate_id}'] = True
                st.rerun()
        elif current_job_id and changing_job:
            # Confirmation state — confirm before allowing change
            st.markdown(glass_card(f"<div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Job Assignment</div><div style='color:#F9B612; font-size:13px;'>Currently: {safe(job_title)}</div>", padding='20px 20px 4px 20px'), unsafe_allow_html=True)
            all_jobs_list = get_jobs()
            job_options = [f"{j['title']} (ID: {j['id']})" for j in all_jobs_list]
            current_index = 0
            for i, j in enumerate(all_jobs_list):
                if j['id'] == current_job_id:
                    current_index = i
                    break
            selected_job = st.selectbox(
                "New Job",
                job_options,
                index=current_index,
                key=f"job_reassign_{candidate_id}",
                label_visibility="collapsed"
            )
            confirm_cols = st.columns(2)
            with confirm_cols[0]:
                if st.button("Confirm", key=f"confirm_job_{candidate_id}", type="primary", use_container_width=True):
                    new_job_id = None
                    try:
                        new_job_id = int(selected_job.split('ID: ')[1].rstrip(')'))
                    except (ValueError, IndexError):
                        pass
                    if new_job_id and new_job_id != current_job_id:
                        update_candidate(candidate_id, job_id=new_job_id)
                        existing_cj = get_candidate_jobs(candidate_id)
                        if not any(cj['job_id'] == new_job_id for cj in existing_cj):
                            add_candidate_to_job(candidate_id, new_job_id, is_primary=1)
                    st.session_state[f'changing_job_{candidate_id}'] = False
                    st.rerun()
            with confirm_cols[1]:
                if st.button("Cancel", key=f"cancel_job_{candidate_id}", use_container_width=True):
                    st.session_state[f'changing_job_{candidate_id}'] = False
                    st.rerun()
        else:
            # No job assigned — show selectbox for initial assignment
            st.markdown(glass_card("<div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Job Assignment</div>", padding='20px 20px 4px 20px'), unsafe_allow_html=True)
            all_jobs_list = get_jobs()
            job_options = ['Select a job...'] + [f"{j['title']} (ID: {j['id']})" for j in all_jobs_list]
            selected_job = st.selectbox(
                "Job",
                job_options,
                index=0,
                key=f"job_assign_{candidate_id}",
                label_visibility="collapsed"
            )
            if selected_job != 'Select a job...':
                new_job_id = None
                try:
                    new_job_id = int(selected_job.split('ID: ')[1].rstrip(')'))
                except (ValueError, IndexError):
                    pass
                if new_job_id:
                    update_candidate(candidate_id, job_id=new_job_id)
                    existing_cj = get_candidate_jobs(candidate_id)
                    if not any(cj['job_id'] == new_job_id for cj in existing_cj):
                        add_candidate_to_job(candidate_id, new_job_id, is_primary=1)
                    st.rerun()

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ============ TABS FOR DIFFERENT SECTIONS ============
    tabs = st.tabs([
        "📄 Resume & Scoring",
        "📈 Stage Progression",
        "📝 Interview Notes",
        "💼 Multi-Role Matching",
        "📋 Contract & Compliance"
    ])

    # ============ TAB 1: RESUME & SCORING ============
    with tabs[0]:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Resume Upload & AI Analysis</div>", unsafe_allow_html=True)

        resume_cols = st.columns(2)

        with resume_cols[0]:
            # Resume upload
            uploaded_file = st.file_uploader(
                "Upload Resume",
                type=get_supported_extensions(),
                key=f"resume_upload_{candidate_id}"
            )

            if uploaded_file:
                if st.button("Process Resume", type="primary"):
                    with st.spinner("Processing resume..."):
                        # Validate file size
                        if not validate_file_size(uploaded_file):
                            st.error("File size exceeds maximum limit")
                        else:
                            # Save file
                            file_path = save_resume_file(uploaded_file, candidate_id)

                            # Parse resume
                            resume_text = parse_resume(file_path)

                            if resume_text:
                                # Update candidate
                                update_candidate(
                                    candidate_id,
                                    resume_text=resume_text,
                                    resume_path=file_path,
                                    resume_original_filename=uploaded_file.name
                                )
                                st.success("Resume uploaded successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to parse resume")

        with resume_cols[1]:
            # Current resume info
            if candidate.get('resume_original_filename') or candidate.get('resume_text'):
                resume_filename = candidate.get('resume_original_filename') or 'Resume on file'
                st.markdown(_clean_html(glass_card(f"""
                <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;'>Current Resume</div>
                <div style='color: rgba(255,255,255,0.9); font-size: 14px; margin-bottom: 16px;'>&#128196; {safe(resume_filename)}</div>
                """, padding='20px')), unsafe_allow_html=True)

                # AI Scoring
                ai_score = candidate.get('ai_resume_score', 0) or 0
                if ai_score > 0:
                    st.markdown(metric_card("AI Resume Score", f"{ai_score:.0f}%", icon="&#129302;", color="#304CB2"), unsafe_allow_html=True)
                    if candidate.get('ai_resume_analysis'):
                        with st.expander("View Analysis"):
                            st.markdown(candidate.get('ai_resume_analysis'), unsafe_allow_html=True)

                # Re-score button
                if candidate.get('resume_text'):
                    if candidate.get('job_id'):
                        if st.button("🤖 AI Score Resume", key="ai_score_btn", type="primary", use_container_width=True):
                            with st.spinner("Analyzing resume..."):
                                job = get_job(candidate['job_id'])
                                if job:
                                    score, analysis = smart_score_resume(
                                        candidate.get('resume_text', ''),
                                        job.get('description', ''),
                                        job.get('requirements', '')
                                    )

                                    update_candidate(
                                        candidate_id,
                                        ai_resume_score=score,
                                        ai_resume_analysis=analysis
                                    )
                                    st.success(f"AI Score: {score:.0f}%")
                                    st.rerun()
                    else:
                        st.info("Assign a job to enable AI resume scoring")
            else:
                st.markdown(empty_state("No resume uploaded", "Upload a resume to enable AI scoring", icon='&#128196;'), unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

        # ============ SCORING CRITERIA ============
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Evaluation Scores</div>", unsafe_allow_html=True)
        if candidate.get('job_id'):

            current_stage = candidate.get('current_stage', 'Resume Screen')
            criteria = get_scoring_criteria(candidate['job_id'], current_stage)

            if criteria:
                scores = get_candidate_scores(candidate_id, current_stage)
                scores_dict = {s['criteria_id']: s for s in scores}

                for criterion in criteria:
                    criterion_id = criterion['id']
                    criterion_name = criterion['criteria_name']
                    max_score = criterion['max_score']
                    weight = criterion['weight']

                    existing_score = scores_dict.get(criterion_id, {}).get('score')

                    # Criterion card
                    criterion_desc_html = f"<div style='color: rgba(255,255,255,0.5); font-size: 13px; margin-top: 4px;'>{safe(criterion.get('description', ''))}</div>" if criterion.get('description') else ''

                    st.markdown(_clean_html(f"""
                    <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 10px; padding: 16px; margin-bottom: 12px;'>
                        <div style='color: white; font-size: 15px; font-weight: 600;'>{safe(criterion_name)}</div>
                        {criterion_desc_html}
                        {progress_bar_html(existing_score if existing_score else 0, max_score, show_label=True) if existing_score else ''}
                    </div>
                    """), unsafe_allow_html=True)

                    cols = st.columns([2, 1, 1])
                    with cols[1]:
                        new_score = st.number_input(
                            f"Score (max {max_score})",
                            min_value=0,
                            max_value=max_score,
                            value=existing_score if existing_score else 0,
                            key=f"score_{criterion_id}",
                            label_visibility="collapsed"
                        )
                    with cols[2]:
                        if st.button("Save", key=f"save_score_{criterion_id}", type="primary", use_container_width=True):
                            score_candidate(
                                candidate_id,
                                criterion_id,
                                new_score,
                                evaluator=get_current_user()['name']
                            )
                            st.success("Saved!")
                            st.rerun()

                # Total score
                total = get_stage_total_score(candidate_id, current_stage)
                st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
                total_percentage = total['percentage']
                st.markdown(metric_card("Total Score", f"{total['total']:.1f} / {total['max_possible']:.1f}", delta=f"{total_percentage:.1f}%", icon="&#127919;", color="#304CB2"), unsafe_allow_html=True)
            else:
                st.markdown(empty_state(f"No scoring criteria defined", f"Configure criteria for {current_stage} stage", icon='&#128207;'), unsafe_allow_html=True)
        else:
            st.markdown(empty_state("No job assigned", "Assign a job to this candidate to enable evaluation scoring and AI features", icon='&#128207;'), unsafe_allow_html=True)

    # ============ TAB 2: STAGE PROGRESSION ============
    with tabs[1]:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Stage Progression</div>", unsafe_allow_html=True)

        current_stage = candidate.get('current_stage', 'Resume Screen')

        # Visual stage progression using pipeline tracker
        st.markdown(pipeline_tracker(STAGES, current_stage, show_icons=True), unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # Action buttons in a glass card
        st.markdown("""<div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; padding: 20px; margin-bottom: 16px;'>
        <div style='color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 16px;'>Actions</div>
        """, unsafe_allow_html=True)

        # Action buttons
        action_cols = st.columns(3)
        current_stage_idx = STAGES.index(current_stage) if current_stage in STAGES else 0

        with action_cols[0]:
            # Advance to next stage
            if current_stage != 'Hired' and current_stage != 'Rejected':
                next_stage_idx = current_stage_idx + 1
                if next_stage_idx < len(STAGES):
                    next_stage = STAGES[next_stage_idx]
                    if st.button(f"✅ Advance to {next_stage}", type="primary", use_container_width=True):
                        advance_candidate(candidate_id, next_stage)
                        trigger_stage_change_email(candidate_id, candidate.get('job_id'), current_stage, next_stage)
                        st.success(f"Advanced to {next_stage}")
                        st.rerun()

        with action_cols[1]:
            # Reject candidate
            if current_stage != 'Rejected':
                if st.button("❌ Reject", use_container_width=True):
                    reject_candidate(candidate_id)
                    trigger_stage_change_email(candidate_id, candidate.get('job_id'), current_stage, 'Rejected')
                    st.warning("Candidate rejected")
                    st.rerun()

        with action_cols[2]:
            # Schedule interview
            if current_stage not in ['Hired', 'Rejected']:
                if st.button("📅 Schedule Interview", use_container_width=True):
                    st.session_state[f'show_schedule_{candidate_id}'] = True
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Schedule interview form
        if st.session_state.get(f'show_schedule_{candidate_id}', False):
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            with st.form(f"schedule_form_{candidate_id}"):
                st.markdown("<div style='color: white; font-size: 18px; font-weight: 600; margin-bottom: 16px;'>Schedule Interview</div>", unsafe_allow_html=True)

                interview_date = st.date_input("Date")
                interview_time = st.time_input("Time")
                interviewer_name = st.text_input("Interviewer Name")
                interviewer_email = st.text_input("Interviewer Email")
                location = st.text_input("Location (optional)")
                meeting_link = st.text_input("Meeting Link (optional)")

                schedule_submitted = st.form_submit_button("Schedule", type="primary")

                if schedule_submitted:
                    scheduled_time = datetime.combine(interview_date, interview_time).isoformat()
                    interview_id = schedule_interview(
                        candidate_id,
                        current_stage,
                        scheduled_time,
                        interviewer_email,
                        interviewer_name,
                        location,
                        meeting_link
                    )
                    st.success("Interview scheduled!")
                    st.session_state[f'show_schedule_{candidate_id}'] = False
                    st.rerun()

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

        # Stage history
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Stage History</div>", unsafe_allow_html=True)
        notes = get_stage_notes(candidate_id)

        if notes:
            for note in notes:
                note_stage = note.get('stage', 'Unknown')
                note_date = note.get('created_at', '')
                note_text = note.get('notes', '')
                interviewer = note.get('interviewer', 'Unknown')

                with st.expander(f"📝 {safe(note_stage)} - {note_date}", expanded=False):
                    st.markdown(f"**Interviewer:** {interviewer}", unsafe_allow_html=True)
                    st.markdown(note_text, unsafe_allow_html=True)

                    if note.get('ai_summary'):
                        st.markdown(_clean_html(f"""
                        <div style='background: rgba(48,76,178,0.1); border-left: 3px solid #304CB2; padding: 12px; border-radius: 6px; margin-top: 12px;'>
                            <div style='color: #304CB2; font-weight: 600; font-size: 13px; margin-bottom: 6px;'>AI SUMMARY</div>
                            <div style='color: rgba(255,255,255,0.8); font-size: 14px;'>{safe(note.get('ai_summary'))}</div>
                        </div>
                        """), unsafe_allow_html=True)
        else:
            st.markdown(empty_state("No stage history recorded", "Interview notes will appear here", icon='&#128221;'), unsafe_allow_html=True)

    # ============ TAB 3: INTERVIEW NOTES ============
    with tabs[2]:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Interview Notes</div>", unsafe_allow_html=True)

        # Add new note
        with st.expander("➕ Add Interview Note", expanded=False):
            with st.form(f"add_note_{candidate_id}"):
                note_stage = st.selectbox("Stage", STAGES, key=f"note_stage_{candidate_id}")
                note_interviewer = st.text_input("Your Name", value=get_current_user()['name'])
                note_date = st.date_input("Interview Date")
                note_text = st.text_area("Notes", height=200)

                note_submitted = st.form_submit_button("Save Note", type="primary")

                if note_submitted:
                    if note_text:
                        add_stage_notes(
                            candidate_id,
                            note_stage,
                            note_text,
                            note_interviewer,
                            note_date.isoformat()
                        )
                        st.success("Note saved!")
                        st.rerun()
                    else:
                        st.error("Note text is required")

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # Display existing notes
        notes = get_stage_notes(candidate_id)

        if notes:
            for note in notes:
                note_stage = note.get('stage', 'Unknown')
                note_date = note.get('interview_date', note.get('created_at', ''))
                note_text = note.get('notes', '')
                interviewer = note.get('interviewer', 'Unknown')
                note_id = note.get('id')

                # Note card
                st.markdown(_clean_html(f"""
                <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; padding: 20px; margin-bottom: 16px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                        <div>
                            {stage_badge(note_stage)}
                        </div>
                        <div style='color: rgba(255,255,255,0.5); font-size: 13px;'>{safe(note_date)}</div>
                    </div>
                    <div style='color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 12px;'>
                        <span style='opacity: 0.6;'>Interviewer:</span> {safe(interviewer)}
                    </div>
                    <div style='color: rgba(255,255,255,0.9); font-size: 14px; line-height: 1.6; white-space: pre-wrap;'>{safe(note_text)}</div>
                </div>
                """), unsafe_allow_html=True)

                # AI Summary
                if note.get('ai_summary'):
                    st.markdown(_clean_html(f"""
                    <div style='background: rgba(48,76,178,0.1); border-left: 3px solid #304CB2; padding: 16px; border-radius: 8px; margin-bottom: 16px;'>
                        <div style='color: #304CB2; font-weight: 600; font-size: 13px; margin-bottom: 8px;'>&#129302; AI SUMMARY</div>
                        <div style='color: rgba(255,255,255,0.9); font-size: 14px; line-height: 1.6;'>{safe(note.get('ai_summary'))}</div>
                    </div>
                    """), unsafe_allow_html=True)
                else:
                    if st.button("Generate AI Summary", key=f"ai_summary_{note_id}", type="secondary"):
                        with st.spinner("Generating summary..."):
                            summary = smart_summarize_notes(note_text, note_stage, candidate_name)
                            update_note_ai_summary(note_id, summary)
                            st.success("Summary generated!")
                            st.rerun()
        else:
            st.markdown(empty_state("No interview notes recorded", "Add notes after interviews", icon='&#128221;'), unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

        # Interview prep AI
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>AI Interview Preparation</div>", unsafe_allow_html=True)
        if candidate.get('job_id'):
            if st.button("🤖 Generate Interview Prep", type="primary", use_container_width=True):
                with st.spinner("Generating interview preparation..."):
                    job = get_job(candidate['job_id'])
                    candidate_data = {
                        'name': candidate.get('name'),
                        'job_title': job.get('title'),
                        'ai_resume_analysis': candidate.get('ai_resume_analysis'),
                        'previous_notes': '\n'.join(
                            n.get('notes', '') for n in get_stage_notes(candidate_id) if n.get('notes')
                        ),
                    }
                    prep = smart_generate_interview_prep(
                        candidate_data,
                        candidate.get('current_stage', 'Resume Screen')
                    )
                    update_candidate(candidate_id, ai_interview_prep=prep)
                    candidate['ai_interview_prep'] = prep

            # Display prep from database
            if candidate.get('ai_interview_prep'):
                with st.container(border=True):
                    st.markdown(candidate['ai_interview_prep'])
        else:
            st.info("Assign a job to enable AI interview prep generation")

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

        # ============ AI INTERVIEW QUESTION GENERATION ============
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>AI Interview Questions</div>", unsafe_allow_html=True)
        if candidate.get('job_id') and candidate.get('resume_text'):
            q_col1, q_col2 = st.columns([2, 1])
            with q_col1:
                question_stage = st.selectbox(
                    "Interview Stage",
                    ["Phone Screen", "Technical Interview", "Behavioral Interview"],
                    key="ai_question_stage"
                )
            with q_col2:
                num_questions = st.selectbox(
                    "Number of Questions",
                    [5, 8, 10, 12],
                    index=1,
                    key="ai_num_questions"
                )

            if st.button("🤖 Generate Interview Questions", type="primary", use_container_width=True, key="gen_questions_btn"):
                with st.spinner("Generating tailored questions..."):
                    job = get_job(candidate['job_id'])
                    previous_notes_text = '\n'.join(
                        n.get('notes', '') for n in get_stage_notes(candidate_id) if n.get('notes')
                    )
                    result = smart_generate_interview_questions(
                        job_description=job.get('description', ''),
                        job_requirements=job.get('requirements', ''),
                        resume_text=candidate.get('resume_text', ''),
                        stage=question_stage,
                        previous_feedback=previous_notes_text or None,
                        num_questions=num_questions
                    )
                    # Save to database with stage info
                    result['_stage'] = question_stage
                    update_candidate(candidate_id, ai_interview_questions=json.dumps(result))
                    candidate['ai_interview_questions'] = json.dumps(result)

            # Load questions from database
            stored_questions_raw = candidate.get('ai_interview_questions')
            if stored_questions_raw:
                try:
                    gen_result = json.loads(stored_questions_raw) if isinstance(stored_questions_raw, str) else stored_questions_raw
                except (json.JSONDecodeError, TypeError):
                    gen_result = None
            else:
                gen_result = None

            if gen_result:
                gen_stage = gen_result.get('_stage', 'Technical Interview')
                questions = gen_result.get('questions', [])
                areas = gen_result.get('areas_to_probe', [])
                concerns = gen_result.get('resume_concerns', [])

                category_colors = {
                    'technical': '#304CB2',
                    'behavioral': '#2EA043',
                    'situational': '#F9B612',
                    'experience': '#7C3AED',
                    'culture_fit': '#0891B2',
                }

                if questions:
                    st.markdown(f"<div style='color: rgba(255,255,255,0.6); font-size: 13px; margin-bottom: 16px;'>{len(questions)} questions generated for {safe(gen_stage)}</div>", unsafe_allow_html=True)

                    for idx, q in enumerate(questions):
                        q_text = q.get('question', '')
                        q_category = q.get('category', 'technical')
                        q_probe = q.get('probing_area', '')
                        cat_color = category_colors.get(q_category, '#304CB2')
                        cat_label = q_category.replace('_', ' ').title()

                        st.markdown(_clean_html(f"""
                        <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                        border-radius: 12px; padding: 20px; margin-bottom: 12px;'>
                            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;'>
                                <div style='color: rgba(255,255,255,0.4); font-size: 12px; font-weight: 600;'>Q{idx + 1}</div>
                                <div style='background: {cat_color}22; color: {cat_color}; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; border: 1px solid {cat_color}44;'>{safe(cat_label)}</div>
                            </div>
                            <div style='color: rgba(255,255,255,0.95); font-size: 14px; line-height: 1.6; margin-bottom: 10px;'>{safe(q_text)}</div>
                            <div style='color: rgba(255,255,255,0.45); font-size: 12px;'>Probing: {safe(q_probe)}</div>
                        </div>
                        """), unsafe_allow_html=True)

                        if st.button("Save to Question Bank", key=f"save_q_{idx}", type="secondary"):
                            save_interview_question(
                                job_id=candidate['job_id'],
                                stage=gen_stage,
                                question=q_text,
                                category=q_category,
                                probing_area=q_probe
                            )
                            st.success(f"Question {idx + 1} saved!")

                # Areas to Probe
                if areas:
                    st.markdown(_clean_html(f"""
                    <div style='background: rgba(48,76,178,0.1); border-left: 3px solid #304CB2; padding: 16px; border-radius: 8px; margin-top: 16px; margin-bottom: 12px;'>
                        <div style='color: #304CB2; font-weight: 600; font-size: 13px; margin-bottom: 10px;'>&#127919; Areas to Probe</div>
                        {''.join(f"<div style='color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.8; padding-left: 8px;'>&bull; {safe(a)}</div>" for a in areas)}
                    </div>
                    """), unsafe_allow_html=True)

                # Resume Concerns
                if concerns:
                    st.markdown(_clean_html(f"""
                    <div style='background: rgba(200,16,46,0.08); border-left: 3px solid #C8102E; padding: 16px; border-radius: 8px; margin-bottom: 12px;'>
                        <div style='color: #C8102E; font-weight: 600; font-size: 13px; margin-bottom: 10px;'>&#9888;&#65039; Resume Concerns</div>
                        {''.join(f"<div style='color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.8; padding-left: 8px;'>&bull; {safe(c)}</div>" for c in concerns)}
                    </div>
                    """), unsafe_allow_html=True)
        elif not candidate.get('job_id'):
            st.info("Assign a job to enable AI question generation")
        elif not candidate.get('resume_text'):
            st.info("Upload a resume to enable AI question generation")

    # ============ TAB 4: MULTI-ROLE MATCHING ============
    with tabs[3]:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Multi-Role Job Matching</div>", unsafe_allow_html=True)

        # Current roles
        candidate_jobs = get_candidate_jobs(candidate_id)

        if candidate_jobs:
            for cj in candidate_jobs:
                job_title = cj.get('job_title', 'Unknown')
                role_stage = cj.get('current_stage', 'Unknown')
                role_status = cj.get('status', 'Unknown')
                is_primary = cj.get('is_primary', 0)
                job_id = cj.get('job_id')

                primary_badge_html = "<span style='background: linear-gradient(135deg, #F9B612, #F9A825); color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-left: 8px;'>⭐ PRIMARY</span>" if is_primary else ""

                status_color = '#2EA043' if role_status == 'Active' else '#C8102E'

                st.markdown(_clean_html(f"""
                <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; padding: 20px; margin-bottom: 16px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                        <div style='color: white; font-size: 16px; font-weight: 600;'>
                            &#128188; {safe(job_title)}
                            {primary_badge_html}
                        </div>
                        <div>{stage_badge(role_stage)}</div>
                    </div>
                    <div style='color: rgba(255,255,255,0.7); font-size: 13px;'>
                        Status: {status_badge(role_status, status_color, 'outlined')}
                    </div>
                </div>
                """), unsafe_allow_html=True)

                job_cols = st.columns([3, 1, 1])
                with job_cols[1]:
                    if not is_primary and st.button("Set Primary", key=f"primary_{job_id}", use_container_width=True):
                        set_primary_job(candidate_id, job_id)
                        st.success("Primary job updated!")
                        st.rerun()
                with job_cols[2]:
                    if st.button("Remove", key=f"remove_{job_id}", use_container_width=True):
                        remove_candidate_from_job(candidate_id, job_id)
                        st.warning("Job association removed")
                        st.rerun()
        else:
            st.markdown(empty_state("No job associations", "Add this candidate to jobs", icon='&#128188;'), unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # Add to new job
        with st.expander("➕ Add to Another Job", expanded=False):
            all_jobs = get_jobs(status='Open')

            if all_jobs:
                job_options = [f"{j['title']} (ID: {j['id']})" for j in all_jobs]
                selected_new_job = st.selectbox("Select Job", job_options, key=f"add_job_{candidate_id}")

                if st.button("Add to Job", type="primary"):
                    try:
                        new_job_id = int(selected_new_job.split('ID: ')[1].rstrip(')'))
                        add_candidate_to_job(candidate_id, new_job_id)
                        st.success("Added to job!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding to job: {e}")
            else:
                st.info("No open jobs available")

    # ============ TAB 5: CONTRACT & COMPLIANCE ============
    with tabs[4]:
        st.markdown("<div style='color: white; font-size: 20px; font-weight: 600; margin-bottom: 20px;'>Contract & Compliance</div>", unsafe_allow_html=True)

        # Contracts
        contracts = get_contracts(candidate_id=candidate_id)

        if contracts:
            st.markdown("<div style='color: rgba(255,255,255,0.8); font-size: 16px; font-weight: 600; margin-bottom: 16px;'>Contracts</div>", unsafe_allow_html=True)
            for contract in contracts:
                start_date = contract.get('start_date', 'N/A')
                end_date = contract.get('end_date', 'N/A')
                rate = contract.get('hourly_rate', 0)
                status = contract.get('status', 'Unknown')

                status_color_map = {
                    'active': '#2EA043',
                    'pending': '#F9B612',
                    'expired': '#C8102E',
                    'completed': '#304CB2'
                }
                status_color = status_color_map.get(status.lower(), '#304CB2')

                contract_notes_html = f"<div style='color: rgba(255,255,255,0.7); font-size: 13px; margin-top: 8px;'>{safe(contract.get('notes'))}</div>" if contract.get('notes') else ''

                st.markdown(_clean_html(f"""
                <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; padding: 20px; margin-bottom: 16px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                        <div style='color: white; font-size: 15px; font-weight: 600;'>
                            &#128203; {safe(start_date)} to {safe(end_date)}
                        </div>
                        <div>{status_badge(status, status_color)}</div>
                    </div>
                    <div style='display: flex; gap: 24px; margin-top: 12px;'>
                        <div>
                            <div style='color: rgba(255,255,255,0.5); font-size: 12px;'>Hourly Rate</div>
                            <div style='color: white; font-size: 18px; font-weight: 600;'>${rate:.2f}/hr</div>
                        </div>
                    </div>
                    {contract_notes_html}
                </div>
                """), unsafe_allow_html=True)
        else:
            st.markdown(empty_state("No contracts recorded", "Contract information will appear here", icon='&#128203;'), unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

        # Compliance documents
        compliance_docs = get_compliance_docs(candidate_id)

        if compliance_docs:
            st.markdown("<div style='color: rgba(255,255,255,0.8); font-size: 16px; font-weight: 600; margin-bottom: 16px;'>Compliance Documents</div>", unsafe_allow_html=True)
            for doc in compliance_docs:
                doc_type = doc.get('doc_type', 'Unknown')
                doc_status = doc.get('status', 'Unknown')
                expiry_date = doc.get('expiry_date', 'N/A')
                received_date = doc.get('received_date', 'N/A')

                doc_status_color_map = {
                    'verified': '#2EA043',
                    'received': '#304CB2',
                    'pending': '#F9B612',
                    'expired': '#C8102E'
                }
                doc_status_color = doc_status_color_map.get(doc_status.lower(), '#304CB2')

                expiry_html = f"<div style='color: rgba(255,255,255,0.7); font-size: 13px;'><span style='opacity: 0.6;'>Expires:</span> {safe(expiry_date)}</div>" if expiry_date != 'N/A' else ''
                received_html = f"<div style='color: rgba(255,255,255,0.7); font-size: 13px;'><span style='opacity: 0.6;'>Received:</span> {safe(received_date)}</div>" if received_date != 'N/A' else ''

                st.markdown(_clean_html(f"""
                <div style='background: rgba(26,35,50,0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; padding: 20px; margin-bottom: 16px;'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                        <div style='color: white; font-size: 15px; font-weight: 600;'>
                            &#128196; {safe(doc_type)}
                        </div>
                        <div>{status_badge(doc_status, doc_status_color)}</div>
                    </div>
                    <div style='display: flex; gap: 24px; margin-top: 12px;'>
                        <div>{received_html}</div>
                        <div>{expiry_html}</div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
        else:
            st.markdown(empty_state("No compliance documents", "Add compliance documentation", icon='&#128196;'), unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        # Add compliance document
        with st.expander("➕ Add Compliance Document", expanded=False):
            with st.form(f"add_compliance_{candidate_id}"):
                doc_type = st.selectbox("Document Type", COMPLIANCE_DOC_TYPES)
                doc_status = st.selectbox("Status", ['pending', 'received', 'verified', 'expired'])
                received_date = st.date_input("Received Date")
                expiry_date = st.date_input("Expiry Date (if applicable)")
                doc_notes = st.text_area("Notes")

                doc_submitted = st.form_submit_button("Add Document", type="primary")

                if doc_submitted:
                    add_compliance_doc(
                        candidate_id,
                        doc_type,
                        doc_status,
                        received_date.isoformat(),
                        expiry_date.isoformat(),
                        notes=doc_notes
                    )
                    st.success("Document added!")
                    st.rerun()
