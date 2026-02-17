from __future__ import annotations
import os, time, subprocess, difflib
from typing import Tuple, Optional, List, Dict, Any


def list_repo_files(repo_ref: str) -> List[str]:
    out = []
    for root, _, files in os.walk(repo_ref):
        if ".venv" in root or "__pycache__" in root:
            continue
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), repo_ref))
    return sorted(out)

def read_text(repo_ref: str, rel_path: str) -> str:
    path = os.path.join(repo_ref, rel_path)
    with open(path, "r", encoding="utf-8") as fp:
        return fp.read()

def write_text(repo_ref: str, rel_path: str, content: str) -> None:
    path = os.path.join(repo_ref, rel_path)
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)

def unified_diff(old: str, new: str, file_path: str) -> str:
    old_lines = old.splitlines(True)
    new_lines = new.splitlines(True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )
    return "".join(diff)

def run_cmd(
    cwd: str,
    cmd: str,
    timeout_sec: int = 30,
) -> Dict[str, Any]:
    start = time.time()
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        dur = time.time() - start
        return {
            "status": "success" if p.returncode == 0 else "fail",
            "exit_code": p.returncode,
            "duration_sec": dur,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    except subprocess.TimeoutExpired as e:
        dur = time.time() - start
        return {
            "status": "timeout",
            "exit_code": None,
            "duration_sec": dur,
            "stdout": (e.stdout or ""),
            "stderr": (e.stderr or "") + "\nTIMEOUT",
        }
    except Exception as e:
        dur = time.time() - start
        return {
            "status": "error",
            "exit_code": None,
            "duration_sec": dur,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
        }

def tail(s: str, n: int = 20000) -> str:
    if not s:
        return ""
    return s[-n:]
