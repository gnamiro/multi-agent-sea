from __future__ import annotations
from typing import Dict, Any, List
import uuid
import json

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from se_assistant.state import TicketState, Patch
from se_assistant.tools import read_text, write_text, unified_diff


# Keep it strict for the sandbox (you can relax later)
ALLOWED_PREFIXES = ("src/sandbox/", "src\\sandbox\\")
DISALLOWED_SUBSTR = ("tests/", "tests\\", "readme", ".md", ".rst", ".txt")
SENSITIVE_SUBSTR = ("security", "secret", "token", "auth", ".env")

def _norm(p: str) -> str:
    return p.replace("\\", "/")

def _is_allowed_path(path: str) -> bool:
    low = _norm(path.lower())
    if any(x in low for x in SENSITIVE_SUBSTR):
        return False
    if any(x in low for x in DISALLOWED_SUBSTR):
        return False
    return low.startswith("src/sandbox/")


def _strip_code_fences(s: str) -> str:
    if "```" in s:
        raise ValueError("LLM output contains markdown code fences.")
    return s


def _invoke_llm_json(model: ChatOllama, prompt: ChatPromptTemplate, payload: dict) -> dict:
    msg = (prompt | model).invoke(payload)
    raw = msg.content.strip()

    # Some models wrap JSON in extra text; try to extract first {...}
    if not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end+1]

    return json.loads(raw)

import re

def _extract_test_paths(pytest_text: str) -> List[str]:
    # grabs things like tests\test_date_utils.py:18
    paths = re.findall(r"(tests[\\/][\w\-/\\\.]+\.py)", pytest_text)
    # unique, keep order
    seen, out = set(), []
    for p in paths:
        p = p.strip()
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:2]  # cap

def _compact_failures(text:str, max_chars: int=2500) -> str:
    t = text.strip()

    marker = 'FAILURES'
    i = t.find(marker) 
    if i != -1: 
        t = t[i:] 
    return t[:max_chars]

def _best_pytest_text(last_test) -> str:
    if not last_test:
        return ""

    # Prefer full stdout/stderr if present, else tail
    stdout = (getattr(last_test, "stdout", "") or "").strip()
    stderr = (getattr(last_test, "stderr", "") or "").strip()
    if not (stdout or stderr):
        stdout = (getattr(last_test, "stdout_tail", "") or "").strip()
        stderr = (getattr(last_test, "stderr_tail", "") or "").strip()

    return (stdout + "\n" + stderr).strip()


def _format_failures_parsed(last_test, max_items: int = 12, max_chars: int = 2200) -> str:
    items = getattr(last_test, "failures_parsed", None) or []
    chunks = []
    for it in items[:max_items]:
        raw = (it.get("raw") if isinstance(it, dict) else str(it)) or ""
        raw = raw.strip()
        if raw:
            chunks.append(raw)
    text = "\n\n---\n\n".join(chunks).strip()
    return text[:max_chars]


