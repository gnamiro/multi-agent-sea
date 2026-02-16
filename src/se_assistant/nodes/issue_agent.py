from __future__ import annotations
from typing import Dict, Any
from se_assistant.state import TicketState

def issue_agent(state: TicketState) -> Dict[str, Any]:
    # For sandbox MVP, assume pytest exists and is the verification signal.
    state.assumptions.append("Use pytest -q as the primary verification command.")
    return {}
