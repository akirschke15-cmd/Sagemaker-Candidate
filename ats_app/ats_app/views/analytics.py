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
from views.utils import (
    safe, metric_card, section_header, kpi_row, progress_bar_html,
    status_badge, empty_state
)


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
    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to view analytics")
        return

    # Check permissions
    if not has_permission('analytics', 'view'):
        st.error("You don't have permission to access analytics")
        return

    st.markdown(section_header("Analytics", "Deep insights into your hiring pipeline"), unsafe_allow_html=True)

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
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Pipeline Metrics", "Analyze hiring efficiency and bottlenecks"), unsafe_allow_html=True)

    # ============ TIME TO HIRE STATS ============
    try:
        time_to_hire = get_time_to_hire_stats()

        if time_to_hire:
            avg_days = time_to_hire.get('avg_days', 0)
            median_days = time_to_hire.get('median_days', 0)
            min_days = time_to_hire.get('min_days', 0)
            max_days = time_to_hire.get('max_days', 0)

            kpi_items = [
                {
                    'label': 'Average Days',
                    'value': f"{avg_days:.1f}" if avg_days else "N/A",
                    'icon': '&#128200;',
                    'color': '#304CB2'
                },
                {
                    'label': 'Median Days',
                    'value': f"{median_days:.1f}" if median_days else "N/A",
                    'icon': '&#128202;',
                    'color': '#3949AB'
                },
                {
                    'label': 'Fastest Hire',
                    'value': f"{min_days:.0f}d" if min_days else "N/A",
                    'icon': '&#9889;',
                    'color': '#2EA043'
                },
                {
                    'label': 'Longest Hire',
                    'value': f"{max_days:.0f}d" if max_days else "N/A",
                    'icon': '&#9200;',
                    'color': '#F9B612'
                }
            ]

            st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

            # Show distribution if available
            if time_to_hire.get('by_job'):
                st.markdown("""
                <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                            border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                            padding:20px; margin-top:24px;'>
                    <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                        Time to Hire by Job
                    </h4>
                """, unsafe_allow_html=True)

                by_job_df = pd.DataFrame(time_to_hire['by_job'])
                if not by_job_df.empty:
                    st.dataframe(by_job_df, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No time-to-hire data available", "Hire candidates to see time-to-hire metrics", "&#128200;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading time to hire stats: {str(e)}")

    # ============ PIPELINE VELOCITY ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Pipeline Velocity", "Average time spent in each stage"), unsafe_allow_html=True)

    try:
        velocity = get_pipeline_velocity()

        if velocity:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

            # Show overall metrics
            col1, col2 = st.columns(2)

            with col1:
                avg_velocity = velocity.get('avg_days_per_stage', 0)
                st.markdown(
                    metric_card("Avg Days Per Stage", f"{avg_velocity:.1f}" if avg_velocity else "N/A", icon="&#9203;", color="#304CB2"),
                    unsafe_allow_html=True
                )

            with col2:
                total_candidates = velocity.get('total_candidates', 0)
                st.markdown(
                    metric_card("Candidates Analyzed", total_candidates, icon="&#128101;", color="#2EA043"),
                    unsafe_allow_html=True
                )

            # Show by stage
            if velocity.get('by_stage'):
                st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
                st.markdown("<h4 style='margin:0 0 12px 0; font-size:15px; color:#ffffff; font-weight:600;'>Average Days in Each Stage</h4>", unsafe_allow_html=True)

                stage_df = pd.DataFrame([
                    {'Stage': stage, 'Avg Days': days}
                    for stage, days in velocity['by_stage'].items()
                ])
                if not stage_df.empty:
                    st.bar_chart(stage_df.set_index('Stage'), color="#304CB2")

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No velocity data available", "Move candidates through stages to see velocity metrics", "&#9203;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading pipeline velocity: {str(e)}")

    # ============ STAGE CONVERSION RATES ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Stage Conversion Rates", "Success rates between stages"), unsafe_allow_html=True)

    try:
        conversion_rates = get_stage_conversion_rates()

        if conversion_rates:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

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
                st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

                # Show progress bars for each conversion
                for item in conversion_rates:
                    from_stage = item['from_stage']
                    to_stage = item['to_stage']
                    rate = item['conversion_rate']
                    advanced = item['advanced_count']
                    total = item['total_count']

                    # Color based on rate
                    if rate >= 70:
                        color = '#2EA043'
                    elif rate >= 50:
                        color = '#F9B612'
                    else:
                        color = '#C8102E'

                    st.markdown(f"""
                    <div style='margin-bottom:16px;'>
                        <div style='font-size:13px; color:#94a3b8; margin-bottom:6px;'>
                            {safe(from_stage)} → {safe(to_stage)}
                        </div>
                        {progress_bar_html(advanced, total, color=color)}
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No conversion data available", "Move candidates through stages to see conversion rates", "&#128259;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading conversion rates: {str(e)}")

    # ============ HIRING TRENDS ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Hiring Trends", "Hiring activity over last 90 days"), unsafe_allow_html=True)

    try:
        trends = get_hiring_trends(days=90)

        if trends and trends.get('by_date'):
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

            # Create DataFrame
            trends_df = pd.DataFrame(trends['by_date'])

            if not trends_df.empty:
                # Convert date strings to datetime
                if 'date' in trends_df.columns:
                    trends_df['date'] = pd.to_datetime(trends_df['date'])
                    trends_df = trends_df.sort_values('date')

                    # Show line chart
                    st.line_chart(trends_df.set_index('date')['hired_count'], color="#304CB2")

                    # Show summary metrics
                    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_hired = trends.get('total_hired', 0)
                        st.markdown(
                            metric_card("Total Hired (90d)", total_hired, icon="&#9989;", color="#2EA043"),
                            unsafe_allow_html=True
                        )
                    with col2:
                        avg_per_month = total_hired / 3 if total_hired else 0
                        st.markdown(
                            metric_card("Avg Per Month", f"{avg_per_month:.1f}", icon="&#128202;", color="#304CB2"),
                            unsafe_allow_html=True
                        )
                    with col3:
                        peak_day = trends.get('peak_day', {})
                        peak_count = peak_day.get('count', 0) if peak_day else 0
                        st.markdown(
                            metric_card("Peak Day", f"{peak_count} hires", icon="&#11014;", color="#F9B612"),
                            unsafe_allow_html=True
                        )

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No hiring trends data available", "Hire candidates to see trends", "&#128200;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading hiring trends: {str(e)}")


def render_vendor_performance():
    """Display vendor performance metrics"""
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Vendor Performance", "Compare vendor effectiveness and quality"), unsafe_allow_html=True)

    try:
        vendor_perf = get_vendor_performance()

        if vendor_perf:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

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

                st.markdown("</div>", unsafe_allow_html=True)

                # Visualize vendor comparison
                st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
                st.markdown(section_header("Vendor Comparison", "Visual comparison of vendor metrics"), unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("""
                    <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                                border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                                padding:20px;'>
                        <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                            Candidates Submitted
                        </h4>
                    """, unsafe_allow_html=True)

                    chart_df = vendor_df[['Vendor', 'Total Candidates']].set_index('Vendor')
                    st.bar_chart(chart_df, color="#304CB2")

                    st.markdown("</div>", unsafe_allow_html=True)

                with col2:
                    st.markdown("""
                    <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                                border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                                padding:20px;'>
                        <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                            Candidates Hired
                        </h4>
                    """, unsafe_allow_html=True)

                    chart_df = vendor_df[['Vendor', 'Hired']].set_index('Vendor')
                    st.bar_chart(chart_df, color="#2EA043")

                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown(
                    empty_state("No vendor performance data available", "Add vendors and candidates to see metrics", "&#128188;"),
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                empty_state("No vendor performance data available", "Add vendors and candidates to see metrics", "&#128188;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading vendor performance: {str(e)}")

    # ============ SOURCE EFFECTIVENESS ============
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Source Effectiveness", "Which sources produce the best hires"), unsafe_allow_html=True)

    try:
        source_eff = get_source_effectiveness()

        if source_eff:
            # Glass card container
            st.markdown("""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        padding:20px;'>
            """, unsafe_allow_html=True)

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
                st.markdown(
                    empty_state("No source effectiveness data available", "Add source information to candidates", "&#127919;"),
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                empty_state("No source effectiveness data available", "Add source information to candidates", "&#127919;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading source effectiveness: {str(e)}")


def render_ai_insights():
    """Display AI scoring insights and accuracy"""
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("AI Insights", "Evaluate AI scoring accuracy and effectiveness"), unsafe_allow_html=True)

    # ============ AI SCORE ACCURACY ============
    try:
        ai_accuracy = get_ai_score_accuracy()

        if ai_accuracy:
            correlation = ai_accuracy.get('correlation', 0)
            avg_hired_score = ai_accuracy.get('avg_hired_score', 0)
            avg_rejected_score = ai_accuracy.get('avg_rejected_score', 0)

            # KPI row for scores
            kpi_items = [
                {
                    'label': 'Correlation with Hires',
                    'value': f"{correlation:.2f}" if correlation else "N/A",
                    'icon': '&#128200;',
                    'color': '#2EA043' if correlation and correlation > 0.5 else '#F9B612' if correlation and correlation > 0.3 else '#C8102E'
                },
                {
                    'label': 'Avg Score (Hired)',
                    'value': f"{avg_hired_score:.1f}%" if avg_hired_score else "N/A",
                    'icon': '&#9989;',
                    'color': '#2EA043'
                },
                {
                    'label': 'Avg Score (Rejected)',
                    'value': f"{avg_rejected_score:.1f}%" if avg_rejected_score else "N/A",
                    'icon': '&#10060;',
                    'color': '#C8102E'
                }
            ]

            st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

            # Show score distribution
            if ai_accuracy.get('score_buckets'):
                st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

                st.markdown("""
                <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                            border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                            padding:20px;'>
                    <h4 style='margin:0 0 16px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                        Score Distribution by Outcome
                    </h4>
                """, unsafe_allow_html=True)

                buckets_df = pd.DataFrame(ai_accuracy['score_buckets'])
                if not buckets_df.empty:
                    st.dataframe(buckets_df, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)

            # Show insights
            st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
            st.markdown(section_header("Key Insights", "AI scoring effectiveness analysis"), unsafe_allow_html=True)

            if correlation and correlation > 0.5:
                insight_color = '#2EA043'
                insight_icon = '&#9989;'
                insight_text = f"AI scores show strong positive correlation ({correlation:.2f}) with hiring outcomes. The AI is effectively predicting candidate success."
            elif correlation and correlation > 0.3:
                insight_color = '#F9B612'
                insight_icon = '&#9888;'
                insight_text = f"AI scores show moderate correlation ({correlation:.2f}) with hiring outcomes. There's room for improvement in prediction accuracy."
            elif correlation and correlation > 0:
                insight_color = '#F9B612'
                insight_icon = '&#9888;'
                insight_text = f"AI scores show weak correlation ({correlation:.2f}) with hiring outcomes. Consider reviewing the scoring criteria."
            else:
                insight_color = '#C8102E'
                insight_icon = '&#10060;'
                insight_text = "AI scores show negative or no correlation with hiring outcomes. Review scoring criteria and training data."

            st.markdown(f"""
            <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                        border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                        border-left: 4px solid {insight_color}; padding:20px;'>
                <div style='display:flex; align-items:flex-start; gap:16px;'>
                    <div style='font-size:32px; line-height:1;'>{insight_icon}</div>
                    <div>
                        <h4 style='margin:0 0 8px 0; font-size:16px; color:#ffffff; font-weight:700;'>
                            Correlation Analysis
                        </h4>
                        <p style='margin:0; font-size:14px; color:#94a3b8; line-height:1.6;'>
                            {insight_text}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(
                empty_state("No AI accuracy data available", "Score more candidates to see insights", "&#129302;"),
                unsafe_allow_html=True
            )

    except Exception as e:
        st.error(f"Error loading AI accuracy: {str(e)}")


def render_data_export():
    """Provide data export functionality"""
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Data Export", "Export candidate data for external analysis"), unsafe_allow_html=True)

    # Glass card container
    st.markdown("""
    <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                border: 1px solid rgba(255,255,255,0.06); border-radius:12px;
                padding:24px;'>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p style='color:#94a3b8; font-size:14px; line-height:1.6; margin-bottom:24px;'>
    Export candidate data for analysis in external tools like Excel or Tableau.
    </p>

    <div style='background: rgba(48,76,178,0.1); border: 1px solid rgba(48,76,178,0.3);
                border-radius:8px; padding:16px; margin-bottom:24px;'>
        <h4 style='margin:0 0 12px 0; font-size:14px; color:#ffffff; font-weight:600;'>
            Exported Fields Include:
        </h4>
        <ul style='margin:0; padding-left:20px; color:#94a3b8; font-size:13px;'>
            <li>Candidate information (name, email, phone)</li>
            <li>Current stage and status</li>
            <li>Job and vendor details</li>
            <li>AI scores and analysis</li>
            <li>Timestamps</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

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

                    st.success("✅ Export ready! Click the button above to download.")

                else:
                    st.warning("No data available to export")

        except Exception as e:
            st.error(f"Export failed: {str(e)}")

    st.markdown("</div>", unsafe_allow_html=True)

    # Additional export options
    st.markdown("<div style='margin-top:32px;'></div>", unsafe_allow_html=True)
    st.markdown(section_header("Advanced Export Options", "Additional export configurations"), unsafe_allow_html=True)

    with st.expander("Custom Date Range Export", expanded=False):
        st.markdown("""
        <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.06); border-radius:8px;
                    padding:16px;'>
        """, unsafe_allow_html=True)

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

        if st.button("Export Date Range", key="export_date_range", use_container_width=True):
            st.info("Date range filtering will be available in a future update")

        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Job-Specific Export", expanded=False):
        st.markdown("""
        <div style='background: rgba(26,35,50,0.8); backdrop-filter: blur(12px);
                    border: 1px solid rgba(255,255,255,0.06); border-radius:8px;
                    padding:16px;'>
        """, unsafe_allow_html=True)

        from database import get_jobs
        jobs = get_jobs()

        if jobs:
            job_options = {j['title']: j['id'] for j in jobs}
            selected_job = st.selectbox("Select Job", list(job_options.keys()), key="export_job")

            if st.button("Export Job Candidates", key="export_job_candidates", use_container_width=True):
                st.info("Job-specific export will be available in a future update")
        else:
            st.markdown(
                empty_state("No jobs available", "Create jobs to enable job-specific export", "&#128188;"),
                unsafe_allow_html=True
            )

        st.markdown("</div>", unsafe_allow_html=True)
