"""
Analytics view - Pipeline metrics, hiring trends, and data insights
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import (
    get_pipeline_velocity, get_time_to_hire_stats, get_stage_conversion_rates,
    get_vendor_performance, get_hiring_trends, get_ai_score_accuracy,
    get_source_effectiveness, export_candidates_data
)
from auth import get_current_user, has_permission
from views.utils import safe


def render_analytics():
    """
    Render the analytics dashboard showing:
    - Pipeline velocity
    - Time to hire stats
    - Stage conversion rates
    - Vendor performance
    - Hiring trends
    - AI score accuracy
    - Source effectiveness
    - Data export
    """
    st.title("📈 Analytics")

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view analytics")
        return

    # Check permissions
    if not has_permission('analytics', 'view'):
        st.error("You don't have permission to access analytics")
        return

    # ============ TABS ============
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Pipeline Metrics",
        "🏢 Vendor Performance",
        "🤖 AI Insights",
        "📤 Data Export"
    ])

    with tab1:
        render_pipeline_metrics()

    with tab2:
        render_vendor_performance()

    with tab3:
        render_ai_insights()

    with tab4:
        render_data_export()


def render_pipeline_metrics():
    """Display pipeline velocity, time to hire, and conversion rates"""
    st.subheader("Pipeline Metrics")

    # ============ TIME TO HIRE STATS ============
    st.markdown("### ⏱️ Time to Hire")

    try:
        time_to_hire = get_time_to_hire_stats()

        if time_to_hire:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                avg_days = time_to_hire.get('avg_days', 0)
                st.metric("Average Days", f"{avg_days:.1f}" if avg_days else "N/A")

            with col2:
                median_days = time_to_hire.get('median_days', 0)
                st.metric("Median Days", f"{median_days:.1f}" if median_days else "N/A")

            with col3:
                min_days = time_to_hire.get('min_days', 0)
                st.metric("Fastest Hire", f"{min_days:.0f} days" if min_days else "N/A")

            with col4:
                max_days = time_to_hire.get('max_days', 0)
                st.metric("Longest Hire", f"{max_days:.0f} days" if max_days else "N/A")

            # Show distribution if available
            if time_to_hire.get('by_job'):
                st.markdown("**Time to Hire by Job**")
                by_job_df = pd.DataFrame(time_to_hire['by_job'])
                if not by_job_df.empty:
                    st.dataframe(by_job_df, use_container_width=True)
        else:
            st.info("No time-to-hire data available yet")

    except Exception as e:
        st.error(f"Error loading time to hire stats: {str(e)}")

    st.divider()

    # ============ PIPELINE VELOCITY ============
    st.markdown("### 🚀 Pipeline Velocity")

    try:
        velocity = get_pipeline_velocity()

        if velocity:
            # Show overall metrics
            col1, col2 = st.columns(2)

            with col1:
                avg_velocity = velocity.get('avg_days_per_stage', 0)
                st.metric("Avg Days Per Stage", f"{avg_velocity:.1f}" if avg_velocity else "N/A")

            with col2:
                total_candidates = velocity.get('total_candidates', 0)
                st.metric("Candidates Analyzed", total_candidates)

            # Show by stage
            if velocity.get('by_stage'):
                st.markdown("**Average Days in Each Stage**")
                stage_df = pd.DataFrame([
                    {'Stage': stage, 'Avg Days': days}
                    for stage, days in velocity['by_stage'].items()
                ])
                if not stage_df.empty:
                    st.bar_chart(stage_df.set_index('Stage'))
        else:
            st.info("No velocity data available yet")

    except Exception as e:
        st.error(f"Error loading pipeline velocity: {str(e)}")

    st.divider()

    # ============ STAGE CONVERSION RATES ============
    st.markdown("### 🔄 Stage Conversion Rates")

    try:
        conversion_rates = get_stage_conversion_rates()

        if conversion_rates:
            # Create DataFrame for display
            conversion_df = pd.DataFrame([
                {
                    'From Stage': item['from_stage'],
                    'To Stage': item['to_stage'],
                    'Conversion Rate': f"{item['conversion_rate']:.1f}%",
                    'Candidates Advanced': item['advanced_count'],
                    'Total Candidates': item['total_count']
                }
                for item in conversion_rates
            ])

            if not conversion_df.empty:
                st.dataframe(conversion_df, use_container_width=True)

                # Visualize conversion rates
                chart_df = pd.DataFrame([
                    {
                        'Stage Transition': f"{item['from_stage']} → {item['to_stage']}",
                        'Rate': item['conversion_rate']
                    }
                    for item in conversion_rates
                ])
                if not chart_df.empty:
                    st.bar_chart(chart_df.set_index('Stage Transition'))
            else:
                st.info("No conversion data available yet")
        else:
            st.info("No conversion data available yet")

    except Exception as e:
        st.error(f"Error loading conversion rates: {str(e)}")

    st.divider()

    # ============ HIRING TRENDS ============
    st.markdown("### 📅 Hiring Trends")

    try:
        trends = get_hiring_trends(days=90)

        if trends and trends.get('by_date'):
            # Create DataFrame
            trends_df = pd.DataFrame(trends['by_date'])

            if not trends_df.empty:
                # Convert date strings to datetime
                if 'date' in trends_df.columns:
                    trends_df['date'] = pd.to_datetime(trends_df['date'])
                    trends_df = trends_df.sort_values('date')

                    # Show line chart
                    st.line_chart(trends_df.set_index('date')['hired_count'])

                    # Show summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_hired = trends.get('total_hired', 0)
                        st.metric("Total Hired (90 days)", total_hired)
                    with col2:
                        avg_per_month = total_hired / 3 if total_hired else 0
                        st.metric("Avg Per Month", f"{avg_per_month:.1f}")
                    with col3:
                        peak_day = trends.get('peak_day', {})
                        if peak_day:
                            st.metric("Peak Day", f"{peak_day.get('count', 0)} hires")
            else:
                st.info("No hiring trends data available yet")
        else:
            st.info("No hiring trends data available yet")

    except Exception as e:
        st.error(f"Error loading hiring trends: {str(e)}")


def render_vendor_performance():
    """Display vendor performance metrics"""
    st.subheader("Vendor Performance")

    try:
        vendor_perf = get_vendor_performance()

        if vendor_perf:
            # Create DataFrame
            vendor_df = pd.DataFrame([
                {
                    'Vendor': item.get('vendor_name', 'Unknown'),
                    'Total Candidates': item.get('total_candidates', 0),
                    'Hired': item.get('hired_count', 0),
                    'Active': item.get('active_count', 0),
                    'Rejected': item.get('rejected_count', 0),
                    'Hire Rate': f"{item.get('hire_rate', 0):.1f}%",
                    'Avg AI Score': f"{item.get('avg_ai_score', 0):.1f}%"
                }
                for item in vendor_perf
            ])

            if not vendor_df.empty:
                st.dataframe(vendor_df, use_container_width=True)

                # Visualize vendor comparison
                st.markdown("### 📊 Vendor Comparison")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Candidates Submitted**")
                    chart_df = vendor_df[['Vendor', 'Total Candidates']].set_index('Vendor')
                    st.bar_chart(chart_df)

                with col2:
                    st.markdown("**Candidates Hired**")
                    chart_df = vendor_df[['Vendor', 'Hired']].set_index('Vendor')
                    st.bar_chart(chart_df)
            else:
                st.info("No vendor performance data available yet")
        else:
            st.info("No vendor performance data available yet")

    except Exception as e:
        st.error(f"Error loading vendor performance: {str(e)}")

    st.divider()

    # ============ SOURCE EFFECTIVENESS ============
    st.markdown("### 🎯 Source Effectiveness")

    try:
        source_eff = get_source_effectiveness()

        if source_eff:
            # Create DataFrame
            source_df = pd.DataFrame([
                {
                    'Source': item.get('source_type', 'Unknown'),
                    'Total Candidates': item.get('total_candidates', 0),
                    'Hired': item.get('hired_count', 0),
                    'Hire Rate': f"{item.get('hire_rate', 0):.1f}%",
                    'Avg Time to Hire': f"{item.get('avg_time_to_hire', 0):.1f} days"
                }
                for item in source_eff
            ])

            if not source_df.empty:
                st.dataframe(source_df, use_container_width=True)
            else:
                st.info("No source effectiveness data available yet")
        else:
            st.info("No source effectiveness data available yet")

    except Exception as e:
        st.error(f"Error loading source effectiveness: {str(e)}")


def render_ai_insights():
    """Display AI scoring insights and accuracy"""
    st.subheader("AI Insights")

    # ============ AI SCORE ACCURACY ============
    st.markdown("### 🤖 AI Score Accuracy")

    try:
        ai_accuracy = get_ai_score_accuracy()

        if ai_accuracy:
            col1, col2, col3 = st.columns(3)

            with col1:
                correlation = ai_accuracy.get('correlation', 0)
                st.metric("Correlation with Hires", f"{correlation:.2f}" if correlation else "N/A")
                st.caption("Score between -1 and 1. Higher is better.")

            with col2:
                avg_hired_score = ai_accuracy.get('avg_hired_score', 0)
                st.metric("Avg Score (Hired)", f"{avg_hired_score:.1f}%" if avg_hired_score else "N/A")

            with col3:
                avg_rejected_score = ai_accuracy.get('avg_rejected_score', 0)
                st.metric("Avg Score (Rejected)", f"{avg_rejected_score:.1f}%" if avg_rejected_score else "N/A")

            # Show score distribution
            if ai_accuracy.get('score_buckets'):
                st.markdown("**Score Distribution by Outcome**")
                buckets_df = pd.DataFrame(ai_accuracy['score_buckets'])
                if not buckets_df.empty:
                    st.dataframe(buckets_df, use_container_width=True)

            # Show insights
            st.markdown("### 💡 Insights")

            if correlation and correlation > 0.5:
                st.success(f"✅ AI scores show strong positive correlation ({correlation:.2f}) with hiring outcomes. "
                          "The AI is effectively predicting candidate success.")
            elif correlation and correlation > 0.3:
                st.info(f"ℹ️ AI scores show moderate correlation ({correlation:.2f}) with hiring outcomes. "
                       "There's room for improvement in prediction accuracy.")
            elif correlation and correlation > 0:
                st.warning(f"⚠️ AI scores show weak correlation ({correlation:.2f}) with hiring outcomes. "
                          "Consider reviewing the scoring criteria.")
            else:
                st.error("❌ AI scores show negative or no correlation with hiring outcomes. "
                        "Review scoring criteria and training data.")

        else:
            st.info("No AI accuracy data available yet. Score more candidates to see insights.")

    except Exception as e:
        st.error(f"Error loading AI accuracy: {str(e)}")


def render_data_export():
    """Provide data export functionality"""
    st.subheader("Data Export")

    st.markdown("""
    Export candidate data for analysis in external tools like Excel or Tableau.

    **Exported fields include:**
    - Candidate information (name, email, phone)
    - Current stage and status
    - Job and vendor details
    - AI scores and analysis
    - Timestamps
    """)

    # Export options
    col1, col2 = st.columns(2)

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Active", "Hired", "Rejected"],
            key="export_status"
        )

    with col2:
        format_option = st.selectbox(
            "Export Format",
            ["CSV", "Excel (.xlsx)"],
            key="export_format"
        )

    if st.button("📤 Export Data", type="primary", use_container_width=True):
        try:
            with st.spinner("Generating export..."):
                # Get export data
                status = None if status_filter == "All" else status_filter
                export_bytes = export_candidates_data(status=status)

                if export_bytes:
                    # Determine file extension and mime type
                    if format_option == "CSV":
                        file_ext = "csv"
                        mime_type = "text/csv"
                    else:
                        file_ext = "xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"ats_candidates_{timestamp}.{file_ext}"

                    # Provide download button
                    st.download_button(
                        label=f"⬇️ Download {format_option}",
                        data=export_bytes,
                        file_name=filename,
                        mime=mime_type,
                        key="download_export"
                    )

                    st.success(f"✅ Export ready! Click the button above to download.")

                else:
                    st.warning("No data available to export")

        except Exception as e:
            st.error(f"Export failed: {str(e)}")

    st.divider()

    # Additional export options
    st.markdown("### 🔧 Advanced Export Options")

    with st.expander("Custom Date Range Export"):
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=90),
                key="export_start_date"
            )

        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                key="export_end_date"
            )

        if st.button("Export Date Range", key="export_date_range"):
            st.info("Date range filtering will be available in a future update")

    with st.expander("Job-Specific Export"):
        from database import get_jobs
        jobs = get_jobs()

        if jobs:
            job_options = {j['title']: j['id'] for j in jobs}
            selected_job = st.selectbox("Select Job", list(job_options.keys()), key="export_job")

            if st.button("Export Job Candidates", key="export_job_candidates"):
                st.info("Job-specific export will be available in a future update")
        else:
            st.info("No jobs available")
