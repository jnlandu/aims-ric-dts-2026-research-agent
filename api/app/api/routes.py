"""REST API routes for the research assistant."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.jobs import create_job, get_job, get_job_events, get_job_state, list_jobs
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


@router.get("/research/{job_id}/reasoning")
def get_reasoning(job_id: str):
    """Get the full reasoning steps for a completed job.

    Returns sources, evidence, themes, contradictions, search queries,
    report outline, and evaluation reasoning.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    state = get_job_state(job_id)
    if state is None:
        return {
            "job_id": job_id,
            "status": job.status,
            "available": False,
            "steps": [],
        }

    steps = []

    # 1. Search queries
    steps.append({
        "stage": "search",
        "title": "Search Queries",
        "description": f"Generated {len(state.search_queries)} search queries",
        "data": state.search_queries,
    })

    # 2. Sources discovered
    steps.append({
        "stage": "search",
        "title": "Sources Found",
        "description": f"Discovered {len(state.sources)} sources",
        "data": [s.model_dump() for s in state.sources],
    })

    # 3. Evidence extracted
    steps.append({
        "stage": "search",
        "title": "Evidence Extracted",
        "description": f"Extracted {len(state.evidence)} pieces of evidence",
        "data": [e.model_dump() for e in state.evidence],
    })

    # 4. Themes identified
    steps.append({
        "stage": "synthesis",
        "title": "Themes Identified",
        "description": f"Identified {len(state.themes)} themes",
        "data": [t.model_dump() for t in state.themes],
    })

    # 5. Contradictions detected
    if state.contradictions:
        steps.append({
            "stage": "synthesis",
            "title": "Contradictions Detected",
            "description": f"Found {len(state.contradictions)} contradictions",
            "data": [c.model_dump() for c in state.contradictions],
        })

    # 6. Report outline
    if state.report_outline:
        steps.append({
            "stage": "report",
            "title": "Report Outline",
            "description": f"Planned {len(state.report_outline)} sections",
            "data": state.report_outline,
        })

    # 7. Evaluation reasoning
    if state.evaluation and state.evaluation.reasoning:
        steps.append({
            "stage": "evaluation",
            "title": "Evaluation Reasoning",
            "description": "Quality assessment rationale",
            "data": state.evaluation.reasoning,
        })

    return {
        "job_id": job_id,
        "status": job.status,
        "available": True,
        "steps": steps,
    }


@router.get("/research", response_model=list[JobResult])
def list_research():
    """List all research jobs."""
    return list_jobs()


@router.get("/research/{job_id}/events")
async def stream_events(job_id: str):
    """Stream reasoning events for a job via Server-Sent Events.

    The client subscribes and receives structured events as they happen.
    The stream closes when the job completes or fails.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator():
        cursor = 0
        while True:
            events = get_job_events(job_id, after=cursor)
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
                cursor += 1
                if event["type"] in ("job_completed", "job_failed"):
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
def health():
    return {"status": "ok"}
