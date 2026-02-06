from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor as RgbColor

# Create presentation
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Colors (Southwest Airlines theme)
SW_RED = RgbColor(0xC8, 0x10, 0x2E)
SW_BLUE = RgbColor(0x30, 0x4C, 0xB2)
SW_YELLOW = RgbColor(0xF9, 0xB6, 0x12)
WHITE = RgbColor(0xFF, 0xFF, 0xFF)
DARK_GRAY = RgbColor(0x33, 0x33, 0x33)

def add_title_slide(title, subtitle=""):
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = SW_BLUE
    shape.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(12.333), Inches(1))
        tf = sub_box.text_frame
        p = tf.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(24)
        p.font.color.rgb = SW_YELLOW
        p.alignment = PP_ALIGN.CENTER

    return slide

def add_section_slide(title):
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(3), prs.slide_width, Inches(1.5))
    shape.fill.solid()
    shape.fill.fore_color.rgb = SW_RED
    shape.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(3.15), Inches(12.333), Inches(1.2))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    return slide

def add_content_slide(title, bullets):
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2))
    shape.fill.solid()
    shape.fill.fore_color.rgb = SW_BLUE
    shape.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = WHITE

    content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12.333), Inches(5.5))
    tf = content_box.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = bullet
        p.font.size = Pt(20)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(14)

    return slide

def add_table_slide(title, headers, rows):
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.2))
    shape.fill.solid()
    shape.fill.fore_color.rgb = SW_BLUE
    shape.line.fill.background()

    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = WHITE

    num_rows = len(rows) + 1
    num_cols = len(headers)
    table_width = Inches(12)
    table_height = Inches(0.5) * num_rows

    table = slide.shapes.add_table(num_rows, num_cols, Inches(0.6), Inches(1.5), table_width, table_height).table

    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = SW_RED
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(16)
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            cell = table.cell(row_idx + 1, col_idx)
            cell.text = str(value)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(14)
            p.font.color.rgb = DARK_GRAY
            if row_idx % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RgbColor(0xF5, 0xF5, 0xF5)

    return slide

# ============ CREATE SLIDES ============

# Slide 1: Title
add_title_slide("Agentic Program ATS", "Intelligent Applicant Tracking for Contractor Hiring")

# Slide 2: Agenda
add_content_slide("Agenda", [
    "1. Executive Overview",
    "2. Key Capabilities",
    "3. Value Proposition",
    "4. Technical Architecture",
    "5. Role-Based Access",
    "6. Demo Walkthrough",
    "7. Roadmap & Next Steps"
])

# Slide 3: Section - Executive Overview
add_section_slide("Executive Overview")

# Slide 4: The Challenge
add_content_slide("The Business Challenge", [
    "Manual resume screening is time-consuming and inconsistent",
    "Candidates get lost in fragmented hiring pipelines",
    "Hiring managers lack real-time visibility into their candidates",
    "Interview feedback is scattered across emails and documents",
    "Vendor/staffing agency performance is difficult to measure",
    "Communication delays slow down the hiring process"
])

# Slide 5: The Solution
add_content_slide("Our Solution: Agentic Program ATS", [
    "Purpose-built ATS for contractor hiring pipelines",
    "AI-powered resume screening scores candidates automatically",
    "Centralized pipeline with 7-stage workflow tracking",
    "Role-based dashboards for recruiters, hiring managers, and interviewers",
    "Mobile-friendly scorecards for interview feedback anywhere",
    "Integrated notifications via Slack and Microsoft Teams",
    "Comprehensive analytics and vendor performance tracking"
])

# Slide 6: Section - Key Capabilities
add_section_slide("Key Capabilities")

# Slide 7: AI-Powered Features
add_content_slide("AI-Powered Intelligence", [
    "Resume Scoring: Automatically scores resumes 0-100% against job requirements",
    "Strength & Gap Analysis: Identifies candidate strengths and skill gaps",
    "Interview Questions: AI-generates tailored questions for each candidate",
    "Note Summarization: Summarizes interview feedback for stage handoffs",
    "Candidate Comparison: AI-assisted recommendations when comparing finalists",
    "Powered by Claude (Anthropic) or AWS Bedrock"
])

# Slide 8: Pipeline Management
add_content_slide("Pipeline Management", [
    "7-Stage Workflow: Resume Screen -> Phone -> Technical -> Behavioral -> Offer -> Hired",
    "Multi-Role Support: Candidates can be considered for multiple positions",
    "Stage Tracking: Monitor time-in-stage and identify bottlenecks",
    "Bulk Operations: Import candidates via CSV/Excel files",
    "Visual Pipeline: Funnel visualization with real-time counts",
    "Automated Notifications: Alerts on stage changes and key events"
])

# Slide 9: Interview Management
add_content_slide("Interview Management", [
    "Interview Scheduling: Schedule with calendar export (ICS format)",
    "Configurable Scorecards: Custom scoring criteria per job and stage",
    "Mobile Scorecards: Secure links for feedback from any device",
    "48-hour expiring tokens for security",
    "Recommendation Options: Strong Yes / Yes / Maybe / No / Strong No",
    "AI Note Summarization: Prep next interviewer with key points"
])

