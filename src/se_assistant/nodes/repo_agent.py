from __future__ import annotations
from typing import Dict, Any
import os
from se_assistant.state import TicketState, RepoMap
from se_assistant.tools import list_repo_files

def repo_agent(state: TicketState) -> Dict[str, Any]:
    files = list_repo_files(state.repo_ref)
    configs = [f for f in files if f in ("pyproject.toml", "package.json", "requirements.txt")]
    test_framework = "pytest" if "pyproject.toml" in configs else None

    repo_map = RepoMap(
        files=[{"path": f} for f in files],
        configs_found=configs,
        test_framework=test_framework,
        entrypoints=[],
    )
    return {"repo_map": repo_map}
