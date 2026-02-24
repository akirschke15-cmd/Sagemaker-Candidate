"""
FastAPI REST API for ATS Application

Provides REST endpoints for candidate tracking, job management, interview scheduling,
and analytics. Can run alongside the Streamlit app.
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import os

from config import settings
from database import (
    # Candidates
    create_candidate, get_candidates, get_candidate, update_candidate,
    advance_candidate, reject_candidate,
    STAGES,
    # Jobs
    create_job, get_jobs, get_job, update_job,
    # Interviews
    schedule_interview, get_interviews,
    # Analytics
    get_pipeline_stats_multirole, get_pipeline_velocity, get_stage_conversion_rates,
    # Connection
    get_connection
)
from rate_limiter import APIRateLimiter

logger = logging.getLogger(__name__)
VALID_STAGES = set(STAGES)

# ============ FastAPI App ============
app = FastAPI(
    title="ATS API",
    description="Applicant Tracking System REST API",
    version="1.0.0"
)

# CORS middleware — restrict origins in production
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "X-API-Key", "Content-Type"],
)


# ============ Security ============
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key — fail closed when not configured"""
    if not settings.API_KEY:
        raise HTTPException(status_code=503, detail="API authentication not configured")
    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


async def rate_limit_dependency(request: Request):
    """Rate limit API requests"""
    identifier = request.headers.get("x-api-key") or request.client.host or "anonymous"
    allowed, retry_after = APIRateLimiter.check(identifier)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)}
        )


# ============ Pydantic Models ============

# Candidate Models
class CandidateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    job_id: Optional[int] = None
    vendor_id: Optional[int] = None
    resume_text: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    job_id: Optional[int] = None
    vendor_id: Optional[int] = None
    current_stage: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    expected_hourly_rate: Optional[float] = None


class CandidateResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    current_stage: str
    status: str
    job_id: Optional[int]
    job_title: Optional[str]
    vendor_id: Optional[int]
    vendor_name: Optional[str]
    ai_resume_score: Optional[float]
    created_at: str
    updated_at: str


# Job Models
class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    slots: int = Field(1, ge=1)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    slots: Optional[int] = Field(None, ge=1)


class JobResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    requirements: Optional[str]
    department: Optional[str]
    status: str
    slots: int
    created_at: str
    updated_at: str


# Interview Models
class InterviewCreate(BaseModel):
    candidate_id: int = Field(..., gt=0)
    stage: str = Field(..., min_length=1)
    scheduled_time: str = Field(..., description="ISO format datetime")
    interviewer_email: Optional[str] = Field(None, max_length=255)
    interviewer_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class InterviewResponse(BaseModel):
    id: int
    candidate_id: int
    candidate_name: Optional[str]
    job_title: Optional[str]
    stage: str
    scheduled_time: str
    interviewer_email: Optional[str]
    interviewer_name: Optional[str]
    location: Optional[str]
    meeting_link: Optional[str]
    status: str


# Pagination Model
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    limit: int
    offset: int


# ============ Health Check ============
@app.get("/api/health")
async def health_check():
    """Health check endpoint with database status"""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "timestamp": datetime.now().isoformat()}
    except Exception:
        logger.exception("Health check: database connection failed")
        return {"status": "degraded", "timestamp": datetime.now().isoformat()}


