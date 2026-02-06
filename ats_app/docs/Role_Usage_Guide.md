# Agentic Program ATS - Role-by-Role Usage Guide

## Overview

The Agentic Program ATS provides tailored experiences based on your role. This guide explains what each role can do and how to accomplish common tasks.

---

## Role Permissions Matrix

| Feature | Admin | Recruiter | Hiring Manager | Interviewer |
|---------|:-----:|:---------:|:--------------:|:-----------:|
| View Dashboard | Yes | Yes | Yes (filtered) | Yes (limited) |
| View All Candidates | Yes | Yes | No | No |
| View Assigned Candidates | Yes | Yes | Yes | Yes |
| Create Candidates | Yes | Yes | No | No |
| Edit Candidates | Yes | Yes | Yes (own jobs) | No |
| Move Pipeline Stage | Yes | Yes | Yes (own jobs) | No |
| View All Jobs | Yes | Yes | No | No |
| Create Jobs | Yes | Yes | No | No |
| Edit Jobs | Yes | Yes | No | No |
| Bulk Import | Yes | Yes | No | No |
| Schedule Interviews | Yes | Yes | Yes | No |
| Submit Scorecards | Yes | Yes | Yes | Yes |
| View Analytics | Yes | Yes | Yes (filtered) | No |
| Manage Users | Yes | No | No | No |
| Configure Webhooks | Yes | Yes | No | No |

---

# Administrator Guide

## Login
- **Email**: admin@agentic.com
- **Access Level**: Full system access

## Key Responsibilities
1. User management and role assignments
2. System configuration (webhooks, settings)
3. Job and hiring manager assignments
4. Overall pipeline oversight

## Common Tasks

### Add a New User
1. Navigate to **Settings**
2. Scroll to **User Management**
3. Click **Add User**
4. Enter email, name, and select role
5. Click **Create User**

### Assign Hiring Manager to Job
1. Navigate to **Jobs**
2. Expand the job you want to configure
3. Scroll to **Hiring Managers** section
4. Select a user from the dropdown
5. Click **Assign**

### Configure Slack/Teams Notifications
1. Navigate to **Settings**
2. Find **Notification Webhooks** section
3. Click **Add Webhook**
4. Enter webhook URL and select platform (Slack/Teams)
5. Choose which events trigger notifications
6. Click **Save**

### View System-Wide Analytics
1. Navigate to **Analytics**
2. Set job filter to **All Jobs**
3. Review tabs:
   - **Pipeline Health**: Overall funnel metrics
   - **Time-to-Hire**: Velocity tracking
   - **Vendor Scorecards**: Agency performance

---

# Recruiter Guide

## Login
- **Email**: recruiter@agentic.com
- **Access Level**: All candidates and jobs (no user management)

## Key Responsibilities
1. Source and add candidates
2. Initial resume screening
3. Pipeline management
4. Vendor coordination
5. Bulk candidate imports

## Common Tasks

### Add a Single Candidate
1. Navigate to **Candidates**
2. Click **Add Candidate**
3. Fill in required fields:
   - Name, Email, Phone
   - Select Job and Vendor
   - Paste or upload resume
4. Click **Create Candidate**
5. System will auto-score resume with AI

### Bulk Import Candidates
1. Navigate to **Bulk Import**
2. Download the CSV template (optional)
3. Upload your CSV or Excel file
4. Map columns to fields (auto-detected)
5. Review validation results
6. Click **Import** to create candidates

### Screen a Candidate (Resume Review)
1. Navigate to **Candidates**
2. Click on a candidate in "Resume Screen" stage
3. Review:
   - AI Resume Score (0-100%)
   - Strengths and Gaps analysis
   - Full resume text
4. Decision:
   - **Advance**: Move to "Phone Screen"
   - **Reject**: Move to "Rejected" with notes

### Move Candidate Through Pipeline
1. Open candidate profile
2. Find **Stage** dropdown
3. Select new stage
4. Add notes explaining the decision
5. Click **Update**

### Schedule an Interview
1. Open candidate profile
2. Click **Schedule Interview**
3. Fill in:
   - Interview stage (Phone/Technical/Behavioral)
   - Interviewer name and email
   - Date, time, duration
   - Location or video link
4. Click **Schedule**
5. Optionally generate calendar invite (ICS)

### Generate Mobile Scorecard Link
1. Open candidate profile or interview
2. Find **Generate Scorecard Link**
3. Enter interviewer email
4. Click **Generate**
5. Copy and share the link with interviewer
6. Link expires in 48 hours

### Compare Candidates
1. Navigate to **Candidates**
2. Check the boxes next to 2-4 candidates
3. Click **Compare Selected**
4. Review side-by-side comparison
5. View AI recommendation (if available)

---

# Hiring Manager Guide

## Login
- **Email**: hiring.manager@agentic.com
- **Access Level**: Only jobs assigned to you and their candidates

## Key Responsibilities
1. Review candidates for your open roles
2. Conduct or coordinate interviews
3. Make hiring decisions
4. Provide interview feedback

## What You'll See
- **Dashboard**: Shows only YOUR jobs and candidates
- **Candidates**: Filtered to candidates for your jobs
- **Jobs**: Only jobs where you're assigned as owner
- **Analytics**: Metrics for your jobs only

