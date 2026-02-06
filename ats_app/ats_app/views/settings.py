"""
Settings view - User management, email automation, notifications, and system settings
"""
import streamlit as st
from datetime import datetime, timedelta
from database import (
    get_users, create_user, get_user, update_user, activate_user, deactivate_user,
    USER_ROLES, get_automation_rules, create_automation_rule, get_automation_rule,
    update_automation_rule, delete_automation_rule, get_email_queue, get_email_templates,
    cancel_pending_email, reset_failed_email, get_webhooks, create_webhook,
    get_webhook, update_webhook, delete_webhook, get_notification_settings,
    update_notification_setting, STAGES
)
from email_automation import (
    process_email_queue, get_automation_summary, validate_automation_rule,
    get_stage_transitions
)
from notifications import send_slack_notification, send_teams_notification, format_test_notification
from auth import get_current_user, has_permission, is_admin
from views.utils import safe, section_header, avatar_badge, status_badge, kpi_row, empty_state


def render_settings():
    """
    Render the settings view showing:
    - User management
    - Email automation rules
    - Email queue management
    - Notification webhooks
    - Email templates
    """
    st.markdown(section_header("Settings", "System configuration"), unsafe_allow_html=True)

    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to access settings")
        return

    # Check permissions
    if not has_permission('settings', 'view'):
        st.error("You don't have permission to access settings")
        return

    # ============ TABS ============
    tabs = []
    tab_functions = []

    # User Management (admin only)
    if is_admin():
        tabs.append("👥 Users")
        tab_functions.append(render_user_management)

    # Email Automation (admin and recruiter)
    if has_permission('settings', 'manage_automation'):
        tabs.append("📧 Email Automation")
        tab_functions.append(render_email_automation)

    # Email Queue
    if has_permission('settings', 'view'):
        tabs.append("📬 Email Queue")
        tab_functions.append(render_email_queue)

    # Notifications (admin only)
    if is_admin():
        tabs.append("🔔 Notifications")
        tab_functions.append(render_notifications)

    if not tabs:
        st.warning("No settings sections available for your role")
        return

    # Create tabs
    tab_objects = st.tabs(tabs)

    # Render each tab
    for tab_obj, tab_func in zip(tab_objects, tab_functions):
        with tab_obj:
            tab_func()


