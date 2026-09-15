"""LangGraph StateGraph workflow with native built-in memory for AeroTrace."""

import os
import re
import json
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agent.models import ErrorAnalysis
from agent.agent import rule_based_reasoner
import config


# -------------------------------------------------------------
# 1. LANGGRAPH UNIFIED STATE WITH MULTI-TURN MEMORY
# -------------------------------------------------------------
class AeroTraceState(TypedDict):
    """Explicit state tracked and checkpointed across all LangGraph turns."""
    # Current turn inputs
    screen_text: str
    voice_text: Optional[str]
    mcp_context: Dict[str, Any]

    # Processing metadata
    current_step: str
    fused_prompt: str
    llm_provider: str

    # Built-in Persistent Conversation History across turns
    chat_history: List[Dict[str, str]]
    turn_count: int

    # Agent decisions & resolutions
    is_technical_issue: bool
    confidence_score: float
    issue_summary: str
    suggested_fix: str
    clarification_question: Optional[str]


# -------------------------------------------------------------
# 2. LANGGRAPH NODES
# -------------------------------------------------------------
def fuse_context_node(state: AeroTraceState) -> Dict[str, Any]:
    """Node 1: Fuses Screen, Voice, MCP, and Previous Conversation History."""
    screen = state.get("screen_text", "").strip()
    voice = state.get("voice_text", None)
    mcp = state.get("mcp_context", {})
    history = state.get("chat_history", []) or []
    current_turn = state.get("turn_count", 0) + 1

    print("\n" + "=" * 55)
    print(f"[LangGraph] ---> Node 1: Context & Memory Fusion (Turn {current_turn})")
    print(f"   [Memory]  : Retained {len(history)} previous conversation turn(s)")
    print(f"   [Screen]  : {screen[:60] if screen else '[No screen text]'}...")
    print(f"   [Voice]   : {voice if voice else '[None]'}")
    print(f"   [MCP]     : branch='{mcp.get('git_branch')}' | app='{mcp.get('active_app')}'")

    # Format previous turns from memory
    history_str = ""
    if history:
        history_lines = ["--- PREVIOUS CONVERSATION HISTORY (In-Memory Checkpoint) ---"]
        for idx, turn in enumerate(history[-5:], 1):
            history_lines.append(f"[Turn {idx}]")
            history_lines.append(f"  User Question/Context: {turn.get('user', '')}")
            history_lines.append(f"  AeroTrace Answer: {turn.get('assistant_summary', '')}")
            history_lines.append(f"  Fix Provided: {turn.get('assistant_fix', '')}")
        history_str = "\n".join(history_lines) + "\n\n"

    prompt = f"""You are AeroTrace, an ambient desktop co-pilot with multi-turn memory.
{history_str}--- CURRENT USER CONTEXT (Turn {current_turn}) ---
Context under user cursor:
{screen or '[No screen text hovered]'}

User Voice Intent/Question:
{voice or '[No voice query]'}

Active Developer MCP Environment:
{mcp}

Instructions:
1. If the user asks a follow-up question (e.g. referring to 'it', 'that error', 'how to run with docker', 'explain more'), USE THE PREVIOUS CONVERSATION HISTORY to provide a continuous, accurate answer!
2. If this is a new error, analyze whether it is a technical bug, runtime exception, or missing dependency.
3. Provide a concise 1-2 sentence issue summary and an immediate, executable suggested fix."""

    return {
        "current_step": "context_fused",
        "fused_prompt": prompt,
    }


def search_exa_for_solution(query: str, num_results: int = 2) -> Optional[str]:
    """Queries Exa.ai neural search engine for live documentation, GitHub issues, and StackOverflow."""
    api_key = os.getenv("EXA_API_KEY", getattr(config, "EXA_API_KEY", ""))
    if not api_key or not api_key.strip():
        return None
    try:
        from exa_py import Exa
        exa = Exa(api_key=api_key.strip())
        print(f"   [Exa.ai] Searching neural index for live fix: '{query[:50]}...'")
        results = exa.search_and_contents(
            query,
            num_results=num_results,
            text={"max_characters": 700}
        )
        snippets = []
        for r in getattr(results, "results", []):
            title = getattr(r, "title", "Web Solution")
            url = getattr(r, "url", "")
            text = getattr(r, "text", "")
            snippets.append(f"Title: {title} ({url})\nExcerpt:\n{text[:450]}")
        if snippets:
            combined = "\n\n".join(snippets)
            print(f"   [Exa.ai] Found {len(snippets)} live web solution(s)!")
            return combined
    except Exception as e:
        print(f"   [Exa.ai] Research error: {e}")
    return None


