"""In-memory job store and background worker for async research jobs.

For production, swap this with Redis + Celery or similar.
"""

from __future__ import annotations

import logging
import threading
import traceback
import uuid
from typing import Dict

from app.core.pipeline import run_pipeline
from app.models.api import JobResult, JobStatus

logger = logging.getLogger(__name__)

# In-memory store  (thread-safe via the GIL for reads/writes to dict)
_jobs: Dict[str, JobResult] = {}


def create_job(question: str) -> JobResult:
    """Create a new research job and start it in a background thread."""
    job_id = uuid.uuid4().hex[:12]
    job = JobResult(
        job_id=job_id,
        status=JobStatus.PENDING,
        question=question,
    )
    _jobs[job_id] = job

    thread = threading.Thread(target=_run_job, args=(job_id, question), daemon=True)
    thread.start()
    logger.info("Job %s created for: %s", job_id, question[:80])
    return job


def get_job(job_id: str) -> JobResult | None:
    """Get job status and result by ID."""
    return _jobs.get(job_id)


def list_jobs() -> list[JobResult]:
    """List all jobs (most recent first)."""
    return list(reversed(_jobs.values()))


def _run_job(job_id: str, question: str) -> None:
    """Execute the pipeline in a background thread and update job status."""
    job = _jobs[job_id]
    try:
        job.status = JobStatus.SEARCHING
        state = run_pipeline(question, output_dir=f"output/{job_id}")

        job.report = state.final_report
        job.evaluation = state.evaluation
        job.sources_count = len(state.sources)
        job.evidence_count = len(state.evidence)
        job.themes_count = len(state.themes)
        job.status = JobStatus.COMPLETED
        logger.info("Job %s completed", job_id)

    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        logger.error("Job %s failed: %s\n%s", job_id, exc, traceback.format_exc())
