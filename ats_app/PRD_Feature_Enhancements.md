# Product Requirements Document (PRD)
## Agentic Program ATS - Feature Enhancements

**Document Version:** 1.0
**Date:** January 30, 2026
**Product Manager:** Product Manager Agent
**Status:** Draft for Review

---

## Executive Summary

This PRD outlines seven feature enhancements for the Agentic Program ATS, a Streamlit-based applicant tracking system designed for managing contractor hiring pipelines. The current system provides candidate lifecycle management, AI-powered resume scoring via Claude, interview scheduling, and email utilities with a Southwest Airlines-themed UI.

The proposed features will enhance the system's capabilities in document processing, data import, external integrations, mobile accessibility, and role-based access control.

---

## Current System Architecture

### Technology Stack
- **Frontend:** Streamlit (Python-based web framework)
- **Database:** SQLite (`ats_data.db`)
- **AI Integration:** Claude API (Direct) / AWS Bedrock (fallback)
- **Email:** SMTP-based with template rendering

### Existing Database Schema
| Table | Purpose |
|-------|---------|
| `candidates` | Core candidate records with resume_text, resume_path, ai_resume_score |
| `jobs` | Job postings with description, requirements, slots |
| `vendors` | Staffing agencies/recruiters |
| `scoring_criteria` | Per-job, per-stage evaluation criteria |
| `stage_scores` | Actual candidate evaluations |
| `stage_notes` | Interview notes with AI summaries |
| `interviews` | Scheduled interviews |
| `email_templates` | Email templates |
| `email_log` | Sent email history |

### Pipeline Stages
`Resume Screen` -> `Phone Screen` -> `Technical Interview` -> `Behavioral Interview` -> `Offer` -> `Hired` / `Rejected`

---

# Feature 1: Resume File Upload + Parsing

## Overview
Enable users to upload resume files (PDF, DOCX, TXT) directly into the system, with automatic text extraction for AI scoring.

## User Stories

### US-1.1: Upload Resume File
**As a** recruiter
**I want to** upload a resume file for a candidate
**So that** I don't have to manually copy/paste resume text

**Acceptance Criteria:**
```gherkin
Given I am on the candidate creation or edit form
When I click the "Upload Resume" button
And I select a file (PDF, DOCX, or TXT format)
Then the file should be uploaded and stored
And the file name should be displayed in the UI
And the resume text should be automatically extracted
And the extracted text should populate the resume_text field
```

### US-1.2: Parse PDF Resume
**As a** recruiter
**I want** PDF resumes to be automatically parsed
**So that** the text content is available for AI scoring

**Acceptance Criteria:**
```gherkin
Given I upload a PDF resume file
When the upload completes
Then the system should extract all text content from the PDF
And preserve reasonable formatting (paragraphs, sections)
And handle multi-page documents
And display a preview of extracted text for verification
```

### US-1.3: Parse DOCX Resume
**As a** recruiter
**I want** Word document resumes to be automatically parsed
**So that** the text content is available for AI scoring

**Acceptance Criteria:**
```gherkin
Given I upload a DOCX resume file
When the upload completes
Then the system should extract all text content
And preserve document structure where possible
And handle tables and formatted sections
```

### US-1.4: Handle Parse Failures
**As a** recruiter
**I want** clear feedback when resume parsing fails
**So that** I can take corrective action

**Acceptance Criteria:**
```gherkin
Given I upload a resume file
When the parsing fails (corrupted file, password-protected, image-only PDF)
Then the system should display a clear error message
And allow manual text entry as fallback
And still store the original file for reference
```

## Complexity Assessment: **Medium**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Moderate - File uploader widget, preview component |
| Backend Logic | Moderate - File handling, parsing libraries |
| Database Changes | Minimal - resume_path column exists |
| External Dependencies | pypdf, python-docx libraries |
| Testing Effort | Moderate - Various file formats, edge cases |

## Integration Requirements

### Frontend Components
- [ ] `st.file_uploader` widget with accept types [".pdf", ".docx", ".doc", ".txt"]
- [ ] File preview component showing extracted text
- [ ] Error/warning display for parse issues
- [ ] Progress indicator for large files

### API/Functions Needed
```python
# New module: resume_parser.py
def parse_resume(file_bytes: bytes, filename: str) -> Tuple[str, List[str]]:
    """Returns (extracted_text, warnings)"""

def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF"""

def parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX"""

def save_resume_file(candidate_id: int, file_bytes: bytes, filename: str) -> str:
    """Save file to storage, return path"""
```

### Database Schema Changes
- No schema changes required (resume_path column exists)
- Consider adding: `resume_original_filename TEXT` to candidates table

### File Storage
- Create `uploads/resumes/` directory structure
- Filename format: `{candidate_id}_{timestamp}_{original_name}`

## Dependencies
- None (can be implemented independently)

## Vertical Slice Recommendation
Not required - Medium complexity can be delivered in single iteration.

**Suggested Implementation Order:**
1. TXT file support (simplest)
2. DOCX parsing with python-docx
3. PDF parsing with pypdf/pdfplumber
4. Error handling and edge cases
5. File storage management

---

# Feature 2: Bulk CSV Resume/Candidate Import

