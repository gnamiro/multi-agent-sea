from __future__ import annotations
from typing import Dict, Any
import uuid
from se_assistant.state import TicketState, ToolRun
from se_assistant.tools import run_cmd, tail
import sys
from pathlib import Path

def parse_pytest_failures(stdout: str, stderr: str) -> list[dict]:
    text = (stdout or "") + "\n" + (stderr or "")
    lines = text.splitlines()

    out = []
    for i, line in enumerate(lines):
        if "FAILED" in line or "E   ValueError" in line or "AssertionError" in line:
            start = max(0, i - 3)
            end = min(len(lines), i + 6)
            out.append({"raw": "\n".join(lines[start:end]).strip()})
    return out[:5]



def test_agent(state: TicketState) -> Dict[str, Any]:
    
    repo = Path(state.repo_ref)
    py = repo / ".venv" / "Scripts" / "python.exe"
    cmd = f'"{py}" -m pytest -q'
    res = run_cmd(state.repo_ref, cmd, timeout_sec=state.timeout_sec)
    print("TEST STDOUT TAIL:", tail(res.get("stdout", ""), 1000))
    # print("TEST STDERR TAIL:", tail(res.get("stderr", "")), file=sys.stderr)
    print(" \n\n\n")

    run = ToolRun(
        run_id=str(uuid.uuid4())[:8],
        run_type="test",
        command=cmd,
        status=res["status"],  # success/fail/timeout/error
        exit_code=res["exit_code"],
        duration_sec=res["duration_sec"],
        stdout_tail=tail(res["stdout"]),
        stderr_tail=tail(res["stderr"]),
        failures_parsed=parse_pytest_failures(res.get("stdout", ""), res.get("stderr", "")),
    )

    return {"tool_runs": state.tool_runs + [run]}
