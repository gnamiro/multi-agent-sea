from __future__ import annotations
from typing import Dict, Any
from se_assistant.state import TicketState

SENSITIVE_HINTS = ("security.py", ".env", "secret", "token", "auth")

def safety_agent(state: TicketState) -> Dict[str, Any]:
    # If any patch touches sensitive files -> require HITL
    touched = set()
    for p in state.patches:
        for f in p.files_touched:
            touched.add(f.lower())

    for f in touched:
        if any(h in f for h in SENSITIVE_HINTS):
            return {
                "safety_ok": False,
                "risk_flags": state.risk_flags + ["sensitive_file_touched"],
                "hitl": {
                    "required": True,
                    "reason": f"Patch touches sensitive file: {f}",
                    "payload": {"files_touched": list(touched)}
                }
            }
    return {"safety_ok": True}
