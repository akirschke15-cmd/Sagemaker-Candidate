# Agentic Program ATS - Technical Stack Document

## Overview

The Agentic Program ATS is a full-featured Applicant Tracking System built for managing contractor hiring pipelines with AI-powered candidate screening and multi-stage interview management.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│                    Streamlit Web Application                     │
│                    (Python-based reactive UI)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Auth      │  │   GenAI     │  │   Business Logic        │  │
│  │   Module    │  │   Module    │  │   (Candidates, Jobs,    │  │
│  │             │  │             │  │    Interviews, etc.)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│                      SQLite Database                             │
│                      (ats_data.db)                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Integrations                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Claude   │  │  AWS     │  │  Slack/  │  │  Calendar        │ │
│  │ API      │  │  Bedrock │  │  Teams   │  │  (ICS Export)    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Frontend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Web Framework | Streamlit | >= 1.25 | Reactive Python web UI |
| Styling | Custom CSS | - | Southwest Airlines brand theming |
| Charts | Streamlit native + Plotly | >= 5.10 | Data visualization |

### Backend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.7+ | Core application logic |
| Database | SQLite | 3.x | Data persistence |
| Data Processing | Pandas | >= 1.5 | Data manipulation & analytics |
| Numerical | NumPy | >= 1.21 | Numerical operations |

### AI/ML Integration
| Component | Technology | Purpose |
|-----------|------------|---------|
| Primary AI | Anthropic Claude API | Resume scoring, note summarization, interview questions |
| Fallback AI | AWS Bedrock (Claude) | Enterprise deployment option |
| Model | Claude Sonnet | Intelligent candidate analysis |

### Document Processing
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| PDF Parsing | pypdf | >= 3.0 | Resume PDF extraction |
| Word Documents | python-docx | >= 0.8 | Resume DOCX extraction |
| Excel/CSV | openpyxl + pandas | >= 3.0 | Bulk candidate import |

### External Integrations
| Integration | Protocol | Purpose |
|-------------|----------|---------|
| Slack | Webhooks | Real-time notifications |
| Microsoft Teams | Webhooks (Adaptive Cards) | Real-time notifications |
| Calendar | ICS (RFC 5545) | Interview scheduling export |

---

## Database Schema

### Core Tables

```
vendors              - Staffing agencies/recruiters
├── id, name, contact_email, contact_phone, notes

jobs                 - Job postings/roles
├── id, title, description, requirements, department
├── slots, status, contractor_role_id

candidates           - Applicant records
├── id, name, email, phone, job_id, vendor_id
├── current_stage, resume_text, resume_path
├── ai_resume_score, ai_resume_analysis
├── expected_hourly_rate, is_past_contractor

candidate_jobs       - Multi-role associations (junction table)
├── candidate_id, job_id, stage, ai_score, notes

interviews           - Scheduled interviews
├── id, candidate_id, job_id, stage, interviewer_name
├── scheduled_time, duration_minutes, location, status

stage_scores         - Interview evaluations
├── interview_id, criteria_name, score, max_score

stage_notes          - Interview feedback
├── candidate_id, job_id, stage, notes, ai_summary
```

### Authentication & Authorization

```
users                - User accounts
├── id, email, name, role, is_active

job_owners           - Hiring manager assignments
├── job_id, user_id (links HMs to specific jobs)
```

### Supporting Tables

```
scoring_criteria     - Per-job, per-stage evaluation rubrics
notification_webhooks - Slack/Teams webhook configurations
notification_log     - Notification history
calendar_events      - ICS event metadata
scorecard_tokens     - Mobile scorecard access tokens
email_templates      - Email automation templates
email_queue          - Outbound email queue
contractor_roles     - Role definitions with rate ranges
contracts            - Contract lifecycle tracking
compliance_documents - Document management
```

---

## Module Structure