## Overview
Enable batch import of candidates from CSV/Excel files, including automatic resume text extraction from linked files or embedded content.

## User Stories

### US-2.1: Import Candidates from CSV
**As a** recruiter
**I want to** import multiple candidates from a CSV file
**So that** I can quickly add candidates from vendor submissions

**Acceptance Criteria:**
```gherkin
Given I have a CSV file with candidate information
When I upload the file on the import page
Then the system should parse the CSV
And display a preview of the data with column mapping
And allow me to map CSV columns to candidate fields
And show validation errors for each row
And import valid candidates on confirmation
```

### US-2.2: Column Mapping Interface
**As a** recruiter
**I want to** map CSV columns to system fields
**So that** I can import data regardless of column naming conventions

**Acceptance Criteria:**
```gherkin
Given I have uploaded a CSV file
When the preview screen displays
Then I should see each CSV column header
And a dropdown to map it to system fields (name, email, phone, resume_text, etc.)
And the system should auto-detect common column names
And allow me to skip unmapped columns
```

### US-2.3: Bulk Job Assignment
**As a** recruiter
**I want to** assign all imported candidates to a specific job
**So that** they are immediately associated with the correct position

**Acceptance Criteria:**
```gherkin
Given I am importing candidates via CSV
When I configure the import
Then I should be able to select a target job for all candidates
And optionally select a vendor source
And the assignment should apply to all imported records
```

### US-2.4: Import Validation & Error Report
**As a** recruiter
**I want** detailed validation feedback during import
**So that** I can identify and fix data issues

**Acceptance Criteria:**
```gherkin
Given I submit a CSV for import
When validation runs
Then I should see which rows passed validation
And which rows have errors (with specific error messages)
And be able to download an error report CSV
And choose to import only valid rows
```

### US-2.5: Duplicate Detection
**As a** recruiter
**I want** the system to detect potential duplicate candidates
**So that** I avoid creating duplicate records

**Acceptance Criteria:**
```gherkin
Given I import candidates via CSV
When a candidate matches an existing record (by email)
Then the system should flag it as a potential duplicate
And allow me to skip, update, or create new
And show the existing candidate details for comparison
```

## Complexity Assessment: **Large**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Significant - Multi-step wizard, preview table, mapping UI |
| Backend Logic | Significant - Parsing, validation, duplicate detection |
| Database Changes | Minimal - Uses existing schema |
| External Dependencies | pandas (already imported), openpyxl for Excel |
| Testing Effort | High - Many edge cases, various file formats |

## Integration Requirements

### Frontend Components
- [ ] File uploader for CSV/Excel files
- [ ] Column mapping interface with dropdowns
- [ ] Data preview table with validation status
- [ ] Job/Vendor selection dropdowns
- [ ] Progress bar for bulk operations
- [ ] Error report download button
- [ ] Import summary dialog

### API/Functions Needed
```python
# New module: bulk_import.py
def parse_import_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Parse CSV or Excel file"""

def auto_detect_columns(df: pd.DataFrame) -> Dict[str, str]:
    """Suggest column mappings based on header names"""

def validate_import_row(row: pd.Series, mapping: Dict) -> Tuple[bool, List[str]]:
    """Validate a single row, return (is_valid, errors)"""

def check_duplicate(email: str) -> Optional[Dict]:
    """Check if candidate with email exists"""

def bulk_create_candidates(
    rows: List[Dict],
    job_id: int = None,
    vendor_id: int = None,
    on_duplicate: str = 'skip'
) -> Dict[str, int]:
    """Create candidates in bulk, return counts"""

# Database additions to database.py
def bulk_insert_candidates(candidates: List[Dict]) -> List[int]:
    """Optimized bulk insert returning new IDs"""
```

### Database Schema Changes
- None required
- Consider adding import_batch_id for tracking bulk imports

## Dependencies
- **Feature 1 (Resume Upload)**: If CSV contains resume file paths, parsing capability is needed

## Vertical Slice Phasing

### Phase 1: Basic CSV Import (Week 1)
- CSV file upload
- Basic column mapping (name, email, phone)
- Simple validation (required fields)
- Bulk insert functionality

### Phase 2: Enhanced Mapping & Validation (Week 2)
- Auto-detect column names
- Full field mapping (all candidate fields)
- Email format validation
- Duplicate detection (skip only)

### Phase 3: Advanced Features (Week 3)
- Excel support (.xlsx)
- Update/merge duplicate handling
- Resume text column support
- Error report download
- Import history/audit log

---

# Feature 3: Slack/Teams Notifications

## Overview
Send automated notifications to Slack and/or Microsoft Teams channels for key hiring pipeline events.

## User Stories

### US-3.1: New Candidate Notification
**As a** hiring manager
**I want to** receive a Slack/Teams notification when new candidates are added
**So that** I stay informed without checking the ATS constantly

**Acceptance Criteria:**
```gherkin
Given Slack/Teams integration is configured for a job
When a new candidate is added to that job
Then a notification should be sent to the configured channel
And include candidate name, job title, vendor source, and AI score (if available)
And include a link to view the candidate in the ATS
```

