"""
Mobile Scorecard UI Component - Feature 5
Renders the mobile-friendly scorecard interface for interviewers

This module provides the UI rendering functions that should be integrated into app.py.
"""
import streamlit as st
from mobile_scorecard import (
    validate_scorecard_token, submit_mobile_scorecard,
    get_recommendation_options
)
from views.utils import _clean_html


# JavaScript for auto-save and unsaved changes warning
AUTO_SAVE_JS = """
<script>
    // Auto-save draft to localStorage every 5 seconds
    const tokenKey = 'scorecard_draft_' + window.location.search;

    function getSelectedRecommendation() {
        const radios = document.querySelectorAll('input[type="radio"]');
        for (const radio of radios) {
            if (radio.checked) {
                // Get the label text for this radio
                const label = radio.closest('label') || radio.parentElement;
                if (label) {
                    return label.textContent.trim();
                }
            }
        }
        return null;
    }

    function saveDraft() {
        const draft = {
            notes: document.querySelector('textarea')?.value || '',
            recommendation: getSelectedRecommendation(),
            timestamp: new Date().toISOString()
        };
        localStorage.setItem(tokenKey, JSON.stringify(draft));
        console.log('Draft saved:', draft.timestamp, 'Rec:', draft.recommendation);
    }

    // Save draft periodically
    setInterval(saveDraft, 5000);

    // Save draft before page unload
    window.addEventListener('beforeunload', function(e) {
        saveDraft();
        // Check if there's unsaved content
        const notes = document.querySelector('textarea')?.value || '';
        const rec = getSelectedRecommendation();
        if (notes.trim().length > 0 || rec) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });

    // Restore draft on page load
    window.addEventListener('load', function() {
        const savedDraft = localStorage.getItem(tokenKey);
        if (savedDraft) {
            try {
                const draft = JSON.parse(savedDraft);

                // Restore notes
                const textarea = document.querySelector('textarea');
                if (textarea && draft.notes && !textarea.value) {
                    textarea.value = draft.notes;
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    console.log('Notes restored from:', draft.timestamp);
                }

                // Restore recommendation
                if (draft.recommendation) {
                    const radios = document.querySelectorAll('input[type="radio"]');
                    for (const radio of radios) {
                        const label = radio.closest('label') || radio.parentElement;
                        if (label && label.textContent.trim() === draft.recommendation) {
                            radio.checked = true;
                            radio.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Recommendation restored:', draft.recommendation);
                            break;
                        }
                    }
                }
            } catch (e) {
                console.error('Error restoring draft:', e);
            }
        }
    });

    // Clear draft after successful submission
    function clearDraft() {
        localStorage.removeItem(tokenKey);
        console.log('Draft cleared');
    }
</script>
"""

# Mobile Scorecard CSS
MOBILE_SCORECARD_CSS = """
<style>
    .scorecard-header {
        background: linear-gradient(135deg, #304CB2 0%, #1a2d6b 100%);
        color: white;
        padding: 24px;
        border-radius: 12px;
        margin-bottom: 24px;
        text-align: center;
    }
    .scorecard-header h1 {
        color: white !important;
        margin: 0;
        font-size: 1.5rem;
    }
    .scorecard-header .candidate-name {
        font-size: 1.25rem;
        margin-top: 8px;
        color: #F9B612;
    }
    .scorecard-header .stage-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 4px 16px;
        border-radius: 20px;
        margin-top: 12px;
    }
    .star-rating-container {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .star-rating-label {
        font-weight: 600;
        margin-bottom: 8px;
        color: #304CB2;
    }
    .ai-analysis-card {
        background: #D6E4F0;
        border-left: 4px solid #304CB2;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }
    .rec-selected {
        padding: 12px;
        border-radius: 4px;
        margin-top: 8px;
    }
    .confirm-modal {
        background: white;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .confirm-modal h2 {
        color: #304CB2;
        margin-bottom: 16px;
    }
    .success-message {
        background: #C8E6C9;
        color: #2E7D32;
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        margin: 24px 0;
    }
    .success-message h2 {
        color: #2E7D32 !important;
        margin: 0 0 8px 0;
    }
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .scorecard-header { padding: 16px; }
        .scorecard-header h1 { font-size: 1.25rem; }
    }
</style>
"""


