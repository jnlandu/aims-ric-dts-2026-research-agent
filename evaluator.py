"""Evaluator — scores the final report on a defined rubric."""

from __future__ import annotations

import json
import re
import textwrap

from groq import Groq

import config
from shared_state import EvaluationScores, SharedState


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


def run(state: SharedState) -> SharedState:
    """Evaluate the final report against a quality rubric."""
    print("\n📊  Evaluator: starting...")
    client = _get_client()

    if not state.final_report:
        print("   ⚠ No report to evaluate.")
        return state

    # Build a summary of available evidence for the evaluator
    evidence_summary = "\n".join(
        f"[{i}] {ev.claim} (source: {state.sources[ev.source_index].title if ev.source_index < len(state.sources) else 'unknown'})"
        for i, ev in enumerate(state.evidence)
    )

    system = textwrap.dedent("""\
        You are a research quality evaluator. You are given:
        1. A research question
        2. The evidence that was available to the report writer
        3. The final report

        Score the report on four dimensions (each 0.0 to 1.0):
        - coverage: Does the report address the key parts of the question?
        - faithfulness: Are the claims in the report supported by the evidence provided?
        - hallucination_rate: What proportion of claims appear unsupported or overstated?
          (0.0 = no hallucination, 1.0 = entirely hallucinated)
        - usefulness: Is the report clear, relevant, and useful for decision-making?

        Return a JSON object:
        {
          "coverage": 0.85,
          "faithfulness": 0.9,
          "hallucination_rate": 0.1,
          "usefulness": 0.8,
          "reasoning": "Brief explanation of scores"
        }
        Return ONLY the JSON object.
    """)
    user = (
        f"Research question: {state.research_question}\n\n"
        f"Available evidence:\n{evidence_summary}\n\n"
        f"Final report:\n{state.final_report}"
    )
    raw = _chat(client, system, user)
    try:
        scores = json.loads(_extract_json(raw))
        state.evaluation = EvaluationScores(
            coverage=float(scores.get("coverage", 0)),
            faithfulness=float(scores.get("faithfulness", 0)),
            hallucination_rate=float(scores.get("hallucination_rate", 0)),
            usefulness=float(scores.get("usefulness", 0)),
            reasoning=scores.get("reasoning", ""),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"   ⚠ Could not parse evaluation: {exc}")
        return state

    print(f"   Coverage:          {state.evaluation.coverage:.2f}")
    print(f"   Faithfulness:      {state.evaluation.faithfulness:.2f}")
    print(f"   Hallucination:     {state.evaluation.hallucination_rate:.2f}")
    print(f"   Usefulness:        {state.evaluation.usefulness:.2f}")
    print(f"   Reasoning:         {state.evaluation.reasoning[:120]}")
    print("✅  Evaluator: done.\n")
    return state
