"""SearchAgent — finds sources and extracts evidence for a research question."""

from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from groq import Groq

import config
from shared_state import Evidence, SharedState, Source


# ── Helpers ──────────────────────────────────────────────────────────────────────────

# print(f"Using Groq model: {config.GROQ_MODEL}")
# print(f"Groq API key set: {config.GROQ_API_KEY }")

def _get_client() -> Groq:
    return Groq(api_key=config.GROQ_API_KEY)


def _chat(client: Groq, system: str, user: str) -> str:
    """Simple wrapper around chat completions."""
    resp = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=config.GROQ_MODEL,
        temperature=config.TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def _extract_json(text: str) -> str:
    """Try to pull a JSON block out of an LLM response."""
    # Try fenced code block first
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


# ── Web fetch ────────────────────────────────────────────────────────────────

def _fetch_page_text(url: str) -> str:
    """Fetch a URL and return cleaned body text (truncated)."""
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as http:
            resp = http.get(url, headers={"User-Agent": "ResearchAssistant/1.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[: config.MAX_CONTENT_LENGTH]
    except Exception:
        return ""


# ── Core SearchAgent logic ───────────────────────────────────────────────────

def generate_search_queries(client: Groq, question: str) -> list[str]:
    """Use the LLM to create targeted search queries for the research question."""
    system = textwrap.dedent("""\
        You are a research assistant. Given a research question, generate a JSON
        list of concise web-search queries (strings) that would help find
        diverse, high-quality sources. Return ONLY a JSON array of strings.
    """)
    user = f"Research question: {question}\n\nGenerate {config.MAX_SEARCH_QUERIES} search queries."
    raw = _chat(client, system, user)
    try:
        queries = json.loads(_extract_json(raw))
        if isinstance(queries, list):
            return [str(q) for q in queries[: config.MAX_SEARCH_QUERIES]]
    except json.JSONDecodeError:
        pass
    # Fallback: use the question itself
    return [question]


def search_web(query: str, max_results: int = config.MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Run a DuckDuckGo search and return result dicts."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception:
        return []


def extract_evidence(
    client: Groq, question: str, source: Source
) -> list[Evidence]:
    """Use the LLM to extract evidence fragments from a source's content."""
    if not source.snippet:
        return []

    system = textwrap.dedent("""\
        You are a research evidence extractor. Given a research question and
        source text, extract important claims, facts, or arguments that are
        relevant to the question.

        Return a JSON array of objects, each with:
          - "claim": a concise statement of the claim/fact
          - "quote": a short direct quote supporting the claim
          - "relevance": why this matters for the research question

        Return ONLY the JSON array.
    """)
    user = (
        f"Research question: {question}\n\n"
        f"Source: {source.title} ({source.url})\n\n"
        f"Content:\n{source.snippet}"
    )
    raw = _chat(client, system, user)
    try:
        items = json.loads(_extract_json(raw))
        if not isinstance(items, list):
            return []
    except json.JSONDecodeError:
        return []

    evidence_list: list[Evidence] = []
    for item in items:
        if isinstance(item, dict) and "claim" in item:
            evidence_list.append(
                Evidence(
                    claim=item.get("claim", ""),
                    source_index=-1,  # will be set by caller
                    quote=item.get("quote", ""),
                    relevance=item.get("relevance", ""),
                )
            )
    return evidence_list


# ── Public entry point ───────────────────────────────────────────────────────

def run(state: SharedState) -> SharedState:
    """Execute the SearchAgent stage: discover sources and extract evidence."""
    print("\n🔍  SearchAgent: starting...")
    client = _get_client()

    # 1. Generate search queries
    queries = generate_search_queries(client, state.research_question)
    state.search_queries = queries
    print(f"   Generated {len(queries)} search queries")

    # 2. Search the web for each query
    seen_urls: set[str] = set()
    for query in queries:
        print(f"   Searching: {query}")
        results = search_web(query)
        for r in results:
            url = r.get("href", r.get("link", ""))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            source = Source(
                title=r.get("title", ""),
                url=url,
                snippet=r.get("body", ""),
                credibility_notes="",
            )
            state.sources.append(source)
    print(f"   Found {len(state.sources)} unique sources")

    # 3. Fetch full content for top sources and extract evidence
    for i, source in enumerate(state.sources):
        print(f"   Fetching [{i+1}/{len(state.sources)}]: {source.title[:60]}...")
        page_text = _fetch_page_text(source.url)
        if page_text:
            source.snippet = page_text  # replace the search snippet with richer content

        evidence = extract_evidence(client, state.research_question, source)
        for ev in evidence:
            ev.source_index = i
        state.evidence.extend(evidence)

    print(f"   Extracted {len(state.evidence)} evidence fragments")
    print("✅  SearchAgent: done.\n")
    return state




if __name__ == "__main__":
    # Example usage
    print(" Testing the chat function with a simple prompt...")
    client = _get_client()
    response = _chat(client, "You are a helpful assistant.", "What is 2+2?")
    print("Response:", response)