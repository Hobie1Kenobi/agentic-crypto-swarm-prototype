"""
LLM-backed handlers for T54 seller SKUs; outputs validated against Pydantic models.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from t54_seller_models import (
    ConstitutionAuditLiteResponse,
    HelloResponse,
    ResearchBriefResponse,
    ResearchSource,
    StructuredQueryResponse,
)

CONSTITUTION = (
    "Only ethical, non-harmful services; no gambling, no illegal content; "
    "sustainable compute usage simulation."
)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            out = json.loads(m.group(1).strip())
            if isinstance(out, dict):
                return out
        except json.JSONDecodeError:
            pass
    raise ValueError("model did not return a JSON object")


def _llm() -> Any:
    from swarm.llm import get_llm

    return get_llm()


def run_structured_query(q: str) -> StructuredQueryResponse:
    q = (q or "").strip() or "What is ethical agent commerce?"
    if len(q) > 512:
        q = q[:512]
    try:
        from api_402 import generate_response_for_query

        answer = generate_response_for_query(q)
    except Exception:
        llm = _llm()
        resp = llm.invoke(
            [
                SystemMessage(content=CONSTITUTION),
                HumanMessage(
                    content=(
                        f"Answer in one or two sentences. Query: {q}. Output only the answer."
                    )
                ),
            ]
        )
        answer = (getattr(resp, "content", None) or str(resp)).strip() or "Response generated."
    return StructuredQueryResponse(query=q, answer=answer)


def run_research_brief(topic: str, context: str | None) -> ResearchBriefResponse:
    topic = (topic or "").strip()
    if not topic:
        topic = "Ethical agent commerce on public testnets"
    if len(topic) > 256:
        topic = topic[:256]
    ctx = (context or "").strip()[:2000]
    llm = _llm()
    prompt = f"""You produce a short research brief as JSON only (no markdown outside JSON).
Topic: {topic}
Optional context from buyer: {ctx or "(none)"}

Return exactly this JSON shape:
{{
  "title": "string",
  "sections": ["string", "string", "string"],
  "sources": [{{"label": "string", "note": "string"}}]
}}
Use 3 sections: overview, key considerations, limitations. Sources: if no URLs in context, use labels like "general knowledge" with honest notes."""
    resp = llm.invoke([SystemMessage(content=CONSTITUTION), HumanMessage(content=prompt)])
    raw = (getattr(resp, "content", None) or str(resp)).strip()
    data = _extract_json_object(raw)
    sections = data.get("sections") or []
    if not isinstance(sections, list):
        sections = [str(sections)]
    sections = [str(s) for s in sections if s][:8]
    if not sections:
        sections = ["(empty)"]
    sources_raw = data.get("sources") or []
    sources: list[ResearchSource] = []
    if isinstance(sources_raw, list):
        for item in sources_raw[:10]:
            if isinstance(item, dict):
                sources.append(
                    ResearchSource(
                        label=str(item.get("label", "source"))[:120],
                        note=str(item.get("note", ""))[:500],
                    )
                )
    title = str(data.get("title", f"Brief: {topic}"))[:200]
    return ResearchBriefResponse(topic=topic, title=title, sections=sections, sources=sources)


def run_constitution_audit_lite(prompt_snippet: str) -> ConstitutionAuditLiteResponse:
    snippet = (prompt_snippet or "").strip()
    if not snippet:
        snippet = "(empty input)"
    if len(snippet) > 4000:
        snippet = snippet[:4000]
    llm = _llm()
    sys = CONSTITUTION + " Review another agent's prompt/config for safety and ethics."
    human = f"""Analyze this prompt/config excerpt and reply with JSON only:
{snippet}

JSON shape:
{{
  "input_summary": "one sentence",
  "jailbreak_risk": "low" | "medium" | "high",
  "ethical_alignment_notes": ["string"],
  "recommendations": ["string"]
}}"""
    resp = llm.invoke([SystemMessage(content=sys), HumanMessage(content=human)])
    raw = (getattr(resp, "content", None) or str(resp)).strip()
    data = _extract_json_object(raw)
    jbr = str(data.get("jailbreak_risk", "medium")).lower()
    if jbr not in ("low", "medium", "high"):
        jbr = "medium"
    notes = data.get("ethical_alignment_notes") or []
    recs = data.get("recommendations") or []
    if not isinstance(notes, list):
        notes = [str(notes)]
    if not isinstance(recs, list):
        recs = [str(recs)]
    return ConstitutionAuditLiteResponse(
        input_summary=str(data.get("input_summary", "Excerpt reviewed."))[:500],
        jailbreak_risk=jbr,
        ethical_alignment_notes=[str(x)[:500] for x in notes][:12],
        recommendations=[str(x)[:500] for x in recs][:12],
    )


def run_hello(path: str) -> HelloResponse:
    return HelloResponse(path=path, message="paid")