def render_user_management():
    """User management section - admin only"""
    st.subheader("User Management")

    # ============ USER LIST ============
    st.markdown("### 👥 Current Users")

    users = get_users(active_only=False)

    if users:
        for user in users:
            role_badge_html = status_badge(user['role'], '#304CB2' if user['role'] == 'admin' else '#6E7681')
            status_text = "Active" if user['is_active'] else "Inactive"
            status_color = "#2EA043" if user['is_active'] else "#C8102E"

            with st.expander(f"{safe(user['name'])} - {user['role']}", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(avatar_badge(user['name'], user['email']), unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top: 12px;'>{role_badge_html} {status_badge(status_text, status_color)}</div>", unsafe_allow_html=True)
                    st.caption(f"Created: {user['created_at']}")

                with col2:
                    st.markdown("**Actions**")

                    # Edit role
                    with st.form(f"edit_role_{user['id']}"):
                        new_role = st.selectbox(
                            "Change Role",
                            USER_ROLES,
                            index=USER_ROLES.index(user['role']),
                            key=f"role_{user['id']}"
                        )

                        if st.form_submit_button("Update Role"):
                            try:
                                update_user(user['id'], role=new_role)
                                st.success(f"Updated role to {new_role}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update role: {str(e)}")

                    # Activate/Deactivate
                    if user['is_active']:
                        if st.button("🚫 Deactivate", key=f"deactivate_{user['id']}", use_container_width=True):
                            try:
                                deactivate_user(user['id'])
                                st.success(f"Deactivated user {user['name']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to deactivate: {str(e)}")
                    else:
                        if st.button("✅ Activate", key=f"activate_{user['id']}", use_container_width=True):
                            try:
                                activate_user(user['id'])
                                st.success(f"Activated user {user['name']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to activate: {str(e)}")
    else:
        st.info("No users found")

    st.divider()

    # ============ CREATE NEW USER ============
    st.markdown("### ➕ Create New User")

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_email = st.text_input("Email", key="new_user_email")
            new_name = st.text_input("Full Name", key="new_user_name")

        with col2:
            new_role = st.selectbox("Role", USER_ROLES, key="new_user_role")

            # Show role descriptions
            role_descriptions = {
                'admin': 'Full access to all features',
                'recruiter': 'Manage candidates, jobs, vendors',
                'hiring_manager': 'View assigned jobs and candidates',
                'interviewer': 'View interviews and submit scorecards'
            }
            st.caption(role_descriptions.get(new_role, ''))

        submitted = st.form_submit_button("Create User", type="primary", use_container_width=True)

        if submitted:
            if not new_email or not new_name:
                st.error("Email and name are required")
            elif '@' not in new_email:
                st.error("Invalid email format")
            else:
                try:
                    user_id = create_user(email=new_email, name=new_name, role=new_role)
                    st.success(f"✅ Created user: {new_name} (ID: {user_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create user: {str(e)}")


def render_email_automation():
    """Email automation rules section"""
    st.subheader("Email Automation Rules")

    # ============ EXISTING RULES ============
    st.markdown("### 📋 Automation Rules")

    rules = get_automation_rules()

    if rules:
        for rule in rules:
            status = "✅ Enabled" if rule.get('is_enabled') else "❌ Disabled"
            job_name = rule.get('job_title', 'All Jobs (Global)')

            with st.expander(f"{status} - {safe(rule['from_stage'])} → {safe(rule['to_stage'])} ({safe(job_name)})"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**From Stage:** {rule['from_stage']}")
                    st.markdown(f"**To Stage:** {rule['to_stage']}")
                    st.markdown(f"**Template:** {rule['template_name']}")
                    st.markdown(f"**Job:** {job_name}")
                    st.markdown(f"**Delay:** {rule.get('delay_minutes', 0)} minutes")
                    st.markdown(f"**Status:** {'Enabled' if rule.get('is_enabled') else 'Disabled'}")

                with col2:
                    st.markdown("**Actions**")

                    # Toggle enabled/disabled
                    if rule.get('is_enabled'):
                        if st.button("⏸️ Disable", key=f"disable_rule_{rule['id']}", use_container_width=True):
                            try:
                                update_automation_rule(rule['id'], is_enabled=0)
                                st.success("Rule disabled")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to disable: {str(e)}")
                    else:
                        if st.button("▶️ Enable", key=f"enable_rule_{rule['id']}", use_container_width=True):
                            try:
                                update_automation_rule(rule['id'], is_enabled=1)
                                st.success("Rule enabled")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to enable: {str(e)}")

                    # Delete rule
                    if st.button("🗑️ Delete", key=f"delete_rule_{rule['id']}", use_container_width=True):
                        try:
                            delete_automation_rule(rule['id'])
                            st.success("Rule deleted")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {str(e)}")
    else:
        st.info("No automation rules configured")

    st.divider()

    # ============ CREATE NEW RULE ============
    st.markdown("### ➕ Create Automation Rule")

    with st.form("create_automation_rule"):
        col1, col2 = st.columns(2)

        with col1:
            # Job selection (optional - None means global)
            from database import get_jobs
            jobs = get_jobs()
            job_options = {"All Jobs (Global)": None}
            if jobs:
                job_options.update({j['title']: j['id'] for j in jobs})

            selected_job_label = st.selectbox("Apply to Job", list(job_options.keys()))
            selected_job_id = job_options[selected_job_label]

            # Stage transition
            transitions = get_stage_transitions()
            transition_options = {t['label']: (t['from_stage'], t['to_stage']) for t in transitions}

            selected_transition = st.selectbox("Stage Transition", list(transition_options.keys()))
            from_stage, to_stage = transition_options[selected_transition]

        with col2:
            # Template selection
            templates = get_email_templates()
            if templates:
                template_options = {t['name']: t['id'] for t in templates}
                selected_template = st.selectbox("Email Template", list(template_options.keys()))
                selected_template_id = template_options[selected_template]
            else:
                st.warning("No email templates available")
                selected_template_id = None

            # Delay
            delay_minutes = st.number_input(
                "Delay (minutes)",
                min_value=0,
                max_value=1440,
                value=0,
                help="Delay before sending email (0 = immediate)"
            )

        submitted = st.form_submit_button("Create Rule", type="primary", use_container_width=True)

        if submitted:
            if not selected_template_id:
                st.error("Please create an email template first")
            else:
                try:
                    # Validate rule
                    is_valid, error_msg = validate_automation_rule(from_stage, to_stage, selected_template_id)

                    if not is_valid:
                        st.error(f"Invalid rule: {error_msg}")
                    else:
                        rule_id = create_automation_rule(
                            job_id=selected_job_id,
                            from_stage=from_stage,
                            to_stage=to_stage,
                            template_id=selected_template_id,
                            delay_minutes=delay_minutes
                        )
                        st.success(f"✅ Created automation rule (ID: {rule_id})")
                        st.rerun()

                except Exception as e:
                    st.error(f"Failed to create rule: {str(e)}")


def render_email_queue():
    """Email queue management section"""
    st.subheader("Email Queue")

    # ============ QUEUE SUMMARY ============
    try:
        summary = get_automation_summary()
        stats = summary.get('stats', {})

        kpi_items = [
            {"label": "Pending", "value": stats.get('pending_count', 0), "icon": "&#9200;", "color": "#F9B612"},
            {"label": "Sent Today", "value": stats.get('sent_today', 0), "icon": "&#10003;", "color": "#2EA043"},
            {"label": "Failed", "value": stats.get('failed_count', 0), "icon": "&#10005;", "color": "#C8102E"},
            {"label": "Total Sent", "value": stats.get('total_sent', 0), "icon": "&#128231;", "color": "#304CB2"}
        ]

        st.markdown(kpi_row(kpi_items), unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Failed to load queue summary: {str(e)}")

    # ============ PROCESS QUEUE BUTTON ============
    if st.button("⚡ Process Email Queue Now", type="primary", use_container_width=True):
        with st.spinner("Processing email queue..."):
            try:
                result = process_email_queue()

                st.success(f"✅ Processed {result['processed']} emails")
                st.info(f"Sent: {result['sent']}, Failed: {result['failed']}")

                if result.get('errors'):
                    with st.expander("⚠️ View Errors"):
                        for error in result['errors']:
                            st.error(f"Queue ID {error['queue_id']}: {error['error']}")

                st.rerun()

            except Exception as e:
                st.error(f"Failed to process queue: {str(e)}")

    st.divider()

    # ============ PENDING EMAILS ============
    st.markdown("### ⏳ Pending Emails")

    try:
        pending_emails = get_email_queue(status='pending', limit=20)

        if pending_emails:
            for email in pending_emails:
                scheduled_time = email.get('scheduled_at', '')
                try:
                    dt = datetime.fromisoformat(scheduled_time)
                    time_str = dt.strftime("%b %d, %I:%M %p")
                except:
                    time_str = scheduled_time

                with st.expander(f"To: {safe(email.get('to_email'))} - {time_str}"):
                    st.markdown(f"**Candidate:** {email.get('candidate_name', 'Unknown')}")
                    st.markdown(f"**Subject:** {email.get('subject')}")
                    st.markdown(f"**Scheduled:** {time_str}")

                    if st.button("❌ Cancel", key=f"cancel_{email['id']}"):
                        try:
                            cancel_pending_email(email['id'])
                            st.success("Email cancelled")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to cancel: {str(e)}")
        else:
            st.info("No pending emails")

    except Exception as e:
        st.error(f"Failed to load pending emails: {str(e)}")

    st.divider()

    # ============ FAILED EMAILS ============
    st.markdown("### ❌ Failed Emails")

    try:
        failed_emails = get_email_queue(status='failed', limit=20)

        if failed_emails:
            for email in failed_emails:
                with st.expander(f"To: {safe(email.get('to_email'))} - Failed"):
                    st.markdown(f"**Candidate:** {email.get('candidate_name', 'Unknown')}")
                    st.markdown(f"**Subject:** {email.get('subject')}")
                    st.markdown(f"**Error:** {email.get('error_message', 'Unknown error')}")

                    if st.button("🔄 Retry", key=f"retry_{email['id']}"):
                        try:
                            reset_failed_email(email['id'])
                            st.success("Email queued for retry")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to retry: {str(e)}")
        else:
            st.info("No failed emails")

    except Exception as e:
        st.error(f"Failed to load failed emails: {str(e)}")


def render_notifications():
    """Notification webhooks section - admin only"""
    st.subheader("Notification Webhooks")

    # ============ EXISTING WEBHOOKS ============
    st.markdown("### 🔔 Configured Webhooks")

    try:
        webhooks = get_webhooks()

        if webhooks:
            for webhook in webhooks:
                platform = webhook.get('platform', 'unknown')
                icon = "💬" if platform == 'slack' else "👥" if platform == 'teams' else "🔔"
                status = "✅ Active" if webhook.get('is_active') else "❌ Inactive"

                with st.expander(f"{icon} {platform.upper()} - {safe(webhook.get('channel_name', 'No channel'))} - {status}"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Platform:** {platform}")
                        st.markdown(f"**Channel:** {webhook.get('channel_name', 'N/A')}")
                        st.markdown(f"**Job:** {webhook.get('job_title', 'All Jobs (Global)')}")
                        st.markdown(f"**Webhook URL:** `{webhook.get('webhook_url', '')[:50]}...`")

                        if webhook.get('last_success'):
                            st.markdown(f"**Last Success:** {webhook.get('last_success')}")
                        if webhook.get('last_failure'):
                            st.markdown(f"**Last Failure:** {webhook.get('last_failure')}")

                    with col2:
                        st.markdown("**Actions**")

                        # Test webhook
                        if st.button("🧪 Test", key=f"test_webhook_{webhook['id']}", use_container_width=True):
                            try:
                                test_payload = format_test_notification()

                                if platform == 'slack':
                                    send_slack_notification(webhook['webhook_url'], test_payload)
                                elif platform == 'teams':
                                    send_teams_notification(webhook['webhook_url'], test_payload)

                                st.success("Test notification sent!")

                            except Exception as e:
                                st.error(f"Test failed: {str(e)}")

                        # Toggle active
                        if webhook.get('is_active'):
                            if st.button("⏸️ Deactivate", key=f"deactivate_webhook_{webhook['id']}", use_container_width=True):
                                try:
                                    update_webhook(webhook['id'], is_active=0)
                                    st.success("Webhook deactivated")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {str(e)}")
                        else:
                            if st.button("▶️ Activate", key=f"activate_webhook_{webhook['id']}", use_container_width=True):
                                try:
                                    update_webhook(webhook['id'], is_active=1)
                                    st.success("Webhook activated")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed: {str(e)}")

                        # Delete
                        if st.button("🗑️ Delete", key=f"delete_webhook_{webhook['id']}", use_container_width=True):
                            try:
                                delete_webhook(webhook['id'])
                                st.success("Webhook deleted")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {str(e)}")
        else:
            st.info("No webhooks configured")

    except Exception as e:
        st.error(f"Failed to load webhooks: {str(e)}")

    st.divider()

    # ============ CREATE NEW WEBHOOK ============
    st.markdown("### ➕ Create Notification Webhook")

    with st.form("create_webhook_form"):
        col1, col2 = st.columns(2)

        with col1:
            platform = st.selectbox("Platform", ["slack", "teams"])

            webhook_url = st.text_input(
                "Webhook URL",
                help="Get this from your Slack or Teams admin panel"
            )

            channel_name = st.text_input(
                "Channel Name",
                placeholder="#hiring or Hiring Channel"
            )

        with col2:
            # Job selection (optional)
            from database import get_jobs
            jobs = get_jobs()
            job_options = {"All Jobs (Global)": None}
            if jobs:
                job_options.update({j['title']: j['id'] for j in jobs})

            selected_job_label = st.selectbox("Notifications for Job", list(job_options.keys()))
            selected_job_id = job_options[selected_job_label]

            st.markdown("**Events to notify:**")
            notify_new_candidate = st.checkbox("New candidate added", value=True)
            notify_stage_change = st.checkbox("Candidate stage change", value=True)
            notify_interview = st.checkbox("Interview scheduled", value=True)

        submitted = st.form_submit_button("Create Webhook", type="primary", use_container_width=True)

        if submitted:
            if not webhook_url:
                st.error("Webhook URL is required")
            else:
                try:
                    webhook_id = create_webhook(
                        platform=platform,
                        webhook_url=webhook_url,
                        channel_name=channel_name,
                        job_id=selected_job_id
                    )

                    # Update notification settings
                    if notify_new_candidate:
                        update_notification_setting(webhook_id, 'new_candidate', is_enabled=1)
                    if notify_stage_change:
                        update_notification_setting(webhook_id, 'stage_change', is_enabled=1)
                    if notify_interview:
                        update_notification_setting(webhook_id, 'interview_scheduled', is_enabled=1)

                    st.success(f"✅ Created webhook (ID: {webhook_id})")
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to create webhook: {str(e)}")