### US-3.2: Stage Advancement Notification
**As a** hiring manager
**I want to** be notified when candidates advance through stages
**So that** I can track pipeline progress

**Acceptance Criteria:**
```gherkin
Given notifications are enabled for stage changes
When a candidate advances to a new stage
Then a notification should be sent
And include the candidate name, previous stage, new stage
And the time since last stage change
```

### US-3.3: Interview Scheduled Notification
**As an** interviewer
**I want to** receive a notification when an interview is scheduled with me
**So that** I can prepare in advance

**Acceptance Criteria:**
```gherkin
Given an interview is scheduled
When the schedule is confirmed
Then the interviewer should receive a notification
And include candidate name, job title, interview stage
And the scheduled date/time
And a link to the candidate profile with prep materials
```

### US-3.4: Configure Notification Channels
**As an** administrator
**I want to** configure which Slack/Teams channels receive notifications
**So that** different teams get relevant updates

**Acceptance Criteria:**
```gherkin
Given I am in the Settings area
When I access the Notifications configuration
Then I can add Slack webhook URLs
And add Teams webhook URLs
And associate channels with specific jobs or all jobs
And enable/disable specific notification types
And test the connection with a sample message
```

### US-3.5: Notification Preferences
**As a** user
**I want to** control which notifications I receive
**So that** I'm not overwhelmed with irrelevant updates

**Acceptance Criteria:**
```gherkin
Given I have notification preferences
When I configure my settings
Then I can enable/disable notification types:
  - New candidates
  - Stage changes
  - Interview scheduled
  - Offer extended
  - Candidate hired
```

## Complexity Assessment: **Medium**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Moderate - Settings UI for webhook configuration |
| Backend Logic | Moderate - Webhook calls, event triggers |
| Database Changes | New tables for webhook config |
| External Dependencies | requests library (HTTP calls) |
| Testing Effort | Moderate - Webhook mocking, event triggers |

## Integration Requirements

### Frontend Components
- [ ] Webhook configuration form (URL, channel name, type)
- [ ] Test notification button
- [ ] Notification type toggles
- [ ] Per-job channel association
- [ ] Webhook status indicators (last success/failure)

### API/Functions Needed
```python
# New module: notifications.py
def send_slack_notification(webhook_url: str, message: Dict) -> bool:
    """Send message to Slack via webhook"""

def send_teams_notification(webhook_url: str, message: Dict) -> bool:
    """Send message to Teams via webhook"""

def format_candidate_notification(candidate: Dict, event_type: str) -> Dict:
    """Format notification payload for candidate events"""

def format_interview_notification(interview: Dict, candidate: Dict) -> Dict:
    """Format notification payload for interview events"""

def trigger_notification(event_type: str, payload: Dict):
    """Main entry point - routes to appropriate channels"""

# Event triggers to add to existing functions:
# - create_candidate() -> trigger 'new_candidate'
# - advance_candidate() -> trigger 'stage_change'
# - schedule_interview() -> trigger 'interview_scheduled'
```

### Database Schema Changes
```sql
CREATE TABLE notification_webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,  -- 'slack' or 'teams'
    webhook_url TEXT NOT NULL,
    channel_name TEXT,
    job_id INTEGER,  -- NULL for all jobs
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE TABLE notification_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- 'new_candidate', 'stage_change', etc.
    is_enabled INTEGER DEFAULT 1,
    FOREIGN KEY (webhook_id) REFERENCES notification_webhooks(id)
);

CREATE TABLE notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id INTEGER,
    event_type TEXT,
    payload TEXT,
    status TEXT,  -- 'sent', 'failed'
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Dependencies
- None (can be implemented independently)

## Vertical Slice Recommendation
Not required - Medium complexity can be delivered in single iteration.

**Suggested Implementation Order:**
1. Slack webhook integration (simpler API)
2. Settings UI for webhook configuration
3. Event trigger points in existing code
4. Teams webhook integration
5. Notification logging and retry logic

---

# Feature 4: Calendar Integration (Google Calendar/Outlook)

## Overview
Integrate with Google Calendar and Microsoft Outlook to create calendar events for scheduled interviews and sync availability.

## User Stories

### US-4.1: Create Calendar Event on Interview Schedule
**As a** recruiter
**I want** a calendar event to be automatically created when I schedule an interview
**So that** interviewers have the meeting on their calendar

**Acceptance Criteria:**
```gherkin
Given calendar integration is configured
When I schedule an interview
Then a calendar event should be created
And the event should include:
  - Interview title with candidate name and stage
  - Meeting link (if provided)
  - Candidate profile link in description
  - Interview prep notes
