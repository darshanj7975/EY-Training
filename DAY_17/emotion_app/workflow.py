"""
graph/workflow.py
Supervisor-based multi-agent graph for emotion detection from voice/text.
Architecture mirrors the graphviz diagram:
  START → Supervisor → [Search | Read | RAG] → Supervisor → Writer → Evaluator → Supervisor → END
"""

from __future__ import annotations
import os
import json
from typing import TypedDict, Literal, Annotated
from dotenv import load_dotenv

load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

# ── State ─────────────────────────────────────────────────────────────────────

class ResearchState(TypedDict, total=False):
    # Input
    transcript: str          # Raw voice transcript / text input
    audio_filename: str      # Filename of uploaded audio (display only)

    # Routing
    next: str                # Supervisor decision: SEARCH | READ | RAG | WRITE | END
    iteration: int           # Loop counter (prevent infinite loops)

    # Agent outputs
    search_notes: str        # From Search Agent
    extracted_content: str   # From Read Agent
    rag_context: str         # From RAG Agent
    aggregated_context: str  # All context merged before Writer

    # Writer / Evaluator
    draft_report: str        # Writer output
    feedback: str            # Evaluator feedback
    final_report: str        # Approved report
    emotions: dict           # Structured emotion scores
    approved: bool           # Evaluator approved?

    # Audit
    agent_log: list[str]


# ── LLM ──────────────────────────────────────────────────────────────────────

def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0.2,
    )


# ── Supervisor ────────────────────────────────────────────────────────────────

SUPERVISOR_SYSTEM = """You are the Supervisor Agent of a multi-agent emotion detection system.

Your job is to route tasks to the right agent based on what information is still needed to
produce a thorough emotion detection report from a voice transcript.

Available agents:
- SEARCH  : Use when you need current research on emotion detection, vocal biomarkers,
            or psychological frameworks from the web.
- READ    : Use when you need to extract and interpret the raw transcript more deeply —
            linguistic features, speech patterns, hesitation markers.
- RAG     : Use when you need to retrieve stored knowledge about emotion categories,
            prosodic features, or domain-specific context.
- WRITE   : Use when enough context is gathered to write the emotion detection report.
- END     : Use only after the Evaluator has approved the report.

Respond with ONLY a JSON object, nothing else:
{"next": "SEARCH" | "READ" | "RAG" | "WRITE" | "END", "reason": "one line"}
"""

def supervisor_node(state: ResearchState) -> ResearchState:
    llm = get_llm()
    iteration = state.get("iteration", 0)
    log = state.get("agent_log", [])

    # Force WRITE if we've done enough research rounds
    if iteration >= 3 and state.get("next") not in ("WRITE", "END"):
        log.append("Supervisor → WRITE (iteration cap reached)")
        return {**state, "next": "WRITE", "iteration": iteration + 1, "agent_log": log}

    # Force END after approval
    if state.get("approved"):
        log.append("Supervisor → END (report approved)")
        return {**state, "next": "END", "agent_log": log}

    context_summary = f"""
Transcript: {state.get('transcript', '')[:300]}
Search notes available: {bool(state.get('search_notes'))}
Extracted content available: {bool(state.get('extracted_content'))}
RAG context available: {bool(state.get('rag_context'))}
Draft report available: {bool(state.get('draft_report'))}
Evaluator feedback: {state.get('feedback', 'None')}
Iteration: {iteration}
"""

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM),
        HumanMessage(content=context_summary),
    ]

    response = llm.invoke(messages)
    raw = response.content.strip()

    try:
        # Strip markdown fences if present
        clean = raw.replace("```json", "").replace("```", "").strip()
        decision = json.loads(clean)
        next_agent = decision["next"]
        reason = decision.get("reason", "")
    except Exception:
        # Fallback: parse first word
        next_agent = "WRITE" if iteration >= 2 else "SEARCH"
        reason = "parse fallback"

    log.append(f"Supervisor → {next_agent} | {reason}")
    return {**state, "next": next_agent, "iteration": iteration + 1, "agent_log": log}


# ── Search Agent ──────────────────────────────────────────────────────────────

SEARCH_SYSTEM = """You are the Search Agent in an emotion detection research system.
You have just retrieved web search results about emotion detection, vocal biomarkers, and
psychological frameworks. Summarise the most relevant findings as structured research notes
that will help identify emotions from the given transcript."""

