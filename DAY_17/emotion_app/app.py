"""
app.py  —  ResearchMind: Emotion Detection from Voice
Multi-agent pipeline: Supervisor → Search / Read / RAG → Writer → Evaluator

Run:  streamlit run app.py
"""

import os, sys, io, time, json, textwrap, threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from graphviz import Digraph

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Emotion Detection · ResearchMind AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.agent-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 13px;
    color: #cbd5e1;
}
.agent-card.active {
    border-color: #3b82f6;
    background: #1e3a5f;
    box-shadow: 0 0 0 1px #3b82f6;
}
.agent-card.done {
    border-color: #22c55e;
    background: #14281e;
}
.agent-card.error {
    border-color: #ef4444;
    background: #2d1515;
}
.emotion-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px;
}
.log-line {
    font-family: monospace;
    font-size: 12px;
    color: #94a3b8;
    padding: 2px 0;
    border-bottom: 1px solid #1e293b;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Architecture diagram (graphviz)
# ─────────────────────────────────────────────────────────────────────────────
def render_architecture(highlight: str = ""):
    dot = Digraph("Emotion Detection Multi-Agent System", format="png")
    dot.attr(bgcolor="transparent", fontname="Arial", rankdir="TB")
    dot.attr("node", fontname="Arial", fontsize="11", style="filled", penwidth="1.5")
    dot.attr("edge", fontname="Arial", fontsize="9", color="#64748b")

    def node(name, label, shape="box", fillcolor="#1e293b", fontcolor="#e2e8f0", color="#475569"):
        is_hl = name == highlight
        dot.node(name, label, shape=shape,
                 fillcolor="#1d4ed8" if is_hl else fillcolor,
                 fontcolor=fontcolor,
                 color="#60a5fa" if is_hl else color,
                 penwidth="2.5" if is_hl else "1.5")

    node("START", "START", shape="oval",  fillcolor="#0f172a", color="#475569")
    node("END",   "END",   shape="oval",  fillcolor="#0f172a", color="#475569")
    node("SUP",   "Supervisor\n(Router)\nStructured Output", fillcolor="#312e81", color="#818cf8")
    node("SEARCH","Search Agent\nTavily Web Search",          fillcolor="#1e3a5f", color="#38bdf8")
    node("READ",  "Read Agent\nLinguistic Analysis",          fillcolor="#1a2e1a", color="#4ade80")
    node("RAG",   "RAG Agent\nEmotion Frameworks",            fillcolor="#3b1f0a", color="#fb923c")
    node("WRITE", "Writer Agent\nReport Generation",          fillcolor="#1a1a3e", color="#a78bfa")
    node("EVAL",  "Evaluator Agent\nRAGAS + Guardrails",      fillcolor="#2d1515", color="#f87171")

    dot.edge("START", "SUP")
    dot.edge("SUP", "SEARCH", label=" need web data")
    dot.edge("SUP", "READ",   label=" need linguistics")
    dot.edge("SUP", "RAG",    label=" need frameworks")
    dot.edge("SEARCH", "SUP", label=" research notes")
    dot.edge("READ",   "SUP", label=" extracted features")
    dot.edge("RAG",    "SUP", label=" context")
    dot.edge("SUP", "WRITE",  label=" enough context")
    dot.edge("WRITE", "EVAL", label=" draft")
    dot.edge("EVAL",  "SUP",  label=" feedback")
    dot.edge("SUP",   "END",  label=" approved")

    return dot.pipe(format="png")


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎙️ ResearchMind AI")
    st.caption("Emotion Detection from Voice")
    st.divider()

    groq_key  = st.text_input("Groq API Key",   type="password",
                               value=os.getenv("GROQ_API_KEY", ""),
                               placeholder="gsk_...")
    tavily_key = st.text_input("Tavily API Key", type="password",
                               value=os.getenv("TAVILY_API_KEY", ""),
                               placeholder="tvly-...")

    if groq_key:  os.environ["GROQ_API_KEY"]   = groq_key
    if tavily_key: os.environ["TAVILY_API_KEY"] = tavily_key

    st.divider()
    st.subheader("⚙️ Settings")
    max_iter = st.slider("Max research iterations", 1, 5, 3)
    st.divider()

    st.subheader("🗺️ Agent Architecture")
    try:
        arch_png = render_architecture()
        st.image(arch_png, use_container_width=True)
    except Exception as e:
        st.caption(f"Diagram error: {e}")

    st.divider()
    st.caption("Groq · LangGraph · Tavily · Streamlit")


# ─────────────────────────────────────────────────────────────────────────────
# Main area
# ─────────────────────────────────────────────────────────────────────────────
st.title("🎭 Emotion Detection from Voice")
st.markdown("*Multi-agent pipeline: Supervisor routes between Search, Read, RAG, Writer, and Evaluator to produce a grounded emotion analysis report.*")

# ── Input tabs ───────────────────────────────────────────────────────────────
tab_text, tab_audio, tab_sample = st.tabs(["📝 Paste transcript", "🎤 Upload audio", "🧪 Try samples"])

transcript = ""
audio_filename = ""

with tab_text:
    transcript_input = st.text_area(
        "Paste voice transcript or any spoken text",
        height=160,
        placeholder="e.g. I… I don't know, everything just feels so heavy lately. "
                    "I keep trying to push through but it's like, I don't know, "
                    "nothing really matters? I smile at work and pretend everything's fine but inside…",
    )
    if transcript_input.strip():
        transcript = transcript_input.strip()

with tab_audio:
    st.info("Upload an audio file — the app will transcribe it using Groq Whisper, then run emotion analysis.")
    audio_file = st.file_uploader("Audio file", type=["mp3", "wav", "m4a", "ogg", "webm"])
    if audio_file:
        audio_filename = audio_file.name
        st.audio(audio_file)
        if st.button("🔊 Transcribe with Groq Whisper"):
            with st.spinner("Transcribing…"):
                try:
                    from groq import Groq
                    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
                    audio_bytes = audio_file.read()
                    transcription = client.audio.transcriptions.create(
                        file=(audio_file.name, audio_bytes),
                        model="whisper-large-v3",
                        response_format="text",
                    )
                    st.session_state["whisper_transcript"] = transcription
                    st.success("Transcription complete!")
                except Exception as e:
                    st.error(f"Transcription failed: {e}")

        if "whisper_transcript" in st.session_state:
            st.text_area("Transcript", st.session_state["whisper_transcript"], height=120)
            transcript = st.session_state["whisper_transcript"]

with tab_sample:
    samples = {
        "😔 Depression markers": (
            "I don't know, I just… I feel like I'm going through the motions, you know? "
            "Every day is the same. I wake up and I just think, what's the point? "
            "I used to love painting but I haven't touched my brushes in months. "
            "I'm tired. Not like sleepy tired. Just… tired of everything. "
            "I keep cancelling on my friends. I don't know why. I just can't face them."
        ),
        "😰 Anxiety markers": (
            "What if I mess this up? Like, what if everything goes wrong? "
            "I've been running through every possible scenario in my head and none of them end well. "
            "My heart's been racing all morning. I checked the time like six times already. "
            "I know I'm probably overthinking but I can't help it. "
            "What if they think I'm incompetent? What if I say something stupid?"
        ),
        "😠 Anger markers": (
            "I can't believe they did that. After everything I've done for this team. "
            "Nobody listens. I tell them exactly what needs to happen and they just ignore it. "
            "It's always the same. Always. I'm done repeating myself. "
            "They had no right to make that decision without me. None. "
            "I'm just — I'm done being the bigger person here. Enough."
        ),
        "😄 Joy / Excitement": (
            "Oh my gosh, I can't even explain how happy I am right now! "
            "We actually did it! After all those months of work, we launched and it's working! "
            "I've been smiling all day, I can't stop. "
            "I called my mum straightaway. She cried, I cried, it was so good. "
            "I feel like anything is possible today. Like, genuinely anything."
        ),
        "😐 Flat affect": (
            "Yeah. It was fine. I went to the thing. It was okay. "
            "People were there. We talked. I came home. "
            "I guess it was alright. Nothing special. "
            "I'm not really sure what else to say about it. It just… happened."
        ),
    }

    chosen = st.selectbox("Choose a sample transcript", list(samples.keys()))
    st.text_area("Sample text", samples[chosen], height=140, disabled=True)
    if st.button("Use this sample"):
        transcript = samples[chosen]
        st.success("Sample loaded — click Run Analysis below.")


# ─────────────────────────────────────────────────────────────────────────────
# Run pipeline
# ─────────────────────────────────────────────────────────────────────────────
st.divider()
col_run, col_info = st.columns([1, 4])
with col_run:
    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True,
                        disabled=not (transcript and groq_key))
