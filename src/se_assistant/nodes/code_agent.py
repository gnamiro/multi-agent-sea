from __future__ import annotations
from typing import Dict, Any
import uuid
from se_assistant.state import TicketState, Hypothesis, CodeLocation

def code_agent(state: TicketState) -> Dict[str, Any]:
    last = state.tool_runs[-1] if state.tool_runs else None
    hyp = None

    if last and last.status == "fail":
        joined = (last.stderr_tail or "") + "\n" + (last.stdout_tail or "")
        if "test_apply_discount_rounds_up" in joined or "apply_discount" in joined:
            loc = CodeLocation(
                path="src/sandbox/pricing.py",
                start_line=1,
                end_line=999,
                reason="Failing test suggests rounding/truncation in apply_discount."
            )
            hyp = Hypothesis(
                id=str(uuid.uuid4())[:8],
                summary="apply_discount truncates instead of rounding; use round(x, 2).",
                locations=[loc],
                confidence=0.75
            )

    if hyp:
        return {
            "hypotheses": state.hypotheses + [hyp],
            "code_locations": state.code_locations + hyp.locations
        }
    return {}