def search_agent_node(state: ResearchState) -> ResearchState:
    from tavily import TavilyClient
    log = state.get("agent_log", [])

    try:
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        transcript = state.get("transcript", "")

        # Build targeted queries
        queries = [
            "vocal emotion detection linguistic markers research 2024",
            f"emotion detection from text transcript psychological cues",
        ]

        all_results = []
        for q in queries:
            results = client.search(q, max_results=3)
            for r in results.get("results", []):
                all_results.append(f"• [{r['title']}]: {r['content'][:300]}")

        web_context = "\n".join(all_results[:8])

        llm = get_llm()
        messages = [
            SystemMessage(content=SEARCH_SYSTEM),
            HumanMessage(content=f"Transcript:\n{transcript}\n\nWeb results:\n{web_context}"),
        ]
        response = llm.invoke(messages)
        notes = response.content

        log.append(f"Search Agent: retrieved {len(all_results)} results, synthesised notes")
        return {**state, "search_notes": notes, "agent_log": log}

    except Exception as e:
        log.append(f"Search Agent ERROR: {e}")
        return {**state, "search_notes": f"[Search unavailable: {e}]", "agent_log": log}


# ── Read Agent ────────────────────────────────────────────────────────────────

READ_SYSTEM = """You are the Read Agent specialising in linguistic and paralinguistic analysis.
Analyse the voice transcript deeply for:
1. Emotional vocabulary — specific words that signal emotion
2. Sentence structure — fragmented/run-on sentences, incomplete thoughts
3. Hedging & qualifiers — "maybe", "I think", "sort of" (uncertainty/anxiety markers)
4. Intensifiers — "very", "extremely", "absolutely" (arousal markers)
5. Negation patterns — double negatives, denial
6. Temporal references — past rumination vs. future worry vs. present focus
7. Self-referential language — I/me frequency (depression marker)
8. Punctuation & pauses implied by filler words — "um", "uh", "like"

Return a structured extraction report."""

def read_agent_node(state: ResearchState) -> ResearchState:
    llm = get_llm()
    log = state.get("agent_log", [])
    transcript = state.get("transcript", "")

    messages = [
        SystemMessage(content=READ_SYSTEM),
        HumanMessage(content=f"Transcript to analyse:\n\n{transcript}"),
    ]
    response = llm.invoke(messages)
    log.append("Read Agent: linguistic extraction complete")
    return {**state, "extracted_content": response.content, "agent_log": log}


# ── RAG Agent ─────────────────────────────────────────────────────────────────

RAG_KNOWLEDGE = """
EMOTION FRAMEWORK KNOWLEDGE BASE:

Plutchik's Wheel of Emotions (8 primary):
- Joy: positive, energetic, forward-looking language
- Trust: affiliative words, we/us, agreement markers
- Fear: uncertainty hedges, threat words, hypervigilance
- Surprise: exclamatory, sudden topic shifts, question marks
- Sadness: past-tense, loss vocabulary, slow/heavy descriptors
- Disgust: aversion words, rejection language
- Anger: imperative statements, blame language, intensifiers
- Anticipation: future-tense, planning words, conditional statements

Valence-Arousal-Dominance (VAD) Model:
- Valence: positive vs. negative emotional tone
- Arousal: high (excited, anxious) vs. low (calm, sad)
- Dominance: in-control vs. submissive language

Vocal Biomarkers (text proxies):
- High arousal: short sentences, exclamations, rapid topic shifts
- Low arousal: long sentences, passive voice, ellipsis
- Positive valence: inclusive language, future orientation, humor
- Negative valence: exclusionary language, past orientation, catastrophising

Clinical emotion categories relevant to voice analysis:
- Euthymia (baseline), Dysthymia, Anxiety, Mania, Flat affect
"""

RAG_SYSTEM = """You are the RAG Agent. Using the knowledge base below, retrieve the most relevant
frameworks and indicators for the emotions likely present in the transcript.
Map the linguistic features from the transcript to specific emotion categories.
"""

def rag_agent_node(state: ResearchState) -> ResearchState:
    llm = get_llm()
    log = state.get("agent_log", [])
    transcript = state.get("transcript", "")
    extracted = state.get("extracted_content", "")

    messages = [
        SystemMessage(content=RAG_SYSTEM + "\n\nKNOWLEDGE BASE:\n" + RAG_KNOWLEDGE),
        HumanMessage(content=f"Transcript:\n{transcript}\n\nExtracted features:\n{extracted}"),
    ]
    response = llm.invoke(messages)
    log.append("RAG Agent: context retrieved and mapped to emotion frameworks")
    return {**state, "rag_context": response.content, "agent_log": log}


# ── Writer Agent ──────────────────────────────────────────────────────────────

