"""Webhook endpoints — WhatsApp Business API + generic webhook.

WhatsApp Cloud API flow:
1. Meta sends GET  /webhook/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
2. We verify and return the challenge.
3. Meta sends POST /webhook/whatsapp with message payloads.
4. We extract the text, create a research job, and send status updates.
"""

from __future__ import annotations

import hmac
import hashlib
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app.core import config
from app.core.jobs import create_job, get_job
from app.models.api import WebhookEvent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


# ── WhatsApp helpers ─────────────────────────────────────────────────────────

def _send_whatsapp_message(to: str, text: str) -> None:
    """Send a text message via WhatsApp Cloud API."""
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
        "text": {"body": text[:4096]},  # WhatsApp max message length
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        logger.info("WhatsApp message sent to %s", to)
    except Exception as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)


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

    # Create a background research job
    job = create_job(text)

    # Send acknowledgement
    _send_whatsapp_message(
        sender,
        f"🔍 Research started!\n\n"
        f"Question: {text[:200]}\n"
        f"Job ID: {job.job_id}\n\n"
        f"I'll send you the report when it's ready."
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