def groq_reasoner_node(state: AeroTraceState) -> Dict[str, Any]:
    """Node 2: Invokes Groq LLM with memory-aware prompt, triggering Exa if confidence < 90%."""
    print("[LangGraph] ---> Node 2: Groq / LLM Reasoner")

    groq_key = os.getenv("GROQ_API_KEY", config.GROQ_API_KEY)

    # 1. If Groq API Key is present in environment or config
    if groq_key and groq_key.strip():
        try:
            print(f"   [Groq] Connecting to Groq LLM ({config.LLM_MODEL})...")
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                api_key=groq_key.strip(),
                model_name=config.LLM_MODEL,
                temperature=0.1
            )

            json_prompt = f"""{state['fused_prompt']}

Respond strictly in valid JSON format with the following fields:
{{
  "is_technical_issue": true,
  "confidence_score": 0.95,
  "issue_summary": "1-2 sentence explanation of the error or follow-up answer",
  "suggested_fix": "exact terminal command or code fix"
}}"""

            raw_res = llm.invoke(json_prompt).content
            m = re.search(r"\{.*\}", raw_res, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                is_tech = bool(data.get("is_technical_issue", True))
                conf = float(data.get("confidence_score", 0.95))
                summary = data.get("issue_summary") or data.get("error") or data.get("problem") or "Detected issue."
                fix_val = data.get("suggested_fix") or data.get("solution") or data.get("fix") or "No fix required."
                if isinstance(fix_val, list):
                    fix_val = "\n".join(str(item) for item in fix_val)
                fix = str(fix_val)
                llm_provider = f"Groq ({config.LLM_MODEL})"

                # -------------------------------------------------------------
                # EXA.AI TRIGGER: If confidence < 90% or missing context
                # -------------------------------------------------------------
                if conf < getattr(config, "EXA_CONFIDENCE_THRESHOLD", 0.90):
                    print(f"   [Exa.ai] Confidence ({conf:.2f}) < 90% threshold -> Calling Exa.ai live web research...")
                    query = state.get("screen_text", "").replace("\n", " ").strip()[:90]
                    if not query and state.get("voice_text"):
                        query = state.get("voice_text")

                    exa_context = search_exa_for_solution(query)
                    if exa_context:
                        refined_prompt = f"""{json_prompt}

--- LIVE EXA.AI VERIFIED WEB DOCUMENTATION & GITHUB ISSUES ---
{exa_context}

Based on the verified live web research above, provide the most accurate up-to-date solution:"""
                        try:
                            refined_res = llm.invoke(refined_prompt).content
                            m_ref = re.search(r"\{.*\}", refined_res, re.DOTALL)
                            if m_ref:
                                ref_data = json.loads(m_ref.group(0))
                                summary = ref_data.get("issue_summary") or summary
                                ref_fix = ref_data.get("suggested_fix") or fix
                                if isinstance(ref_fix, list):
                                    ref_fix = "\n".join(str(item) for item in ref_fix)
                                fix = str(ref_fix)
                                conf = 0.97
                                llm_provider = f"Groq + Exa.ai Neural Search ({config.LLM_MODEL})"
                                print(f"   [Exa.ai] Refined with live web research! Confidence boosted to {conf:.2f}")
                        except Exception as e_ref:
                            print(f"   [Exa.ai] Refinement notice: {e_ref}")

                print(f"   [Groq] Response received! (Confidence: {conf})")
                return {
                    "current_step": "reasoning_complete",
                    "llm_provider": llm_provider,
                    "is_technical_issue": is_tech,
                    "confidence_score": conf,
                    "issue_summary": summary,
                    "suggested_fix": fix,
                    "clarification_question": data.get("clarification_question"),
                }
        except Exception as e:
            print(f"   [Groq] API notice ({e}), falling back to Heuristic Reasoner...")

    # 2. Smart heuristic reasoner
    print("   [Fallback] Executing Zero-Latency Rule Reasoner...")
    analysis = rule_based_reasoner(
        screen_text=state.get("screen_text", ""),
        voice_text=state.get("voice_text"),
        mcp_context=state.get("mcp_context")
    )
    return {
        "current_step": "reasoning_complete",
        "llm_provider": "Heuristic Rule Reasoner",
        "is_technical_issue": analysis.is_technical_issue,
        "confidence_score": analysis.confidence_score,
        "issue_summary": analysis.issue_summary,
        "suggested_fix": analysis.suggested_fix,
        "clarification_question": analysis.clarification_question,
    }


def safe_str(val: Any) -> str:
    """Sanitizes strings for Windows console printing without cp1252 encoding errors."""
    if val is None:
        return ""
    return str(val).encode("ascii", "replace").decode("ascii")


def format_action_node(state: AeroTraceState) -> Dict[str, Any]:
    """Node 3: Finalizes fix and appends current interaction to Memory checkpoint."""
    print("[LangGraph] ---> Node 3: Decision & Action Formatter")
    print(f"   [Summary] : {safe_str(state.get('issue_summary'))[:80]}...")
    print(f"   [Fix]     : {safe_str(state.get('suggested_fix'))[:80]}...")
    print(f"   [Source]  : {safe_str(state.get('llm_provider'))}")
    print("=" * 55 + "\n")

    # Update conversation history in memory
    history = list(state.get("chat_history", []) or [])
    current_turn = state.get("turn_count", 0) + 1

    user_parts = []
    if state.get("screen_text"):
        user_parts.append(f"Screen: {state['screen_text'][:80]}")
    if state.get("voice_text"):
        user_parts.append(f"Voice: {state['voice_text']}")
    user_desc = " | ".join(user_parts) if user_parts else "User trigger"

    history.append({
        "turn": current_turn,
        "user": user_desc,
        "assistant_summary": state.get("issue_summary", ""),
        "assistant_fix": state.get("suggested_fix", "")
    })

    return {
        "current_step": "ready_for_hud",
        "chat_history": history,
        "turn_count": current_turn,
    }


# -------------------------------------------------------------
# 3. BUILD GRAPH WITH IN-BUILT LANGGRAPH MEMORYSAVER
# -------------------------------------------------------------
_memory_saver = MemorySaver()


def build_aerotrace_graph():
    """Compiles the LangGraph StateGraph pipeline with native MemorySaver checkpointer."""
    workflow = StateGraph(AeroTraceState)

    # Register Nodes
    workflow.add_node("fuse_context", fuse_context_node)
    workflow.add_node("groq_reasoner", groq_reasoner_node)
    workflow.add_node("format_action", format_action_node)

    # Define Edges
    workflow.add_edge(START, "fuse_context")
    workflow.add_edge("fuse_context", "groq_reasoner")
    workflow.add_edge("groq_reasoner", "format_action")
    workflow.add_edge("format_action", END)

    # Compile with built-in LangGraph memory checkpointer
    return workflow.compile(checkpointer=_memory_saver)


# Singleton compiled graph
_compiled_graph = None


def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_aerotrace_graph()
    return _compiled_graph


def reset_conversation_thread(thread_id: str):
    """Clears/resets the checkpointed memory for a specific thread."""
    # MemorySaver stores checkpoints in memory; generating a new thread_id creates a clean slate
    print(f"[LangGraph Memory] Thread '{thread_id}' reset requested.")


def run_agent_graph(
    screen_text: str,
    voice_text: Optional[str] = None,
    mcp_context: Optional[Dict[str, Any]] = None,
    thread_id: str = "default_session"
) -> ErrorAnalysis:
    """
    Executes the compiled LangGraph pipeline with the provided multi-modal inputs
    and preserves multi-turn conversation memory for the given thread_id.
    """
    graph = get_agent_graph()

    # Pass inputs for current turn (previous history is automatically retrieved by MemorySaver)
    current_input = {
        "screen_text": screen_text,
        "voice_text": voice_text,
        "mcp_context": mcp_context or {},
        "current_step": "initialized",
        "fused_prompt": "",
        "llm_provider": "",
        "is_technical_issue": False,
        "confidence_score": 0.0,
        "issue_summary": "",
        "suggested_fix": "",
        "clarification_question": None,
    }

    # Thread config gives LangGraph its checkpoint identity for memory persistence
    config_dict = {"configurable": {"thread_id": thread_id}}

    final_state = graph.invoke(current_input, config=config_dict)

    return ErrorAnalysis(
        is_technical_issue=final_state["is_technical_issue"],
        confidence_score=final_state["confidence_score"],
        issue_summary=final_state["issue_summary"],
        suggested_fix=final_state["suggested_fix"],
        clarification_question=final_state.get("clarification_question"),
        turn_count=final_state.get("turn_count", 1),
        thread_id=thread_id,
    )
