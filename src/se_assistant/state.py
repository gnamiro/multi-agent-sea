from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

TaskType = Literal["bugfix", "refactor", "optimization", "docs"]
RunStatus = Literal["success", "fail", "timeout", "error"]
FinalStatus = Literal["completed", "completed_with_warnings", "stopped_for_review", "failed"]

class CodeLocation(BaseModel):
    path: str
    start_line: int
    end_line: int
    reason: str

class Hypothesis(BaseModel):
    id: str
    summary: str
    locations: List[CodeLocation] = Field(default_factory=list)
    confidence: float = 0.5

class Patch(BaseModel):
    patch_id: str
    summary: str
    diff_unified: str
    files_touched: List[str] = Field(default_factory=list)
    confidence: float = 0.5

class ToolRun(BaseModel):
    run_id: str
    run_type: Literal["install", "test", "lint", "typecheck"]
    command: str
    status: RunStatus
    exit_code: Optional[int] = None
    duration_sec: Optional[float] = None
    stdout_tail: Optional[str] = None
    stderr_tail: Optional[str] = None
    failures_parsed: List[Dict[str, Any]] = Field(default_factory=list)

class RepoMap(BaseModel):
    files: List[Dict[str, Any]] = Field(default_factory=list)   # path, language, size
    configs_found: List[str] = Field(default_factory=list)      # pyproject.toml, package.json, ...
    test_framework: Optional[str] = None                        # pytest, jest, ...
    entrypoints: List[str] = Field(default_factory=list)

class HITL(BaseModel):
    required: bool = False
    reason: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    human_decision: Optional[Dict[str, Any]] = None

class Iteration(BaseModel):
    count: int = 0
    max: int = 5
    last_route: Optional[str] = None
    stop_reason: Optional[str] = None

class Quality(BaseModel):
    overall_confidence: float = 0.5
    conflict_count: int = 0
    coverage_score: float = 0.0
    missing_verification_steps: int = 0

class TicketState(BaseModel):
    # identifiers
    run_id: str
    repo_ref: str              # local path to sandbox repo
    task_prompt: str
    task_type: TaskType = "bugfix"
    priority: Literal["standard", "rush"] = "standard"

    # settings
    timeout_sec: int = 30

    # shared context
    repo_map: RepoMap = Field(default_factory=RepoMap)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    code_locations: List[CodeLocation] = Field(default_factory=list)

    # agent outputs
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    patches: List[Patch] = Field(default_factory=list)
    tool_runs: List[ToolRun] = Field(default_factory=list)

    # safety & control
    risk_flags: List[str] = Field(default_factory=list)
    safety_ok: bool = True
    hitl: HITL = Field(default_factory=HITL)
    iteration: Iteration = Field(default_factory=Iteration)
    quality: Quality = Field(default_factory=Quality)

    # final
    final_report: Optional[str] = None
    final_status: Optional[FinalStatus] = None