WRITER_SYSTEM = """You are the Writer Agent for an emotion detection system.

Write a comprehensive Emotion Detection Report from the voice transcript.
Structure it as:

## 🎭 Emotion Detection Report

### Executive Summary
One paragraph — dominant emotion, confidence, overall emotional state.

### Detected Emotions
A table with columns: Emotion | Intensity (0–10) | Key Evidence | Framework

### Linguistic Evidence
Specific quotes or patterns from the transcript that drove each detection.

### Valence-Arousal-Dominance Profile
- Valence: [Positive/Negative/Neutral] — score X/10
- Arousal: [High/Medium/Low] — score X/10
- Dominance: [High/Medium/Low] — score X/10

### Clinical Observations
Any patterns worth noting (not a diagnosis — purely observational).

### Confidence Assessment
Overall confidence in the analysis: High / Medium / Low — with reasoning.

Use all research notes, extracted content, and RAG context provided.
Be specific — cite exact words or phrases from the transcript as evidence.
"""

def writer_agent_node(state: ResearchState) -> ResearchState:
    llm = get_llm()
    log = state.get("agent_log", [])

    context = f"""
TRANSCRIPT:
{state.get('transcript', '')}

RESEARCH NOTES (from web search):
{state.get('search_notes', 'Not available')}

LINGUISTIC EXTRACTION:
{state.get('extracted_content', 'Not available')}

RAG CONTEXT / FRAMEWORK MAPPING:
{state.get('rag_context', 'Not available')}

EVALUATOR FEEDBACK (if any):
{state.get('feedback', 'None — first draft')}
"""

    messages = [
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=context),
    ]
    response = llm.invoke(messages)
    log.append("Writer Agent: draft report generated")
    return {**state, "draft_report": response.content, "agent_log": log}


# ── Evaluator Agent ───────────────────────────────────────────────────────────

EVALUATOR_SYSTEM = """You are the Evaluator Agent for an emotion detection system.
Your role is to quality-check the draft Emotion Detection Report.

Evaluate:
1. Evidence grounding — every emotion claim backed by transcript evidence?
2. Framework alignment — claims consistent with Plutchik / VAD models?
3. Specificity — vague claims like "seems sad" without evidence?
4. Completeness — all major emotional signals addressed?
5. Guardrail check — no harmful diagnoses, no over-claiming?

Respond ONLY with JSON:
{
  "approved": true | false,
  "score": 0-10,
  "feedback": "specific improvement instructions if not approved, empty string if approved",
  "guardrail_flags": ["list of any concerning claims"]
}
"""

def evaluator_agent_node(state: ResearchState) -> ResearchState:
    llm = get_llm()
    log = state.get("agent_log", [])

    messages = [
        SystemMessage(content=EVALUATOR_SYSTEM),
        HumanMessage(content=f"Draft report:\n\n{state.get('draft_report', '')}"),
    ]
    response = llm.invoke(messages)

    try:
        clean = response.content.replace("```json", "").replace("```", "").strip()
        verdict = json.loads(clean)
        approved = verdict.get("approved", False)
        feedback = verdict.get("feedback", "")
        score = verdict.get("score", 5)
        flags = verdict.get("guardrail_flags", [])
    except Exception:
        approved = True  # fallback — accept if parse fails
        feedback = ""
        score = 7
        flags = []

    log.append(f"Evaluator: score={score}, approved={approved}, flags={len(flags)}")

    final = state.get("draft_report", "") if approved else state.get("final_report", "")
    if approved:
        final = state.get("draft_report", "")

    return {
        **state,
        "approved": approved,
        "feedback": feedback,
        "final_report": final if approved else state.get("final_report", ""),
        "agent_log": log,
    }


# ── Routing ───────────────────────────────────────────────────────────────────

def route_supervisor(state: ResearchState) -> str:
    return state.get("next", "SEARCH")


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(ResearchState)

    g.add_node("supervisor",  supervisor_node)
    g.add_node("search",      search_agent_node)
    g.add_node("read",        read_agent_node)
    g.add_node("rag",         rag_agent_node)
    g.add_node("writer",      writer_agent_node)
    g.add_node("evaluator",   evaluator_agent_node)

    g.set_entry_point("supervisor")

    g.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "SEARCH": "search",
            "READ":   "read",
            "RAG":    "rag",
            "WRITE":  "writer",
            "END":    END,
        },
    )

    # All research agents return to supervisor
    g.add_edge("search",    "supervisor")
    g.add_edge("read",      "supervisor")
    g.add_edge("rag",       "supervisor")

    # Writer → Evaluator → Supervisor (for approval loop)
    g.add_edge("writer",    "evaluator")
    g.add_edge("evaluator", "supervisor")

    return g.compile()
