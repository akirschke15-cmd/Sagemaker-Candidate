"""
Scheduling view - Interview scheduling, calendar integration, and scorecard management
"""
import streamlit as st
from datetime import datetime, timedelta
import io
from database import (
    get_interviews, schedule_interview_for_role, get_candidates, get_jobs,
    get_candidate, get_job, get_candidate_jobs
)
from calendar_integration import (
    generate_ics_event, generate_ics_filename
)
from mobile_scorecard import (
    generate_scorecard_token, get_scorecard_tokens_for_interview
)
from genai import generate_interview_prep
from auth import get_current_user, has_permission
from views.utils import safe, section_header, avatar_badge, stage_badge, empty_state, _clean_html


def render_scheduling():
    """
    Render the scheduling view showing:
    - Upcoming interviews list
    - Schedule new interview form
    - Calendar download (ICS)
    - Mobile scorecard links
    - Interview prep generation
    """
    st.markdown(section_header("Scheduling", "Interview calendar and management"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to access scheduling")
        return

    # Check permissions
    if not has_permission('scheduling', 'view'):
        st.error("You don't have permission to access scheduling")
        return

    # ============ TABS ============
    tab1, tab2 = st.tabs(["📋 Upcoming Interviews", "➕ Schedule Interview"])

    with tab1:
        render_upcoming_interviews()

    with tab2:
        if has_permission('scheduling', 'create'):
            render_schedule_interview_form()
        else:
            st.info("You don't have permission to schedule interviews")


def render_upcoming_interviews():
    """Display list of upcoming interviews with actions"""
    st.subheader("Upcoming Interviews")

    # Get upcoming interviews
    interviews = get_interviews(upcoming_only=True)

    if not interviews:
        st.markdown(empty_state("No upcoming interviews scheduled", "Schedule your first interview below", "&#128197;"), unsafe_allow_html=True)
        return

    # Display interviews
    for interview in interviews:
        candidate_id = interview.get('candidate_id')
        job_id = interview.get('job_id')
        interview_id = interview.get('id')

        # Get candidate and job details
        candidate = get_candidate(candidate_id) if candidate_id else None
        job = get_job(job_id) if job_id else None

        if not candidate:
            continue

        # Parse scheduled time
        scheduled_time_str = interview.get('scheduled_time', '')
        try:
            if isinstance(scheduled_time_str, str):
                if 'T' in scheduled_time_str:
                    dt = datetime.fromisoformat(scheduled_time_str.replace('Z', ''))
                else:
                    dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
            else:
                dt = scheduled_time_str
            time_str = dt.strftime("%b %d, %Y at %I:%M %p")
            is_past = dt < datetime.now()
        except (ValueError, TypeError):
            time_str = scheduled_time_str
            is_past = False

        # Create premium card for each interview
        card_color = "#1A2332" if not is_past else "rgba(26, 35, 50, 0.5)"
        border_color = "rgba(48, 76, 178, 0.3)" if not is_past else "rgba(110, 118, 129, 0.2)"

        card_html = f"""
        <div style="background: {card_color};
                    border: 1px solid {border_color};
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 16px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                <div>
                    {avatar_badge(candidate.get('name', 'Unknown'), f"{time_str}")}
                </div>
                <div>
                    {stage_badge(interview.get('stage', 'Unknown'))}
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 14px;">
                <div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Email</div>
                    <div style="color: #FFFFFF;">{safe(candidate.get('email', 'N/A'))}</div>
                </div>
                <div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Phone</div>
                    <div style="color: #FFFFFF;">{safe(candidate.get('phone', 'N/A'))}</div>
                </div>
                {f'''<div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Job</div>
                    <div style="color: #FFFFFF;">{safe(job.get('title', 'N/A'))}</div>
                </div>''' if job else ''}
                <div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Interviewer</div>
                    <div style="color: #FFFFFF;">{safe(interview.get('interviewer_name', 'N/A'))}</div>
                </div>
                {f'''<div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Location</div>
                    <div style="color: #FFFFFF;">{safe(interview.get('location', ''))}</div>
                </div>''' if interview.get('location') else ''}
                {f'''<div>
                    <div style="color: #8B949E; margin-bottom: 4px;">Meeting Link</div>
                    <div style="color: #304CB2;"><a href="{safe(interview.get('meeting_link', ''))}" target="_blank" rel="noopener noreferrer" style="color: #304CB2; text-decoration: none;">Join Meeting &#8599;</a></div>
                </div>''' if interview.get('meeting_link') else ''}
            </div>
        </div>
        """

        st.markdown(_clean_html(card_html), unsafe_allow_html=True)

        with st.expander(f"Actions for {candidate.get('name', 'Unknown')}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col2:
                st.markdown("**Actions**", unsafe_allow_html=True)

                # ============ DOWNLOAD CALENDAR (ICS) ============
                if st.button("📥 Download .ics", key=f"ics_{interview_id}", use_container_width=True):
                    try:
                        # Generate interview prep notes
                        prep_notes = None
                        if job and candidate.get('resume_text'):
                            prep_result = generate_interview_prep(
                                candidate_id=candidate_id,
                                job_id=job_id,
                                stage=interview.get('stage')
                            )
                            if prep_result.get('success'):
                                prep_notes = prep_result.get('prep_notes')

                        # Generate ICS content
                        ics_content, uid = generate_ics_event(
                            interview=interview,
                            candidate=candidate,
                            job=job or {},
                            duration_minutes=60,
                            prep_notes=prep_notes,
                            previous_notes=None
                        )

                        # Generate filename
                        filename = generate_ics_filename(
                            candidate.get('name', 'candidate'),
                            interview.get('stage', 'interview'),
                            scheduled_time_str
                        )

                        # Create download button
                        st.download_button(
                            label="⬇️ Save Calendar Event",
                            data=ics_content.encode('utf-8'),
                            file_name=filename,
                            mime="text/calendar",
                            key=f"download_ics_{interview_id}"
                        )
                        st.success("Calendar event ready for download!")

                    except Exception as e:
                        st.error(f"Failed to generate calendar event: {str(e)}")

                # ============ MOBILE SCORECARD LINK ============
                if st.button("📱 Scorecard Link", key=f"scorecard_{interview_id}", use_container_width=True):
                    try:
                        # Check if token already exists
                        existing_tokens = get_scorecard_tokens_for_interview(interview_id)
                        active_tokens = [t for t in existing_tokens if t.get('is_active')]

                        if active_tokens:
                            token = active_tokens[0]['token']
                            st.info("Using existing active token")
                        else:
                            # Generate new token
                            token = generate_scorecard_token(
                                interview_id=interview_id,
                                interviewer_email=interview.get('interviewer_email'),
                                expires_hours=72
                            )
                            st.success("Generated new scorecard token!")

                        # Build URL (use current domain)
                        scorecard_url = f"?token={token}"

                        st.code(scorecard_url, language=None)
                        st.caption("Copy this URL and send it to the interviewer. The link expires in 72 hours.")

                    except Exception as e:
                        st.error(f"Failed to generate scorecard link: {str(e)}")

                # ============ INTERVIEW PREP ============
                if st.button("🤖 Generate Prep", key=f"prep_{interview_id}", use_container_width=True):
                    if not job:
                        st.warning("Job information required for interview prep")
                    elif not candidate.get('resume_text'):
                        st.warning("Resume text required for interview prep")
                    else:
                        with st.spinner("Generating interview prep notes..."):
                            try:
                                prep_result = generate_interview_prep(
                                    candidate_id=candidate_id,
                                    job_id=job_id,
                                    stage=interview.get('stage')
                                )

                                if prep_result.get('success'):
                                    st.success("Interview prep generated!")
                                    st.markdown("**Interview Prep Notes:**", unsafe_allow_html=True)
                                    st.markdown(prep_result.get('prep_notes', ''))
                                else:
                                    st.error(prep_result.get('message', 'Failed to generate prep notes'))

                            except Exception as e:
                                st.error(f"Error generating prep notes: {str(e)}")


def render_schedule_interview_form():
    """Form to schedule a new interview"""
    st.subheader("Schedule New Interview")

    # Get candidates and jobs
    candidates = get_candidates(status='Active')
    jobs = get_jobs(status='Open')

    if not candidates:
        st.warning("No active candidates available")
        return

    if not jobs:
        st.warning("No open jobs available")
        return

    with st.form("schedule_interview_form"):
        # Candidate selection
        candidate_options = {f"{c['name']} ({c.get('email', 'No email')})": c['id'] for c in candidates}
        selected_candidate_label = st.selectbox("Candidate", list(candidate_options.keys()))
        selected_candidate_id = candidate_options[selected_candidate_label]

        # Job selection
        job_options = {f"{j['title']} ({j.get('department', 'No dept')})": j['id'] for j in jobs}
        selected_job_label = st.selectbox("Job", list(job_options.keys()))
        selected_job_id = job_options[selected_job_label]

        # Stage selection
        from database import STAGES
        interview_stages = [s for s in STAGES if s not in ['Resume Screen', 'Hired', 'Rejected']]
        selected_stage = st.selectbox("Interview Stage", interview_stages)

        # Interviewer details
        col1, col2 = st.columns(2)
        with col1:
            interviewer_name = st.text_input("Interviewer Name", key="interviewer_name")
        with col2:
            interviewer_email = st.text_input("Interviewer Email", key="interviewer_email")

        # Date and time
        col3, col4 = st.columns(2)
        with col3:
            interview_date = st.date_input("Interview Date", min_value=datetime.now().date())
        with col4:
            interview_time = st.time_input("Interview Time")

        # Combine date and time
        scheduled_datetime = datetime.combine(interview_date, interview_time)

        # Location and meeting link
        col5, col6 = st.columns(2)
        with col5:
            location = st.text_input("Location (optional)", placeholder="Building A, Room 101")
        with col6:
            meeting_link = st.text_input("Meeting Link (optional)", placeholder="https://zoom.us/...")

        submitted = st.form_submit_button("📅 Schedule Interview", type="primary", use_container_width=True)

        if submitted:
            # Validate inputs
            if not interviewer_name or not interviewer_email:
                st.error("Interviewer name and email are required")
            elif '@' not in interviewer_email:
                st.error("Invalid interviewer email format")
            elif scheduled_datetime < datetime.now():
                st.error("Interview time must be in the future")
            else:
                try:
                    # Schedule the interview
                    interview_id = schedule_interview_for_role(
                        candidate_id=selected_candidate_id,
                        job_id=selected_job_id,
                        stage=selected_stage,
                        scheduled_time=scheduled_datetime.isoformat(),
                        interviewer_email=interviewer_email,
                        interviewer_name=interviewer_name,
                        location=location if location else None,
                        meeting_link=meeting_link if meeting_link else None
                    )

                    st.success(f"✅ Interview scheduled successfully! (ID: {interview_id})")
                    st.balloons()

                    # Show next steps
                    st.info("**Next Steps:**\n"
                           "1. Download the .ics file from 'Upcoming Interviews'\n"
                           "2. Generate a mobile scorecard link for the interviewer\n"
                           "3. Generate interview prep notes")

                    # Rerun to refresh the list
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to schedule interview: {str(e)}")