with col_info:
    if not groq_key:
        st.warning("Add your Groq API key in the sidebar.")
    elif not transcript:
        st.info("Paste a transcript, upload audio, or pick a sample.")
    else:
        st.success(f"Ready — {len(transcript)} chars · {len(transcript.split())} words")

if run_btn and transcript and groq_key:

    # ── Layout ────────────────────────────────────────────────────────────
    left, right = st.columns([1, 2])

    with left:
        st.subheader("🤖 Agent Pipeline")
        agent_cards = {}
        agent_defs = [
            ("supervisor", "🧭 Supervisor",     "Router & planner"),
            ("search",     "🔍 Search Agent",   "Tavily web research"),
            ("read",       "📖 Read Agent",     "Linguistic extraction"),
            ("rag",        "🗂️ RAG Agent",      "Emotion frameworks"),
            ("writer",     "✍️ Writer Agent",   "Report generation"),
            ("evaluator",  "⚖️ Evaluator",      "Quality & guardrails"),
        ]
        for key, name, desc in agent_defs:
            ph = st.empty()
            ph.markdown(
                f'<div class="agent-card">'
                f'<b>{name}</b><br><span style="color:#64748b;font-size:11px">{desc}</span>'
                f'<br><span style="color:#475569">⏳ waiting</span>'
                f'</div>', unsafe_allow_html=True
            )
            agent_cards[key] = (ph, name, desc)

        st.subheader("📋 Agent Log")
        log_ph = st.empty()

    with right:
        st.subheader("📊 Analysis Results")
        result_ph   = st.empty()
        diagram_ph  = st.empty()

    def update_card(key, status, detail=""):
        ph, name, desc = agent_cards[key]
        icons  = {"waiting": "⏳", "active": "🔄", "done": "✅", "error": "❌"}
        colors = {"waiting": "", "active": "active", "done": "done", "error": "error"}
        icon   = icons.get(status, "⏳")
        cls    = colors.get(status, "")
        detail_html = f'<br><span style="font-size:11px;color:#94a3b8">{detail}</span>' if detail else ""
        ph.markdown(
            f'<div class="agent-card {cls}">'
            f'<b>{name}</b><br>'
            f'<span style="color:#64748b;font-size:11px">{desc}</span>'
            f'<br><span>{icon} {status}</span>{detail_html}'
            f'</div>', unsafe_allow_html=True
        )

    def update_log(log_lines):
        html = "".join(
            f'<div class="log-line">→ {line}</div>'
            for line in log_lines[-20:]
        )
        log_ph.markdown(f'<div style="max-height:300px;overflow-y:auto">{html}</div>',
                        unsafe_allow_html=True)

    # ── Run graph with streaming status updates ───────────────────────────
    from workflow import build_graph

    graph = build_graph()

    initial_state = {
        "transcript":    transcript,
        "audio_filename": audio_filename,
        "iteration":     0,
        "approved":      False,
        "agent_log":     [],
        "next":          "SEARCH",
    }

    result_ph.info("🚀 Pipeline starting…")

    # Map LangGraph node names to our card keys
    node_map = {
        "supervisor": "supervisor",
        "search":     "search",
        "read":       "read",
        "rag":        "rag",
        "writer":     "writer",
        "evaluator":  "evaluator",
    }

    last_state = initial_state
    try:
        for step in graph.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in step.items():
                card_key = node_map.get(node_name)
                if card_key:
                    # Mark previous active as done
                    for k in node_map.values():
                        pass  # just update the active one

                    update_card(card_key, "active",
                                f"iteration {node_output.get('iteration', '?')}" if node_name == "supervisor"
                                else "processing…")

                    # Show live diagram highlight
                    try:
                        arch_bytes = render_architecture(
                            {"supervisor": "SUP", "search": "SEARCH",
                             "read": "READ", "rag": "RAG",
                             "writer": "WRITE", "evaluator": "EVAL"}.get(node_name, "")
                        )
                        with left:
                            pass  # diagram is in sidebar
                    except Exception:
                        pass

                    time.sleep(0.3)  # visual breathing room
                    update_card(card_key, "done",
                                node_output.get("next", "") if node_name == "supervisor" else "complete")

                    # Update log
                    update_log(node_output.get("agent_log", []))
                    last_state = {**last_state, **node_output}

    except Exception as e:
        result_ph.error(f"Pipeline error: {e}")
        import traceback
        st.code(traceback.format_exc())
        st.stop()

    # ── Display results ───────────────────────────────────────────────────
    final_report = last_state.get("final_report") or last_state.get("draft_report", "")
    approved     = last_state.get("approved", False)
    score_text   = "Approved ✅" if approved else "Needs review ⚠️"

    # Metrics row
    with right:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Evaluator", score_text)
        m2.metric("Iterations", last_state.get("iteration", 0))
        m3.metric("Word count", len((final_report or "").split()))
        m4.metric("Sources", "Tavily + RAG")

        if last_state.get("feedback"):
            st.warning(f"**Evaluator feedback**: {last_state['feedback']}")

        # Final report
        result_ph.empty()
        st.markdown("---")
        if final_report:
            st.markdown(final_report)
        else:
            st.warning("No report generated — check API keys and try again.")

        # Export
        if final_report:
            st.download_button(
                "⬇️ Download Report (Markdown)",
                data=final_report,
                file_name="emotion_detection_report.md",
                mime="text/markdown",
            )

    # ── Architecture diagram with final highlight ─────────────────────────
    with left:
        st.subheader("🗺️ Final Architecture")
        try:
            st.image(render_architecture("END"), use_container_width=True)
        except Exception:
            pass

    # Show full log
    with st.expander("📋 Full agent log", expanded=False):
        for line in last_state.get("agent_log", []):
            st.markdown(f"`{line}`")

    # Research context
    with st.expander("🔍 Research context (what agents found)", expanded=False):
        if last_state.get("search_notes"):
            st.subheader("Search Agent notes")
            st.markdown(last_state["search_notes"])
        if last_state.get("extracted_content"):
            st.subheader("Read Agent extraction")
            st.markdown(last_state["extracted_content"])
        if last_state.get("rag_context"):
            st.subheader("RAG Agent context")
            st.markdown(last_state["rag_context"])
