from langgraph.graph import StateGraph, START, END
from se_assistant.state import TicketState

from se_assistant.nodes.repo_agent import repo_agent
from se_assistant.nodes.issue_agent import issue_agent
from se_assistant.nodes.test_agent import test_agent
from se_assistant.nodes.file_selector_agent import file_selector_agent
from se_assistant.nodes.patch_agent_llm import patch_agent_llm
from se_assistant.nodes.safety_agent import safety_agent
from se_assistant.nodes.synthesis_agent import synthesis_agent

def route_after_test(state: TicketState) -> str:
    last_test = next((r for r in reversed(state.tool_runs) if r.run_type == "test"), None)

    # If tests passed -> go to synthesis
    if last_test and last_test.exit_code == 0:
        state.final_status = "success"  # IMPORTANT: use a canonical value
        return "synthesis"

    # Tests failed -> continue agent loop (unless HITL or max iters)
    if state.iteration.count >= state.iteration.max:
        state.hitl.required = True
        state.hitl.reason = "Max iterations reached."
        state.final_status = "stopped_for_review"
        return "synthesis"

    return "file_select"


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
    g.add_node("file_select", file_selector_agent)
    g.add_node("patch", patch_agent_llm)
    g.add_node("safety", safety_agent)
    g.add_node("synthesis", synthesis_agent)

    g.add_edge(START, "repo")
    g.add_edge("repo", "issue")
    g.add_edge("issue", "test")

    g.add_conditional_edges("test", route_after_test, {
        "file_select": "file_select",
        "synthesis": "synthesis",
    })

    g.add_edge("file_select", "patch")
    g.add_edge("patch", "safety")

    g.add_conditional_edges("safety", route_after_safety, {
        "test": "test",
        "synthesis": "synthesis",
    })

    g.add_edge("synthesis", END)
    return g.compile()