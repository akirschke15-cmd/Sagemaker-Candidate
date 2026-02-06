# Agentic Program ATS - Feature List

**Version:** 1.0
**Last Updated:** January 31, 2026
**Platform:** Streamlit (Python)
**AI Backend:** Claude API / AWS Bedrock

---

## Table of Contents

1. [Core Candidate Management](#1-core-candidate-management)
2. [Resume Upload & Parsing](#2-resume-upload--parsing)
3. [AI Resume Scoring](#3-ai-resume-scoring)
4. [Multi-Role Matching](#4-multi-role-matching)
5. [Interview Scheduling](#5-interview-scheduling)
6. [Mobile Interview Scorecards](#6-mobile-interview-scorecards)
7. [AI Interview Question Generator](#7-ai-interview-question-generator)
8. [Candidate Comparison View](#8-candidate-comparison-view)
9. [Contractor Roles & Rate Management](#9-contractor-roles--rate-management)
10. [Contractor Lifecycle Tracking](#10-contractor-lifecycle-tracking)
11. [Email Management & Automation](#11-email-management--automation)
12. [Notifications (Slack/Teams)](#12-notifications-slackteams)
13. [Calendar Integration](#13-calendar-integration)
14. [Bulk CSV Import](#14-bulk-csv-import)
15. [Analytics Dashboard](#15-analytics-dashboard)
16. [Role-Based Access Control (RBAC)](#16-role-based-access-control-rbac)
17. [Vendor Management](#17-vendor-management)

---

## 1. Core Candidate Management

**Location:** Candidates view (sidebar)

### Functionality
- **Candidate Profiles**: Store and manage candidate information including name, email, phone, resume text, and metadata
- **Pipeline Stages**: Track candidates through configurable stages:
  - Resume Screen → Phone Screen → Technical Interview → Behavioral Interview → Offer → Hired/Rejected
- **Stage Advancement**: Move candidates forward or reject with one click
- **Stage Scoring**: Score candidates on configurable criteria per stage
- **Interview Notes**: Add timestamped notes with interviewer attribution
- **AI Note Summarization**: Claude summarizes interview notes for quick review

### Key Features
- Filterable candidate list by job, vendor, and stage
- Quick search and sort capabilities
- Candidate detail view with tabbed interface
- Audit trail of all stage changes

---

## 2. Resume Upload & Parsing

**Location:** Candidate creation form, Candidate profile → Resume tab
**Module:** `resume_parser.py`

### Functionality
- **File Upload**: Accept PDF, DOCX, and TXT resume files
- **Auto-Extraction**: Automatically extract text content from uploaded files
- **Text Preview**: Review extracted text before saving
- **Manual Fallback**: Paste resume text manually if parsing fails
- **File Storage**: Store original files in `uploads/resumes/` directory

### Supported Formats
| Format | Library | Features |
|--------|---------|----------|
| PDF | pypdf | Multi-page support, text extraction |
| DOCX | python-docx | Tables, formatted sections |
| TXT | Built-in | Multiple encoding support |

### Error Handling
- Clear error messages for corrupted or password-protected files
- Graceful fallback to manual text entry
- File size validation (max 10MB)

---

## 3. AI Resume Scoring

**Location:** Candidate profile, Bulk operations
**Module:** `genai.py`

### Functionality
- **Automated Scoring**: Claude analyzes resumes against job descriptions
- **Score Range**: 0-100% match score
- **Detailed Analysis**: Strengths, gaps, and hiring recommendation
- **Per-Job Scoring**: Different scores for same candidate across multiple roles

### AI Analysis Output
```
Score: 85%
Analysis: Strong Python background with relevant AWS experience...
Strengths: 8+ years Python, AWS certified, ML experience
Gaps: No Kubernetes experience, limited frontend skills
```

### Backend Options
1. **Claude API (Direct)**: Uses `ANTHROPIC_API_KEY` environment variable
2. **AWS Bedrock**: Falls back to Bedrock if direct API unavailable
3. **Mock Mode**: Keyword-based scoring when no AI available

---

## 4. Multi-Role Matching

**Location:** Candidate profile → Roles tab
**Database:** `candidate_jobs` junction table

### Functionality
- **Multiple Job Associations**: Link one candidate to multiple open positions
- **Independent Tracking**: Separate stage progression per job
- **Per-Role AI Scoring**: Different AI scores based on each job's requirements
- **Role Context**: Notes and interviews tagged with associated role
- **Primary Role**: Designate one role as primary for reporting

### Use Cases
- Candidate fits multiple open positions
- Internal transfers/promotions
- Contractor considering different projects

---

## 5. Interview Scheduling

**Location:** Candidate profile → Schedule tab, Scheduling view
**Database:** `interviews` table

### Functionality
- **Schedule Interviews**: Set date, time, duration, stage
- **Interviewer Assignment**: Assign interviewer with email
- **Meeting Links**: Store video conference URLs
- **Location Support**: Physical or virtual meeting locations
- **Status Tracking**: Scheduled, Completed, Cancelled, No-show

### Interview Details
- Candidate name and current stage
- Job/position being interviewed for
- Interviewer name and contact
- Duration and meeting link
- Previous interview notes for prep

---

## 6. Mobile Interview Scorecards

**Location:** Shareable link (no login required)
**Modules:** `mobile_scorecard.py`, `mobile_scorecard_ui.py`

### Functionality
- **Token-Based Access**: Secure links valid for 48 hours
- **Mobile-Optimized UI**: Large touch targets, responsive design
- **Scoring Interface**: Slider-based scoring for each criterion
- **Recommendation Selection**: Strong Yes / Yes / Maybe / No / Strong No
- **Auto-Save Drafts**: Notes and recommendations save every 5 seconds to localStorage
- **Unsaved Changes Warning**: Browser prompts before closing with unsaved work
- **Draft Restoration**: Reopening link restores previous work

### Workflow
1. Schedule interview in ATS
2. Click "Generate Scorecard Link"
3. Share link with interviewer (email, Slack, etc.)
4. Interviewer completes scorecard on phone
5. Scores saved to database, token invalidated

---

## 7. AI Interview Question Generator

**Location:** Candidate profile → Interview Prep, Scheduling view
**Module:** `genai.py`

### Functionality
- **Stage-Specific Questions**: Different questions for Phone/Technical/Behavioral
- **Resume-Based Probing**: Questions target specific resume claims
- **Gap Analysis**: Identifies areas of concern to explore
- **Previous Feedback Integration**: Later interviews reference earlier notes
- **Question Bank**: Save good questions for reuse

### Question Categories
- **Technical**: Skill validation, problem-solving
- **Behavioral**: STAR format, leadership, conflict resolution
- **Situational**: Hypothetical scenarios
- **Experience**: Deep-dive on past roles
- **Culture Fit**: Values alignment

### Output Format
```
Questions:
1. [Technical] "Describe your experience with async Python..."
   → Probing: Validate claimed asyncio expertise

Areas to Probe:
- 6-month gap between Company A and Company B
- Claims "led team of 10" but title was "Junior Developer"

Resume Concerns:
- Buzzword-heavy descriptions without specifics
- No quantifiable achievements listed
```

---

## 8. Candidate Comparison View

**Location:** Candidates view → Select 2-3 candidates → Compare Selected
**Module:** `comparison_view.py`

### Functionality
- **Side-by-Side View**: Compare 2-3 candidates simultaneously
- **AI Scores**: Visual comparison with winner highlighting
- **Strengths/Gaps**: Bullet-point comparison
- **Rate Analysis**: Expected rate vs role range with "best value" indicator
- **Interview Performance**: Scores by stage with totals
- **AI Verdict**: Claude recommends strongest candidate with reasoning
- **Quick Actions**: Advance or reject directly from comparison view

### Comparison Metrics
| Metric | Display |
|--------|---------|
| AI Resume Score | Progress bar with percentage |
| Days in Pipeline | Number with color coding |
| Expected Rate | Rate with in/out of range indicator |
| Interview Total | Percentage with winner highlight |
| Recommendation | AI-generated with reasoning |

---

## 9. Contractor Roles & Rate Management

**Location:** Contractor Roles view (sidebar)
**Database:** `contractor_roles` table

### Functionality
- **Role Definitions**: Create roles with title and description
- **Rate Ranges**: Set min/max hourly rates per role
- **Job Assignment**: Link jobs to contractor roles
- **Candidate Rates**: Enter expected hourly rate per candidate
- **Rate Flagging**: Auto-flag candidates outside role's range

### Rate Status Indicators
| Status | Color | Meaning |
|--------|-------|---------|
| In Range | Blue (#304CB2) | Rate within min-max |
| Warning | Yellow (#F9B612) | Within 10% of boundary |
| Out of Range | Red (#C8102E) | Above max or below min |

### Dashboard Integration
- Compensation summary showing in/out of range counts
- Breakdown by position with rate ranges

---

## 10. Contractor Lifecycle Tracking

**Location:** Contractors view (sidebar)
**Database:** `contracts`, `compliance_documents` tables

### Functionality

#### Contract Management
- **Create Contracts**: Start date, end date, hourly rate
- **Extension Tracking**: Link extensions to original contracts
- **Status Management**: Active, Completed, Terminated, Extended
- **Expiration Alerts**: 30/60/90 day warnings before contract end

#### Compliance Documents
- **Document Types**: W9, Insurance, NDA, Background Check, I-9, Direct Deposit
- **Status Tracking**: Pending, Received, Verified, Expired
- **Expiry Alerts**: Warning before document expiration
- **Compliance Matrix**: At-a-glance status for all contractors

#### Past Contractor Management
- **Rehire Eligibility**: Flag contractors as eligible/ineligible for rehire
- **Rehire Notes**: Document reasons for eligibility status
- **Re-engage Button**: Quick action to bring back past contractors

### Views
| Tab | Contents |
|-----|----------|
| Active Contracts | Current contracts with days remaining |
| Expiring Soon | Color-coded alerts by urgency |
| Past Contractors | History with rehire status |
| Compliance | Document status matrix |

---

## 11. Email Management & Automation

**Location:** Candidate profile → Email tab, Settings → Email Automation
**Module:** `email_automation.py`

### Email Templates
- **Template Library**: Reusable email templates with variables
- **Variable Substitution**: `{{candidate_name}}`, `{{job_title}}`, etc.
- **Preview**: See rendered email before sending
- **Logging**: All sent emails logged for audit

### Email Automation
- **Stage-Based Rules**: Auto-send emails on stage transitions
- **Configurable Triggers**: From Stage → To Stage → Template
- **Delay Support**: Wait N minutes before sending
- **Per-Job Rules**: Different rules for different positions
- **Global Rules**: Apply to all jobs

### Email Queue
- **Status Tracking**: Pending, Sent, Failed
- **Retry Logic**: Up to 3 retry attempts for failed emails
- **Manual Processing**: "Process Queue Now" button
- **Cancel Pending**: Cancel emails before they send

---

## 12. Notifications (Slack/Teams)

**Location:** Settings → Notifications
**Module:** `notifications.py`

### Functionality
- **Webhook Integration**: Connect Slack and Microsoft Teams
- **Event Triggers**: New candidate, Stage change, Interview scheduled
- **Per-Job Channels**: Route notifications to different channels by job
- **Test Notifications**: Verify webhook configuration
- **Failure Tracking**: Monitor webhook health

### Supported Platforms
| Platform | Format |
|----------|--------|
| Slack | Block Kit messages with attachments |
| Microsoft Teams | Adaptive Cards |

### Event Types
- `new_candidate` - New candidate added to pipeline
- `stage_change` - Candidate advances or is rejected
- `interview_scheduled` - Interview scheduled

---

## 13. Calendar Integration

**Location:** Candidate profile → Schedule tab, Scheduling view
**Module:** `calendar_integration.py`

### Functionality
- **ICS Generation**: Create downloadable calendar files
- **RFC 5545 Compliant**: Works with all major calendar apps
- **Rich Event Details**: Includes candidate info, prep notes, meeting links
- **Reminder**: 15-minute VALARM before interview

### ICS Event Contents
```
Summary: Technical Interview: Jane Doe - Senior Python Developer
Location: https://zoom.us/j/123456
Description:
  Candidate: Jane Doe (jane@example.com)
  Position: Senior Python Developer
  AI Score: 85%
  Prep Notes: Focus on async Python experience...
Reminder: 15 minutes before
```

### Future Phases (Stubs Ready)
- Google Calendar OAuth integration
- Microsoft 365/Outlook OAuth integration
- Automatic event creation on scheduling

---

## 14. Bulk CSV Import

**Location:** Candidates view → Bulk Import
**Module:** `bulk_import.py`

### Functionality
- **File Support**: CSV and Excel (.xlsx, .xls)
- **Column Mapping**: Map CSV columns to system fields
- **Auto-Detection**: Recognize common column names automatically
- **Validation**: Check required fields, email format, phone format
- **Duplicate Detection**: Find existing candidates by email
- **Bulk Assignment**: Assign all imports to a job and vendor

### 5-Step Wizard
1. **Upload**: Select file and preview data
2. **Map Columns**: Match CSV columns to system fields
3. **Validate**: Review errors and duplicates
4. **Configure**: Set job, vendor, duplicate handling
5. **Import**: Execute with progress bar, download error report

### Duplicate Handling Options
- **Skip**: Don't import duplicate rows
- **Update**: Update existing candidate with new data
- **Create**: Create new candidate anyway

---

## 15. Analytics Dashboard

**Location:** Analytics view (sidebar)
**Database:** Various analytics functions in `database.py`

### Dashboard Tabs

#### Pipeline Health
- Funnel visualization by stage
- Pipeline velocity (avg days per stage)
- Color coding: Green (<5 days), Yellow (5-10), Red (>10)

#### Time-to-Hire
- Average, median, min, max days to hire
- Breakdown by job/role
- Trend chart over time

#### Stage Conversion
- Conversion rate between stages
- Drop-off analysis (where rejections happen)
- Progress bar visualizations

#### Vendor Scorecards
- Candidates submitted per vendor
- Hire rate and pass rate
- Average AI score by vendor
- Top performer highlighting

#### AI Calibration
- AI scores for hired vs rejected candidates
- Predictive accuracy metrics
- Score distribution charts
- Calibration recommendations

#### Trends
- Applications vs hires over time
- Configurable period (30/60/90/180 days)
- Weekly summary table

#### Export
- Filter by job and vendor
- Download as CSV

---

## 16. Role-Based Access Control (RBAC)

**Location:** Sidebar user selector, Settings → User Management
**Module:** `auth.py`

### User Roles
| Role | Description |
|------|-------------|
| Admin | Full system access including settings |
| Recruiter | All candidates and jobs, no settings |
| Hiring Manager | Only assigned jobs and their candidates |
| Interviewer | View only, submit scorecards |

### Functionality
- **User Management**: Create, edit, activate/deactivate users
- **Job Ownership**: Assign hiring managers to specific jobs
- **Permission Filtering**: Views automatically filter by access
- **Navigation Control**: Hide inaccessible menu items

### Permission Matrix
| Resource | Admin | Recruiter | Hiring Manager | Interviewer |
|----------|-------|-----------|----------------|-------------|
| Dashboard | Full | Full | Own jobs | View only |
| Candidates | Full | Full | Own jobs | Own interviews |
| Jobs | Full | Full | Own jobs | None |
| Vendors | Full | Full | None | None |
| Settings | Full | None | None | None |
| Users | Full | None | None | None |

### Default Users (Auto-seeded)
- admin@agentic.com (Admin)
- recruiter@agentic.com (Recruiter)
- hiring.manager@agentic.com (Hiring Manager)
- interviewer@agentic.com (Interviewer)

---

## 17. Vendor Management

**Location:** Vendors view (sidebar)

### Functionality
- **Vendor Profiles**: Staffing agency name, contact info, notes
- **Candidate Source Tracking**: Link candidates to their source vendor
- **Vendor Performance**: Track submission and hire rates
- **Active/Inactive Status**: Manage vendor relationships

### Vendor Metrics (in Analytics)
- Candidates submitted
- Candidates hired
- Pass rate percentage
- Average AI score of submissions
- Average days to hire

---

## Technical Specifications

### Tech Stack
- **Frontend**: Streamlit (Python)
- **Database**: SQLite
- **AI**: Claude API (Anthropic) / AWS Bedrock
- **File Storage**: Local filesystem

### Database Tables
| Table | Purpose |
|-------|---------|
| candidates | Core candidate records |
| jobs | Job postings |
| vendors | Staffing agencies |
| candidate_jobs | Multi-role junction |
| interviews | Scheduled interviews |
| stage_scores | Interview scoring |
| stage_notes | Interview notes |
| scoring_criteria | Per-job scoring config |
| contractor_roles | Role rate definitions |
| contracts | Active/past contracts |
| compliance_documents | W9, insurance, etc. |
| users | System users |
| job_owners | RBAC job assignments |
| notification_webhooks | Slack/Teams config |
| notification_settings | Per-webhook settings |
| notification_log | Notification history |
| email_templates | Email template library |
| email_log | Sent email history |
| email_automation_rules | Auto-email rules |
| email_queue | Pending/sent emails |
| scorecard_tokens | Mobile scorecard access |
| saved_questions | Interview question bank |
| calendar_integrations | OAuth tokens (future) |
| calendar_events | Linked calendar events |

### Color Theme (Southwest Airlines)
- **Primary Blue**: #304CB2
- **Accent Red**: #C8102E
- **Highlight Yellow**: #F9B612
- **Success Green**: #2E7D32

---

## Getting Started

### Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...  # For Claude AI features
SMTP_HOST=smtp.example.com    # For email sending
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
```

### First Run
1. Database tables auto-create on startup
2. Default admin user seeded automatically
3. Access at http://localhost:8501

---

*Document generated for Agentic Program ATS v1.0*
