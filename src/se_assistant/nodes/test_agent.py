from __future__ import annotations
from typing import Dict, Any
import uuid
from se_assistant.state import TicketState, ToolRun
from se_assistant.tools import run_cmd, tail

def parse_pytest_failures(stderr: str) -> list[dict]:
    # Minimal parser for MVP: just capture failing test name lines like:
    # FAILED tests/test_pricing.py::test_apply_discount_rounds_up - ...
    out = []
    for line in (stderr or "").splitlines():
        if line.startswith("FAILED "):
            out.append({"raw": line.strip()})
    return out

def test_agent(state: TicketState) -> Dict[str, Any]:
    cmd = "pytest -q"
    res = run_cmd(state.repo_ref, cmd, timeout_sec=state.timeout_sec)

    run = ToolRun(
        run_id=str(uuid.uuid4())[:8],
        run_type="test",
        command=cmd,
        status=res["status"],  # success/fail/timeout/error
        exit_code=res["exit_code"],
        duration_sec=res["duration_sec"],
        stdout_tail=tail(res["stdout"]),
        stderr_tail=tail(res["stderr"]),
        failures_parsed=parse_pytest_failures(res["stderr"]),
    )

    return {"tool_runs": state.tool_runs + [run]}
