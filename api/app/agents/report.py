"""ReportAgent — produces a structured, evidence-backed research report."""

from __future__ import annotations

import logging
import textwrap

from app.core.llm import get_client, chat, chat_json
from app.models.state import SharedState

logger = logging.getLogger(__name__)


def _build_context(state: SharedState) -> str:
    sections: list[str] = []

    sections.append("## Themes")
    for i, t in enumerate(state.themes):
        refs = ", ".join(str(idx) for idx in t.evidence_indices)
        sections.append(
            f"### Theme {i+1}: {t.name} (confidence: {t.confidence.value})\n"
            f"{t.summary}\n"
            f"Supporting evidence indices: [{refs}]"
        )

    if state.contradictions:
        sections.append("\n## Contradictions")
        for c in state.contradictions:
            refs = ", ".join(str(idx) for idx in c.evidence_indices)
            sections.append(
                f"- {c.description} (evidence: [{refs}])\n"
                f"  Resolution: {c.resolution}"
            )

    sections.append("\n## Evidence")
    for i, ev in enumerate(state.evidence):
        src = state.sources[ev.source_index] if ev.source_index < len(state.sources) else None
        src_label = f"{src.title} — {src.url}" if src else "unknown"
        sections.append(
            f"[{i}] {ev.claim}\n"
            f"    Quote: \"{ev.quote}\"\n"
            f"    Source: {src_label}"
        )

    sections.append("\n## Sources")
    for i, src in enumerate(state.sources):
        sections.append(f"[{i}] {src.title} — {src.url} (accessed {src.accessed_at})")

    return "\n".join(sections)


def _generate_outline(client, state: SharedState) -> list[str]:
    system = textwrap.dedent("""\
        You are a report planner. Given a research question and synthesised
        themes, produce a clear outline for a research report.

        Return a JSON array of section heading strings. A good outline
        typically includes: Title, Introduction, one section per major theme,
        Discussion (agreements/disagreements), Limitations, Conclusion,
        and References.

        Return ONLY the JSON array.
    """)
    theme_summary = "\n".join(f"- {t.name}: {t.summary}" for t in state.themes)
    user = f"Research question: {state.research_question}\n\nThemes:\n{theme_summary}"
    result = chat_json(client, system, user)
    if isinstance(result, list) and result:
        return [str(s) for s in result]
    return ["Introduction", "Findings", "Discussion", "Limitations", "Conclusion", "References"]


def _write_report(client, state: SharedState) -> str:
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
    return chat(client, system, user)


def run(state: SharedState) -> SharedState:
    logger.info("ReportAgent: starting...")
    client = get_client()

    if not state.themes:
        logger.warning("No themes to report on.")
        return state

    state.report_outline = _generate_outline(client, state)
    logger.info("Outline: %s", state.report_outline)

    state.final_report = _write_report(client, state)
    logger.info("Report generated (%d chars)", len(state.final_report))

    return state
