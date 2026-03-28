"""Webhook endpoints — WhatsApp Business API + generic webhook.

WhatsApp Cloud API flow:
1. Meta sends GET  /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
2. We verify and return the challenge.
3. Meta sends POST /webhook/whatsapp with message payloads.
4. We extract the text, run a research job, and send back results.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import textwrap

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app.core import config
from app.core.jobs import create_job, get_job
from app.models.api import JobResult, JobStatus, WebhookEvent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])

# Human-readable status labels
_STATUS_EMOJI: dict[JobStatus, str] = {
    JobStatus.PENDING: "⏳",
    JobStatus.SEARCHING: "🔍 Searching the web…",
    JobStatus.SYNTHESISING: "🧠 Synthesising evidence…",
    JobStatus.REPORTING: "📝 Writing report…",
    JobStatus.EVALUATING: "✅ Evaluating quality…",
    JobStatus.COMPLETED: "✅ Done!",
    JobStatus.FAILED: "❌ Something went wrong",
}

# WhatsApp max message body length
_WA_MAX_LEN = 4096


# ── WhatsApp helpers ─────────────────────────────────────────────────────────

def _send_whatsapp_message(to: str, text: str) -> None:
    """Send a single text message via WhatsApp Cloud API."""
    if not config.WHATSAPP_TOKEN or not config.WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp not configured — skipping send to %s", to)
        return

    url = f"https://graph.facebook.com/v18.0/{config.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:_WA_MAX_LEN]},
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        logger.info("WhatsApp message sent to %s", to)
    except Exception as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)


def _send_whatsapp_chunked(to: str, text: str) -> None:
    """Send a long message as multiple WhatsApp messages, splitting on paragraph boundaries."""
    if len(text) <= _WA_MAX_LEN:
        _send_whatsapp_message(to, text)
        return

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > _WA_MAX_LEN:
            if current:
                chunks.append(current)
            # If a single paragraph exceeds the limit, hard-wrap it
            if len(paragraph) > _WA_MAX_LEN:
                for i in range(0, len(paragraph), _WA_MAX_LEN):
                    chunks.append(paragraph[i : i + _WA_MAX_LEN])
                current = ""
            else:
                current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)

    total = len(chunks)
    for idx, chunk in enumerate(chunks, 1):
        header = f"[{idx}/{total}]\n\n" if total > 1 else ""
        _send_whatsapp_message(to, header + chunk)


def _extract_whatsapp_message(body: dict) -> tuple[str, str] | None:
    """Extract (sender_phone, text) from a WhatsApp webhook payload.

    Returns None if not a text message.
    """
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        message = value["messages"][0]
        if message["type"] != "text":
            return None
        sender = message["from"]
        text = message["text"]["body"]
        return sender, text
    except (KeyError, IndexError):
        return None


# ── WhatsApp delivery callbacks ──────────────────────────────────────────────

def _make_progress_callback(sender: str):
    """Return a callback that sends stage updates to the WhatsApp user."""
    def on_progress(job_id: str, status: JobStatus) -> None:
        label = _STATUS_EMOJI.get(status, str(status.value))
        # Only send for the main stage transitions, not COMPLETED/FAILED (handled by on_complete)
        if status in (JobStatus.SEARCHING, JobStatus.SYNTHESISING, JobStatus.REPORTING, JobStatus.EVALUATING):
            _send_whatsapp_message(sender, label)
    return on_progress


def _make_complete_callback(sender: str):
    """Return a callback that delivers the final report (or error) to the WhatsApp user."""
    def on_complete(job_id: str, job: JobResult) -> None:
        if job.status == JobStatus.FAILED:
            _send_whatsapp_message(
                sender,
                f"❌ Research failed.\n\nError: {job.error[:500]}\n\n"
                f"Please try again or rephrase your question.",
            )
            return

        # Build a summary header
        scores = ""
        if job.evaluation:
            scores = (
                f"\n📊 Quality scores:\n"
                f"  • Coverage: {job.evaluation.coverage:.0%}\n"
                f"  • Faithfulness: {job.evaluation.faithfulness:.0%}\n"
                f"  • Usefulness: {job.evaluation.usefulness:.0%}\n"
                f"  • Hallucination risk: {job.evaluation.hallucination_rate:.0%}"
            )

        header = (
            f"✅ Research complete!\n\n"
            f"📚 {job.sources_count} sources · {job.evidence_count} evidence pieces · {job.themes_count} themes"
            f"{scores}\n\n"
            f"─── Report ───\n\n"
        )

        _send_whatsapp_chunked(sender, header + job.report)

    return on_complete


# ── WhatsApp webhook endpoints ───────────────────────────────────────────────

@router.get("/whatsapp")
def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Verification endpoint for Meta webhook setup."""
    if hub_mode == "subscribe" and hub_verify_token == config.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified")
        return int(hub_challenge) if hub_challenge else ""
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_inbound(request: Request):
    """Receive inbound WhatsApp messages and start research jobs."""
    # Verify Meta signature if WEBHOOK_SECRET is configured
    if config.WEBHOOK_SECRET:
        signature = request.headers.get("x-hub-signature-256", "")
        body_bytes = await request.body()
        expected = "sha256=" + hmac.new(
            config.WEBHOOK_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
        body = __import__("json").loads(body_bytes)
    else:
        body = await request.json()

    result = _extract_whatsapp_message(body)
    if result is None:
        return {"status": "ignored"}

    sender, text = result
    logger.info("WhatsApp message from %s: %s", sender, text[:80])

    # Create a background research job with WhatsApp delivery callbacks
    job = create_job(
        text,
        on_progress=_make_progress_callback(sender),
        on_complete=_make_complete_callback(sender),
    )

    # Send acknowledgement
    _send_whatsapp_message(
        sender,
        f"🔍 Research started!\n\n"
        f"Question: {text[:200]}\n"
        f"Job ID: {job.job_id}\n\n"
        f"I'll send you progress updates and the full report when it's ready.",
    )

    return {"status": "accepted", "job_id": job.job_id}


# ── Generic webhook endpoint ────────────────────────────────────────────────

@router.post("/inbound")
async def generic_inbound(event: WebhookEvent):
    """Generic webhook endpoint for any integration (Slack, custom frontend, etc.)."""
    if not event.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    job = create_job(event.message.strip())
    logger.info("Generic webhook job created: %s from %s", job.job_id, event.source)

    return {"status": "accepted", "job_id": job.job_id, "question": job.question}
