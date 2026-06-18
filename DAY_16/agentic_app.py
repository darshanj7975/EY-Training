import streamlit as st
import json
import time
from groq import Groq

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic AI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.04);
    border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stHeader"] { background: transparent; }

.agent-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}
.agent-card.active {
    border-color: rgba(99,179,237,0.6);
    box-shadow: 0 0 24px rgba(99,179,237,0.18);
    background: rgba(99,179,237,0.06);
}
.agent-card.done {
    border-color: rgba(72,187,120,0.5);
    box-shadow: 0 0 16px rgba(72,187,120,0.12);
    background: rgba(72,187,120,0.05);
}
.agent-card.error {
    border-color: rgba(252,129,74,0.5);
    background: rgba(252,129,74,0.05);
}
.agent-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}
.agent-icon {
    font-size: 28px;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    background: rgba(255,255,255,0.06);
}
.agent-name {
    font-size: 15px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: 0.5px;
}
.agent-role {
    font-size: 11px;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.status-badge {
    margin-left: auto;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge-waiting  { background: rgba(113,128,150,0.2); color: #718096; }
.badge-thinking { background: rgba(99,179,237,0.2);  color: #63b3ed; }
.badge-done     { background: rgba(72,187,120,0.2);  color: #48bb78; }
.badge-error    { background: rgba(252,129,74,0.2);  color: #fc814a; }

.agent-output {
    background: rgba(0,0,0,0.25);
    border-radius: 10px;
    padding: 14px;
    font-size: 13px;
    color: #cbd5e0;
    line-height: 1.7;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
    border: 1px solid rgba(255,255,255,0.06);
}
.step-pill {
    display: inline-block;
    background: rgba(159,122,234,0.15);
    border: 1px solid rgba(159,122,234,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    margin: 4px 4px 4px 0;
    font-size: 12px;
    color: #d6bcfa;
}
.pipeline-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 6px 0;
}
.pipeline-node {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 12px;
    color: #a0aec0;
    font-weight: 600;
}
.pipeline-arrow { color: #4a5568; font-size: 18px; padding: 0 6px; }

.final-box {
    background: linear-gradient(135deg, rgba(72,187,120,0.08), rgba(56,178,172,0.08));
    border: 1px solid rgba(72,187,120,0.3);
    border-radius: 16px;
    padding: 24px;
    margin-top: 8px;
}
.final-title {
    color: #48bb78;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
}
.stTextArea textarea,
.stTextArea textarea:hover,
.stTextArea textarea:focus,
.stTextArea div[data-baseweb="textarea"] textarea,
[data-testid="stTextArea"] textarea {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 12px !important;
    color: #f0f4f8 !important;
    font-size: 14px !important;
    caret-color: #63b3ed !important;
    -webkit-text-fill-color: #f0f4f8 !important;
}
.stTextArea textarea::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: rgba(160,174,192,0.6) !important;
    -webkit-text-fill-color: rgba(160,174,192,0.6) !important;
}
.stTextArea textarea:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(99,179,237,0.6) !important;
    box-shadow: 0 0 0 2px rgba(99,179,237,0.2) !important;
    background: rgba(255,255,255,0.09) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 28px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(102,126,234,0.4) !important;
}
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.metric-value { font-size: 26px; font-weight: 700; color: #e2e8f0; }
.metric-label { font-size: 11px; color: #718096; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.groq-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(249,115,22,0.12);
    border: 1px solid rgba(249,115,22,0.3);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11px;
    color: #fb923c;
    font-weight: 600;
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Groq client ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client(api_key: str):
    return Groq(api_key=api_key)

def call_groq(client, system_prompt: str, user_message: str,
              model: str = "llama-3.3-70b-versatile", max_tokens: int = 1500) -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
    )
    return response.choices[0].message.content

# ── Agents ─────────────────────────────────────────────────────────────────────
def planner_agent(client, task: str, model: str) -> dict:
    system = """You are a Planner Agent. Break the user task into clear numbered steps.
Respond ONLY with valid JSON — no markdown fences, no extra text:
{
  "goal": "one-sentence goal",
  "steps": ["step 1", "step 2", "step 3"],
  "complexity": "low|medium|high",
  "estimated_time": "e.g. 30 seconds"
}"""
    raw = call_groq(client, system, f"Task: {task}", model=model)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception:
        return {
            "goal": task,
            "steps": ["Analyse the task", "Execute the task", "Review the output"],
            "complexity": "medium",
            "estimated_time": "unknown",
        }

def executor_agent(client, task: str, plan: dict, model: str) -> str:
    steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan.get("steps", [])))
    system = """You are an Executor Agent. Given a goal and a plan, carry out each step thoroughly.
Write a detailed, well-structured response. Be specific and helpful."""
    return call_groq(
        client, system,
        f"Goal: {plan.get('goal', task)}\n\nPlan:\n{steps_text}\n\nOriginal task: {task}",
        model=model, max_tokens=2000,
    )

def validator_agent(client, task: str, plan: dict, execution: str, model: str) -> dict:
    system = """You are a Validator Agent. Review the execution output against the task and plan.
Respond ONLY with valid JSON — no markdown fences:
{
  "passed": true or false,
  "score": number 0-100,
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1"],
  "summary": "one paragraph quality summary"
}"""
    steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan.get("steps", [])))
    raw = call_groq(
        client, system,
        f"Original task: {task}\n\nPlan:\n{steps_text}\n\nExecution:\n{execution}",
        model=model,
    )
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception:
        return {
            "passed": True, "score": 75,
            "strengths": ["Task addressed"],
            "improvements": ["Could not parse validator response"],
            "summary": raw[:300],
        }

# ── Session state ──────────────────────────────────────────────────────────────
for key in ["history", "plan", "execution", "validation", "elapsed"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "history" else None

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 Agentic AI System")
    st.markdown("<div class='groq-badge'>⚡ Powered by Groq</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#718096;font-size:12px;margin:8px 0 20px'>Planner → Executor → Validator</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**🔑 Groq API Key**")
    api_key = st.text_input("Groq API Key", type="password",
                            placeholder="gsk_…", label_visibility="collapsed")

    st.markdown("**🧠 Model**")
    model_choice = st.selectbox(
        "Model", label_visibility="collapsed",
        options=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    )

    st.markdown("---")
    st.markdown("**Pipeline**")
    st.markdown("""
<div class='pipeline-row'>
  <div class='pipeline-node'>🧠 Planner</div>
  <div class='pipeline-arrow'>→</div>
  <div class='pipeline-node'>⚙️ Executor</div>
  <div class='pipeline-arrow'>→</div>
  <div class='pipeline-node'>✅ Validator</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown("""<div style='font-size:12px;color:#718096;line-height:1.9'>
🧠 <b style='color:#a0aec0'>Planner</b> — breaks your task into steps<br>
⚙️ <b style='color:#a0aec0'>Executor</b> — carries out the plan in detail<br>
✅ <b style='color:#a0aec0'>Validator</b> — scores quality &amp; gives feedback
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Example tasks**")
    examples = [
        "Write a Python function to sort a list",
        "Explain how neural networks work",
        "Create a marketing plan for a coffee shop",
        "Debug: why does my API return 401?",
        "Pros and cons of microservices vs monolith",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state["example_task"] = ex

    if st.session_state.history:
        st.markdown("---")
        st.markdown(f"**Run history ({len(st.session_state.history)})**")
        for h in reversed(st.session_state.history[-5:]):
            score = h.get("score", "?")
            color = "#48bb78" if score >= 75 else "#fc814a"
            st.markdown(
                f"<div style='font-size:11px;color:#718096;padding:4px 0;"
                f"border-bottom:1px solid rgba(255,255,255,0.05)'>"
                f"<span style='color:{color};font-weight:700'>{score}/100</span>"
                f" · {h['task'][:32]}…</div>", unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='color:#e2e8f0;font-size:28px;font-weight:800;margin-bottom:4px'>🤖 Agentic AI Pipeline</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#718096;font-size:14px;margin-bottom:4px'>Planner · Executor · Validator — powered by <span style='color:#fb923c;font-weight:600'>Groq</span></p>", unsafe_allow_html=True)

if not api_key:
    st.warning("⚠️ Enter your Groq API key in the sidebar to get started. Get one free at [console.groq.com](https://console.groq.com)")

default_val = st.session_state.pop("example_task", "")
task = st.text_area("Your task", value=default_val,
    placeholder="e.g. Write a Python function to reverse a string and explain how it works…",
    height=90, label_visibility="collapsed")

col_btn, col_clear, col_space = st.columns([2, 1, 6])
with col_btn:
    run_clicked = st.button("▶  Run Agents", use_container_width=True, disabled=not api_key)
with col_clear:
    if st.button("Clear", use_container_width=True):
        for k in ["plan", "execution", "validation", "elapsed"]:
            st.session_state[k] = None
        st.rerun()

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

# ── Agent card renderer ────────────────────────────────────────────────────────
def agent_card(col, icon, name, role, status="waiting", output="", steps=None):
    badge_map = {
        "waiting":  ("badge-waiting",  "● Waiting"),
        "thinking": ("badge-thinking", "⟳ Thinking…"),
        "done":     ("badge-done",     "✓ Done"),
        "error":    ("badge-error",    "✗ Error"),
    }
    card_cls  = {"thinking": "active", "done": "done", "error": "error"}.get(status, "")
    badge_cls, badge_txt = badge_map.get(status, badge_map["waiting"])
    steps_html  = ("".join(f"<span class='step-pill'>{s}</span>" for s in steps)
                   if steps else "")
    output_html = f"<div class='agent-output'>{output}</div>" if output else ""
    col.markdown(f"""
<div class='agent-card {card_cls}'>
  <div class='agent-header'>
    <div class='agent-icon'>{icon}</div>
    <div>
      <div class='agent-name'>{name}</div>
      <div class='agent-role'>{role}</div>
    </div>
    <span class='status-badge {badge_cls}'>{badge_txt}</span>
  </div>
  {steps_html}
  {output_html}
</div>""", unsafe_allow_html=True)

# ── Initial state ──────────────────────────────────────────────────────────────
if not run_clicked and st.session_state.plan is None:
    agent_card(col1, "🧠", "Planner Agent",   "Breaks task into steps")
    agent_card(col2, "⚙️", "Executor Agent",  "Carries out the plan")
    agent_card(col3, "✅", "Validator Agent", "Scores quality & feedback")

# ── Run pipeline ───────────────────────────────────────────────────────────────
if run_clicked and task.strip() and api_key:
    groq_client = get_client(api_key)
    start = time.time()

    # Planner
    agent_card(col1, "🧠", "Planner Agent", "Breaks task into steps", status="thinking")
    agent_card(col2, "⚙️", "Executor Agent", "Carries out the plan")
    agent_card(col3, "✅", "Validator Agent", "Scores quality & feedback")
    with st.spinner("🧠 Planner thinking…"):
        plan = planner_agent(groq_client, task, model_choice)
    st.session_state.plan = plan
    agent_card(col1, "🧠", "Planner Agent", "Breaks task into steps",
               status="done", steps=plan.get("steps", []),
               output=f"Goal: {plan.get('goal','')}\nComplexity: {plan.get('complexity','')}\nEst. time: {plan.get('estimated_time','')}")

    # Executor
    agent_card(col2, "⚙️", "Executor Agent", "Carries out the plan", status="thinking")
    with st.spinner("⚙️ Executor working…"):
        execution = executor_agent(groq_client, task, plan, model_choice)
    st.session_state.execution = execution
    agent_card(col2, "⚙️", "Executor Agent", "Carries out the plan",
               status="done", output=execution[:600] + ("…" if len(execution) > 600 else ""))

    # Validator
    agent_card(col3, "✅", "Validator Agent", "Scores quality & feedback", status="thinking")
    with st.spinner("✅ Validator reviewing…"):
        validation = validator_agent(groq_client, task, plan, execution, model_choice)
    st.session_state.validation = validation
    score  = validation.get("score", 0)
    passed = validation.get("passed", False)
    val_out = (
        f"Score: {score}/100  {'✓ Passed' if passed else '✗ Needs work'}\n\n"
        "Strengths:\n" + "\n".join(f"  • {s}" for s in validation.get("strengths", [])) +
        "\n\nImprovements:\n" + "\n".join(f"  • {i}" for i in validation.get("improvements", []))
    )
    agent_card(col3, "✅", "Validator Agent", "Scores quality & feedback",
               status="done", output=val_out)

    st.session_state.elapsed = round(time.time() - start, 1)
    st.session_state.history.append({"task": task, "score": score})

# ── Restore state after rerun ──────────────────────────────────────────────────
elif st.session_state.plan and not run_clicked:
    plan       = st.session_state.plan
    execution  = st.session_state.execution or ""
    validation = st.session_state.validation or {}
    score      = validation.get("score", 0)
    passed     = validation.get("passed", False)
    val_out = (
        f"Score: {score}/100  {'✓ Passed' if passed else '✗ Needs work'}\n\n"
        "Strengths:\n" + "\n".join(f"  • {s}" for s in validation.get("strengths", [])) +
        "\n\nImprovements:\n" + "\n".join(f"  • {i}" for i in validation.get("improvements", []))
    )
    agent_card(col1, "🧠", "Planner Agent", "Breaks task into steps",
               status="done", steps=plan.get("steps", []),
               output=f"Goal: {plan.get('goal','')}\nComplexity: {plan.get('complexity','')}\nEst. time: {plan.get('estimated_time','')}")
    agent_card(col2, "⚙️", "Executor Agent", "Carries out the plan",
               status="done", output=execution[:600] + ("…" if len(execution) > 600 else ""))
    agent_card(col3, "✅", "Validator Agent", "Scores quality & feedback",
               status="done", output=val_out)

# ── Metrics ────────────────────────────────────────────────────────────────────
if st.session_state.validation:
    validation = st.session_state.validation
    score      = validation.get("score", 0)
    score_color = "#48bb78" if score >= 75 else "#f6ad55" if score >= 50 else "#fc814a"
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    for col, val, label, color in [
        (m1, f"{score}/100",                                                  "Quality score",  score_color),
        (m2, "✓ Passed" if validation.get("passed") else "✗ Review",         "Validation",     "#48bb78" if validation.get("passed") else "#fc814a"),
        (m3, len(st.session_state.plan.get("steps", [])),                    "Steps planned",  "#63b3ed"),
        (m4, f"{st.session_state.elapsed}s" if st.session_state.elapsed else "—", "Total time", "#b794f4"),
    ]:
        col.markdown(f"""
<div class='metric-card'>
  <div class='metric-value' style='color:{color}'>{val}</div>
  <div class='metric-label'>{label}</div>
</div>""", unsafe_allow_html=True)

# ── Full output ────────────────────────────────────────────────────────────────
if st.session_state.execution:
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='final-box'><div class='final-title'>⚙️ Full Execution Output</div>"
        f"<div style='color:#cbd5e0;font-size:14px;line-height:1.8;white-space:pre-wrap'>"
        f"{st.session_state.execution}</div></div>", unsafe_allow_html=True)

    if st.session_state.validation:
        st.markdown(f"""
<div style='margin-top:16px;background:rgba(159,122,234,0.07);
     border:1px solid rgba(159,122,234,0.25);border-radius:16px;padding:20px'>
  <div style='color:#b794f4;font-size:13px;font-weight:700;margin-bottom:8px'>✅ Validator Summary</div>
  <div style='color:#cbd5e0;font-size:14px;line-height:1.7'>{st.session_state.validation.get('summary','')}</div>
</div>""", unsafe_allow_html=True)
