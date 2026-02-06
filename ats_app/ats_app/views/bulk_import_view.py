"""
Bulk Import View - CSV/Excel candidate import with column mapping and validation
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from bulk_import import (
    parse_import_file, auto_detect_columns, validate_import_row,
    check_duplicate, bulk_create_candidates, generate_error_report,
    get_import_preview, validate_all_rows, SYSTEM_FIELDS
)
from database import get_jobs, get_vendors
from auth import get_current_user, has_permission
from views.utils import safe, section_header, kpi_row, empty_state


def render_bulk_import():
    """
    Render the bulk import view showing:
    - File upload (CSV/Excel)
    - Column mapping UI
    - Preview imported data
    - Validation
    - Duplicate handling
    - Import execution
    - Results summary
    """
    st.markdown(section_header("Bulk Import", "Import candidates from CSV or Excel"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to access bulk import")
        return

    # Check permissions
    if not has_permission('candidates', 'create'):
        st.error("You don't have permission to import candidates")
        return

    st.markdown("""
    Import multiple candidates from a CSV or Excel file. The system will:
    - Auto-detect column mappings
    - Validate data before import
    - Check for duplicates
    - Provide detailed error reports
    """)

    # Initialize session state for import process
    if 'import_df' not in st.session_state:
        st.session_state.import_df = None
    if 'import_mapping' not in st.session_state:
        st.session_state.import_mapping = {}
    if 'import_validation' not in st.session_state:
        st.session_state.import_validation = None

    # ============ STEP 1: FILE UPLOAD ============
    step_html = """
    <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                border-left: 4px solid #304CB2;
                border-radius: 8px;
                padding: 16px 20px;
                margin: 20px 0;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="background: #304CB2; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center; font-weight: 600;">1</div>
            <h3 style="margin: 0; color: #FFFFFF;">Upload File</h3>
        </div>
    </div>
    """
    st.markdown(step_html, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload a file with candidate information. First row should contain column headers."
    )

    if uploaded_file is not None:
        # Parse file
        if st.session_state.import_df is None or uploaded_file.name != st.session_state.get('last_filename'):
            with st.spinner("Parsing file..."):
                file_bytes = uploaded_file.getvalue()
                df, error = parse_import_file(file_bytes, uploaded_file.name)

                if error:
                    st.error(f"Failed to parse file: {error}")
                    return

                st.session_state.import_df = df
                st.session_state.last_filename = uploaded_file.name

                # Auto-detect columns
                st.session_state.import_mapping = auto_detect_columns(df)

                st.success(f"✅ Loaded {len(df)} rows from {uploaded_file.name}")

        df = st.session_state.import_df

        # Show file info - Premium KPI Row
        kpi_items = [
            {"label": "Total Rows", "value": len(df), "icon": "&#128203;", "color": "#304CB2"},
            {"label": "Columns", "value": len(df.columns), "icon": "&#128196;", "color": "#2EA043"},
            {"label": "File Size", "value": f"{uploaded_file.size / 1024:.1f} KB", "icon": "&#128190;", "color": "#F9B612"}
        ]
        st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

        st.divider()

        # ============ STEP 2: COLUMN MAPPING ============
        step_html = """
        <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                    border-left: 4px solid #304CB2;
                    border-radius: 8px;
                    padding: 16px 20px;
                    margin: 20px 0;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #304CB2; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center; font-weight: 600;">2</div>
                <h3 style="margin: 0; color: #FFFFFF;">Map Columns</h3>
            </div>
        </div>
        """
        st.markdown(step_html, unsafe_allow_html=True)

        st.markdown("Map your CSV columns to system fields. Required fields are marked with *")

        mapping = st.session_state.import_mapping
        csv_columns = ['[Not Mapped]'] + list(df.columns)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Required Fields**")
            for field, config in SYSTEM_FIELDS.items():
                if config['required']:
                    current_mapping = mapping.get(field)
                    if current_mapping and current_mapping in csv_columns:
                        default_index = csv_columns.index(current_mapping)
                    else:
                        default_index = 0

                    selected = st.selectbox(
                        f"{config['label']} *",
                        csv_columns,
                        index=default_index,
                        key=f"map_{field}"
                    )

                    if selected != '[Not Mapped]':
                        mapping[field] = selected
                    else:
                        mapping[field] = None

        with col2:
            st.markdown("**Optional Fields**")
            for field, config in SYSTEM_FIELDS.items():
                if not config['required']:
                    current_mapping = mapping.get(field)
                    if current_mapping and current_mapping in csv_columns:
                        default_index = csv_columns.index(current_mapping)
                    else:
                        default_index = 0

                    selected = st.selectbox(
                        config['label'],
                        csv_columns,
                        index=default_index,
                        key=f"map_{field}"
                    )

                    if selected != '[Not Mapped]':
                        mapping[field] = selected
                    else:
                        mapping[field] = None

        st.session_state.import_mapping = mapping

        st.divider()

        # ============ STEP 3: PREVIEW AND VALIDATE ============
        step_html = """
        <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                    border-left: 4px solid #304CB2;
                    border-radius: 8px;
                    padding: 16px 20px;
                    margin: 20px 0;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #304CB2; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center; font-weight: 600;">3</div>
                <h3 style="margin: 0; color: #FFFFFF;">Preview & Validate</h3>
            </div>
        </div>
        """
        st.markdown(step_html, unsafe_allow_html=True)

        if st.button("🔍 Validate Data", type="primary"):
            with st.spinner("Validating data..."):
                validation = validate_all_rows(df, mapping)
                st.session_state.import_validation = validation

        if st.session_state.import_validation:
            validation = st.session_state.import_validation

            # Show validation summary - Premium KPI Row
            kpi_items = [
                {"label": "Total Rows", "value": validation['total_rows'], "icon": "&#128203;", "color": "#304CB2"},
                {"label": "Valid Rows", "value": validation['valid_rows'], "icon": "&#9989;", "color": "#2EA043"},
                {"label": "Invalid Rows", "value": validation['invalid_rows'], "icon": "&#10060;", "color": "#C8102E"},
                {"label": "Duplicates Found", "value": validation['duplicate_emails'], "icon": "&#128260;", "color": "#F9B612"}
            ]
            st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

            # Show errors if any
            if validation['errors']:
                with st.expander(f"⚠️ Validation Errors ({len(validation['errors'])})", expanded=True):
                    for row_index, errors in validation['errors'][:20]:  # Show first 20
                        st.error(f"**Row {row_index}:** {'; '.join(safe(e) for e in errors)}")

                    if len(validation['errors']) > 20:
                        st.caption(f"... and {len(validation['errors']) - 20} more errors")

            # Show duplicates if any
            if validation['duplicates']:
                with st.expander(f"🔄 Duplicate Emails ({len(validation['duplicates'])})", expanded=True):
                    for row_index, email, existing_info in validation['duplicates'][:20]:
                        st.warning(f"**Row {row_index}:** {safe(email)} - {safe(existing_info)}")

                    if len(validation['duplicates']) > 20:
                        st.caption(f"... and {len(validation['duplicates']) - 20} more duplicates")

        # Show preview
        st.markdown("**Preview of Mapped Data (first 10 rows)**")
        preview_df = get_import_preview(df, mapping, max_rows=10)
        st.dataframe(preview_df, use_container_width=True)

        st.divider()

        # ============ STEP 4: IMPORT SETTINGS ============
        step_html = """
        <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                    border-left: 4px solid #304CB2;
                    border-radius: 8px;
                    padding: 16px 20px;
                    margin: 20px 0;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #304CB2; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center; font-weight: 600;">4</div>
                <h3 style="margin: 0; color: #FFFFFF;">Import Settings</h3>
            </div>
        </div>
        """
        st.markdown(step_html, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # Job assignment
            jobs = get_jobs(status='Open')
            if jobs:
                job_options = {'[None - Assign later]': None}
                job_options.update({j['title']: j['id'] for j in jobs})
                selected_job_label = st.selectbox("Assign to Job", list(job_options.keys()))
                selected_job_id = job_options[selected_job_label]
            else:
                st.info("No open jobs available")
                selected_job_id = None

            # Vendor assignment
            vendors = get_vendors()
            if vendors:
                vendor_options = {'[None - No vendor]': None}
                vendor_options.update({v['name']: v['id'] for v in vendors})
                selected_vendor_label = st.selectbox("Assign to Vendor", list(vendor_options.keys()))
                selected_vendor_id = vendor_options[selected_vendor_label]
            else:
                st.info("No vendors available")
                selected_vendor_id = None

        with col2:
            # Duplicate handling
            duplicate_strategy = st.radio(
                "Handle Duplicates (by email)",
                [
                    "Skip (keep existing)",
                    "Update (merge with existing)",
                    "Create anyway (allow duplicates)"
                ],
                help="How to handle candidates with matching email addresses"
            )

            # Map radio selection to strategy code
            if "Skip" in duplicate_strategy:
                on_duplicate = 'skip'
            elif "Update" in duplicate_strategy:
                on_duplicate = 'update'
            else:
                on_duplicate = 'create'

        st.divider()

        # ============ STEP 5: EXECUTE IMPORT ============
        step_html = """
        <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                    border-left: 4px solid #304CB2;
                    border-radius: 8px;
                    padding: 16px 20px;
                    margin: 20px 0;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="background: #304CB2; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center; font-weight: 600;">5</div>
                <h3 style="margin: 0; color: #FFFFFF;">Execute Import</h3>
            </div>
        </div>
        """
        st.markdown(step_html, unsafe_allow_html=True)

        # Check if validation passed
        can_import = True
        if st.session_state.import_validation:
            validation = st.session_state.import_validation
            if validation['invalid_rows'] > 0:
                st.warning(f"⚠️ There are {validation['invalid_rows']} invalid rows. These will be skipped during import.")

        # Import button
        if st.button("🚀 Start Import", type="primary", use_container_width=True, disabled=not can_import):
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            def progress_callback(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processing row {current} of {total}...")

            with st.spinner("Importing candidates..."):
                try:
                    results = bulk_create_candidates(
                        df=df,
                        mapping=mapping,
                        job_id=selected_job_id,
                        vendor_id=selected_vendor_id,
                        on_duplicate=on_duplicate,
                        progress_callback=progress_callback
                    )

                    # Clear progress
                    progress_bar.empty()
                    status_text.empty()

                    # Show results - Premium KPI Row
                    st.success("✅ Import completed!")

                    kpi_items = [
                        {"label": "Created", "value": results['created'], "icon": "&#10004;", "color": "#2EA043"},
                        {"label": "Updated", "value": results['updated'], "icon": "&#128260;", "color": "#304CB2"},
                        {"label": "Skipped", "value": results['skipped'], "icon": "&#10145;", "color": "#F9B612"},
                        {"label": "Failed", "value": results['failed'], "icon": "&#10060;", "color": "#C8102E"}
                    ]
                    st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

                    # Show failed rows if any
                    if results['failed_rows']:
                        with st.expander(f"❌ Failed Rows ({len(results['failed_rows'])})", expanded=True):
                            for row_index, row_data, errors in results['failed_rows'][:20]:
                                st.error(f"**Row {row_index}:** {safe(row_data.get('name', 'Unknown'))} - {'; '.join(safe(e) for e in errors)}")

                            if len(results['failed_rows']) > 20:
                                st.caption(f"... and {len(results['failed_rows']) - 20} more failed rows")

                        # Generate error report
                        st.markdown("**Download Error Report**")
                        error_csv = generate_error_report(results['failed_rows'])

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="📥 Download Error Report (CSV)",
                            data=error_csv,
                            file_name=f"import_errors_{timestamp}.csv",
                            mime="text/csv"
                        )

                    # Clear session state to allow new import
                    if st.button("🔄 Import Another File"):
                        st.session_state.import_df = None
                        st.session_state.import_mapping = {}
                        st.session_state.import_validation = None
                        st.rerun()

                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"Import failed: {str(e)}")

    else:
        # Show instructions when no file uploaded
        st.markdown(empty_state("Upload a CSV or Excel file to begin", "Drag and drop or click to browse", "&#128190;"), unsafe_allow_html=True)

        st.markdown("### 📋 File Format Guidelines")

        st.markdown("""
        **Required columns:**
        - Full Name (required)

        **Optional columns:**
        - Email Address
        - Phone Number
        - Resume Text
        - Notes

        **Example CSV format:**
        ```
        Full Name,Email Address,Phone Number,Resume Text,Notes
        John Doe,john@example.com,555-1234,Experienced developer...,"Great candidate"
        Jane Smith,jane@example.com,555-5678,Senior engineer...,"Needs follow-up"
        ```

        **Tips:**
        - First row must contain column headers
        - Column names will be auto-detected (e.g., "name", "full name", "candidate name" all work)
        - Emails are used to detect duplicates
        - CSV files should be UTF-8 encoded
        - Excel files (.xlsx) are also supported
        """)

        # Show sample data
        with st.expander("📄 View Sample CSV"):
            sample_data = {
                'Full Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
                'Email Address': ['john@example.com', 'jane@example.com', 'bob@example.com'],
                'Phone Number': ['555-1234', '555-5678', '555-9012'],
                'Resume Text': [
                    '5+ years Python development...',
                    '10+ years Java experience...',
                    'Full-stack developer with...'
                ],
                'Notes': ['Great communication', 'Strong technical skills', 'Team player']
            }
            sample_df = pd.DataFrame(sample_data)
            st.dataframe(sample_df, use_container_width=True)

            # Provide download for sample
            import io
            csv_buffer = io.StringIO()
            sample_df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')

            st.download_button(
                label="📥 Download Sample CSV",
                data=csv_bytes,
                file_name="sample_import.csv",
                mime="text/csv"
            )
