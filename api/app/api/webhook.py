"""Webhook endpoints — WhatsApp Business API, Telegram Bot API + generic webhook.

WhatsApp Cloud API flow:
1. Meta sends GET  /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
2. We verify and return the challenge.
3. Meta sends POST /webhook/whatsapp with message payloads.
4. We extract the text, run a research job, and send back results.

Telegram Bot API flow:
1. Set webhook via https://api.telegram.org/bot<TOKEN>/setWebhook?url=<URL>/webhook/telegram
2. Telegram sends POST /webhook/telegram with Update JSON.
3. We extract the text, run a research job, and send back results.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import re
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

# ── Telegram helpers ─────────────────────────────────────────────────────────

# Telegram max message length
_TG_MAX_LEN = 4096

# Regex patterns for Markdown → Telegram conversion
_MERMAID_RE = re.compile(r"```mermaid\s*\n.*?```", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_IMG_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _markdown_to_telegram(md: str) -> str:
    """Convert a Markdown report to clean Telegram-friendly plain text.

    - Strips Mermaid code blocks (not renderable)
    - Strips HTML tags
    - Converts headings to bold uppercase lines
    - Converts images to alt text
    - Converts links to "text (url)" format
    - Preserves bold/italic (Telegram supports these in plain mode)
    """
    text = _MERMAID_RE.sub("", md)
    text = _HTML_TAG_RE.sub("", text)
    text = _IMG_RE.sub(r"[Image: \1]", text)
    text = _LINK_RE.sub(r"\1 (\2)", text)

    def _heading_to_bold(m: re.Match) -> str:
        level = len(m.group(1))
        title = m.group(2).strip()
        if level <= 2:
            return f"\n{'━' * 30}\n  {title.upper()}\n{'━' * 30}"
        return f"\n▸ {title}"

    text = _HEADING_RE.sub(_heading_to_bold, text)

    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _send_telegram_message(chat_id: int | str, text: str, parse_mode: str | None = None) -> None:
    """Send a single text message via Telegram Bot API."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram not configured — skipping send to %s", chat_id)
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text[:_TG_MAX_LEN],
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Telegram message sent to %s", chat_id)
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)


def _send_telegram_chunked(chat_id: int | str, text: str) -> None:
    """Send a long message as multiple Telegram messages, splitting on paragraph boundaries."""
    if len(text) <= _TG_MAX_LEN:
        _send_telegram_message(chat_id, text)
        return

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > _TG_MAX_LEN:
            if current:
                chunks.append(current)
            if len(paragraph) > _TG_MAX_LEN:
                for i in range(0, len(paragraph), _TG_MAX_LEN):
                    chunks.append(paragraph[i : i + _TG_MAX_LEN])
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
        _send_telegram_message(chat_id, header + chunk)


def _extract_telegram_message(body: dict) -> tuple[int, str] | None:
    """Extract (chat_id, text) from a Telegram Update payload.

    Returns None if not a text message.
    """
    try:
        message = body.get("message") or body.get("edited_message")
        if not message or "text" not in message:
            return None
        chat_id = message["chat"]["id"]
        text = message["text"]
        return chat_id, text
    except (KeyError, TypeError):
        return None


# ── Telegram delivery callbacks ──────────────────────────────────────────────

def _make_telegram_progress_callback(chat_id: int | str):
    """Return a callback that sends stage updates to the Telegram user."""
    def on_progress(job_id: str, status: JobStatus) -> None:
        label = _STATUS_EMOJI.get(status, str(status.value))
        if status in (JobStatus.SEARCHING, JobStatus.SYNTHESISING, JobStatus.REPORTING, JobStatus.EVALUATING):
            _send_telegram_message(chat_id, label)
    return on_progress


def _make_telegram_complete_callback(chat_id: int | str):
    """Return a callback that delivers the final report (or error) to the Telegram user."""
    def on_complete(job_id: str, job: JobResult) -> None:
        if job.status == JobStatus.FAILED:
            _send_telegram_message(
                chat_id,
                f"❌ Research failed.\n\nError: {job.error[:500]}\n\n"
                f"Please try again or rephrase your question.",
            )
            return

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

        report_text = _markdown_to_telegram(job.report)
        _send_telegram_chunked(chat_id, header + report_text)

    return on_complete


# ── Telegram webhook endpoint ────────────────────────────────────────────────

@router.post("/telegram")
async def telegram_inbound(request: Request):
    """Receive inbound Telegram messages and start research jobs."""
    body = await request.json()

    result = _extract_telegram_message(body)
    if result is None:
        return {"status": "ignored"}

    chat_id, text = result

    # Ignore bot commands like /start — only process research questions
    if text.startswith("/start"):
        _send_telegram_message(
            chat_id,
            "👋 Welcome to ML-ESS Research Assistant!\n\n"
            "Send me any research question and I'll produce a structured, "
            "evidence-backed report with quality scores.\n\n"
            "Example: What are the trade-offs between CNNs and Vision Transformers for medical imaging?",
        )
        return {"status": "start"}

    if text.startswith("/"):
        _send_telegram_message(chat_id, "Send me a research question as plain text.")
        return {"status": "ignored"}

    logger.info("Telegram message from %s: %s", chat_id, text[:80])

    job = create_job(
        text,
        on_progress=_make_telegram_progress_callback(chat_id),
        on_complete=_make_telegram_complete_callback(chat_id),
    )

    _send_telegram_message(
        chat_id,
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
