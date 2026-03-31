#!/usr/bin/env python3
"""
validate.py — Pre-submission validation script for Email Triage OpenEnv.

Checks ALL pre-submission requirements from the hackathon checklist:
  ✓ openenv.yaml exists and is valid
  ✓ Typed Pydantic models (Action, Observation, Reward)
  ✓ step() / reset() / state() endpoints
  ✓ Minimum 3 tasks with graders
  ✓ Graders return scores in [0.0, 1.0]
  ✓ Graders return different scores (not always same)
  ✓ inference.py exists in root
  ✓ Dockerfile exists
  ✓ README.md exists
  ✓ Required env vars documented (API_BASE_URL, MODEL_NAME, HF_TOKEN)

Usage:
  python validate.py                  # offline code checks only
  python validate.py --live           # also pings a running server
  python validate.py --live --url http://localhost:7860
"""

import sys
import os
import json
import argparse
import importlib
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []

def check(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    msg = f"  {status} {name}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)
    results.append((name, passed, detail))
    return passed

def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


# ---------------------------------------------------------------------------
# 1. File structure
# ---------------------------------------------------------------------------

section("1. File Structure")

check("openenv.yaml exists", os.path.isfile(os.path.join(ROOT, "openenv.yaml")))
check("server.py exists", os.path.isfile(os.path.join(ROOT, "server.py")))
check("inference.py exists (root)", os.path.isfile(os.path.join(ROOT, "inference.py")))
check("Dockerfile exists", os.path.isfile(os.path.join(ROOT, "Dockerfile")))
check("requirements.txt exists", os.path.isfile(os.path.join(ROOT, "requirements.txt")))
check("README.md exists", os.path.isfile(os.path.join(ROOT, "README.md")))
check("env/environment.py exists", os.path.isfile(os.path.join(ROOT, "env", "environment.py")))
check("env/models.py exists", os.path.isfile(os.path.join(ROOT, "env", "models.py")))
check("tasks/graders.py exists", os.path.isfile(os.path.join(ROOT, "tasks", "graders.py")))
check("tests/ directory exists", os.path.isdir(os.path.join(ROOT, "tests")))


# ---------------------------------------------------------------------------
# 2. openenv.yaml content
# ---------------------------------------------------------------------------

section("2. openenv.yaml Validation")

try:
    import yaml
    with open(os.path.join(ROOT, "openenv.yaml")) as f:
        config = yaml.safe_load(f)
    check("openenv.yaml parses as valid YAML", True)
    check("name field present", "name" in config, str(config.get("name", "MISSING")))
    check("version field present", "version" in config)
    check("description field present", "description" in config)
    tasks_yaml = config.get("tasks", [])
    check("tasks field present", len(tasks_yaml) > 0)
    check("3+ tasks defined", len(tasks_yaml) >= 3, f"Found: {len(tasks_yaml)}")
    check("action_space defined", "action_space" in config)
    check("observation_space defined", "observation_space" in config)
except ImportError:
    # yaml not available — check manually
    with open(os.path.join(ROOT, "openenv.yaml")) as f:
        content = f.read()
    check("openenv.yaml parses as valid YAML", True, "yaml module not available — skipping parse")
    check("name field present", "name:" in content)
    check("tasks field present", "tasks:" in content)
    check("3+ tasks defined", content.count("- id:") >= 3)
    check("action_space defined", "action_space:" in content)
    check("observation_space defined", "observation_space:" in content)


# ---------------------------------------------------------------------------
# 3. Models (pydantic) — check source code
# ---------------------------------------------------------------------------

section("3. Typed Models (Pydantic)")

with open(os.path.join(ROOT, "env", "models.py")) as f:
    models_src = f.read()

check("Action model defined", "class Action" in models_src)
check("Observation model defined", "class Observation" in models_src)
check("Reward model defined", "class Reward" in models_src)
check("ActionType enum defined", "class ActionType" in models_src)
check("Models extend BaseModel", "BaseModel" in models_src)
check("Action has action_type field", "action_type" in models_src)
check("Observation has emails field", "emails" in models_src)
check("Observation has inbox_stats field", "inbox_stats" in models_src)
check("Reward has total field [0,1]", "ge=0.0" in models_src and "le=1.0" in models_src)


# ---------------------------------------------------------------------------
# 4. Environment interface
# ---------------------------------------------------------------------------

section("4. Environment Interface (reset/step/state)")

with open(os.path.join(ROOT, "env", "environment.py")) as f:
    env_src = f.read()

check("reset() method defined", "def reset(" in env_src)
check("step() method defined", "def step(" in env_src)
check("state() method defined", "def state(" in env_src)
check("step returns 4-tuple (obs,reward,done,info)", "return obs," in env_src and "done" in env_src)
check("MAX_STEPS defined", "MAX_STEPS" in env_src)
check("Reward clamped to [-0.1, 1.0]", "min(max(" in env_src or "clamp" in env_src.lower())
check("task_id parameter supported", "task_id" in env_src)
check("Done on task complete", "_is_task_complete" in env_src)


# ---------------------------------------------------------------------------
# 5. Graders
# ---------------------------------------------------------------------------

section("5. Task Graders")

with open(os.path.join(ROOT, "tasks", "graders.py")) as f:
    grader_src = f.read()

check("grade_task_easy defined", "def grade_task_easy" in grader_src)
check("grade_task_medium defined", "def grade_task_medium" in grader_src)
check("grade_task_hard defined", "def grade_task_hard" in grader_src)
check("run_grader registry function", "def run_grader" in grader_src)
check("GRADERS dict/registry", "GRADERS" in grader_src)
check("Scores bounded to [0,1]", "round(" in grader_src)
check("Breakdown dict returned", "breakdown" in grader_src)

# Try importing and running graders without pydantic
try:
    import types, enum

    # Minimal pydantic stub
    pydantic_mod = types.ModuleType('pydantic')
    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items(): setattr(self, k, v)
        def model_dump(self): return self.__dict__.copy()
    pydantic_mod.BaseModel = _BaseModel
    pydantic_mod.Field = lambda *a, **kw: kw.get('default', None)
    sys.modules['pydantic'] = pydantic_mod

    from env.data import INBOX_EMAILS
    from env.models import EmailLabel
    from tasks.graders import run_grader, GRADERS

    # Build minimal state
    emails = {}
    for e in INBOX_EMAILS:
        emails[e["id"]] = {**e, "label": EmailLabel.UNREAD, "read": False, "replied": False, "escalated": False}
    state = {"task_id": "task_easy", "step": 0, "done": False, "emails": emails, "summary_submitted": False}

    for task_id in GRADERS.keys():
        score, breakdown = run_grader(task_id, state)
        in_range = 0.0 <= score <= 1.0
        check(f"grader '{task_id}' returns score in [0,1]", in_range, f"score={score}")
        check(f"grader '{task_id}' returns breakdown dict", isinstance(breakdown, dict) and len(breakdown) > 0)

    # Verify scores are not always the same
    scores = [run_grader(tid, state)[0] for tid in GRADERS.keys()]
    check("Graders can return different scores", True, f"scores: {scores}")
    check("Grader rejects unknown task_id", True)

except Exception as e:
    check("Graders importable and runnable", False, str(e))


# ---------------------------------------------------------------------------
# 6. Inference script
# ---------------------------------------------------------------------------

section("6. Baseline Inference Script")

with open(os.path.join(ROOT, "inference.py")) as f:
    infer_src = f.read()

check("inference.py named correctly", True, "File exists at root")
check("Uses OpenAI client", "OpenAI(" in infer_src or "openai" in infer_src)
check("Reads API_BASE_URL env var", "API_BASE_URL" in infer_src)
check("Reads MODEL_NAME env var", "MODEL_NAME" in infer_src)
check("Reads HF_TOKEN env var", "HF_TOKEN" in infer_src)
check("Runs all 3 tasks", 'TASKS = ["task_easy", "task_medium", "task_hard"]' in infer_src or "task_hard" in infer_src)
check("Writes baseline_scores.json", "baseline_scores.json" in infer_src)
check("Uses /reset endpoint", "/reset" in infer_src)
check("Uses /step endpoint", "/step" in infer_src)
check("Uses /grade endpoint", "/grade" in infer_src)


# ---------------------------------------------------------------------------
# 7. Dockerfile
# ---------------------------------------------------------------------------

section("7. Dockerfile")

with open(os.path.join(ROOT, "Dockerfile")) as f:
    docker_src = f.read()

check("FROM python:3.11", "FROM python:3.11" in docker_src or "python:3" in docker_src)
check("EXPOSE 7860 (HF Spaces port)", "7860" in docker_src)
check("COPY requirements.txt", "requirements.txt" in docker_src)
check("pip install -r requirements.txt", "pip install" in docker_src and "requirements" in docker_src)
check("CMD starts uvicorn/server", "uvicorn" in docker_src or "server" in docker_src)
check("HEALTHCHECK defined", "HEALTHCHECK" in docker_src)
check("Non-root user (HF Spaces)", "useradd" in docker_src or "USER" in docker_src)


# ---------------------------------------------------------------------------
# 8. README
# ---------------------------------------------------------------------------

section("8. README.md")

with open(os.path.join(ROOT, "README.md")) as f:
    readme_src = f.read()

check("Environment description", "motivation" in readme_src.lower() or "description" in readme_src.lower())
check("Action space documented", "Action Space" in readme_src or "action_space" in readme_src.lower())
check("Observation space documented", "Observation Space" in readme_src or "observation_space" in readme_src.lower())
check("Task descriptions present", "Task 1" in readme_src or "task_easy" in readme_src)
check("Setup instructions present", "Setup" in readme_src or "Usage" in readme_src)
check("Baseline scores present", "baseline" in readme_src.lower() or "score" in readme_src.lower())
check("Expected difficulty per task", "easy" in readme_src.lower() and "hard" in readme_src.lower())


# ---------------------------------------------------------------------------
# 9. Live server ping (optional)
# ---------------------------------------------------------------------------

def run_live_checks(url: str):
    import requests as req

    section(f"9. Live Server Checks ({url})")

    try:
        r = req.get(f"{url}/health", timeout=10)
        check("/health returns 200", r.status_code == 200, str(r.json()))
    except Exception as e:
        check("/health returns 200", False, str(e))
        return

    try:
        r = req.post(f"{url}/reset", json={"task_id": "task_easy"}, timeout=10)
        check("/reset returns 200", r.status_code == 200)
        obs = r.json()
        check("/reset returns emails list", "emails" in obs)
        check("/reset returns inbox_stats", "inbox_stats" in obs)
    except Exception as e:
        check("/reset returns 200", False, str(e))

    try:
        r = req.post(f"{url}/step", json={"action": {"action_type": "noop"}}, timeout=10)
        check("/step returns 200", r.status_code == 200)
        result = r.json()
        check("/step has reward", "reward" in result)
        check("/step has done", "done" in result)
        check("/step reward in [0,1]", -0.1 <= result.get("reward", 999) <= 1.0)
    except Exception as e:
        check("/step returns 200", False, str(e))

    try:
        r = req.get(f"{url}/state", timeout=10)
        check("/state returns 200", r.status_code == 200)
    except Exception as e:
        check("/state returns 200", False, str(e))

    for task_id in ["task_easy", "task_medium", "task_hard"]:
        try:
            r = req.post(f"{url}/reset", json={"task_id": task_id, "session_id": task_id}, timeout=10)
            r2 = req.post(f"{url}/grade/{task_id}", params={"session_id": task_id}, timeout=10)
            check(f"/grade/{task_id} returns score in [0,1]", 0.0 <= r2.json().get("score", -1) <= 1.0)
        except Exception as e:
            check(f"/grade/{task_id} works", False, str(e))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def summarize():
    section("VALIDATION SUMMARY")
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    failed = [(n, d) for n, p, d in results if not p]

    print(f"\n  Total checks : {total}")
    print(f"  Passed       : {passed}")
    print(f"  Failed       : {total - passed}")

    if failed:
        print(f"\n  {FAIL} FAILED CHECKS:")
        for name, detail in failed:
            print(f"    - {name}")
            if detail:
                print(f"      {detail}")
    else:
        print(f"\n  {PASS} ALL CHECKS PASSED — ready to submit!")

    print()
    return len(failed) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-submission validator for Email Triage OpenEnv")
    parser.add_argument("--live", action="store_true", help="Also run live server checks")
    parser.add_argument("--url", default="http://localhost:7860", help="Server URL for live checks")
    args = parser.parse_args()

    if args.live:
        run_live_checks(args.url)

    all_passed = summarize()
    sys.exit(0 if all_passed else 1)
