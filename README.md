# Multi-Agent Software Engineering Assistant (LangGraph)

⚠️ **Status: In Progress — Experimental Patch Agent**

This project is a multi-agent software engineering assistant built with **LangGraph**.
It simulates an automated code-fixing workflow that:

* Runs tests inside a controlled sandbox repository
* Analyzes failures
* Selects relevant source files
* Proposes patches
* Re-runs tests
* Produces a PR-style report

The system demonstrates advanced LangGraph concepts including:

* State management
* Conditional routing
* Iterative repair loops
* Error handling
* Multi-agent coordination
* Human-in-the-loop (HITL) safety gates

---

## 🎯 Goal of the Project

The goal is to build a collaborative multi-agent system that can:

1. Detect failing unit tests
2. Identify relevant source files
3. Generate patches automatically using an LLM
4. Validate fixes by re-running tests
5. Escalate to human review when unsafe or uncertain

The project focuses on orchestration and architecture rather than just code editing.

---

## 🏗 Architecture Overview

The system is built as a LangGraph workflow with the following nodes:

### 1️⃣ Test Agent

* Executes `pytest` inside a sandbox repo
* Captures structured test results
* Stores failure traces in shared state

### 2️⃣ File Selector Agent

* Analyzes pytest output
* Identifies relevant source files
* Filters out:

  * `tests/`
  * documentation files
  * sensitive paths
* Can operate deterministically (from stack traces) or via LLM reasoning

### 3️⃣ Patch Agent (LLM-based)

* Receives:

  * failing test output
  * read-only test files
  * selected source files
* Generates minimal diffs in structured JSON format
* Applies patch safely
* Enforces:

  * no test modification
  * no markdown fences
  * no sensitive file edits

⚠️ **Current limitation:**
The patch agent is still experimental and struggles with complex logic bugs (e.g., datetime edge cases). It works better on simple arithmetic errors.

### 4️⃣ Safety Gate

* Prevents modification of sensitive files
* Can trigger HITL if:

  * invalid JSON
  * unsafe modification attempt
  * ambiguous patch

### 5️⃣ Iterative Loop

If tests fail after patch:

```
test → file_select → patch → safety → test
```

The loop continues until:

* tests pass
* max iterations reached
* human review required

### 6️⃣ Synthesis Agent

Produces a final PR-style report including:

* Task description
* Patch diff
* Verification status
* Risk notes

---

## 🔁 Example Workflow

1. Sandbox repo contains intentionally buggy code.
2. `pytest -q` fails.
3. File selector identifies relevant `src/` file.
4. Patch agent proposes JSON updates.
5. Patch applied.
6. Tests re-run.
7. Final report generated.

---

## 🧠 Advanced Concepts Demonstrated

This project showcases:

### ✔ Shared Graph State

All agents read/write to a central structured state object.

### ✔ Conditional Routing

Edges depend on:

* test result
* safety gate
* HITL status

### ✔ Multi-Agent Collaboration

Agents specialize in:

* execution
* reasoning
* editing
* reporting
* safety validation

### ✔ Human-in-the-Loop (HITL)

If:

* LLM output invalid
* unsafe file selected
* patch cannot be parsed

→ system transitions to `stopped_for_review`.

---

## 📂 Project Structure

```
se_assistant/
  src/
    se_assistant/
      graph.py
      state.py
      nodes/
        test_agent.py
        file_selector_agent.py
        patch_agent_llm.py
        safety_agent.py
        synthesis_agent.py
  run.py

sandbox_repo/
  src/sandbox/
    simple_math.py
    date_utils.py
  tests/
```

---

## ⚙ Environment

* Python
* LangGraph
* LangChain
* Ollama (local LLM)
* pytest
* uv (package manager)

---

## ⚠ Current Limitations

* Patch agent is still under refinement.
* LLM struggles with:

  * datetime parsing edge cases
  * multi-branch logic
  * structured JSON consistency
* No advanced memory mechanism yet.
* No semantic diff ranking yet.

This project is actively being improved to:

* Add better failure compression
* Improve test-context grounding
* Stabilize JSON output parsing
* Improve patch quality evaluation

---

## 🚀 Roadmap

Planned improvements:

* Deterministic + LLM hybrid file selection
* Confidence-based patch scoring
* Patch ranking agent
* Self-reflection / critique agent
* Token-optimized failure summarization
* Parallel patch attempts
* LangSmith tracing integration