## Common Tasks

### Review Your Pipeline
1. Navigate to **Dashboard**
2. View funnel showing your candidates by stage
3. Click on any stage number to see those candidates

### Review a Candidate
1. Navigate to **Candidates**
2. Click on a candidate name
3. Review:
   - Resume and AI analysis
   - Interview history and scores
   - Previous stage notes
4. Add your own notes if needed

### Advance or Reject a Candidate
1. Open candidate profile
2. Change **Stage** dropdown to new stage
3. Add notes explaining your decision
4. Click **Update**

### Submit Interview Feedback
**Option A: In-App**
1. Open candidate profile
2. Find the interview record
3. Click **Add Scores**
4. Rate each criterion
5. Add written feedback
6. Select recommendation (Strong Yes/Yes/Maybe/No/Strong No)
7. Click **Submit**

**Option B: Mobile Scorecard**
1. Open the scorecard link sent to you
2. Review candidate info
3. Enter your feedback and scores
4. Select recommendation
5. Click **Submit Feedback**

### View Interview Questions
1. Open candidate profile
2. Click **Generate Interview Questions**
3. Select interview stage
4. Review AI-generated questions tailored to:
   - Job requirements
   - Candidate's resume
   - Previous interview feedback

---

# Interviewer Guide

## Login
- **Email**: interviewer@agentic.com
- **Access Level**: View-only, primarily uses mobile scorecards

## Key Responsibilities
1. Conduct interviews
2. Submit feedback via scorecards

## Primary Workflow: Mobile Scorecard

### Using a Scorecard Link
1. **Receive link** via email or Slack from recruiter/hiring manager
2. **Open link** on any device (phone, tablet, computer)
3. **Review candidate info** displayed at top:
   - Name and role
   - Interview stage
   - Key background info
4. **Enter feedback**:
   - Score each criterion (if applicable)
   - Write detailed notes
   - Select overall recommendation
5. **Submit** your feedback
6. **Confirmation** appears when saved

### Recommendation Options
| Option | When to Use |
|--------|-------------|
| **Strong Yes** | Exceptional candidate, hire immediately |
| **Yes** | Good candidate, recommend advancing |
| **Maybe** | Mixed signals, needs more evaluation |
| **No** | Does not meet requirements |
| **Strong No** | Significant concerns, do not advance |

### Tips for Good Feedback
- Be specific with examples
- Note both strengths and concerns
- Mention specific skills validated
- Flag any red flags clearly
- Your notes will be summarized by AI for the next interviewer

---

## Quick Reference: Navigation

### Sidebar Menu (varies by role)
| Menu Item | Purpose |
|-----------|---------|
| Dashboard | Pipeline overview and metrics |
| Candidates | Browse and manage candidates |
| Bulk Import | CSV/Excel candidate upload |
| Jobs | Manage job postings |
| Contractors | Active contractor tracking |
| Contractor Roles | Rate range definitions |
| Vendors | Staffing agency management |
| Scheduling | Interview calendar |
| Analytics | Reports and metrics |
| Settings | System configuration |

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Refresh page | F5 or Ctrl+R |
| Hard refresh | Ctrl+Shift+R |

---

## Getting Help

### Common Issues

**Can't see candidates/jobs?**
- Check you're logged in as the correct user
- Hiring Managers only see assigned jobs
- Try refreshing the page

**Scorecard link not working?**
- Links expire after 48 hours
- Request a new link from recruiter

**AI features not working?**
- Check AI Backend Status in sidebar
- If showing "Mock", AI key not configured

**Page appears blank?**
- Clear browser cache (Ctrl+Shift+R)
- Check for errors in browser console (F12)

---

## Workflow Diagrams

### Candidate Lifecycle
```
┌──────────────┐
│   Sourced    │  (Recruiter adds candidate)
└──────┬───────┘
       ▼
┌──────────────┐
│Resume Screen │  (AI scores, Recruiter reviews)
└──────┬───────┘
       ▼
┌──────────────┐
│ Phone Screen │  (Recruiter/HM conducts)
└──────┬───────┘
       ▼
┌──────────────┐
│  Technical   │  (Technical interviewer)
│  Interview   │
└──────┬───────┘
       ▼
┌──────────────┐
│  Behavioral  │  (Hiring Manager)
│  Interview   │
└──────┬───────┘
       ▼
┌──────────────┐
│    Offer     │  (HM decision)
└──────┬───────┘
       ▼
┌──────────────┐
│Hired/Rejected│
└──────────────┘
```

### Interview Feedback Flow
```
┌────────────────┐
│ Recruiter      │
│ schedules      │
│ interview      │
└───────┬────────┘
        ▼
┌────────────────┐
│ Generates      │
│ scorecard link │
└───────┬────────┘
        ▼
┌────────────────┐
│ Interviewer    │
│ receives link  │
└───────┬────────┘
        ▼
┌────────────────┐
│ Conducts       │
│ interview      │
└───────┬────────┘
        ▼
┌────────────────┐
│ Submits        │
│ scorecard      │
└───────┬────────┘
        ▼
┌────────────────┐
│ AI summarizes  │
│ for next stage │
└────────────────┘
```

---

*For technical support or feature requests, contact your system administrator.*
