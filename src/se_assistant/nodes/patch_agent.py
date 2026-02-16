from __future__ import annotations
from typing import Dict, Any
import uuid
from se_assistant.state import TicketState, Patch
from se_assistant.tools import read_text, write_text, unified_diff

def patch_agent(state: TicketState) -> Dict[str, Any]:
    # MVP: implement the known fix for sandbox pricing.py
    target = "src/sandbox/pricing.py"
    old = read_text(state.repo_ref, target)
    print(f"Current content of {target}:\n{old}\n---\n")
    if "int(discounted * 100" not in old:
        # Nothing to patch (or already fixed)
        return {}

    new = old.replace(
        "return float(int(discounted * 100) / 100)",
        "return round(discounted, 2)"
    )

    diff = unified_diff(old, new, target)

    # Apply
    write_text(state.repo_ref, target, new)

    p = Patch(
        patch_id=str(uuid.uuid4())[:8],
        summary="Fix rounding bug in apply_discount by using round(..., 2) instead of truncation.",
        diff_unified=diff,
        files_touched=[target],
        confidence=0.8
    )

    return {"patches": state.patches + [p]}
