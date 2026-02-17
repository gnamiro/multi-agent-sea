from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, conlist
import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from se_assistant.state import TicketState

class FileSelectionOut(BaseModel):
    files: conlist(str, min_length=1, max_length=5) = Field(
        description="Relative file paths to inspect/modify."
    )
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

def _allowed(p: str) -> bool:
    low = p.lower()
    low = p.lower().replace("\\", "/")
    if low.startswith("tests/") or low.startswith("/tests/"):
        return False
    if low.endswith(".md") or "readme" in low:
        return False
    if any(x in low for x in ["security", "secret", "token", "auth", ".env"]):
        return False
    return True
 
def extract_json(text: str) -> str:
    text = text.strip()
    # Remove code fences if any
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    # Try to extract first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def file_selector_agent(state: TicketState) -> dict:
    last_test = next((r for r in reversed(state.tool_runs) if r.run_type == "test"), None)
    pytest_out = ""
    if last_test:
        pytest_out = (last_test.stderr_tail or "") + "\n" + (last_test.stdout_tail or "")

    # Build a compact repo file list (paths only)
    repo_files = [f["path"] for f in state.repo_map.files] if state.repo_map and state.repo_map.files else []
    repo_files = [p for p in repo_files if p.lower().replace("\\","/").startswith("src/")]

    model = ChatOllama(model="qwen2.5:7b", temperature=0.0, timeout=60)


    prompt = ChatPromptTemplate.from_messages([
        ("system",
            "You are a build-fixing assistant. "
            "Given pytest output and a repository file list, select the smallest set of files "
            "most likely related to the failure.\n"
            "Rules:\n"
            "- DO NOT select test files under tests/.\n"
            "- DO NOT select sensitive files (paths containing security, secret, token, auth, .env).\n"
            "- DO NOT select documentation files (README, *.md).\n"
            "- Prefer source files under src/.\n"
            "- Return ONLY valid JSON matching this schema:\n"
            "{{"
            "\"files\": [\"path1\", \"path2\"], "
            "\"confidence\": 0.0, "
            "\"rationale\": \"...\""
            "}}\n"
        ),
        ("human",
         "PYTEST OUTPUT:\n{pytest_out}\n\n"
         "REPO FILES (paths):\n{repo_files}\n"
        )
    ])

    msg = (prompt | model).invoke({
        "pytest_out": pytest_out[:6000],
        "repo_files": "\n".join(repo_files[:2000])  # cap to avoid huge prompt
    })

    raw = msg.content.strip()
    obj = None
    for attempt in range(2):
        try:
            json_text = extract_json(raw)
            obj = json.loads(json_text)
            out = FileSelectionOut.model_validate(obj)
            break
        except Exception:
            if attempt == 0:
                # retry once with stricter instruction
                msg = (prompt | model).invoke({
                    "pytest_out": pytest_out[:6000] + "\n\nREMINDER: output JSON only.",
                    "repo_files": "\n".join(repo_files[:2000])
                })
                raw = msg.content.strip()
                continue
            state.hitl.required = True
            state.hitl.reason = "LLM file selection returned invalid JSON."
            state.final_status = "stopped_for_review"
            return {}
        
    files = [p for p in out.files if _allowed(p)]
    print(f"LLM selected files: {out.files} with confidence {out.confidence:.2f}. Allowed files after filtering: {files}")
    if not files:
        state.hitl.required = True
        state.hitl.reason = f"No files selected or all selected files were disallowed by rules. Rationale: {out.rationale}"
        state.final_status = "stopped_for_review"
        return {}

    return {
        "open_questions": state.open_questions + [f"File selection: {out.rationale} (conf={out.confidence:.2f})"],
        # store selected files in state for next node
        "selected_files": out.files,
    }
