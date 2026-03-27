"""ReportAgent — produces a structured, evidence-backed research report."""

from __future__ import annotations

import json
import re
import textwrap

from groq import Groq

import config
from shared_state import SharedState


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


# ── Context builders ─────────────────────────────────────────────────────────

def _build_context(state: SharedState) -> str:
    """Create a rich context string from the shared state for the LLM."""
    sections: list[str] = []

    # Themes
    sections.append("## Themes")
    for i, t in enumerate(state.themes):
        evidence_refs = ", ".join(str(idx) for idx in t.evidence_indices)
        sections.append(
            f"### Theme {i+1}: {t.name} (confidence: {t.confidence.value})\n"
            f"{t.summary}\n"
            f"Supporting evidence indices: [{evidence_refs}]"
        )

    # Contradictions
    if state.contradictions:
        sections.append("\n## Contradictions")
        for c in state.contradictions:
            refs = ", ".join(str(idx) for idx in c.evidence_indices)
            sections.append(
                f"- {c.description} (evidence: [{refs}])\n"
                f"  Resolution: {c.resolution}"
            )

    # Evidence list with source details
    sections.append("\n## Evidence")
    for i, ev in enumerate(state.evidence):
        src = state.sources[ev.source_index] if ev.source_index < len(state.sources) else None
        src_label = f"{src.title} — {src.url}" if src else "unknown"
        sections.append(
            f"[{i}] {ev.claim}\n"
            f"    Quote: \"{ev.quote}\"\n"
            f"    Source: {src_label}"
        )

    # Sources list for references
    sections.append("\n## Sources")
    for i, src in enumerate(state.sources):
        sections.append(f"[{i}] {src.title} — {src.url} (accessed {src.accessed_at})")

    return "\n".join(sections)


# ── Outline generation ───────────────────────────────────────────────────────

def generate_outline(client: Groq, state: SharedState) -> list[str]:
    """Ask the LLM to create a report outline based on the themes."""
    system = textwrap.dedent("""\
        You are a report planner. Given a research question and synthesised
        themes, produce a clear outline for a research report.

        Return a JSON array of section heading strings. A good outline
        typically includes: Title, Introduction, one section per major theme,
        Discussion (agreements/disagreements), Limitations, Conclusion,
        and References.

        Return ONLY the JSON array.
    """)
    theme_summary = "\n".join(
        f"- {t.name}: {t.summary}" for t in state.themes
    )
    user = (
        f"Research question: {state.research_question}\n\n"
        f"Themes:\n{theme_summary}"
    )
    raw = _chat(client, system, user)
    try:
        outline = json.loads(_extract_json(raw))
        if isinstance(outline, list):
            return [str(s) for s in outline]
    except json.JSONDecodeError:
        pass
    return ["Introduction", "Findings", "Discussion", "Limitations", "Conclusion", "References"]


# ── Report writing ───────────────────────────────────────────────────────────

def write_report(client: Groq, state: SharedState) -> str:
    """Generate the full markdown report."""
    system = textwrap.dedent("""\
        You are an academic research report writer. Write a well-structured
        research report in Markdown following the outline provided.

        Requirements:
        - Every major claim MUST cite its source using numbered references
          like [1], [2], etc. matching the source numbers provided.
        - Include a Limitations section acknowledging gaps and uncertainties.
        - Where sources disagree, present both perspectives fairly.
        - Do NOT invent claims beyond the evidence provided.
        - Use formal, clear academic language.
        - End with a References section listing all cited sources with URLs.
        - The report should be thorough but concise (aim for 1500-2500 words).
    """)
    user = (
        f"Research question: {state.research_question}\n\n"
        f"Report outline:\n" + "\n".join(f"- {s}" for s in state.report_outline) + "\n\n"
        f"Context:\n{_build_context(state)}"
    )
    return _chat(client, system, user)


# ── Public entry point ───────────────────────────────────────────────────────

def run(state: SharedState) -> SharedState:
    """Execute the ReportAgent stage."""
    print("\n📝  ReportAgent: starting...")
    client = _get_client()

    if not state.themes:
        print("   ⚠ No themes to report on.")
        return state

    # 1. Generate outline
    state.report_outline = generate_outline(client, state)
    print(f"   Outline ({len(state.report_outline)} sections):")
    for s in state.report_outline:
        print(f"     - {s}")

    # 2. Write the report
    print("   Writing report...")
    state.final_report = write_report(client, state)
    print(f"   Report generated ({len(state.final_report)} chars)")

    print("✅  ReportAgent: done.\n")
    return state