And the interviewer should receive a calendar invite
And the candidate should optionally receive an invite
```

### US-4.2: Google Calendar Integration
**As an** administrator
**I want to** connect the ATS to Google Calendar
**So that** interview events sync to Google calendars

**Acceptance Criteria:**
```gherkin
Given I am in Settings
When I configure Google Calendar integration
Then I should be able to authenticate via OAuth
And select which calendar to use
And test the connection
And see the integration status
```

### US-4.3: Outlook/Microsoft 365 Integration
**As an** administrator
**I want to** connect the ATS to Microsoft 365 calendars
**So that** interview events sync to Outlook

**Acceptance Criteria:**
```gherkin
Given I am in Settings
When I configure Microsoft 365 integration
Then I should be able to authenticate via OAuth
And select which calendar to use
And test the connection
And see the integration status
```

### US-4.4: Update/Cancel Calendar Events
**As a** recruiter
**I want** calendar events to update when interview details change
**So that** calendars stay synchronized

**Acceptance Criteria:**
```gherkin
Given an interview has a linked calendar event
When I update the interview time or cancel it
Then the calendar event should be updated or deleted accordingly
And attendees should receive update notifications
```

### US-4.5: View Interviewer Availability (Future)
**As a** recruiter
**I want to** see interviewer availability when scheduling
**So that** I can pick times that work

**Acceptance Criteria:**
```gherkin
Given calendar integration is configured
When I am scheduling an interview
Then I should see busy/free times for the interviewer
And be warned if I select a conflicting time
```

## Complexity Assessment: **XL (Extra Large)**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Significant - OAuth flows, calendar picker, availability view |
| Backend Logic | Complex - OAuth token management, API integrations |
| Database Changes | New tables for OAuth tokens, event mapping |
| External Dependencies | Google Calendar API, Microsoft Graph API |
| Testing Effort | High - OAuth flows, API mocking, token refresh |
| Security Considerations | High - Secure token storage, refresh handling |

## Integration Requirements

### Frontend Components
- [ ] OAuth authentication buttons for each provider
- [ ] Calendar selection dropdown
- [ ] Connection status indicators
- [ ] Token refresh/disconnect buttons
- [ ] Availability timeline view (Phase 2)

### API/Functions Needed
```python
# New module: calendar_integration.py
class GoogleCalendarClient:
    def authenticate(self, auth_code: str) -> Dict:
        """Exchange auth code for tokens"""

    def refresh_token(self, refresh_token: str) -> str:
        """Refresh access token"""

    def create_event(self, calendar_id: str, event: Dict) -> str:
        """Create event, return event_id"""

    def update_event(self, calendar_id: str, event_id: str, event: Dict):
        """Update existing event"""

    def delete_event(self, calendar_id: str, event_id: str):
        """Delete event"""

    def get_free_busy(self, calendar_id: str, time_min: str, time_max: str) -> List[Dict]:
        """Get busy periods"""

class OutlookCalendarClient:
    # Similar interface for Microsoft Graph API
    pass

def create_interview_event(interview: Dict, candidate: Dict) -> str:
    """Create calendar event for interview"""

def sync_interview_update(interview_id: int):
    """Sync interview changes to calendar"""
```

### Database Schema Changes
```sql
CREATE TABLE calendar_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,  -- 'google' or 'microsoft'
    user_id TEXT,  -- for multi-user future
    calendar_id TEXT,
    access_token TEXT,  -- encrypted
    refresh_token TEXT,  -- encrypted
    token_expires_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_id INTEGER NOT NULL,
    integration_id INTEGER NOT NULL,
    external_event_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id),
    FOREIGN KEY (integration_id) REFERENCES calendar_integrations(id)
);
```

## Dependencies
- None (can be implemented independently)

## Vertical Slice Phasing

### Phase 1: ICS Download Enhancement (Week 1)
- Enhance existing `generate_calendar_invite` function
- Add "Download .ics" button to interview scheduling
- Include full event details (prep notes, links)

### Phase 2: Google Calendar Basic (Weeks 2-3)
- OAuth flow implementation
- Token storage (encrypted)
- Create event on interview schedule
- Basic settings UI

### Phase 3: Outlook/Microsoft 365 (Weeks 4-5)
- Microsoft Graph API integration
- OAuth flow for Microsoft
- Event creation parity with Google

### Phase 4: Event Sync & Updates (Week 6)
- Update events on interview reschedule
- Delete events on cancellation
- Handle token refresh

### Phase 5: Availability View (Future)
- Free/busy API integration
- Availability timeline component
- Conflict detection

---

# Feature 5: Mobile-Friendly Interview Scorecards

## Overview
Create a responsive, mobile-optimized interface for interviewers to complete scorecards during or after interviews.

## User Stories

### US-5.1: Access Scorecard on Mobile
**As an** interviewer
**I want to** access and complete scorecards on my phone
**So that** I can score candidates immediately after interviews

**Acceptance Criteria:**
```gherkin
Given I receive an interview notification with a scorecard link
When I open the link on my mobile device
Then I should see a mobile-optimized scorecard interface
And be able to view candidate details
And score each criterion easily
And submit scores without difficulty
```

### US-5.2: Mobile-Optimized Scoring Interface
**As an** interviewer
**I want** large, touch-friendly score inputs
**So that** I can quickly rate candidates on my phone

**Acceptance Criteria:**
```gherkin
Given I am on the mobile scorecard
When I view the scoring criteria
Then each criterion should have large touch targets
And use a simple 1-5 star or slider interface
And show the criterion description clearly
And allow quick progression between criteria
```

### US-5.3: Offline-Capable Notes
**As an** interviewer
**I want to** take notes even without internet
**So that** I don't lose my feedback if connectivity drops

**Acceptance Criteria:**
```gherkin
Given I am entering notes on the mobile scorecard
When I lose internet connectivity
Then my notes should be saved locally
And synced when connectivity returns
And I should be notified of sync status
```

### US-5.4: Quick Interview Summary
**As an** interviewer
**I want to** quickly record an overall recommendation
**So that** I can provide a fast initial decision

**Acceptance Criteria:**
```gherkin
Given I have completed the scorecard
When I reach the summary section
Then I should see options for:
  - Strong Yes / Yes / Maybe / No / Strong No
