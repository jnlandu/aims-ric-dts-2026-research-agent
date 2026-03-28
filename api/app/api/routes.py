"""REST API routes for the research assistant."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.jobs import create_job, get_job, list_jobs
from app.models.api import JobResponse, JobResult, ResearchRequest

router = APIRouter(tags=["research"])


@router.post("/research", response_model=JobResponse, status_code=202)
def submit_research(req: ResearchRequest):
    """Submit a research question. Returns a job ID immediately.

    The pipeline runs in the background. Poll GET /api/research/{job_id}
    for status and results.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    job = create_job(req.question.strip())
    return JobResponse(job_id=job.job_id, status=job.status, question=job.question)


@router.get("/research/{job_id}", response_model=JobResult)
def get_research(job_id: str):
    """Get the status and result of a research job."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/research", response_model=list[JobResult])
def list_research():
    """List all research jobs."""
    return list_jobs()


@router.get("/health")
def health():
    return {"status": "ok"}