# ============ Candidate Endpoints ============
@app.get("/api/candidates", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def list_candidates(
    status: Optional[str] = Query("Active", description="Filter by status"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """List candidates with filters and pagination"""
    try:
        # Get all matching candidates
        candidates = get_candidates(job_id=job_id, stage=stage, status=status)

        # Apply pagination
        total = len(candidates)
        paginated = candidates[offset:offset + limit]

        return {
            "items": paginated,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.exception("Error fetching candidates")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/candidates/{candidate_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def get_candidate_detail(candidate_id: int):
    """Get candidate details by ID"""
    try:
        candidate = get_candidate(candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return candidate
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching candidate")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/candidates", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)], status_code=201)
async def create_candidate_endpoint(candidate: CandidateCreate):
    """Create a new candidate"""
    try:
        candidate_id = create_candidate(
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            job_id=candidate.job_id,
            vendor_id=candidate.vendor_id,
            resume_text=candidate.resume_text
        )

        # Fetch and return the created candidate
        created = get_candidate(candidate_id)
        return created
    except Exception as e:
        logger.exception("Error creating candidate")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/api/candidates/{candidate_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def update_candidate_endpoint(candidate_id: int, candidate: CandidateUpdate):
    """Update candidate fields"""
    try:
        # Check if candidate exists
        existing = get_candidate(candidate_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Build update dict from non-None fields
        update_data = {k: v for k, v in candidate.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update candidate
        update_candidate(candidate_id, **update_data)

        # Fetch and return updated candidate
        updated = get_candidate(candidate_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating candidate")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/candidates/{candidate_id}/advance", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def advance_candidate_endpoint(candidate_id: int, new_stage: str = Query(..., description="New stage name")):
    """Advance candidate to next stage"""
    try:
        # Validate stage
        if new_stage not in VALID_STAGES:
            raise HTTPException(status_code=422, detail=f"Invalid stage. Must be one of: {', '.join(STAGES)}")

        # Check if candidate exists
        existing = get_candidate(candidate_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Advance candidate
        advance_candidate(candidate_id, new_stage)

        # Fetch and return updated candidate
        updated = get_candidate(candidate_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error advancing candidate")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/candidates/{candidate_id}/reject", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def reject_candidate_endpoint(candidate_id: int):
    """Reject candidate"""
    try:
        # Check if candidate exists
        existing = get_candidate(candidate_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Reject candidate
        reject_candidate(candidate_id)

        # Fetch and return updated candidate
        updated = get_candidate(candidate_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error rejecting candidate")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Job Endpoints ============
@app.get("/api/jobs", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def list_jobs(status: Optional[str] = Query(None, description="Filter by status")):
    """List jobs with optional status filter"""
    try:
        jobs = get_jobs(status=status)
        return jobs
    except Exception as e:
        logger.exception("Error fetching jobs")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/jobs/{job_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def get_job_detail(job_id: int):
    """Get job details with stats"""
    try:
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Get candidate stats for this job
        candidates = get_candidates(job_id=job_id)
        job['total_candidates'] = len(candidates)
        job['active_candidates'] = len([c for c in candidates if c['status'] == 'Active'])
        job['hired_count'] = len([c for c in candidates if c['current_stage'] == 'Hired'])
        job['remaining_slots'] = job['slots'] - job['hired_count']

        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching job")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/jobs", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)], status_code=201)
async def create_job_endpoint(job: JobCreate):
    """Create a new job"""
    try:
        job_id = create_job(
            title=job.title,
            description=job.description,
            requirements=job.requirements,
            department=job.department,
            slots=job.slots
        )

        # Fetch and return the created job
        created = get_job(job_id)
        return created
    except Exception as e:
        logger.exception("Error creating job")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/api/jobs/{job_id}", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def update_job_endpoint(job_id: int, job: JobUpdate):
    """Update job fields"""
    try:
        # Check if job exists
        existing = get_job(job_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Job not found")

        # Build update dict from non-None fields
        update_data = {k: v for k, v in job.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update job
        update_job(job_id, **update_data)

        # Fetch and return updated job
        updated = get_job(job_id)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating job")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Interview Endpoints ============
@app.get("/api/interviews", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def list_interviews(
    upcoming_only: bool = Query(False, description="Only return upcoming interviews")
):
    """List interviews with optional upcoming filter"""
    try:
        interviews = get_interviews(upcoming_only=upcoming_only)
        return interviews
    except Exception as e:
        logger.exception("Error fetching interviews")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/interviews", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)], status_code=201)
async def schedule_interview_endpoint(interview: InterviewCreate):
    """Schedule a new interview"""
    try:
        # Validate candidate exists
        candidate = get_candidate(interview.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Validate datetime format
        try:
            datetime.fromisoformat(interview.scheduled_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid datetime format. Use ISO format.")

        # Schedule interview
        interview_id = schedule_interview(
            candidate_id=interview.candidate_id,
            stage=interview.stage,
            scheduled_time=interview.scheduled_time,
            interviewer_email=interview.interviewer_email,
            interviewer_name=interview.interviewer_name,
            location=interview.location,
            meeting_link=interview.meeting_link
        )

        # Fetch and return created interview
        interviews = get_interviews(candidate_id=interview.candidate_id)
        created = next((i for i in interviews if i['id'] == interview_id), None)

        return created if created else {"id": interview_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error scheduling interview")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Analytics Endpoints ============
@app.get("/api/analytics/pipeline", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def get_pipeline_analytics(job_id: Optional[int] = Query(None, description="Filter by job ID")):
    """Get pipeline statistics by stage"""
    try:
        stats = get_pipeline_stats_multirole(job_id=job_id)
        return {
            "job_id": job_id,
            "stats_by_stage": stats,
            "total_active": sum(stats.values())
        }
    except Exception as e:
        logger.exception("Error fetching pipeline stats")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/analytics/velocity", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def get_velocity_analytics(job_id: Optional[int] = Query(None, description="Filter by job ID")):
    """Get pipeline velocity (days in each stage)"""
    try:
        velocity = get_pipeline_velocity(job_id=job_id)
        return {
            "job_id": job_id,
            "velocity_by_stage": velocity
        }
    except Exception as e:
        logger.exception("Error fetching velocity stats")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/analytics/conversion", dependencies=[Depends(verify_api_key), Depends(rate_limit_dependency)])
async def get_conversion_analytics(job_id: Optional[int] = Query(None, description="Filter by job ID")):
    """Get stage conversion rates"""
    try:
        conversion = get_stage_conversion_rates(job_id=job_id)
        return {
            "job_id": job_id,
            "conversion_rates": conversion
        }
    except Exception as e:
        logger.exception("Error fetching conversion rates")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============ Root Endpoint ============
@app.get("/")
async def root():
    """API root with available endpoints"""
    return {
        "name": "ATS API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "candidates": "/api/candidates",
            "jobs": "/api/jobs",
            "interviews": "/api/interviews",
            "analytics": {
                "pipeline": "/api/analytics/pipeline",
                "velocity": "/api/analytics/velocity",
                "conversion": "/api/analytics/conversion"
            }
        },
        "docs": "/docs",
        "authentication": "X-API-Key header"
    }
