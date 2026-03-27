"""SynthesisAgent — organises evidence into themes and identifies contradictions."""

from __future__ import annotations

import json
import re
import textwrap

from groq import Groq

import config
from shared_state import Confidence, Contradiction, SharedState, Theme


# ── Helpers ──────────────────────────────────────────────────────────────────────────

def _get_client() -> Groq:
    return Groq(api_key=config.GROQ_API_KEY)


def _chat(client: Groq, system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=config.TEMPERATURE,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


# ── Evidence formatting for the LLM ─────────────────────────────────────────

def _format_evidence(state: SharedState) -> str:
    """Build a numbered list of evidence for the LLM prompt."""
    lines: list[str] = []
    for i, ev in enumerate(state.evidence):
        src = state.sources[ev.source_index] if ev.source_index < len(state.sources) else None
        src_label = src.title if src else "unknown source"
        lines.append(
            f"[{i}] Claim: {ev.claim}\n"
            f"    Quote: {ev.quote}\n"
            f"    Source: {src_label}\n"
            f"    Relevance: {ev.relevance}"
        )
    return "\n\n".join(lines)


# ── Core synthesis ───────────────────────────────────────────────────────────

def identify_themes(client: Groq, state: SharedState) -> list[Theme]:
    """Group evidence into thematic clusters."""
    system = textwrap.dedent("""\
        You are a research synthesis expert. You are given a research question
        and a numbered list of evidence fragments. Group them into coherent
        themes. Each theme should capture a distinct aspect of the answer.

        Return a JSON array of theme objects:
        [
          {
            "name": "Theme title",
            "summary": "2-3 sentence summary of this theme",
            "evidence_indices": [0, 3, 7],
            "confidence": "high" | "medium" | "low"
          }
        ]
        Return ONLY the JSON array.
    """)
    user = (
        f"Research question: {state.research_question}\n\n"
        f"Evidence:\n{_format_evidence(state)}"
    )
    raw = _chat(client, system, user)
    try:
        items = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return []

    themes: list[Theme] = []
    for item in items:
        if isinstance(item, dict) and "name" in item:
            themes.append(
                Theme(
                    name=item.get("name", ""),
                    summary=item.get("summary", ""),
                    evidence_indices=item.get("evidence_indices", []),
                    confidence=Confidence(item.get("confidence", "medium")),
                )
            )
    return themes


def identify_contradictions(client: Groq, state: SharedState) -> list[Contradiction]:
    """Find disagreements across the evidence."""
    system = textwrap.dedent("""\
        You are a research analyst. You are given a research question and
        a numbered list of evidence fragments. Identify any contradictions,
        disagreements, or tensions between pieces of evidence.

        Return a JSON array of contradiction objects:
        [
          {
            "description": "What the disagreement is about",
            "evidence_indices": [2, 5],
            "resolution": "How the contradiction might be explained or reconciled"
          }
        ]
        If there are no contradictions, return an empty array [].
        Return ONLY the JSON array.
    """)
    user = (
        f"Research question: {state.research_question}\n\n"
        f"Evidence:\n{_format_evidence(state)}"
    )
    raw = _chat(client, system, user)
    try:
        items = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        return []

    contradictions: list[Contradiction] = []
    for item in items:
        if isinstance(item, dict) and "description" in item:
            contradictions.append(
                Contradiction(
                    description=item.get("description", ""),
                    evidence_indices=item.get("evidence_indices", []),
                    resolution=item.get("resolution", ""),
                )
            )
    return contradictions


# ── Public entry point ───────────────────────────────────────────────────────

def run(state: SharedState) -> SharedState:
    """Execute the SynthesisAgent stage."""
    print("\n🧩  SynthesisAgent: starting...")
    client = _get_client()

    if not state.evidence:
        print("   ⚠ No evidence to synthesise.")
        return state

    # 1. Identify themes
    state.themes = identify_themes(client, state)
    print(f"   Identified {len(state.themes)} themes")
    for t in state.themes:
        print(f"     - {t.name} ({t.confidence.value}, {len(t.evidence_indices)} pieces)")

    # 2. Identify contradictions
    state.contradictions = identify_contradictions(client, state)
    print(f"   Found {len(state.contradictions)} contradictions")
    for c in state.contradictions:
        print(f"     - {c.description[:80]}")

    print("✅  SynthesisAgent: done.\n")
    return state