And a text field for key observations
And a submit button that confirms my scores
```

### US-5.5: Shareable Scorecard Links
**As a** recruiter
**I want to** send scorecards to interviewers via link
**So that** they can access without logging into the full system

**Acceptance Criteria:**
```gherkin
Given I have scheduled an interview
When I click "Generate Scorecard Link"
Then a unique, secure URL should be created
And include a token that expires after submission or 48 hours
And the link should be copyable and shareable
```

## Complexity Assessment: **Medium**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Significant - New responsive views, touch-optimized UI |
| Backend Logic | Moderate - Token generation, secure routes |
| Database Changes | New table for scorecard tokens |
| External Dependencies | None |
| Testing Effort | Moderate - Mobile testing, responsive layouts |

## Integration Requirements

### Frontend Components
- [ ] Mobile-responsive scorecard page (separate route or view)
- [ ] Touch-friendly star rating or slider components
- [ ] Swipe navigation between criteria
- [ ] Large text areas for notes
- [ ] Recommendation quick-select buttons
- [ ] Progress indicator
- [ ] Submit confirmation modal

### API/Functions Needed
```python
# New module: mobile_scorecard.py
def generate_scorecard_token(interview_id: int, expires_hours: int = 48) -> str:
    """Generate secure token for scorecard access"""

def validate_scorecard_token(token: str) -> Optional[Dict]:
    """Validate token and return interview/candidate info"""

def submit_mobile_scorecard(token: str, scores: Dict, notes: str, recommendation: str):
    """Submit scores via mobile interface"""

# Additions to app.py
def render_mobile_scorecard():
    """Render mobile-optimized scorecard view"""
```

### Database Schema Changes
```sql
CREATE TABLE scorecard_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    interviewer_email TEXT,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id)
);
```

### CSS/Styling Additions
```css
/* Mobile scorecard styles */
@media (max-width: 768px) {
    .scorecard-container { ... }
    .score-input-large { ... }
    .swipe-navigation { ... }
}
```

## Dependencies
- None (can be implemented independently)

## Vertical Slice Recommendation
Not required - Medium complexity can be delivered in single iteration.

**Suggested Implementation Order:**
1. Secure token generation and validation
2. Basic mobile scorecard page with responsive CSS
3. Touch-friendly scoring inputs
4. Notes and recommendation fields
5. Submit and confirmation flow
6. Offline capability (localStorage)

---

# Feature 6: Multi-Role Matching

## Overview
Allow candidates to be evaluated against multiple job openings simultaneously, with separate AI scores and tracking per role.

## User Stories

### US-6.1: Associate Candidate with Multiple Jobs
**As a** recruiter
**I want to** associate a candidate with multiple open positions
**So that** I can consider them for different roles

**Acceptance Criteria:**
```gherkin
Given I am viewing a candidate profile
When I click "Add to Additional Role"
Then I should see a list of open jobs
And be able to select one or more jobs
And the candidate should be linked to those jobs
And each job association should have its own stage and scores
```

### US-6.2: Separate AI Scoring Per Role
**As a** recruiter
**I want** AI resume scores calculated per job
**So that** I understand the candidate's fit for each role

**Acceptance Criteria:**
```gherkin
Given a candidate is associated with multiple jobs
When I view their AI scores
Then I should see a separate score for each job
And the analysis should reflect the specific job requirements
And I can trigger re-scoring for any job
```

### US-6.3: Independent Stage Tracking
**As a** recruiter
**I want** to track a candidate's stage independently per job
**So that** their progress in one role doesn't affect another

**Acceptance Criteria:**
```gherkin
Given a candidate is in multiple pipelines
When I advance them in one role
Then their stage in other roles should remain unchanged
And I should see all role statuses in their profile
And pipeline dashboards should count them correctly
```

### US-6.4: Unified Notes with Role Context
**As an** interviewer
**I want** interview notes to be viewable across roles
**So that** previous feedback informs all evaluations

**Acceptance Criteria:**
```gherkin
Given a candidate has multiple role associations
When I view their interview notes
Then I should see all notes with role context
And be able to filter notes by role
And notes should indicate which role the interview was for
```

### US-6.5: Multi-Role Dashboard View
**As a** recruiter
**I want to** see candidates who are active in multiple pipelines
**So that** I can coordinate across hiring efforts

**Acceptance Criteria:**
```gherkin
Given multiple candidates are in multiple pipelines
When I view the multi-role dashboard
Then I should see candidates with their role associations
And their stages in each role
And be able to filter by specific role combinations
```

## Complexity Assessment: **Large**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Significant - Multi-role UI throughout |
| Backend Logic | Significant - Restructure job-candidate relationship |
| Database Changes | Major - New junction table, schema refactor |
| External Dependencies | None |
| Testing Effort | High - Data integrity, migration |

## Integration Requirements

### Frontend Components
- [ ] Multi-role selector in candidate profile
- [ ] Role-specific stage indicators
- [ ] Per-role AI score display
- [ ] Role context badges on notes
- [ ] Multi-role filter in candidate list
- [ ] Cross-role analytics dashboard

### API/Functions Needed
```python
# Modifications to database.py
def add_candidate_to_job(candidate_id: int, job_id: int) -> int:
    """Add candidate to additional job, return association ID"""