# Slide 10: Section - Value Proposition
add_section_slide("Value Proposition")

# Slide 11: Value by Role
add_table_slide("Value by Stakeholder",
    ["Stakeholder", "Key Benefits"],
    [
        ["Recruiters", "60% faster screening, bulk import, automated notifications"],
        ["Hiring Managers", "Real-time pipeline visibility, structured feedback, AI comparison"],
        ["Interviewers", "Mobile scorecards, AI-generated questions, context from prior stages"],
        ["Leadership", "Pipeline analytics, vendor tracking, compliance audit trail"]
    ])

# Slide 12: Section - Technical Architecture
add_section_slide("Technical Architecture")

# Slide 13: Tech Stack
add_table_slide("Technology Stack",
    ["Layer", "Technology", "Purpose"],
    [
        ["Frontend", "Streamlit", "Reactive Python web UI"],
        ["Backend", "Python 3.7+", "Core application logic"],
        ["Database", "SQLite", "Data persistence"],
        ["AI/ML", "Claude API / Bedrock", "Resume scoring, summarization"],
        ["Documents", "pypdf, python-docx", "Resume parsing"],
        ["Notifications", "Webhooks", "Slack and Teams"],
        ["Calendar", "ICS (RFC 5545)", "Interview scheduling"]
    ])

# Slide 14: Architecture
add_content_slide("System Architecture", [
    "Frontend Layer: Streamlit Web Application",
    "   - Responsive UI with Southwest Airlines branding",
    "   - Role-based navigation and dashboards",
    "",
    "Application Layer: Python Modules",
    "   - Auth, GenAI, Database, Notifications, Calendar",
    "",
    "Data Layer: SQLite Database",
    "   - Candidates, Jobs, Interviews, Scores, Users",
    "",
    "External: Claude API, Slack, Teams, Calendar"
])

# Slide 15: Section - Role-Based Access
add_section_slide("Role-Based Access Control")

# Slide 16: User Roles
add_table_slide("Four User Roles",
    ["Role", "Access Level", "Primary Functions"],
    [
        ["Admin", "Full system", "User management, config, all data"],
        ["Recruiter", "All candidates/jobs", "Sourcing, screening, pipeline mgmt"],
        ["Hiring Manager", "Assigned jobs only", "Review, feedback, decisions"],
        ["Interviewer", "Limited view", "Submit scorecards via mobile"]
    ])

# Slide 17: Section - Demo
add_section_slide("Live Demo")

# Slide 18: Demo Accounts
add_table_slide("Demo Login Accounts",
    ["Role", "Email"],
    [
        ["Admin", "admin@agentic.com"],
        ["Recruiter", "recruiter@agentic.com"],
        ["Hiring Manager", "hiring.manager@agentic.com"],
        ["Interviewer", "interviewer@agentic.com"]
    ])

# Slide 19: Demo Data
add_content_slide("Demo Data Available", [
    "3 Vendors: Acme Staffing, TechTalent, Two Roads",
    "7 Jobs: Including AI/ML Engineer - Agentic Systems",
    "26 Candidates: Distributed across all pipeline stages",
    "   - Resume Screen: 4    |    Phone Screen: 6",
    "   - Technical: 2         |    Behavioral: 4",
    "   - Offer: 4             |    Hired: 2",
    "5 Users: One per role type for testing RBAC"
])

# Slide 20: Demo Flow
add_content_slide("Demo Walkthrough", [
    "1. Login as Admin - show full navigation",
    "2. Dashboard - pipeline funnel and metrics",
    "3. Candidates - browse, filter, view AI scores",
    "4. Candidate Detail - resume analysis, stage progression",
    "5. AI Features - generate interview questions",
    "6. Mobile Scorecard - generate link, show mobile view",
    "7. Analytics - pipeline health, vendor scorecards",
    "8. Role Switch - show Hiring Manager filtered view"
])

# Slide 21: Section - Roadmap
add_section_slide("Roadmap & Next Steps")

# Slide 22: Roadmap
add_table_slide("Current State & Roadmap",
    ["Status", "Features"],
    [
        ["Implemented", "Core ATS, AI scoring, mobile scorecards, RBAC"],
        ["Implemented", "Bulk import, analytics, vendor tracking"],
        ["Phase 2", "Google Calendar OAuth integration"],
        ["Phase 3", "Microsoft 365 OAuth integration"],
        ["Future", "Advanced email automation, availability scheduling"]
    ])

# Slide 23: Success Metrics
add_table_slide("Success Metrics",
    ["Metric", "Target"],
    [
        ["Time-to-Screen", "< 24 hours"],
        ["Pipeline Visibility", "100% candidates tracked"],
        ["Interview Feedback", "> 90% within 24hrs"],
        ["User Adoption", "> 80% active weekly"]
    ])

# Slide 24: Thank You
add_title_slide("Thank You", "Questions?")

# Save
prs.save("Agentic_Program_ATS_Presentation.pptx")
print("Presentation created successfully!")
