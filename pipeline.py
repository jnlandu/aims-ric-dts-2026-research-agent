"""Pipeline — orchestrates the multi-agent research workflow."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import search_agent
import synthesis_agent
import report_agent
import evaluator
from shared_state import SharedState


def run_pipeline(question: str, output_dir: str = "output") -> SharedState:
    """Run the full research pipeline for a given question.

    Stages:
        1. SearchAgent   — discover sources, extract evidence
        2. SynthesisAgent — organise evidence into themes
        3. ReportAgent    — generate structured report
        4. Evaluator      — score report quality

    Returns the final SharedState with all outputs.
    """
    state = SharedState(research_question=question)

    print("=" * 70)
    print(f"  Multi-Agent Research Assistant")
    print(f"  Question: {question}")
    print("=" * 70)

    # Stage 1
    state = search_agent.run(state)

    # Stage 2
    state = synthesis_agent.run(state)

    # Stage 3
    state = report_agent.run(state)

    # Stage 4 (evaluation)
    state = evaluator.run(state)

    # Mark completed
    state.completed_at = datetime.now(timezone.utc).isoformat()

    # Save outputs
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Save the report as markdown
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in question[:50]).strip().replace(" ", "_")
    report_path = out / f"{slug}_report.md"
    report_path.write_text(state.final_report, encoding="utf-8")
    print(f"📄  Report saved to {report_path}")

    # Save the full state as JSON for inspection
    state_path = out / f"{slug}_state.json"
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    print(f"💾  Full state saved to {state_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("  Pipeline Summary")
    print("=" * 70)
    print(state.summary())
    print("=" * 70)

    return state