def get_candidate_jobs(candidate_id: int) -> List[Dict]:
    """Get all jobs a candidate is associated with"""

def get_candidate_role_status(candidate_id: int, job_id: int) -> Dict:
    """Get stage, scores, status for specific role"""

def advance_candidate_in_role(candidate_id: int, job_id: int, new_stage: str):
    """Advance candidate in specific role"""

def score_candidate_for_role(candidate_id: int, job_id: int) -> Tuple[float, str]:
    """AI score candidate against specific job"""

# Modifications to existing functions:
# - get_candidates() - handle multiple job associations
# - get_pipeline_stats() - count correctly across roles
```

### Database Schema Changes
```sql
-- New junction table for multi-role support
CREATE TABLE candidate_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    current_stage TEXT DEFAULT 'Resume Screen',
    status TEXT DEFAULT 'Active',  -- Active, Rejected, Hired, Withdrawn
    ai_resume_score REAL,
    ai_resume_analysis TEXT,
    is_primary INTEGER DEFAULT 0,  -- Primary role association
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(candidate_id, job_id)
);

-- Update stage_scores to include job context
ALTER TABLE stage_scores ADD COLUMN job_id INTEGER REFERENCES jobs(id);

-- Update stage_notes to include job context
ALTER TABLE stage_notes ADD COLUMN job_id INTEGER REFERENCES jobs(id);

-- Update interviews to include job context
ALTER TABLE interviews ADD COLUMN job_id INTEGER REFERENCES jobs(id);

-- Index for efficient queries
CREATE INDEX idx_candidate_jobs_candidate ON candidate_jobs(candidate_id);
CREATE INDEX idx_candidate_jobs_job ON candidate_jobs(job_id);
```

## Dependencies
- None (can be implemented independently, but requires data migration)

## Vertical Slice Phasing

### Phase 1: Schema Migration (Week 1)
- Create candidate_jobs junction table
- Migrate existing candidate.job_id to candidate_jobs
- Update queries to use new structure
- Maintain backward compatibility

### Phase 2: Basic Multi-Role Assignment (Week 2)
- UI to add candidate to additional roles
- Display multiple roles in candidate profile
- Role-specific stage tracking

### Phase 3: Per-Role Scoring & Notes (Week 3)
- AI scoring per role
- Role context on stage_scores
- Role filtering on notes

### Phase 4: Dashboard & Analytics (Week 4)
- Update pipeline stats for multi-role
- Multi-role dashboard view
- Cross-role analytics

---

# Feature 7: Hiring Manager Views (Role-Based Dashboards)

## Overview
Implement role-based access control with specialized dashboard views for hiring managers, recruiters, and interviewers.

## User Stories

### US-7.1: Hiring Manager Dashboard
**As a** hiring manager
**I want** a focused dashboard showing only my roles and candidates
**So that** I can efficiently manage my hiring pipeline

**Acceptance Criteria:**
```gherkin
Given I am logged in as a hiring manager
When I view my dashboard
Then I should only see jobs I own
And candidates in those pipelines
And key metrics for my roles only
And quick actions for common tasks
```

### US-7.2: User Roles and Permissions
**As an** administrator
**I want to** assign roles to users
**So that** they have appropriate access levels

**Acceptance Criteria:**
```gherkin
Given I am in the user management area
When I configure a user
Then I can assign roles: Admin, Recruiter, Hiring Manager, Interviewer
And assign specific jobs to Hiring Managers
And set permissions for each role:
  - Admin: Full access
  - Recruiter: All candidates, all jobs
  - Hiring Manager: Owned jobs only
  - Interviewer: View assigned candidates, submit scorecards only
