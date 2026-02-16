from __future__ import annotations
from typing import Dict, Any
from se_assistant.state import TicketState

def synthesis_agent(state: TicketState) -> Dict[str, Any]:
    last_test = next((r for r in reversed(state.tool_runs) if r.run_type == "test"), None)

    lines = []
    lines.append("# PR Report")
    lines.append("")
    lines.append(f"**Task:** {state.task_prompt}")
    lines.append("")
    if state.hypotheses:
        lines.append("## Diagnosis")
        for h in state.hypotheses[-2:]:
            lines.append(f"- {h.summary} (confidence={h.confidence:.2f})")
            for loc in h.locations:
                lines.append(f"  - Location: `{loc.path}` ({loc.reason})")
        lines.append("")
    if state.patches:
        lines.append("## Patch")
        for p in state.patches[-2:]:
            lines.append(f"- {p.summary} (confidence={p.confidence:.2f})")
            lines.append("```diff")
            lines.append(p.diff_unified.strip()[:3000])
            lines.append("```")
        lines.append("")
    lines.append("## Verification")
    if last_test:
        lines.append(f"- Command: `{last_test.command}`")
        lines.append(f"- Status: `{last_test.status}` (exit_code={last_test.exit_code})")
        if last_test.status != "success":
            lines.append("- Failures:")
            for f in last_test.failures_parsed:
                lines.append(f"  - {f.get('raw')}")
    else:
        lines.append("- Tests were not executed.")
    lines.append("")
    lines.append("## Notes / Risks")
    if not state.safety_ok:
        lines.append("- Safety gate triggered; requires human approval.")
    else:
        lines.append("- No safety flags triggered in this run.")

    return {"final_report": "\n".join(lines)}
