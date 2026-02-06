"""
Candidates view - List and detail views for candidate management
"""
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
    smart_score_resume, smart_summarize_notes, generate_interview_prep,
    smart_generate_interview_questions
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
from views.utils import get_stage_color, safe


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
    st.title("👥 Candidates")

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view candidates")
        return

    # ============ FILTERS ============
    st.subheader("Filters")

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

    st.divider()

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

    st.divider()

    # ============ CANDIDATE LIST ============
    st.subheader("Candidate List")

    # Fetch candidates
    candidates = get_candidates(
        job_id=filter_job_id,
        vendor_id=filter_vendor_id,
        stage=filter_stage,
        status=filter_status
    )

    if not candidates:
        st.info("No candidates found matching the filters")
    else:
        # Table headers
        header_cols = st.columns([0.5, 2, 2, 1.5, 1.5, 1])
        with header_cols[0]:
            st.markdown("**Select**")
        with header_cols[1]:
            st.markdown("**Name**")
        with header_cols[2]:
            st.markdown("**Job**")
        with header_cols[3]:
            st.markdown("**Stage**")
        with header_cols[4]:
            st.markdown("**AI Score**")
        with header_cols[5]:
            st.markdown("**Rate Status**")

        st.divider()

        # Candidate rows
        for candidate in candidates:
            row_cols = st.columns([0.5, 2, 2, 1.5, 1.5, 1])

            candidate_id = candidate['id']
            candidate_name = candidate.get('name', 'Unknown')
            job_title = candidate.get('job_title', 'No job assigned')
            stage = candidate.get('current_stage', 'Unknown')
            ai_score = candidate.get('ai_resume_score', 0) or 0
            expected_rate = candidate.get('expected_hourly_rate')

            # Checkbox for comparison
            with row_cols[0]:
                is_selected = candidate_id in st.session_state.get('comparison_candidates', [])
                if st.checkbox("", value=is_selected, key=f"select_{candidate_id}"):
                    if candidate_id not in st.session_state.comparison_candidates:
                        if len(st.session_state.comparison_candidates) < 3:
                            st.session_state.comparison_candidates.append(candidate_id)
                        else:
                            st.warning("Maximum 3 candidates can be compared")
                            st.rerun()
                else:
                    if candidate_id in st.session_state.comparison_candidates:
                        st.session_state.comparison_candidates.remove(candidate_id)

            # Clickable name
            with row_cols[1]:
                if st.button(candidate_name, key=f"view_{candidate_id}"):
                    st.session_state.selected_candidate = candidate_id
                    st.rerun()

            # Job title
            with row_cols[2]:
                st.markdown(job_title)

            # Stage with color
            with row_cols[3]:
                color = get_stage_color(stage)
                st.markdown(
                    f"<span style='background-color:{color}; color:white; padding:4px 12px; "
                    f"border-radius:16px; font-size:12px; font-weight:600;'>{safe(stage)}</span>",
                    unsafe_allow_html=True
                )

            # AI Score progress bar
            with row_cols[4]:
                if ai_score > 0:
                    st.progress(ai_score / 100)
                    st.caption(f"{ai_score:.0f}%")
                else:
                    st.caption("Not scored")

            # Rate status
            with row_cols[5]:
                if expected_rate and candidate.get('job_id'):
                    job = jobs_dict.get(candidate['job_id'])
                    if job and job.get('contractor_role_id'):
                        rate_status = get_rate_status(candidate['job_id'], expected_rate)
                        if rate_status == 'in_range':
                            st.success("✓")
                        elif rate_status == 'below_range':
                            st.info("↓")
                        elif rate_status == 'above_range':
                            st.warning("↑")
                        else:
                            st.caption("-")
                    else:
                        st.caption("-")
                else:
                    st.caption("-")

        st.caption(f"Total: {len(candidates)} candidates")

    st.divider()

    # ============ ADD CANDIDATE FORM ============
    with st.expander("➕ Add New Candidate"):
        st.subheader("Create Candidate")

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

                    # Create candidate
                    candidate_id = create_candidate(
                        name=new_name,
                        email=new_email if new_email else None,
                        phone=new_phone if new_phone else None,
                        vendor_id=vendor_id,
                        job_id=job_id
                    )

                    # Update rate if provided
                    if new_rate > 0:
                        update_candidate(candidate_id, expected_hourly_rate=new_rate)

                    # Add to candidate_jobs if job assigned
                    if job_id:
                        add_candidate_to_job(candidate_id, job_id, is_primary=1)

                    st.success(f"Candidate '{new_name}' created successfully!")
                    st.session_state.selected_candidate = candidate_id
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
            st.rerun()
        return

    # ============ HEADER WITH BACK BUTTON ============
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to List"):
            st.session_state.selected_candidate = None
            st.rerun()
    with col2:
        st.title(f"👤 {candidate.get('name', 'Unknown')}")

    st.divider()

    # ============ CANDIDATE INFO SECTION ============
    info_cols = st.columns(3)

    with info_cols[0]:
        st.markdown("**Contact Information**")
        st.markdown(f"📧 {candidate.get('email', 'N/A')}")
        st.markdown(f"📱 {candidate.get('phone', 'N/A')}")
        vendor_name = candidate.get('vendor_name', 'Direct')
        st.markdown(f"🏢 Vendor: {vendor_name}")

    with info_cols[1]:
        st.markdown("**Current Status**")
        stage = candidate.get('current_stage', 'Unknown')
        color = get_stage_color(stage)
        st.markdown(
            f"<div style='background-color:{color}; color:white; padding:8px 16px; "
            f"border-radius:8px; text-align:center; font-weight:600;'>{safe(stage)}</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**Status:** {candidate.get('status', 'Unknown')}")

    with info_cols[2]:
        st.markdown("**Job Assignment**")
        job_title = candidate.get('job_title', 'No job assigned')
        st.markdown(f"💼 {job_title}")
        expected_rate = candidate.get('expected_hourly_rate')
        if expected_rate:
            st.markdown(f"💰 Expected Rate: ${expected_rate:.2f}/hr")

    st.divider()

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
        st.subheader("Resume Upload & AI Analysis")

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
            if candidate.get('resume_original_filename'):
                st.markdown(f"**Current Resume:** {candidate.get('resume_original_filename')}")

                # AI Scoring
                ai_score = candidate.get('ai_resume_score', 0) or 0
                if ai_score > 0:
                    st.metric("AI Resume Score", f"{ai_score:.0f}%")
                    if candidate.get('ai_resume_analysis'):
                        with st.expander("View Analysis"):
                            st.markdown(candidate.get('ai_resume_analysis'))

                # Re-score button
                if candidate.get('job_id') and candidate.get('resume_text'):
                    if st.button("🤖 AI Score Resume", key="ai_score_btn"):
                        with st.spinner("Analyzing resume..."):
                            job = get_job(candidate['job_id'])
                            if job:
                                result = smart_score_resume(
                                    candidate.get('resume_text', ''),
                                    job.get('description', ''),
                                    job.get('requirements', '')
                                )

                                score = result.get('score', 0)
                                analysis = result.get('analysis', '')

                                update_candidate(
                                    candidate_id,
                                    ai_resume_score=score,
                                    ai_resume_analysis=analysis
                                )
                                st.success(f"AI Score: {score:.0f}%")
                                st.rerun()
            else:
                st.info("No resume uploaded yet")

        st.divider()

        # ============ SCORING CRITERIA ============
        if candidate.get('job_id'):
            st.subheader("Evaluation Scores")

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

                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{criterion_name}**")
                        if criterion.get('description'):
                            st.caption(criterion['description'])
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
                        if st.button("Save", key=f"save_score_{criterion_id}"):
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
                st.divider()
                st.metric(
                    "Total Score",
                    f"{total['total']:.1f} / {total['max_possible']:.1f} ({total['percentage']:.1f}%)"
                )
            else:
                st.info(f"No scoring criteria defined for {current_stage} stage")

    # ============ TAB 2: STAGE PROGRESSION ============
    with tabs[1]:
        st.subheader("Stage Progression")

        current_stage = candidate.get('current_stage', 'Resume Screen')
        current_stage_idx = STAGES.index(current_stage) if current_stage in STAGES else 0

        # Visual stage progression
        stage_cols = st.columns(len(STAGES))
        for i, stage in enumerate(STAGES):
            with stage_cols[i]:
                color = get_stage_color(stage)
                is_current = (i == current_stage_idx)
                is_past = (i < current_stage_idx)

                if is_current:
                    st.markdown(
                        f"<div style='background-color:{color}; color:white; padding:12px; "
                        f"border-radius:8px; text-align:center; font-weight:700; border:3px solid {color};'>"
                        f"{safe(stage)}</div>",
                        unsafe_allow_html=True
                    )
                elif is_past:
                    st.markdown(
                        f"<div style='background-color:{color}40; color:{color}; padding:12px; "
                        f"border-radius:8px; text-align:center; font-weight:600;'>{safe(stage)}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div style='background-color:#f0f0f0; color:#888; padding:12px; "
                        f"border-radius:8px; text-align:center;'>{safe(stage)}</div>",
                        unsafe_allow_html=True
                    )

        st.divider()

        # Action buttons
        action_cols = st.columns(3)

        with action_cols[0]:
            # Advance to next stage
            if current_stage != 'Hired' and current_stage != 'Rejected':
                next_stage_idx = current_stage_idx + 1
                if next_stage_idx < len(STAGES):
                    next_stage = STAGES[next_stage_idx]
                    if st.button(f"✅ Advance to {next_stage}", type="primary", use_container_width=True):
                        advance_candidate(candidate_id, next_stage)
                        trigger_stage_change_email(candidate_id, current_stage, next_stage)
                        st.success(f"Advanced to {next_stage}")
                        st.rerun()

        with action_cols[1]:
            # Reject candidate
            if current_stage != 'Rejected':
                if st.button("❌ Reject", use_container_width=True):
                    reject_candidate(candidate_id)
                    trigger_stage_change_email(candidate_id, current_stage, 'Rejected')
                    st.warning("Candidate rejected")
                    st.rerun()

        with action_cols[2]:
            # Schedule interview
            if current_stage not in ['Hired', 'Rejected']:
                if st.button("📅 Schedule Interview", use_container_width=True):
                    st.session_state[f'show_schedule_{candidate_id}'] = True
                    st.rerun()

        # Schedule interview form
        if st.session_state.get(f'show_schedule_{candidate_id}', False):
            with st.form(f"schedule_form_{candidate_id}"):
                st.subheader("Schedule Interview")

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

        st.divider()

        # Stage history
        st.subheader("Stage History")
        notes = get_stage_notes(candidate_id)

        if notes:
            for note in notes:
                note_stage = note.get('stage', 'Unknown')
                note_date = note.get('created_at', '')
                note_text = note.get('notes', '')
                interviewer = note.get('interviewer', 'Unknown')

                with st.expander(f"{safe(note_stage)} - {note_date}"):
                    st.markdown(f"**Interviewer:** {interviewer}")
                    st.markdown(note_text)

                    if note.get('ai_summary'):
                        st.info(f"**AI Summary:** {note.get('ai_summary')}")
        else:
            st.info("No stage history recorded")

    # ============ TAB 3: INTERVIEW NOTES ============
    with tabs[2]:
        st.subheader("Interview Notes")

        # Add new note
        with st.expander("➕ Add Interview Note"):
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

        st.divider()

        # Display existing notes
        notes = get_stage_notes(candidate_id)

        if notes:
            for note in notes:
                note_stage = note.get('stage', 'Unknown')
                note_date = note.get('interview_date', note.get('created_at', ''))
                note_text = note.get('notes', '')
                interviewer = note.get('interviewer', 'Unknown')
                note_id = note.get('id')

                with st.expander(f"📝 {safe(note_stage)} - {safe(interviewer)} - {note_date}"):
                    st.markdown(note_text)

                    # AI Summary
                    if note.get('ai_summary'):
                        st.info(f"**AI Summary:** {note.get('ai_summary')}")
                    else:
                        if st.button("Generate AI Summary", key=f"ai_summary_{note_id}"):
                            with st.spinner("Generating summary..."):
                                summary = smart_summarize_notes(note_text)
                                update_note_ai_summary(note_id, summary)
                                st.success("Summary generated!")
                                st.rerun()
        else:
            st.info("No interview notes recorded")

        st.divider()

        # Interview prep AI
        if candidate.get('job_id'):
            st.subheader("AI Interview Preparation")
            if st.button("🤖 Generate Interview Prep", type="primary"):
                with st.spinner("Generating interview preparation..."):
                    job = get_job(candidate['job_id'])
                    prep = generate_interview_prep(
                        candidate.get('resume_text', ''),
                        job.get('description', ''),
                        candidate.get('current_stage', 'Resume Screen')
                    )
                    st.markdown(prep)

    # ============ TAB 4: MULTI-ROLE MATCHING ============
    with tabs[3]:
        st.subheader("Multi-Role Job Matching")

        # Current roles
        candidate_jobs = get_candidate_jobs(candidate_id)

        if candidate_jobs:
            st.markdown("**Current Job Associations:**")

            for cj in candidate_jobs:
                job_title = cj.get('job_title', 'Unknown')
                role_stage = cj.get('current_stage', 'Unknown')
                role_status = cj.get('status', 'Unknown')
                is_primary = cj.get('is_primary', 0)
                job_id = cj.get('job_id')

                job_cols = st.columns([3, 2, 2, 1, 1])

                with job_cols[0]:
                    if is_primary:
                        st.markdown(f"**{job_title}** ⭐ Primary")
                    else:
                        st.markdown(f"**{job_title}**")

                with job_cols[1]:
                    color = get_stage_color(role_stage)
                    st.markdown(
                        f"<span style='background-color:{color}; color:white; padding:4px 12px; "
                        f"border-radius:12px; font-size:11px;'>{safe(role_stage)}</span>",
                        unsafe_allow_html=True
                    )

                with job_cols[2]:
                    st.markdown(f"Status: {role_status}")

                with job_cols[3]:
                    if not is_primary and st.button("Set Primary", key=f"primary_{job_id}"):
                        set_primary_job(candidate_id, job_id)
                        st.success("Primary job updated!")
                        st.rerun()

                with job_cols[4]:
                    if st.button("Remove", key=f"remove_{job_id}"):
                        remove_candidate_from_job(candidate_id, job_id)
                        st.warning("Job association removed")
                        st.rerun()
        else:
            st.info("No job associations")

        st.divider()

        # Add to new job
        with st.expander("➕ Add to Another Job"):
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
        st.subheader("Contract & Compliance")

        # Contracts
        contracts = get_contracts(candidate_id=candidate_id)

        if contracts:
            st.markdown("**Contracts:**")
            for contract in contracts:
                start_date = contract.get('start_date', 'N/A')
                end_date = contract.get('end_date', 'N/A')
                rate = contract.get('hourly_rate', 0)
                status = contract.get('status', 'Unknown')

                with st.expander(f"Contract: {start_date} to {end_date} - {status}"):
                    st.markdown(f"**Rate:** ${rate:.2f}/hr")
                    st.markdown(f"**Status:** {status}")
                    if contract.get('notes'):
                        st.markdown(f"**Notes:** {contract.get('notes')}")
        else:
            st.info("No contracts recorded")

        st.divider()

        # Compliance documents
        compliance_docs = get_compliance_docs(candidate_id)

        if compliance_docs:
            st.markdown("**Compliance Documents:**")
            for doc in compliance_docs:
                doc_type = doc.get('doc_type', 'Unknown')
                status = doc.get('status', 'Unknown')
                expiry_date = doc.get('expiry_date', 'N/A')

                with st.expander(f"{doc_type} - {status}"):
                    st.markdown(f"**Status:** {status}")
                    if expiry_date != 'N/A':
                        st.markdown(f"**Expires:** {expiry_date}")
                    if doc.get('received_date'):
                        st.markdown(f"**Received:** {doc.get('received_date')}")
        else:
            st.info("No compliance documents recorded")

        st.divider()

        # Add compliance document
        with st.expander("➕ Add Compliance Document"):
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