```
ats_app/
├── app.py                    # Main Streamlit application (~3,900 lines)
│                             # - UI rendering for all pages
│                             # - Navigation and routing
│                             # - Session state management
│
├── database.py               # Database operations (~700 lines)
│                             # - SQLite connection management
│                             # - CRUD operations for all entities
│                             # - Analytics queries
│
├── auth.py                   # Authentication & RBAC (~350 lines)
│                             # - User session management
│                             # - Role-based permissions
│                             # - Access control helpers
│
├── genai.py                  # AI integration (~620 lines)
│                             # - Claude API / Bedrock clients
│                             # - Resume scoring
│                             # - Note summarization
│                             # - Interview question generation
│
├── resume_parser.py          # Document parsing (~340 lines)
│                             # - PDF text extraction
│                             # - DOCX text extraction
│                             # - Plain text handling
│
├── bulk_import.py            # Batch operations (~400 lines)
│                             # - CSV/Excel parsing
│                             # - Validation and error reporting
│                             # - Duplicate detection
│
├── notifications.py          # Webhook notifications (~700 lines)
│                             # - Slack message formatting
│                             # - Teams adaptive cards
│                             # - Event triggers
│
├── calendar_integration.py   # Calendar features (~450 lines)
│                             # - ICS file generation
│                             # - Event formatting
│
├── mobile_scorecard.py       # Token management (~240 lines)
│                             # - Secure token generation
│                             # - Token validation
│                             # - Scorecard submission
│
├── mobile_scorecard_ui.py    # Mobile UI (~500 lines)
│                             # - Responsive scorecard interface
│                             # - Touch-friendly controls
│
├── comparison_view.py        # Candidate comparison (~400 lines)
│                             # - Side-by-side comparison
│                             # - AI-powered recommendations
│
├── email_automation.py       # Email workflows (~300 lines)
│                             # - Template rendering
│                             # - Queue management
│
└── email_utils.py            # Email utilities (~150 lines)
                              # - SMTP configuration
                              # - Send operations
```

---

## Security Considerations

### Authentication
- Session-based authentication using Streamlit session state
- Role-based access control (RBAC) with 4 permission levels
- No passwords stored (simplified for internal use)

### Data Protection
- SQLite database file stored locally
- API keys should be stored in environment variables
- Mobile scorecard tokens expire after 48 hours

### Recommended Production Enhancements
1. Migrate to PostgreSQL for multi-user concurrency
2. Implement proper password hashing (bcrypt)
3. Add HTTPS/TLS termination
4. Implement audit logging
5. Add rate limiting for API endpoints

---

## Deployment

### Local Development
```bash
cd ats_app
pip install -r requirements.txt
streamlit run app.py
```

### AWS SageMaker (DSCP)
```bash
pip install -r requirements.txt \
  --index-url https://nexus-tools.swacorp.com/repository/pypi-all/simple \
  --trusted-host nexus-tools.swacorp.com

streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.baseUrlPath="/proxy/absolute/8501"
```

### Environment Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| ANTHROPIC_API_KEY | Claude API access | For AI features |
| SMTP_HOST | Email server | For email features |
| SMTP_USER | Email authentication | For email features |
| SMTP_PASSWORD | Email authentication | For email features |

---

## Performance Characteristics

- **Startup Time**: ~3-5 seconds
- **Page Load**: <1 second for most views
- **AI Operations**: 2-5 seconds (API dependent)
- **Database**: Optimized for <1000 candidates
- **Concurrent Users**: Limited by SQLite (recommend <10 simultaneous)

---

## Dependencies

```
streamlit>=1.25,<2.0
pandas>=1.5,<3.0
numpy>=1.21,<2.0
boto3>=1.26,<2.0
pypdf>=3.0,<5.0
python-docx>=0.8,<1.0
openpyxl>=3.0,<4.0
plotly>=5.10,<6.0
anthropic  # Optional: for direct Claude API
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024 | Initial release with core ATS functionality |
| 1.1 | 2024 | Added AI resume scoring, mobile scorecards |
| 1.2 | 2024 | Added multi-role support, RBAC, notifications |
