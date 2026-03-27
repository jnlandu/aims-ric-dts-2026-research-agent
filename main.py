#!/usr/bin/env python3
"""Multi-Agent Research Assistant — CLI entry point.

Usage:
    python main.py "Your research question here"
    python main.py                      # uses default example prompts
"""

from __future__ import annotations

import sys

from pipeline import run_pipeline


# ── Default example prompts (one technical, one policy) ──────────────────────

EXAMPLE_PROMPTS = [
    "What are the main trade-offs between CNNs and Vision Transformers for medical imaging?",
    "What are the opportunities and risks of adopting AI in higher education institutions?",
]


def main() -> None:
    if len(sys.argv) > 1:
        # Single question from CLI argument
        question = " ".join(sys.argv[1:])
        run_pipeline(question)
    else:
        # Run both example prompts
        print("No question provided. Running both example prompts.\n")
        for i, question in enumerate(EXAMPLE_PROMPTS, 1):
            print(f"\n{'#' * 70}")
            print(f"  PROMPT {i} of {len(EXAMPLE_PROMPTS)}")
            print(f"{'#' * 70}\n")
            run_pipeline(question, output_dir=f"output/prompt_{i}")


if __name__ == "__main__":
    main()