def render_mobile_scorecard(token: str):
    """
    Render the mobile-friendly scorecard interface.

    This function should be called when a scorecard token is detected in the URL.
    It provides a complete mobile-optimized UI for interviewers to submit their feedback.

    Args:
        token: The scorecard access token from the URL parameter
    """
    # Add a "Back to ATS" button at the top for easy navigation
    if st.button("← Back to ATS", key="back_to_ats"):
        del st.query_params["token"]
        st.rerun()

    # Validate token
    interview_data = validate_scorecard_token(token)

    if not interview_data:
        st.error("This scorecard link is invalid, expired, or has already been used.")
        st.markdown("""
        ### What to do:
        - Contact the hiring team for a new scorecard link
        - Check if you've already submitted your feedback
        - The link may have expired (links are valid for 48 hours)
        """)
        return

    # Apply mobile CSS and auto-save JavaScript
    st.markdown(MOBILE_SCORECARD_CSS, unsafe_allow_html=True)
    st.markdown(AUTO_SAVE_JS, unsafe_allow_html=True)

    # Check for saved draft notification
    st.markdown("""
    <div id="draft-notification" style="display:none; background: #FEF5D4; color: #B8860B; padding: 12px; border-radius: 8px; margin-bottom: 16px; border-left: 4px solid #F9B612;">
        <strong>📝 Draft Restored</strong> - Your previous notes and recommendation have been restored. Changes auto-save every 5 seconds.
    </div>
    <script>
        const tokenKey = 'scorecard_draft_' + window.location.search;
        if (localStorage.getItem(tokenKey)) {
            document.getElementById('draft-notification').style.display = 'block';
            setTimeout(() => {
                document.getElementById('draft-notification').style.display = 'none';
            }, 5000);
        }
    </script>
    """, unsafe_allow_html=True)

    # Hide sidebar for mobile view
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none; }
        .block-container { max-width: 600px; padding: 1rem; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(_clean_html(f"""
    <div class="scorecard-header">
        <h1>Interview Scorecard</h1>
        <div class="candidate-name">{interview_data['candidate_name']}</div>
        <div class="stage-badge">{interview_data['stage']}</div>
        <div style="margin-top: 8px; font-size: 0.9rem; opacity: 0.9;">
            {interview_data['job_title']}
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Initialize session state for form data
    if 'scorecard_scores' not in st.session_state:
        st.session_state.scorecard_scores = {}
    if 'scorecard_recommendation' not in st.session_state:
        st.session_state.scorecard_recommendation = None
    if 'scorecard_submitted' not in st.session_state:
        st.session_state.scorecard_submitted = False
    if 'show_confirm' not in st.session_state:
        st.session_state.show_confirm = False

    # Check if already submitted
    if st.session_state.scorecard_submitted:
        st.markdown("""
        <div class="success-message">
            <h2>Thank You!</h2>
            <p>Your feedback has been submitted successfully.</p>
            <p>You may close this window.</p>
        </div>
        <script>
            // Clear saved draft after successful submission
            const tokenKey = 'scorecard_draft_' + window.location.search;
            localStorage.removeItem(tokenKey);
            console.log('Draft cleared after submission');
        </script>
        """, unsafe_allow_html=True)
        return

    # AI Analysis (if available)
    if interview_data.get('ai_resume_analysis'):
        with st.expander("View AI Resume Analysis", expanded=False):
            st.markdown(_clean_html(f"""
            <div class="ai-analysis-card">
                {interview_data['ai_resume_analysis']}
            </div>
            """), unsafe_allow_html=True)

    # Scoring Section
    st.markdown("### Scoring Criteria")

    criteria = interview_data.get('criteria', [])

    if criteria:
        for c in criteria:
            st.markdown(_clean_html(f"""
            <div class="star-rating-container">
                <div class="star-rating-label">{c['criteria_name']}</div>
            </div>
            """), unsafe_allow_html=True)

            # Use slider for touch-friendly scoring
            score = st.slider(
                f"Score for {c['criteria_name']}",
                min_value=0,
                max_value=c['max_score'],
                value=st.session_state.scorecard_scores.get(c['id'], 0),
                key=f"score_{c['id']}",
                help=c.get('description', '')
            )
            st.session_state.scorecard_scores[c['id']] = score

            # Visual star representation
            stars_filled = int((score / c['max_score']) * 5) if c['max_score'] > 0 else 0
            st.caption(f"{'*' * stars_filled}{'.' * (5 - stars_filled)} ({score}/{c['max_score']})")
    else:
        st.info("No specific scoring criteria defined for this interview stage.")

    st.markdown("---")

    # Recommendation Section
    st.markdown("### Overall Recommendation")
    st.markdown("Select your hiring recommendation:")

    recommendations = get_recommendation_options()

    # Use radio button for clear selection
    rec_labels = [r[0] for r in recommendations]
    current_rec_index = None
    if st.session_state.scorecard_recommendation:
        for i, r in enumerate(recommendations):
            if r[0] == st.session_state.scorecard_recommendation:
                current_rec_index = i
                break

    selected_rec = st.radio(
        "Recommendation",
        options=rec_labels,
        index=current_rec_index,
        key="recommendation_radio",
        horizontal=False,
        label_visibility="collapsed"
    )

    if selected_rec:
        st.session_state.scorecard_recommendation = selected_rec
        # Show selected recommendation with color
        rec_color = next((r[2] for r in recommendations if r[0] == selected_rec), "#666")
        st.markdown(_clean_html(f"""
        <div class="rec-selected" style="background: {rec_color}20; border-left: 4px solid {rec_color};">
            <strong style="color: {rec_color};">Selected: {selected_rec}</strong>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("---")

    # Notes Section
    st.markdown("### Interview Notes")
    st.caption("💾 Your notes and recommendation auto-save every 5 seconds to prevent data loss")
    notes = st.text_area(
        "Share your observations, key discussion points, and any concerns:",
        height=200,
        placeholder="Enter your interview notes here...\n\n- Key strengths observed\n- Areas of concern\n- Technical depth demonstrated\n- Communication skills\n- Culture fit observations",
        key="scorecard_notes"
    )

    # Auto-save status indicator
    st.markdown("""
    <div id="save-status" style="font-size: 0.8rem; color: #666; text-align: right;">
        <span id="save-indicator">✓ Auto-saving enabled</span>
    </div>
    <script>
        // Update save indicator when draft is saved
        const originalSaveDraft = window.saveDraft;
        if (typeof saveDraft === 'function') {
            const indicator = document.getElementById('save-indicator');
            setInterval(() => {
                if (indicator) {
                    indicator.textContent = '✓ Draft saved';
                    indicator.style.color = '#2E7D32';
                    setTimeout(() => {
                        indicator.textContent = '✓ Auto-saving enabled';
                        indicator.style.color = '#666';
                    }, 2000);
                }
            }, 5000);
        }
    </script>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Submit Section
    can_submit = st.session_state.scorecard_recommendation is not None

    if not can_submit:
        st.warning("Please select a recommendation before submitting.")

    # Confirmation flow
    if st.session_state.show_confirm:
        st.markdown("""
        <div class="confirm-modal">
            <h2>Confirm Submission</h2>
            <p>Are you sure you want to submit this scorecard?</p>
            <p><strong>Note:</strong> This action cannot be undone.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_confirm = False
                st.rerun()
        with col2:
            if st.button("Submit", type="primary", use_container_width=True):
                # Submit the scorecard
                success, message = submit_mobile_scorecard(
                    token=token,
                    scores=st.session_state.scorecard_scores,
                    notes=notes,
                    recommendation=st.session_state.scorecard_recommendation,
                    interviewer_name=interview_data.get('interviewer_name')
                )

                if success:
                    st.session_state.scorecard_submitted = True
                    st.session_state.show_confirm = False
                    st.rerun()
                else:
                    st.error(message)
                    st.session_state.show_confirm = False
    else:
        if st.button(
            "Submit Scorecard",
            type="primary",
            use_container_width=True,
            disabled=not can_submit
        ):
            st.session_state.show_confirm = True
            st.rerun()

    # Footer
    st.markdown("---")
    st.caption(f"Interviewer: {interview_data.get('interviewer_name', 'Not specified')}")
    st.caption(f"Link expires: {interview_data.get('expires_at', 'Unknown')}")
