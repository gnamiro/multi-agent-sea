from __future__ import annotations
import uuid
from se_assistant.graph import build_graph
from se_assistant.state import TicketState
from pprint import pprint

def safe_get(obj, name, default=None):
    # Works for dicts and objects
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

if __name__ == "__main__":
    # IMPORTANT: set this to your sandbox repo folder path
    SANDBOX_PATH = r"C:\Users\naeem\Desktop\LangGraph\Multi-Agent_Software_Engineering_Assistant\sandbox_repo"

    app = build_graph()

    state = TicketState(
        run_id=str(uuid.uuid4())[:8],
        repo_ref=SANDBOX_PATH,
        task_prompt="Fix failing pytest tests.",
        task_type="bugfix",
        priority="standard",
        timeout_sec=30,
    )

    print("Starting graph...\n")

    final = None
    for state_snapshot in app.stream(state, stream_mode="values"):
        print("---- step ----")

        patches = safe_get(state_snapshot, "patches", []) or []

        hitl = safe_get(state_snapshot, "hitl", None)
        if hitl is not None:
            print("hitl_required:", safe_get(hitl, "required", False))
            reason = safe_get(hitl, "reason", None)
            if reason:
                print("hitl_reason:", reason)
        else:
            print("hitl_required:", False)

        print("selected_files:", safe_get(state_snapshot, "selected_files", None))

        tool_runs = safe_get(state_snapshot, "tool_runs", []) or []
        if tool_runs:
            last = tool_runs[-1]
            print("last_run:", safe_get(last, "run_type", None),
                safe_get(last, "status", None),
                safe_get(last, "exit_code", None))

        final = state_snapshot

    print("\nDONE")
    print(final.get("final_report"))
