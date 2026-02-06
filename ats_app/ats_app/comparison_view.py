"""
Candidate Comparison View Module
Side-by-side comparison of 2-3 candidates for the same role
"""
import streamlit as st
from database import get_candidates_for_comparison, STAGES, advance_candidate, reject_candidate
from genai import compare_candidates


def render_comparison_view(candidate_ids: list):
    """
    Render the side-by-side candidate comparison view.
    Compares 2-3 candidates for the same role with visual indicators.
    """
    # Southwest Airlines colors
    COLOR_WINNER = '#304CB2'       # Southwest Blue - winner/best
    COLOR_CONCERN = '#C8102E'      # Southwest Red - concerns/gaps
    COLOR_WARNING = '#F9B612'      # Southwest Yellow - warning
    COLOR_GOOD = '#2E7D32'         # Green - good/in range

    # Get detailed comparison data
    candidates = get_candidates_for_comparison(candidate_ids)

    if len(candidates) < 2:
        st.error("Could not load candidate data for comparison")
        if st.button("Back to Candidates"):
            st.session_state.show_comparison_view = False
            st.session_state.comparison_candidates = []
            st.rerun()
        return

    # Back button
    if st.button("Back to Candidates List"):
        st.session_state.show_comparison_view = False
        st.rerun()

    # Header with job title
    job_titles = list(set([c.get('job_title', 'Unknown') for c in candidates if c.get('job_title')]))
    job_title = job_titles[0] if len(job_titles) == 1 else "Multiple Roles"
    st.header(f"Candidate Comparison: {job_title}")

    # Get AI comparison recommendation
    job_desc = candidates[0].get('job_description', '') if candidates else ''
    ai_comparison = compare_candidates(candidates, job_desc)

    # Create column layout based on number of candidates
    num_candidates = len(candidates)
    cols = st.columns(num_candidates)

    # Helper function to find winner for a metric
    def get_winner_for_metric(metric_key, higher_is_better=True):
        values = [(c.get('name'), c.get(metric_key, 0) or 0) for c in candidates]
        if higher_is_better:
            winner = max(values, key=lambda x: x[1])
        else:
            winner = min(values, key=lambda x: x[1])
        return winner[0] if winner[1] > 0 else None

    # ============ OVERVIEW SECTION ============
    st.subheader("Overview")
    for i, candidate in enumerate(candidates):
        with cols[i]:
            name = candidate.get('name', 'Unknown')
            is_recommended = ai_comparison.get('recommendation') == name

            if is_recommended:
                st.markdown(f"### {name}")
                st.markdown(
                    f"<span style='background-color:{COLOR_WINNER}; color:white; "
                    f"padding:4px 8px; border-radius:4px; font-size:12px;'>AI Recommended</span>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(f"### {name}")

            st.markdown(f"**Stage:** {candidate.get('current_stage', 'N/A')}")
            st.markdown(f"**Days in Pipeline:** {candidate.get('days_in_pipeline', 0)}")
            st.markdown(f"**Vendor:** {candidate.get('vendor_name', 'Direct')}")

    st.divider()

    # ============ AI ANALYSIS SECTION ============
    st.subheader("AI Resume Analysis")
    ai_score_winner = get_winner_for_metric('ai_resume_score', higher_is_better=True)

    for i, candidate in enumerate(candidates):
        with cols[i]:
            score = candidate.get('ai_resume_score', 0) or 0
            is_winner = candidate.get('name') == ai_score_winner and score > 0

            if is_winner:
                st.markdown(
                    f"<div style='background-color:{COLOR_WINNER}; color:white; "
                    f"padding:12px; border-radius:8px; text-align:center;'>"
                    f"<strong>AI Score: {score:.0f}%</strong><br><small>Highest</small></div>",
                    unsafe_allow_html=True
                )
            else:
                st.metric("AI Score", f"{score:.0f}%")

            st.progress(score/100 if score else 0)

            st.markdown("**Key Strengths:**")
            strengths = candidate.get('strengths', [])
            if strengths:
                for s in strengths[:3]:
                    st.markdown(f"- {s}")
            else:
                st.caption("No strengths identified")

            st.markdown("**Identified Gaps:**")
            gaps = candidate.get('gaps', [])
            if gaps:
                for g in gaps[:3]:
                    st.markdown(
                        f"<span style='color:{COLOR_CONCERN}'>- {g}</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No gaps identified")

    st.divider()

    # ============ COMPENSATION SECTION ============
    st.subheader("Compensation")

    def get_best_rate_candidate():
        in_range = [
            (c.get('name'), c.get('expected_hourly_rate', 0))
            for c in candidates
            if c.get('rate_status') == 'in_range'
        ]
        if in_range:
            return min(in_range, key=lambda x: x[1])[0]
        return None

    best_rate = get_best_rate_candidate()

    for i, candidate in enumerate(candidates):
        with cols[i]:
            expected_rate = candidate.get('expected_hourly_rate', 0)
            min_rate = candidate.get('role_min_rate')
            max_rate = candidate.get('role_max_rate')
            rate_status = candidate.get('rate_status', 'no_data')
            is_best_value = candidate.get('name') == best_rate

            if expected_rate:
                if is_best_value:
                    st.markdown(
                        f"<div style='background-color:{COLOR_GOOD}; color:white; "
                        f"padding:8px; border-radius:4px; text-align:center;'>"
                        f"<strong>${expected_rate:.0f}/hr</strong><br><small>Best Value</small></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.metric("Expected Rate", f"${expected_rate:.0f}/hr")
            else:
                st.metric("Expected Rate", "Not specified")

            if min_rate or max_rate:
                min_display = f"${min_rate:.0f}" if min_rate else "N/A"
                max_display = f"${max_rate:.0f}" if max_rate else "N/A"
                st.caption(f"Role Range: {min_display} - {max_display}/hr")

            if rate_status == 'in_range':
                st.markdown(
                    f"<span style='color:{COLOR_GOOD}'>Within Range</span>",
                    unsafe_allow_html=True
                )
            elif rate_status == 'above':
                variance = candidate.get('rate_variance', 0)
                st.markdown(
                    f"<span style='color:{COLOR_CONCERN}'>+{variance:.1f}% Above Max</span>",
                    unsafe_allow_html=True
                )
            elif rate_status == 'below':
                variance = candidate.get('rate_variance', 0)
                st.markdown(
                    f"<span style='color:{COLOR_WARNING}'>{variance:.1f}% Below Min</span>",
                    unsafe_allow_html=True
                )
            else:
                st.caption("Rate status: N/A")

    st.divider()

    # ============ INTERVIEW SCORES SECTION ============
    st.subheader("Interview Performance")
    interview_winner = get_winner_for_metric('total_interview_score', higher_is_better=True)

    for i, candidate in enumerate(candidates):
        with cols[i]:
            interview_scores = candidate.get('interview_scores', {})
            total_score = candidate.get('total_interview_score', 0)
            is_winner = candidate.get('name') == interview_winner and total_score > 0

            if total_score > 0:
                if is_winner:
                    st.markdown(
                        f"<div style='background-color:{COLOR_WINNER}; color:white; "
                        f"padding:8px; border-radius:4px; text-align:center;'>"
                        f"<strong>Overall: {total_score:.0f}%</strong><br><small>Top Performer</small></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.metric("Overall Interview Score", f"{total_score:.0f}%")
            else:
                st.metric("Overall Interview Score", "No scores")

            if interview_scores:
                st.markdown("**By Stage:**")
                for stage, score_data in interview_scores.items():
                    pct = score_data.get('percentage', 0)
                    if pct >= 80:
                        color = COLOR_GOOD
                    elif pct >= 60:
                        color = COLOR_WARNING
                    else:
                        color = COLOR_CONCERN
                    st.markdown(
                        f"- {stage}: <span style='color:{color}'>{pct:.0f}%</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No interview scores recorded")

            recs = candidate.get('recommendations', 0)
            notes_count = candidate.get('notes_count', 0)
            st.caption(f"Recommendations: {recs} | Notes: {notes_count}")

    st.divider()

    # ============ AI VERDICT SECTION ============
    st.subheader("AI Recommendation")
    verdict_col1, verdict_col2 = st.columns([2, 1])

    with verdict_col1:
        recommended = ai_comparison.get('recommendation', 'Unable to determine')
        reasoning = ai_comparison.get('reasoning', '')
        summary = ai_comparison.get('comparison_summary', '')

        st.markdown(
            f"<div style='background-color:{COLOR_WINNER}; color:white; "
            f"padding:16px; border-radius:8px;'>"
            f"<h4 style='color:white; margin:0;'>Recommended: {recommended}</h4>"
            f"<p style='margin-top:8px; margin-bottom:0;'>{reasoning}</p></div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**Summary:** {summary}")

        rankings = ai_comparison.get('rankings', [])
        if rankings:
            st.markdown("**Rankings:**")
            for idx, name in enumerate(rankings):
                medal = "1st" if idx == 0 else ("2nd" if idx == 1 else "3rd")
                st.markdown(f"- {medal}: {name}")

    with verdict_col2:
        st.markdown("**Quick Actions**")
        for candidate in candidates:
            cid = candidate.get('id')
            name = candidate.get('name', 'Unknown')
            current_stage = candidate.get('current_stage', 'Resume Screen')
            current_idx = STAGES.index(current_stage) if current_stage in STAGES else 0

            st.markdown(f"**{name}:**")
            action_cols = st.columns(2)

            with action_cols[0]:
                if current_idx < len(STAGES) - 2:
                    next_stage = STAGES[current_idx + 1]
                    if st.button(f"Advance", key=f"cmp_adv_{cid}", type="primary"):
                        advance_candidate(cid, next_stage)
                        st.success(f"Advanced {name} to {next_stage}")
                        st.rerun()

            with action_cols[1]:
                if st.button(f"Reject", key=f"cmp_rej_{cid}"):
                    reject_candidate(cid)
                    st.warning(f"Rejected {name}")
                    st.rerun()

    st.divider()

    if st.button("Back to Candidates List", key="back_bottom"):
        st.session_state.show_comparison_view = False
        st.rerun()