```

### US-7.3: Job Ownership
**As a** recruiter
**I want to** assign hiring managers to jobs
**So that** they can see relevant candidates and metrics

**Acceptance Criteria:**
```gherkin
Given I am creating or editing a job
When I configure job ownership
Then I can assign one or more hiring managers
And they will see this job on their dashboard
And receive notifications for this job
```

### US-7.4: Interviewer View
**As an** interviewer
**I want** a simple view of my upcoming interviews
**So that** I can prepare and submit feedback efficiently

**Acceptance Criteria:**
```gherkin
Given I am logged in as an interviewer
When I view my dashboard
Then I should see my scheduled interviews
And candidate prep materials for each
And quick links to submit scorecards
And my recent scorecard submissions
```

### US-7.5: Role-Based Navigation
**As a** user
**I want** navigation tailored to my role
**So that** I'm not confused by features I can't use

**Acceptance Criteria:**
```gherkin
Given I am logged in with a specific role
When I view the navigation menu
Then I should only see menu items I have access to
And attempting to access restricted pages should show an error
```

## Complexity Assessment: **XL (Extra Large)**

| Factor | Assessment |
|--------|------------|
| Frontend Changes | Major - Role-based navigation, multiple dashboards |
| Backend Logic | Major - Authentication, authorization system |
| Database Changes | Major - Users, roles, permissions tables |
| External Dependencies | Auth provider (optional) |
| Testing Effort | Very High - Permission combinations, security |
| Security Considerations | Critical - Access control |

## Integration Requirements

### Frontend Components
- [ ] Login/authentication UI (if implementing basic auth)
- [ ] Role-based navigation menu
- [ ] Hiring Manager dashboard
- [ ] Interviewer dashboard
- [ ] User management UI (Admin only)
- [ ] Permission denied error pages

### API/Functions Needed
```python
# New module: auth.py
def authenticate_user(email: str, password: str = None) -> Optional[Dict]:
    """Authenticate user, return user info with role"""

def get_current_user() -> Optional[Dict]:
    """Get current session user"""

def check_permission(user: Dict, resource: str, action: str) -> bool:
    """Check if user has permission for action on resource"""

def require_role(*roles: str):
    """Decorator to require specific roles"""

# New module: user_management.py
def create_user(email: str, name: str, role: str) -> int:
    """Create new user"""

def assign_job_owner(job_id: int, user_id: int):
    """Assign user as hiring manager for job"""

def get_user_jobs(user_id: int) -> List[Dict]:
    """Get jobs user has access to"""

# Dashboard functions
def render_hiring_manager_dashboard(user_id: int):
    """Render HM-specific dashboard"""

def render_interviewer_dashboard(user_id: int):
    """Render interviewer-specific dashboard"""
```

### Database Schema Changes
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'admin', 'recruiter', 'hiring_manager', 'interviewer'
    password_hash TEXT,  -- Optional, for basic auth
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE job_owners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'hiring_manager',  -- could be 'recruiter', 'hiring_manager'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(job_id, user_id)
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_job_owners_job ON job_owners(job_id);
CREATE INDEX idx_job_owners_user ON job_owners(user_id);
```

## Dependencies
- None, but implementing this early affects how other features handle user context

## Vertical Slice Phasing

### Phase 1: Basic User Model (Week 1)
- Create users table
- Simple session management via Streamlit session state
- Basic role field (no enforcement)

### Phase 2: Job Ownership (Week 2)
- job_owners table
- Assign hiring managers to jobs
- Filter jobs by ownership in queries

### Phase 3: Role-Based Filtering (Week 3)
- Hiring Manager dashboard (their jobs only)
- Interviewer view (their interviews only)
- Role-based navigation

### Phase 4: Permission Enforcement (Week 4)
- Permission checks on all actions
- Access denied handling
- Admin user management UI

### Phase 5: Authentication (Future)
- Login page (if needed beyond SSO)
- Password hashing
- Session management
- Integration with corporate SSO (if required)

---

# Implementation Roadmap

## Priority Assessment Matrix

| Feature | Business Value | Complexity | Dependencies | Priority Score |
|---------|---------------|------------|--------------|----------------|
| 1. Resume Upload | High | Medium | None | **P1** |
| 2. Bulk CSV Import | High | Large | Feature 1 (optional) | **P2** |
| 3. Slack/Teams Notifications | Medium | Medium | None | **P3** |
| 5. Mobile Scorecards | High | Medium | None | **P1** |
| 4. Calendar Integration | Medium | XL | None | **P4** |
| 6. Multi-Role Matching | Medium | Large | Schema refactor risk | **P3** |
| 7. Hiring Manager Views | Medium | XL | None but foundational | **P5** |

## Recommended Implementation Order

### Phase 1: Quick Wins (Weeks 1-3)
**Focus:** High value, lower complexity features

| Week | Feature | Deliverable |
|------|---------|-------------|
| 1 | Resume Upload (F1) | PDF/DOCX/TXT parsing and storage |
| 2 | Mobile Scorecards (F5) | Token-based mobile scorecard view |
| 3 | Slack/Teams (F3) | Basic webhook notifications |

**Value Delivered:**
- Recruiters can upload resumes directly
- Interviewers can score on mobile
- Hiring managers get notified of pipeline changes

### Phase 2: Data Management (Weeks 4-6)
**Focus:** Bulk operations and data import

| Week | Feature | Deliverable |
|------|---------|-------------|
| 4 | Bulk Import (F2) - Phase 1 | Basic CSV import with mapping |
| 5 | Bulk Import (F2) - Phase 2 | Validation, duplicate detection |
| 6 | Bulk Import (F2) - Phase 3 | Excel support, error reports |

**Value Delivered:**
- Vendor submissions can be imported in bulk
- Time saved on manual data entry

### Phase 3: Advanced Tracking (Weeks 7-10)
**Focus:** Multi-role support

