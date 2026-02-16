from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from se_assistant.state import TicketState

from se_assistant.nodes.repo_agent import repo_agent
from se_assistant.nodes.issue_agent import issue_agent
from se_assistant.nodes.test_agent import test_agent
from se_assistant.nodes.code_agent import code_agent
from se_assistant.nodes.patch_agent import patch_agent
from se_assistant.nodes.safety_agent import safety_agent
from se_assistant.nodes.synthesis_agent import synthesis_agent

def route_after_test(state: TicketState) -> str:
    # increment iteration after each test run
    state.iteration.count += 1

    last = state.tool_runs[-1] if state.tool_runs else None
    if last and last.status == "success":
        return "synthesis"

    # stop if too many loops
    if state.iteration.count >= state.iteration.max:
        state.hitl.required = True
        state.hitl.reason = "Max iterations reached without passing tests."
        state.final_status = "stopped_for_review"
        return "synthesis"

    # fail/timeout/error → analyze and patch
    return "code"

def route_after_safety(state: TicketState) -> str:
    if state.hitl.required:
        state.final_status = "stopped_for_review"
        return "synthesis"
    return "test"

def build_graph():
    g = StateGraph(TicketState)

    g.add_node("repo", repo_agent)
    g.add_node("issue", issue_agent)
    g.add_node("test", test_agent)
    g.add_node("code", code_agent)
    g.add_node("patch", patch_agent)
    g.add_node("safety", safety_agent)
    g.add_node("synthesis", synthesis_agent)

    g.add_edge(START, "repo")
    g.add_edge("repo", "issue")
    g.add_edge("issue", "test")

    g.add_conditional_edges("test", route_after_test, {
        "code": "code",
        "synthesis": "synthesis",
    })

    g.add_edge("code", "patch")
    g.add_edge("patch", "safety")

    g.add_conditional_edges("safety", route_after_safety, {
        "test": "test",
        "synthesis": "synthesis",
    })

    g.add_edge("synthesis", END)
    return g.compile()
