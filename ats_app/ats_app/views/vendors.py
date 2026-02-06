"""
Vendors view - Simple CRUD for vendor management
"""
import streamlit as st
from database import get_vendors, create_vendor, get_vendor, get_candidates
from auth import has_permission, get_current_user
from views.utils import safe


def render_vendors():
    """Render vendor management page"""
    st.title("🏢 Vendors")

    current_user = get_current_user()
    if not current_user:
        st.error("Please log in to access this page")
        return

    # Get all vendors
    vendors = get_vendors()

    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Vendors", len(vendors))
    with col2:
        # Count total candidates from all vendors
        all_candidates = get_candidates()
        vendor_candidates = [c for c in all_candidates if c.get('vendor_id')]
        st.metric("Total Vendor Candidates", len(vendor_candidates))

    st.divider()

    # Create vendor form
    if has_permission('vendors', 'create'):
        with st.expander("➕ Add New Vendor", expanded=False):
            with st.form("create_vendor_form"):
                col1, col2 = st.columns(2)

                with col1:
                    name = st.text_input("Vendor Name*", placeholder="ABC Staffing Agency")
                    contact_email = st.text_input("Contact Email", placeholder="contact@vendor.com")

                with col2:
                    contact_phone = st.text_input("Contact Phone", placeholder="+1-555-0123")
                    notes = st.text_area("Notes", height=80, placeholder="Additional information about the vendor...")

                submitted = st.form_submit_button("Add Vendor", type="primary", use_container_width=True)

                if submitted:
                    if not name:
                        st.error("Vendor name is required")
                    else:
                        vendor_id = create_vendor(
                            name=name,
                            contact_email=contact_email if contact_email else None,
                            contact_phone=contact_phone if contact_phone else None,
                            notes=notes if notes else None
                        )
                        st.success(f"Added vendor: {name}")
                        st.rerun()

    # Vendor list
    st.subheader("All Vendors")

    if not vendors:
        st.info("No vendors found. Add your first vendor using the form above.")
    else:
        # Sort vendors by name
        vendors = sorted(vendors, key=lambda x: x['name'])

        # Search/filter
        search = st.text_input("🔍 Search vendors", placeholder="Type to filter by name or email...")

        if search:
            vendors = [v for v in vendors if
                      search.lower() in v['name'].lower() or
                      (v.get('contact_email') and search.lower() in v['contact_email'].lower())]

        if not vendors:
            st.warning(f"No vendors found matching '{search}'")
        else:
            # Display vendors as cards
            for vendor in vendors:
                render_vendor_card(vendor)


def render_vendor_card(vendor: dict):
    """Render a single vendor card with details"""
    # Count candidates from this vendor
    all_candidates = get_candidates()
    vendor_candidates = [c for c in all_candidates if c.get('vendor_id') == vendor['id']]

    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"### 🏢 {safe(vendor['name'])}")
            if vendor.get('contact_email'):
                st.caption(f"📧 {safe(vendor['contact_email'])}")
            if vendor.get('contact_phone'):
                st.caption(f"📞 {safe(vendor['contact_phone'])}")

        with col2:
            st.metric("Candidates", len(vendor_candidates))

            # Show active vs inactive candidates
            active = len([c for c in vendor_candidates if c.get('status') == 'Active'])
            if active > 0:
                st.caption(f"{active} active")

        with col3:
            if st.button("View Details", key=f"view_vendor_{vendor['id']}", use_container_width=True):
                st.session_state[f'show_vendor_{vendor["id"]}'] = not st.session_state.get(f'show_vendor_{vendor["id"]}', False)
                st.rerun()

        # Expandable details section
        if st.session_state.get(f'show_vendor_{vendor["id"]}'):
            with st.container():
                st.markdown("---")

                # Vendor info
                if vendor.get('notes'):
                    st.markdown("**Notes:**")
                    st.markdown(vendor['notes'])

                st.caption(f"Created: {vendor.get('created_at', 'N/A')}")

                # Candidate list from this vendor
                if vendor_candidates:
                    st.markdown(f"**Candidates from {safe(vendor['name'])}:**")

                    # Group by status
                    active_candidates = [c for c in vendor_candidates if c.get('status') == 'Active']
                    inactive_candidates = [c for c in vendor_candidates if c.get('status') != 'Active']

                    if active_candidates:
                        st.markdown("*Active:*")
                        for candidate in active_candidates[:10]:  # Show first 10
                            stage = candidate.get('current_stage', 'Unknown')
                            st.markdown(f"- {safe(candidate['name'])} ({safe(stage)})")

                        if len(active_candidates) > 10:
                            st.caption(f"...and {len(active_candidates) - 10} more")

                    if inactive_candidates:
                        with st.expander(f"Inactive Candidates ({len(inactive_candidates)})"):
                            for candidate in inactive_candidates:
                                stage = candidate.get('current_stage', 'Unknown')
                                status = candidate.get('status', 'Unknown')
                                st.markdown(f"- {safe(candidate['name'])} ({safe(stage)} - {status})")
                else:
                    st.info("No candidates from this vendor yet")

                # Edit vendor (future enhancement)
                if has_permission('vendors', 'edit'):
                    with st.expander("✏️ Edit Vendor"):
                        with st.form(f"edit_vendor_{vendor['id']}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                name = st.text_input("Vendor Name", value=vendor['name'])
                                contact_email = st.text_input("Contact Email", value=vendor.get('contact_email') or '')

                            with col2:
                                contact_phone = st.text_input("Contact Phone", value=vendor.get('contact_phone') or '')
                                notes = st.text_area("Notes", value=vendor.get('notes') or '', height=80)

                            if st.form_submit_button("Save Changes", type="primary"):
                                # Note: This would require an update_vendor function in database.py
                                st.info("Vendor update functionality coming soon")

        st.divider()
