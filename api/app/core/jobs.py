"""In-memory job store and background worker for async research jobs.

For production, swap this with Redis + Celery or similar.
"""

from __future__ import annotations

import logging
import threading
import traceback
import uuid
from typing import Callable, Dict, Optional

from app.core.pipeline import run_pipeline
from app.models.api import JobResult, JobStatus
from app.models.state import SharedState

logger = logging.getLogger(__name__)

# Type alias for callbacks
ProgressCallback = Callable[[str, JobStatus], None]   # (job_id, new_status)
CompleteCallback = Callable[[str, JobResult], None]    # (job_id, final_result)

# In-memory store  (thread-safe via the GIL for reads/writes to dict)
_jobs: Dict[str, JobResult] = {}
_states: Dict[str, SharedState] = {}


def create_job(
    question: str,
    on_progress: Optional[ProgressCallback] = None,
    on_complete: Optional[CompleteCallback] = None,
) -> JobResult:
    """Create a new research job and start it in a background thread."""
    job_id = uuid.uuid4().hex[:12]
    job = JobResult(
        job_id=job_id,
        status=JobStatus.PENDING,
        question=question,
    )
    _jobs[job_id] = job

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, question, on_progress, on_complete),
        daemon=True,
    )
    thread.start()
    logger.info("Job %s created for: %s", job_id, question[:80])
    return job


def get_job(job_id: str) -> JobResult | None:
    """Get job status and result by ID."""
    return _jobs.get(job_id)


def get_job_state(job_id: str) -> SharedState | None:
    """Get the full pipeline state (reasoning details) for a completed job."""
    return _states.get(job_id)


def list_jobs() -> list[JobResult]:
    """List all jobs (most recent first)."""
    return list(reversed(_jobs.values()))


def _set_status(
    job: JobResult,
    job_id: str,
    status: JobStatus,
    on_progress: Optional[ProgressCallback],
) -> None:
    """Update job status and fire progress callback."""
    job.status = status
    if on_progress:
        try:
            on_progress(job_id, status)
        except Exception:
            logger.exception("Progress callback failed for job %s", job_id)


def _run_job(
    job_id: str,
    question: str,
    on_progress: Optional[ProgressCallback],
    on_complete: Optional[CompleteCallback],
) -> None:
    """Execute the pipeline in a background thread and update job status."""
    job = _jobs[job_id]
    try:
        _set_status(job, job_id, JobStatus.SEARCHING, on_progress)
        state = run_pipeline(
            question,
            output_dir=f"output/{job_id}",
            on_stage=lambda stage: _set_status(job, job_id, stage, on_progress),
        )

        job.report = state.final_report
        job.evaluation = state.evaluation
        job.sources_count = len(state.sources)
        job.evidence_count = len(state.evidence)
        job.themes_count = len(state.themes)
        _states[job_id] = state
        _set_status(job, job_id, JobStatus.COMPLETED, on_progress)
        logger.info("Job %s completed", job_id)

    except Exception as exc:
        job.error = str(exc)
        _set_status(job, job_id, JobStatus.FAILED, on_progress)
        logger.error("Job %s failed: %s\n%s", job_id, exc, traceback.format_exc())

    finally:
        if on_complete:
            try:
                on_complete(job_id, _jobs[job_id])
            except Exception:
                logger.exception("Complete callback failed for job %s", job_id)
