from __future__ import annotations
import uuid
from se_assistant.graph import build_graph
from se_assistant.state import TicketState

if __name__ == "__main__":
    # IMPORTANT: set this to your sandbox repo folder path
    SANDBOX_PATH = r"C:\Users\naeem\Desktop\LangGraph\Multi-Agent_Software_Engineering_Assistant\sandbox_repo"
    print("SANDBOX_PATH =", SANDBOX_PATH)

    app = build_graph()

    state = TicketState(
        run_id=str(uuid.uuid4())[:8],
        repo_ref=SANDBOX_PATH,
        task_prompt="Fix failing pytest tests (pricing rounding bug).",
        task_type="bugfix",
        priority="standard",
        timeout_sec=30,
    )

    final = app.invoke(state)
    print(final.get("final_report"))
    print("\nFINAL STATUS:", final.get("final_status") or "completed")