def patch_agent_llm(state: TicketState) -> Dict[str, Any]:
    if state.hitl.required:
        return {}

    model = ChatOllama(model="qwen2.5:7b", temperature=0.0, timeout=60)


    last_test = next((r for r in reversed(state.tool_runs) if r.run_type == "test"), None)

    pytest_text = _best_pytest_text(last_test)
    print("DEBUG pytest_text length:", len(pytest_text))

    # The big compact chunk (FAILURES section)
    failures_compact = _compact_failures(pytest_text, max_chars=2500)

    # Even cleaner signal: the parsed failures (often includes assert lines)
    failures_parsed = _format_failures_parsed(last_test)

    run_info = ""
    if last_test:
        run_info = (
            f"COMMAND: {last_test.command}\n"
            f"STATUS: {last_test.status}\n"
            f"EXIT_CODE: {last_test.exit_code}\n"
            f"DURATION_SEC: {getattr(last_test, 'duration_sec', '')}\n"
        )
    test_paths = _extract_test_paths(pytest_text)
    test_blocks = []
    for tp in test_paths:
        try:
            test_blocks.append(f"=== READ-ONLY TEST: {tp} ===\n{read_text(state.repo_ref, tp)}\n")
        except FileNotFoundError:
            pass

    targets = state.selected_files or []
    if not targets:
        state.hitl.required = True
        state.hitl.reason = "No files selected for patching."
        state.final_status = "stopped_for_review"
        return {}

    # Enforce allowed paths at runtime (never trust the model)
    targets = [p for p in targets if _is_allowed_path(p)]
    if not targets:
        state.hitl.required = True
        state.hitl.reason = "Selected files were not allowed (tests/docs/sensitive)."
        state.final_status = "stopped_for_review"
        return {}

    file_blocks: List[str] = []
    for path in targets:
        try:
            file_blocks.append(f"=== {path} ===\n{read_text(state.repo_ref, path)}\n")
        except FileNotFoundError:
            continue

    prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You fix failing pytest tests by editing source files.\n"
        "STRICT RULES:\n"
        "- Only modify the provided SOURCE files.\n"
        "- Tests are READ-ONLY.\n"
        "- Do NOT modify tests/ or documentation files.\n"
        "- Make the smallest possible change (minimal diff).\n"
        "- Output MUST be valid JSON ONLY.\n"
        "- Return ONLY JSON with top-level key 'updates' (a list).\n"
        "- Each update: {{\'path\': string, \'content\': string}} where content is the FULL file.\n"
        "- If no change:{{\"updates\": []}}.\n"
        ),
        ("human",
        "TASK:\n{task}\n\n"
        "RUN INFO:\n{run_info}\n\n"
        "PYTEST FAILURES (FAILURES SECTION):\n{failures_compact}\n\n"
        "PYTEST FAILURES (PARSED KEY LINES):\n{failures_parsed}\n\n"
        "READ-ONLY TESTS:\n{tests}\n\n"
        "SOURCE FILES (you may modify only these):\n{files}\n"
        )
    ])
    print("Invoking LLM for patch generation...")
    print("TASK:", state.task_prompt)

    print("FAILURE CONTEXT:\n", failures_compact)
    print("PARSED FAILURES:\n", failures_parsed)
    print("READ-ONLY TESTS:\n", "\n".join(test_blocks[:8000]))
    print("SOURCE FILES:\n", "\n".join(file_blocks[:12000]))
    print("\n\n\n")
    payload = {
        "task": state.task_prompt,
        "run_info": run_info,
        "failures_compact": failures_compact,
        "failures_parsed": failures_parsed or "(none)",
        "tests": "\n".join(test_blocks)[:8000],
        "files": "\n".join(file_blocks)[:12000],
    }

    # Try once; if JSON fails or fences appear, retry once with stronger warning
    for attempt in range(2):
        try:
            obj = _invoke_llm_json(model, prompt, payload)
            updates = obj.get("updates", [])
            if not isinstance(updates, list):
                raise ValueError("updates must be a list")
            print(f"LLM returned {len(updates)} updates.")
            print("LLM updates preview:", updates[:2])  # show first 2 updates for debugging
            new_patches: List[Patch] = []
            for u in updates:
                path = _norm(u.get("path", "")).strip()
                content = u.get("content", "")
                if not path or not isinstance(content, str):
                    continue

                if not _is_allowed_path(path):
                    raise ValueError(f"LLM attempted to modify disallowed path: {path}")

                content = _strip_code_fences(content)
                # Also block the stray NO_CHANGE token appearing inside files
                if "NO_CHANGE" in content.strip().splitlines()[:3]:
                    raise ValueError("LLM inserted NO_CHANGE into file content.")

                old = read_text(state.repo_ref, path)
                # Normalize trailing newline
                new = content if content.endswith("\n") else content + "\n"
                if old == new:
                    print(f"\n\n No change for {path}, skipping patch. \n\n")
                    continue

                diff = unified_diff(old, new, path)
                print(f"\n\n diff for {path}:\n{diff}\n\n")
                write_text(state.repo_ref, path, new)

                new_patches.append(Patch(
                    patch_id=str(uuid.uuid4())[:8],
                    summary=f"LLM-generated fix for {path}",
                    diff_unified=diff,
                    files_touched=[path],
                    confidence=0.6,
                ))

            if not new_patches:
                return {}  # no changes

            return {"patches": state.patches + new_patches}

        except Exception as e:
            print(f"Error during LLM patch generation attempt {attempt+1}: {type(e).__name__}: {e}")
            if attempt == 0:
                # tighten payload and retry once
                payload["task"] = state.task_prompt + "\n\nREMINDER: Output JSON only. No markdown. No extra text."
                continue

            state.hitl.required = True
            state.hitl.reason = f"Patch generation failed/unsafe: {type(e).__name__}: {e}"
            state.final_status = "stopped_for_review"
            return {}