| Week | Feature | Deliverable |
|------|---------|-------------|
| 7 | Multi-Role (F6) - Phase 1 | Schema migration |
| 8 | Multi-Role (F6) - Phase 2 | Multi-role assignment UI |
| 9 | Multi-Role (F6) - Phase 3 | Per-role scoring |
| 10 | Multi-Role (F6) - Phase 4 | Dashboard updates |

**Value Delivered:**
- Candidates can be tracked across multiple roles
- Better visibility into cross-role hiring

### Phase 4: Calendar Integration (Weeks 11-14)
**Focus:** External calendar sync

| Week | Feature | Deliverable |
|------|---------|-------------|
| 11 | Calendar (F4) - Phase 1 | Enhanced ICS download |
| 12-13 | Calendar (F4) - Phase 2 | Google Calendar OAuth + events |
| 14 | Calendar (F4) - Phase 3 | Outlook/Microsoft 365 |

**Value Delivered:**
- Interviews automatically appear on calendars
- Reduced scheduling coordination

### Phase 5: Access Control (Weeks 15-18)
**Focus:** Role-based views and permissions

| Week | Feature | Deliverable |
|------|---------|-------------|
| 15 | RBAC (F7) - Phase 1 | User model, basic roles |
| 16 | RBAC (F7) - Phase 2 | Job ownership |
| 17 | RBAC (F7) - Phase 3 | Role-specific dashboards |
| 18 | RBAC (F7) - Phase 4 | Permission enforcement |

**Value Delivered:**
- Hiring managers see only their roles
- Better security and focused UX

---

## Dependency Graph

```
[Resume Upload (F1)]
         │
         ▼
[Bulk CSV Import (F2)] ──────────────────┐
                                          │
[Mobile Scorecards (F5)] ◄────────────────┤
                                          │
[Slack/Teams Notifications (F3)] ◄────────┤
         │                                │
         ▼                                │
[Multi-Role Matching (F6)] ◄──────────────┤
         │                                │
         ▼                                │
[Calendar Integration (F4)] ◄─────────────┤
         │                                │
         ▼                                ▼
[Hiring Manager Views (F7)] ◄─────────────┘
```

**Legend:**
- Solid arrows: Recommended sequence
- All features can technically be implemented independently
- F7 (RBAC) benefits from being implemented last as it affects all other features

---

## Resource Estimates

| Feature | Dev Effort | Testing | Total |
|---------|------------|---------|-------|
| Resume Upload | 3 days | 1 day | 4 days |
| Bulk CSV Import | 8 days | 3 days | 11 days |
| Slack/Teams | 3 days | 1 day | 4 days |
| Calendar Integration | 12 days | 3 days | 15 days |
| Mobile Scorecards | 4 days | 2 days | 6 days |
| Multi-Role Matching | 10 days | 4 days | 14 days |
| Hiring Manager Views | 12 days | 4 days | 16 days |
| **Total** | **52 days** | **18 days** | **70 days** |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PDF parsing fails on complex resumes | Medium | Medium | Provide manual text entry fallback |
| OAuth token management complexity | Medium | High | Use established libraries, implement refresh logic |
| Multi-role schema migration breaks existing data | Low | Critical | Thorough migration testing, rollback plan |
| Mobile scorecard security (token guessing) | Low | High | Secure token generation, short expiry |
| Calendar API rate limits | Low | Medium | Implement retry logic, batch operations |
| RBAC performance impact | Medium | Medium | Efficient permission caching |

---

## Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| Resume Upload | % resumes with parsed text | 90%+ |
| Bulk Import | Time to import 100 candidates | < 2 minutes |
| Notifications | Notification delivery rate | 99%+ |
| Calendar | Calendar event creation rate | 95%+ |
| Mobile Scorecards | Scorecard completion rate | 80%+ within 24h |
| Multi-Role | Candidates in 2+ roles | Track adoption |
| RBAC | Unauthorized access attempts | 0 |

---

## Appendix A: Technical Notes

### Current File Structure
```
ats_app/
├── ats_app/
│   ├── app.py           # Main Streamlit application
│   ├── database.py      # SQLite database layer
│   ├── genai.py         # Claude AI integration
│   ├── email_utils.py   # Email utilities
│   └── ats_data.db      # SQLite database
```

### Proposed New Modules
```
ats_app/
├── ats_app/
│   ├── app.py
│   ├── database.py
│   ├── genai.py
│   ├── email_utils.py
│   ├── resume_parser.py    # Feature 1
│   ├── bulk_import.py      # Feature 2
│   ├── notifications.py    # Feature 3
│   ├── calendar_integration.py  # Feature 4
│   ├── mobile_scorecard.py # Feature 5
│   ├── auth.py             # Feature 7
│   └── ats_data.db
├── uploads/
│   └── resumes/            # Feature 1 file storage
└── requirements.txt        # Updated dependencies
```

### New Dependencies to Add
```
# Feature 1: Resume Parsing
pypdf>=3.0.0
python-docx>=0.8.11

# Feature 2: Bulk Import
openpyxl>=3.1.0  # Excel support

# Feature 4: Calendar Integration
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
msal>=1.20.0  # Microsoft auth

# Feature 3: Notifications (uses requests, usually already available)
requests>=2.28.0
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-30 | PM Agent | Initial PRD creation |

---

*End of PRD Document*
