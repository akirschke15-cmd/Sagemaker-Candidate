# Agentic Program ATS - Executive Summary

## What Is It?

The **Agentic Program ATS** is a purpose-built Applicant Tracking System designed to streamline contractor hiring for agentic AI programs. It combines traditional recruiting workflow management with AI-powered candidate screening to reduce time-to-hire and improve hiring quality.

---

## Business Problem Solved

| Challenge | Solution |
|-----------|----------|
| Manual resume screening is time-consuming | AI-powered resume scoring against job requirements |
| Candidates get lost in the pipeline | Visual pipeline tracking with stage-based workflow |
| Hiring managers lack visibility | Role-based dashboards with real-time metrics |
| Interview feedback is scattered | Centralized scorecards with mobile access |
| Vendor performance is opaque | Vendor analytics and conversion tracking |
| Communication delays | Slack/Teams notifications for pipeline events |

---

## Key Capabilities

### 1. AI-Powered Screening
- **Resume Scoring**: Automatically scores resumes against job requirements (0-100%)
- **Strength/Gap Analysis**: Identifies candidate strengths and skill gaps
- **Interview Question Generation**: AI-generated questions tailored to each candidate
- **Candidate Comparison**: AI-assisted recommendations when comparing finalists

### 2. Pipeline Management
- **7-Stage Workflow**: Resume Screen → Phone Screen → Technical → Behavioral → Offer → Hired/Rejected
- **Multi-Role Support**: Candidates can be considered for multiple positions simultaneously
- **Stage Tracking**: Track time-in-stage and identify bottlenecks
- **Bulk Operations**: Import candidates via CSV/Excel

### 3. Interview Management
- **Scheduling**: Interview scheduling with calendar export (ICS)
- **Scorecards**: Configurable scoring criteria per stage
- **Mobile Scorecards**: Interviewers can submit feedback from any device via secure links
- **Note Summarization**: AI summarizes interview notes for handoff between stages

### 4. Analytics & Reporting
- **Pipeline Health**: Funnel visualization and conversion rates
- **Time-to-Hire**: Track hiring velocity by stage and job
- **Vendor Scorecards**: Compare staffing agency performance
- **AI Calibration**: Monitor AI scoring accuracy vs. hiring outcomes

### 5. Role-Based Access Control
| Role | Access Level |
|------|--------------|
| Admin | Full system access, user management |
| Recruiter | All candidates, all jobs, bulk operations |
| Hiring Manager | Only assigned jobs and their candidates |
| Interviewer | View-only access to interview-relevant data |

---

## Value Proposition

### For Recruiters
- **60% faster** initial screening with AI resume scoring
- Bulk import eliminates manual data entry
- Automated notifications keep stakeholders informed

### For Hiring Managers
- Real-time visibility into their pipeline
- Structured interview feedback in one place
- AI-assisted candidate comparison for final decisions

### For Interviewers
- Mobile-friendly scorecards - submit feedback from anywhere
- AI-generated questions tailored to each candidate
- Previous stage summaries for context

### For Leadership
- Pipeline analytics and hiring metrics
- Vendor performance tracking
- Compliance and audit trail

---

## Technical Highlights

| Aspect | Implementation |
|--------|----------------|
| **Platform** | Python/Streamlit web application |
| **AI Backend** | Claude API (Anthropic) or AWS Bedrock |
| **Database** | SQLite (upgradable to PostgreSQL) |
| **Deployment** | AWS SageMaker compatible |
| **Integrations** | Slack, Microsoft Teams, Calendar (ICS) |

---

## Current State

### Implemented Features
- Core ATS workflow (candidates, jobs, interviews)
- AI resume scoring and analysis
- Multi-role candidate tracking
- Role-based access control (4 roles)
- Mobile interview scorecards
- Slack/Teams webhook notifications
- Calendar ICS export
- Bulk CSV/Excel import
- Analytics dashboard with 7 report types
- Vendor performance tracking
- Contract lifecycle management

### Roadmap Items
- Google Calendar OAuth integration
- Microsoft 365 OAuth integration
- Advanced email automation
- Interviewer availability scheduling
- Enhanced reporting and exports

---

## Demo Data

The system includes sample data for demonstration:
- **3 Vendors**: Acme Staffing, TechTalent, Two Roads
- **7 Jobs**: Including "AI/ML Engineer - Agentic Systems"
- **26 Candidates**: Distributed across all pipeline stages
- **5 Users**: One per role type for testing RBAC

---

## Getting Started

### Quick Start
```
1. Navigate to http://localhost:8501
2. Select user: admin@agentic.com
3. Explore Dashboard, Candidates, Jobs, Analytics
```

### Demo Login Accounts
| Role | Email |
|------|-------|
| Admin | admin@agentic.com |
| Recruiter | recruiter@agentic.com |
| Hiring Manager | hiring.manager@agentic.com |
| Interviewer | interviewer@agentic.com |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time-to-Screen | <24 hours | AI scoring turnaround |
| Pipeline Visibility | 100% | All candidates tracked in system |
| Interview Feedback | >90% | Scorecards submitted within 24hrs |
| Hiring Manager Adoption | >80% | Active users per week |

---

## Contact & Support

For questions about the Agentic Program ATS:
- Technical Issues: Review logs in Streamlit console
- Feature Requests: Document in PRD_Feature_Enhancements.md
- User Access: Contact system administrator

---

*Built for the Agentic AI Program - Streamlining Contractor Hiring with Intelligence*
