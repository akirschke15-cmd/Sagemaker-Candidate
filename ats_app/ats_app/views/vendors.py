"""
Vendors view - Simple CRUD for vendor management
"""
import streamlit as st
from database import get_vendors, create_vendor, get_vendor, get_candidates
from auth import has_permission, get_current_user
from views.utils import safe, section_header, kpi_row, avatar_badge, metric_card, empty_state, _clean_html


def render_vendors():
    """Render vendor management page"""
    st.markdown(section_header("Vendors", "Staffing agency management"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.error("Please log in to access this page")
        return

    # Get all vendors
    vendors = get_vendors()

    # OPTIMIZATION: Fetch all candidates once at the top level to avoid N+1 queries
    all_candidates = get_candidates()
    vendor_candidates = [c for c in all_candidates if c.get('vendor_id')]

    kpi_items = [
        {"label": "Total Vendors", "value": len(vendors), "icon": "&#127970;", "color": "#304CB2"},
        {"label": "Total Candidates", "value": len(vendor_candidates), "icon": "&#128100;", "color": "#2EA043"}
    ]

    st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

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
        st.markdown(empty_state("No vendors found", "Add your first vendor using the form above", "&#127970;"), unsafe_allow_html=True)
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
            # Display vendors as cards - pass all_candidates to avoid re-fetching
            for vendor in vendors:
                render_vendor_card(vendor, all_candidates)


def render_vendor_card(vendor: dict, all_candidates: list):
    """Render a single vendor card with details"""
    # OPTIMIZATION: Use pre-fetched candidates instead of calling get_candidates() again
    vendor_candidates = [c for c in all_candidates if c.get('vendor_id') == vendor['id']]
    active = len([c for c in vendor_candidates if c.get('status') == 'Active'])

    # Premium vendor card
    contact_info = ""
    if vendor.get('contact_email'):
        contact_info += f"<div style='color: #8B949E; font-size: 14px; margin-bottom: 4px;'>&#128231; {safe(vendor.get('contact_email'))}</div>"
    if vendor.get('contact_phone'):
        contact_info += f"<div style='color: #8B949E; font-size: 14px;'>&#128222; {safe(vendor.get('contact_phone'))}</div>"

    card_html = f"""
    <div style="background: linear-gradient(135deg, #1A2332 0%, #0F1419 100%);
                border: 1px solid rgba(48, 76, 178, 0.2);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 16px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div style="flex: 1;">
                {avatar_badge(safe(vendor['name']), f"{len(vendor_candidates)} total candidates • {active} active", size='lg')}
                <div style="margin-top: 12px;">
                    {contact_info}
                </div>
            </div>
            <div>
                {metric_card("Candidates", len(vendor_candidates), delta=f"{active} active" if active > 0 else None, icon="&#128100;", color="#304CB2")}
            </div>
        </div>
    </div>
    """

    st.markdown(_clean_html(card_html), unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            pass  # Spacer

        with col2:
            pass  # Spacer

        with col3:
            if st.button("View Details", key=f"view_vendor_{vendor['id']}", use_container_width=True):
                st.session_state[f'show_vendor_{vendor["id"]}'] = not st.session_state.get(f'show_vendor_{vendor["id"]}', False)
                st.rerun()

        # Expandable details section
        if st.session_state.get(f'show_vendor_{vendor["id"]}'):
            with st.container():
                st.markdown("---", unsafe_allow_html=True)

                # Vendor info
                if vendor.get('notes'):
                    st.markdown("**Notes:**", unsafe_allow_html=True)
                    st.markdown(vendor['notes'], unsafe_allow_html=True)

                st.caption(f"Created: {vendor.get('created_at', 'N/A')}")

                # Candidate list from this vendor
                if vendor_candidates:
                    st.markdown(f"**Candidates from {safe(vendor['name'])}:**", unsafe_allow_html=True)

                    # Group by status
                    active_candidates = [c for c in vendor_candidates if c.get('status') == 'Active']
                    inactive_candidates = [c for c in vendor_candidates if c.get('status') != 'Active']

                    if active_candidates:
                        st.markdown("*Active:*", unsafe_allow_html=True)
                        for candidate in active_candidates[:10]:  # Show first 10
                            stage = candidate.get('current_stage', 'Unknown')
                            st.markdown(f"- {safe(candidate['name'])} ({safe(stage)})", unsafe_allow_html=True)

                        if len(active_candidates) > 10:
                            st.caption(f"...and {len(active_candidates) - 10} more")

                    if inactive_candidates:
                        with st.expander(f"Inactive Candidates ({len(inactive_candidates)})"):
                            for candidate in inactive_candidates:
                                stage = candidate.get('current_stage', 'Unknown')
                                status = candidate.get('status', 'Unknown')
                                st.markdown(f"- {safe(candidate['name'])} ({safe(stage)} - {status})", unsafe_allow_html=True)
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
